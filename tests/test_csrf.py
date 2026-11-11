"""CSRF protection tests: protection is ON and every form carries a token."""

import itertools
import re

from flask.testing import FlaskClient

from app.extensions import db
from app.models import Employee
from conftest import TEST_PASSWORD, make_user

TOKEN_FIELD = re.compile(rb'name="csrf_token" value="([^"]+)"')
REGISTRATION = {"employee_code": "EMP-501", "full_name": "Meera Iyer", "department": "Finance"}


_user_numbers = itertools.count(1)


def browser(app) -> FlaskClient:
    """A plain client with no helper, like a real browser, signed in via the real form."""

    client = FlaskClient(app, app.response_class, use_cookies=True)
    username = f"admin{next(_user_numbers)}"
    make_user(app, username)
    token = TOKEN_FIELD.search(client.get("/login").data).group(1).decode()
    response = client.post("/login", data={"username": username, "password": TEST_PASSWORD, "csrf_token": token})
    assert response.status_code == 302, "sign-in through the form must succeed"
    return client


def employee_count(app) -> int:
    with app.app_context():
        return db.session.query(Employee).count()


def test_csrf_is_enabled_in_tests(app):
    assert app.config["CSRF_ENABLED"] is True


def test_registration_form_contains_a_csrf_token(app):
    page = browser(app).get("/employees/new")
    assert TOKEN_FIELD.search(page.data), "the registration form must include a hidden csrf_token field"


def test_registration_succeeds_with_token_from_the_rendered_form(app):
    client = browser(app)
    token = TOKEN_FIELD.search(client.get("/employees/new").data).group(1).decode()

    response = client.post("/employees/new", data={**REGISTRATION, "csrf_token": token}, follow_redirects=True)

    assert response.status_code == 200
    assert b"was registered successfully" in response.data
    assert employee_count(app) == 1


def test_registration_without_token_is_rejected(app):
    response = browser(app).post("/employees/new", data=REGISTRATION)

    assert response.status_code == 400
    assert b"Form expired" in response.data
    assert employee_count(app) == 0


def test_registration_with_wrong_token_is_rejected(app):
    client = browser(app)
    client.get("/employees/new")  # creates the real session token

    response = client.post("/employees/new", data={**REGISTRATION, "csrf_token": "forged-token"})

    assert response.status_code == 400
    assert employee_count(app) == 0


def test_token_from_another_session_is_rejected(app):
    victim, attacker = browser(app), browser(app)
    attacker_token = TOKEN_FIELD.search(attacker.get("/employees/new").data).group(1).decode()
    victim.get("/employees/new")

    response = victim.post("/employees/new", data={**REGISTRATION, "csrf_token": attacker_token})

    assert response.status_code == 400
    assert employee_count(app) == 0


def test_json_requests_get_a_json_csrf_error(client):
    response = client.post(
        "/employees/1/enrollment/samples", csrf_token="wrong", headers={"Accept": "application/json"}
    )
    assert response.status_code == 400
    assert "expired" in response.get_json()["error"]


def test_every_post_form_on_employee_pages_has_a_token(app, client):
    with app.app_context():
        employee = Employee(employee_code="EMP-1", full_name="Asha Rao")
        db.session.add(employee)
        db.session.commit()
        employee_id = employee.id
    for url in ("/employees/new", f"/employees/{employee_id}", f"/employees/{employee_id}/edit",
                f"/employees/{employee_id}/enrollment/"):
        html = client.get(url).data
        forms = html.count(b'method="post"')
        assert forms == len(TOKEN_FIELD.findall(html)), f"a POST form on {url} is missing its csrf_token"
