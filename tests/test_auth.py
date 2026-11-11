"""Sign-in, roles, account lockout, session timeouts and user management."""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models import Employee, User
from app.services.user_service import UserValidationError, deactivate_user
from conftest import TEST_CSRF_TOKEN, TEST_PASSWORD, make_user, sign_in_as

GOOD_PASSWORD = "a-long-enough-pass"


def login(client, username="admin", password=TEST_PASSWORD, **kwargs):
    return client.post(f"/login{kwargs.pop('query', '')}", data={"username": username, "password": password}, **kwargs)


def get_user(app, username) -> User:
    with app.app_context():
        user = db.session.query(User).filter_by(username=username).one()
        db.session.expunge(user)
        return user


# ---------- the access gate ----------

@pytest.mark.parametrize("path", ["/", "/employees", "/employees/new", "/recognition/", "/users"])
def test_signed_out_visitors_are_sent_to_sign_in(app, anon_client, path):
    make_user(app)
    response = anon_client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?next=")


def test_signed_out_javascript_requests_get_401_json(app, anon_client):
    make_user(app)
    response = anon_client.post("/recognition/check-in", headers={"Accept": "application/json"})
    assert response.status_code == 401
    assert "sign in" in response.get_json()["error"].lower()


def test_signed_out_form_posts_change_nothing(app, anon_client):
    make_user(app)
    response = anon_client.post("/employees/new", data={"employee_code": "E1", "full_name": "X"})
    assert response.status_code == 401
    with app.app_context():
        assert db.session.query(Employee).count() == 0


def test_css_and_js_load_without_signing_in(app, anon_client):
    assert anon_client.get("/static/css/style.css").status_code == 200


# ---------- first-time setup ----------

def test_without_any_user_sign_in_leads_to_setup(anon_client):
    assert anon_client.get("/login").headers["Location"] == "/setup"
    assert anon_client.get("/").status_code == 302


def test_setup_creates_an_admin_and_signs_in(app, anon_client):
    response = anon_client.post("/setup", data={"username": "Owner", "password": GOOD_PASSWORD,
                                                "confirm_password": GOOD_PASSWORD})
    assert response.status_code == 302 and response.headers["Location"] == "/"
    owner = get_user(app, "owner")  # usernames are stored in lowercase
    assert owner.role == "admin"
    assert anon_client.get("/").status_code == 200


def test_setup_disappears_once_a_user_exists(app, anon_client):
    make_user(app)
    assert anon_client.get("/setup").headers["Location"] == "/login"
    anon_client.post("/setup", data={"username": "intruder", "password": GOOD_PASSWORD,
                                     "confirm_password": GOOD_PASSWORD})
    with app.app_context():
        assert db.session.query(User).filter_by(username="intruder").count() == 0


def test_setup_is_refused_from_another_computer(anon_client):
    response = anon_client.get("/setup", environ_base={"REMOTE_ADDR": "192.168.1.50"})
    assert response.status_code == 403


def test_setup_rejects_a_weak_password(app, anon_client):
    response = anon_client.post("/setup", data={"username": "owner", "password": "short",
                                                "confirm_password": "short"})
    assert response.status_code == 200 and b"at least 10 characters" in response.data
    with app.app_context():
        assert db.session.query(User).count() == 0


# ---------- signing in ----------

def test_password_is_stored_only_as_a_hash(app, anon_client):
    anon_client.post("/setup", data={"username": "owner", "password": GOOD_PASSWORD,
                                     "confirm_password": GOOD_PASSWORD})
    stored = get_user(app, "owner").password_hash
    assert GOOD_PASSWORD not in stored and stored.startswith("scrypt:")


def test_correct_password_signs_in_and_follows_a_safe_next(app, anon_client):
    make_user(app)
    response = login(anon_client, query="?next=/employees")
    assert response.status_code == 302 and response.headers["Location"] == "/employees"
    assert anon_client.get("/employees").status_code == 200


@pytest.mark.parametrize("target", ["https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)"],
                         ids=["absolute", "scheme-relative", "backslash", "javascript"])
def test_next_never_redirects_to_another_site(app, anon_client, target):
    make_user(app)
    response = login(anon_client, query_string={"next": target})
    assert response.status_code == 302 and response.headers["Location"] == "/"


def test_wrong_password_and_unknown_user_get_the_same_message(app, anon_client):
    make_user(app)
    wrong = login(anon_client, password="not-the-password")
    unknown = login(anon_client, username="nobody")
    assert wrong.status_code == unknown.status_code == 401
    assert b"Incorrect username or password." in wrong.data
    assert b"Incorrect username or password." in unknown.data
    assert anon_client.get("/").status_code == 302  # still signed out


def test_sign_in_form_needs_a_csrf_token(app, anon_client):
    make_user(app)
    response = login(anon_client, csrf_token=None)
    assert response.status_code == 400


def test_signing_in_starts_a_fresh_session(app, anon_client):
    make_user(app)
    with anon_client.session_transaction() as session:
        session["planted_by_attacker"] = "x"
    login(anon_client)
    with anon_client.session_transaction() as session:
        assert "planted_by_attacker" not in session
        assert session.get("csrf_token") != TEST_CSRF_TOKEN or "csrf_token" not in session


def test_disabled_account_cannot_sign_in(app, anon_client):
    user_id = make_user(app)
    with app.app_context():
        db.session.get(User, user_id).is_active = False
        db.session.commit()
    response = login(anon_client)
    assert response.status_code == 401 and b"disabled" in response.data


# ---------- lockout ----------

def test_account_locks_after_five_wrong_passwords(app, anon_client):
    make_user(app)
    for _ in range(4):
        assert b"Incorrect username or password." in login(anon_client, password="wrong-guess").data
    fifth = login(anon_client, password="wrong-guess")
    assert b"locked for 15 minutes" in fifth.data

    correct_while_locked = login(anon_client)  # even the right password is refused now
    assert correct_while_locked.status_code == 401 and b"locked" in correct_while_locked.data
    assert get_user(app, "admin").locked_now()


def test_lock_expires_by_itself(app, anon_client):
    user_id = make_user(app)
    with app.app_context():
        db.session.get(User, user_id).locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
    assert login(anon_client).status_code == 302


def test_successful_sign_in_resets_the_failure_count(app, anon_client):
    make_user(app)
    for _ in range(4):
        login(anon_client, password="wrong-guess")
    login(anon_client)
    assert get_user(app, "admin").failed_login_count == 0


def test_admin_can_unlock_an_account(app, client):
    locked_id = make_user(app, "clerk", "kiosk")
    with app.app_context():
        db.session.get(User, locked_id).locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        db.session.commit()
    assert b"Locked" in client.get("/users").data
    client.post(f"/users/{locked_id}/unlock")
    assert not get_user(app, "clerk").locked_now()


# ---------- signing out and session timeouts ----------

def test_sign_out_ends_the_session(client):
    response = client.post("/logout")
    assert response.headers["Location"] == "/login"
    assert client.get("/").status_code == 302


def test_sign_out_needs_post_and_a_csrf_token(client):
    assert client.get("/logout").status_code == 405
    assert client.post("/logout", csrf_token=None).status_code == 400
    assert client.get("/").status_code == 200  # still signed in


def _age_session(client, *, idle_seconds=0, login_seconds_ago=0):
    now = int(time.time())
    with client.session_transaction() as session:
        session["last_seen"] = now - idle_seconds
        session["login_at"] = now - max(login_seconds_ago, idle_seconds)


def test_idle_admin_session_expires_after_30_minutes(client):
    _age_session(client, idle_seconds=31 * 60)
    response = client.get("/employees")
    assert response.status_code == 302 and response.headers["Location"].startswith("/login")
    assert b"session has expired" in client.get(response.headers["Location"]).data


def test_active_use_keeps_the_session_alive(client):
    _age_session(client, idle_seconds=29 * 60)
    assert client.get("/").status_code == 200


def test_kiosk_session_survives_a_quiet_hour(kiosk_client):
    _age_session(kiosk_client, idle_seconds=60 * 60)
    assert kiosk_client.get("/recognition/").status_code == 200


def test_every_session_ends_after_the_maximum_lifetime(client):
    _age_session(client, login_seconds_ago=13 * 3600)
    assert client.get("/").status_code == 302


def test_disabling_a_user_ends_their_session_immediately(app, kiosk_client):
    assert kiosk_client.get("/recognition/").status_code == 200
    with app.app_context():
        db.session.query(User).filter_by(username="kiosk").one().is_active = False
        db.session.commit()
    assert kiosk_client.get("/recognition/").status_code == 302


# ---------- roles ----------

def test_kiosk_can_open_check_in_without_admin_links(kiosk_client):
    page = kiosk_client.get("/recognition/")
    assert page.status_code == 200
    assert b'href="/employees"' not in page.data and b'href="/users"' not in page.data


@pytest.mark.parametrize("path", ["/", "/employees", "/employees/new", "/users", "/users/new"])
def test_kiosk_is_sent_back_to_check_in_from_admin_pages(kiosk_client, path):
    response = kiosk_client.get(path)
    assert response.status_code == 302 and response.headers["Location"] == "/recognition/"


def test_kiosk_cannot_change_data(app, kiosk_client):
    response = kiosk_client.post("/employees/new", data={"employee_code": "E1", "full_name": "X"})
    assert response.status_code == 403
    assert kiosk_client.post("/users/new", data={"username": "evil", "role": "admin"}).status_code == 403
    with app.app_context():
        assert db.session.query(Employee).count() == 0
        assert db.session.query(User).filter_by(username="evil").count() == 0


def test_kiosk_cannot_use_the_diagnostic_identify_endpoint(kiosk_client):
    response = kiosk_client.post("/recognition/identify", headers={"Accept": "application/json"})
    assert response.status_code == 403


def test_kiosk_can_reach_check_in(kiosk_client):
    response = kiosk_client.post("/recognition/check-in", headers={"Accept": "application/json"})
    assert response.status_code == 400  # past the gate; rejected only because no image was sent


def test_kiosk_always_starts_at_check_in(app, anon_client):
    make_user(app, "door", "kiosk")
    response = login(anon_client, "door", query="?next=/employees")
    assert response.headers["Location"] == "/recognition/"


# ---------- user management ----------

def _new_user_form(**overrides):
    form = {"username": "frontdesk", "role": "kiosk", "password": GOOD_PASSWORD, "confirm_password": GOOD_PASSWORD}
    form.update(overrides)
    return form


def test_admin_creates_a_kiosk_user_that_can_sign_in(app, client, anon_client):
    response = client.post("/users/new", data=_new_user_form())
    assert response.status_code == 302
    assert login(anon_client, "frontdesk", GOOD_PASSWORD).headers["Location"] == "/recognition/"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"username": "ab"}, b"3\xe2\x80\x9332 characters"),
        ({"username": "bad name!"}, b"3\xe2\x80\x9332 characters"),
        ({"role": "superuser"}, b"valid role"),
        ({"password": "short", "confirm_password": "short"}, b"at least 10"),
        ({"password": "frontdesk-2026", "confirm_password": "frontdesk-2026"}, b"must not contain the username"),
        ({"confirm_password": "something-else"}, b"do not match"),
        ({"username": "admin"}, b"already taken"),
    ],
    ids=["too-short-name", "bad-characters", "bad-role", "short-password", "password-has-name", "mismatch", "duplicate"],
)
def test_invalid_new_users_are_rejected(app, client, overrides, message):
    response = client.post("/users/new", data=_new_user_form(**overrides))
    assert response.status_code == 200 and message in response.data


def test_admin_cannot_disable_their_own_account(app, client):
    admin_id = get_user(app, "admin").id
    response = client.post(f"/users/{admin_id}/deactivate", follow_redirects=True)
    assert b"cannot disable your own account" in response.data
    assert get_user(app, "admin").is_active


def test_the_last_active_admin_cannot_be_disabled(app):
    admin_id = make_user(app)
    kiosk_id = make_user(app, "door", "kiosk")
    with app.app_context():
        with pytest.raises(UserValidationError, match="At least one active administrator"):
            deactivate_user(db.session.get(User, admin_id), db.session.get(User, kiosk_id))


def test_admin_can_disable_and_enable_another_user(app, client):
    other = make_user(app, "door", "kiosk")
    client.post(f"/users/{other}/deactivate")
    assert not get_user(app, "door").is_active
    client.post(f"/users/{other}/reactivate")
    assert get_user(app, "door").is_active


def test_failed_sign_in_logs_the_username_but_never_the_password(app, anon_client, caplog):
    make_user(app)
    login(anon_client, password="secret-guess-123")
    assert "admin" in caplog.text
    assert "secret-guess-123" not in caplog.text


# ---------- emergency password reset ----------

def test_reset_password_command_sets_a_new_password_and_unlocks(app, anon_client):
    user_id = make_user(app)
    with app.app_context():
        db.session.get(User, user_id).locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        db.session.commit()
    result = app.test_cli_runner().invoke(args=["reset-password", "admin"], input=f"{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n")
    assert result.exit_code == 0, result.output
    assert login(anon_client, password=GOOD_PASSWORD).status_code == 302


def test_reset_password_command_rejects_unknown_users(app):
    result = app.test_cli_runner().invoke(args=["reset-password", "ghost"], input="x\nx\n")
    assert result.exit_code != 0 and "No user called" in result.output


def test_no_template_puts_a_form_without_a_csrf_token(app, client):
    """Every POST form on the user pages carries the token (the logout form too)."""

    for path in ["/users", "/users/new", "/"]:
        html = client.get(path).data.decode()
        forms = re.findall(r"<form[^>]*method=\"post\".*?</form>", html, flags=re.S)
        assert forms, path
        assert all('name="csrf_token"' in form for form in forms), path
