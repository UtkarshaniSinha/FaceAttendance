"""Application factory and dashboard tests."""

from datetime import datetime, timezone

from sqlalchemy import inspect

from app.extensions import db
from app.models import Attendance, Employee
from app.services.attendance_service import organization_today
from conftest import make_user, sign_in_as


def test_application_initializes_database(app):
    with app.app_context():
        table_names = inspect(db.engine).get_table_names()
        assert Employee.__table__.name in table_names
        assert Attendance.__table__.name in table_names


def test_configuration_can_be_overridden_for_tests(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"


def test_dashboard_handles_an_empty_database(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Total employees" in response.data
    assert b"No attendance yet" in response.data
    assert b"future" not in response.data  # no outdated "future recognition" wording
    assert b">0<" in response.data


def test_dashboard_uses_database_statistics(client, app):
    with app.app_context():
        active = Employee(employee_code="EMP-001", full_name="Asha Rao", department="People")
        inactive = Employee(employee_code="EMP-002", full_name="Kiran Shah", is_active=False)
        db.session.add_all([active, inactive])
        db.session.commit()
        db.session.add(
            Attendance(
                employee=active,
                attendance_date=organization_today(),
                check_in_time=datetime.now(timezone.utc),
                recognition_method="manual",
            )
        )
        db.session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Asha Rao" in response.data
    assert b"EMP-001" in response.data
    assert b">2<" in response.data
    assert b">1<" in response.data


def test_times_are_displayed_in_the_organisation_timezone(app):
    to_local = app.jinja_env.filters["localtime"]
    stored_utc = datetime(2026, 11, 10, 10, 47)  # SQLite gives back naive UTC values

    assert app.config["ORGANIZATION_TIMEZONE"] == "Asia/Kolkata"
    assert to_local(stored_utc, "%H:%M") == "16:17"  # UTC+05:30
    assert to_local(None) == "—"


def test_env_example_settings_point_to_the_normal_database(tmp_path):
    """Copying .env.example to .env (as the installation guide says) must work.

    Never starts the app against the real project database.
    """

    from pathlib import Path

    from dotenv import dotenv_values

    from app import create_app
    from config import BASE_DIR, DEFAULT_DATABASE_PATH

    example = dotenv_values(Path(__file__).resolve().parents[1] / ".env.example")
    if not example.get("DATABASE_URL"):
        # Not set: the default must be <project>/instance/face_attendance.db.
        assert DEFAULT_DATABASE_PATH == BASE_DIR / "instance" / "face_attendance.db"
        return
    instance = tmp_path / "instance"
    app = create_app({"SQLALCHEMY_DATABASE_URI": example["DATABASE_URL"], "SECRET_KEY": "x",
                      "BIOMETRIC_STORAGE_PATH": str(tmp_path / "bio")}, instance_path=str(instance))
    with app.app_context():
        assert Path(db.engine.url.database).parent == instance, "the database must live directly in instance/"
        db.session.remove()
        db.engine.dispose()


def test_missing_secret_key_is_replaced_by_a_private_random_key_that_persists(tmp_path):
    from app import SECRET_KEY_FILENAME, create_app

    instance = tmp_path / "instance"
    settings = {"SECRET_KEY": None, "SQLALCHEMY_DATABASE_URI": "sqlite://", "BIOMETRIC_STORAGE_PATH": str(tmp_path / "bio")}
    first = create_app(settings, instance_path=str(instance)).config["SECRET_KEY"]
    second = create_app(settings, instance_path=str(instance)).config["SECRET_KEY"]
    assert first == second and len(first) == 64  # same key after a restart
    assert first != "development-only-change-me"
    assert (instance / SECRET_KEY_FILENAME).read_text(encoding="utf-8") == first


def test_unknown_pages_use_the_app_layout(client):
    page = client.get("/employees/999")
    assert page.status_code == 404
    assert b"Employee not found." in page.data and b"Back to dashboard" in page.data
    assert client.get("/no-such-page").status_code == 404
    api = client.get("/no-such-page", headers={"Accept": "application/json"})
    assert api.status_code == 404 and api.get_json()["error"]


def test_run_py_does_not_force_debug_mode():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "run.py").read_text(encoding="utf-8")
    assert "debug=True" not in source and 'os.getenv("FLASK_DEBUG") == "1"' in source


def _bare_settings(tmp_path, **extra):
    settings = {"SQLALCHEMY_DATABASE_URI": "sqlite://", "BIOMETRIC_STORAGE_PATH": str(tmp_path / "bio")}
    settings.update(extra)
    return settings


def test_generated_secret_key_is_random_and_private(tmp_path):
    import os

    from app import SECRET_KEY_FILENAME, create_app

    first = create_app(_bare_settings(tmp_path, SECRET_KEY=None), instance_path=str(tmp_path / "a")).config["SECRET_KEY"]
    other = create_app(_bare_settings(tmp_path, SECRET_KEY=None), instance_path=str(tmp_path / "b")).config["SECRET_KEY"]
    assert first != other  # a fresh random key per installation, not a fixed value
    int(first, 16)  # 64 hexadecimal characters
    if os.name == "posix":  # Windows does not use these permission bits
        assert (tmp_path / "a" / SECRET_KEY_FILENAME).stat().st_mode & 0o077 == 0


def test_empty_or_short_secret_key_file_is_replaced(tmp_path):
    from app import SECRET_KEY_FILENAME, create_app

    instance = tmp_path / "instance"
    instance.mkdir()
    (instance / SECRET_KEY_FILENAME).write_text("short", encoding="utf-8")
    key = create_app(_bare_settings(tmp_path, SECRET_KEY=None), instance_path=str(instance)).config["SECRET_KEY"]
    assert len(key) == 64
    assert (instance / SECRET_KEY_FILENAME).read_text(encoding="utf-8") == key
    assert [p.name for p in instance.iterdir()] == [SECRET_KEY_FILENAME]  # no temporary file left behind


def test_unreadable_secret_key_storage_stops_startup_with_a_clear_message(tmp_path):
    import pytest

    from app import SECRET_KEY_FILENAME, SecretKeyError, create_app

    instance = tmp_path / "instance"
    (instance / SECRET_KEY_FILENAME).mkdir(parents=True)  # a folder where the key file should be: cannot be read
    with pytest.raises(SecretKeyError) as error:
        create_app(_bare_settings(tmp_path, SECRET_KEY=None), instance_path=str(instance))
    assert "SECRET_KEY" in str(error.value) and str(tmp_path) not in str(error.value)


def test_public_example_secret_keys_are_ignored(tmp_path):
    from app import create_app

    for public in ("development-only-change-me", "replace-with-a-long-random-local-secret"):
        app = create_app(_bare_settings(tmp_path, SECRET_KEY=public), instance_path=str(tmp_path / "instance"))
        assert app.config["SECRET_KEY"] != public and len(app.config["SECRET_KEY"]) == 64


def test_server_errors_hide_details_and_database_values_from_pages_and_logs(tmp_path, caplog):
    import logging

    from sqlalchemy import text

    from app import create_app

    app = create_app(
        _bare_settings(tmp_path, SECRET_KEY="x", CSRF_ENABLED=False,
                       SQLALCHEMY_DATABASE_URI=f"sqlite:///{(tmp_path / 'errors.db').as_posix()}"),
        instance_path=str(tmp_path / "instance"),
    )
    assert not app.debug and not app.testing

    marker = "-".join(["FAKE", "EMBEDDING", "BYTES"])  # built at run time, so tracebacks of this source cannot contain it

    @app.post("/__failing_insert")
    def failing_insert():
        values = {"id": "not-a-number", "embedding": marker.encode()}
        db.session.execute(text("INSERT INTO face_templates (id, embedding) VALUES (:id, :embedding)"), values)
        db.session.commit()

    @app.get("/__failing_page")
    def failing_page():
        raise RuntimeError("internal detail C:/private/path")

    with caplog.at_level(logging.ERROR):
        client = app.test_client()
        sign_in_as(client, make_user(app))
        page = client.get("/__failing_page")
        insert = client.post("/__failing_insert", headers={"Accept": "application/json"})
    assert page.status_code == 500 and b"Back to dashboard" in page.data
    assert b"internal detail" not in page.data and b"Traceback" not in page.data
    assert insert.status_code == 500 and marker.encode() not in insert.data
    assert marker not in caplog.text  # SQL parameter values are hidden in logs
    assert "IntegrityError" in caplog.text  # the error itself is still logged for debugging
    with app.app_context():
        db.engine.dispose()


def test_every_response_carries_security_headers(client, app):
    from app.security_headers import SECURITY_HEADERS

    for path in ("/", "/employees", "/recognition/", "/no-such-page"):
        response = client.get(path)
        for name, value in SECURITY_HEADERS.items():
            assert response.headers.get(name) == value, (path, name)
    csp = SECURITY_HEADERS["Content-Security-Policy"]
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp and "unsafe-inline" not in csp


def test_sign_in_page_also_carries_security_headers(app):
    anonymous = app.test_client()  # not signed in
    response = anonymous.get("/login", follow_redirects=True)
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")


def test_templates_have_no_inline_scripts_or_styles():
    """The Content-Security-Policy blocks inline code, so pages must not use any."""

    import re
    from pathlib import Path

    templates = Path(__file__).resolve().parents[1] / "app" / "templates"
    for page in templates.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)", html), f"inline <script> in {page.name}"
        assert not re.search(r"\sstyle=|\son[a-z]+=", html), f"inline style or event handler in {page.name}"
