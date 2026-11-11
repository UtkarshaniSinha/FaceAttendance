"""Shared pytest fixtures for FaceAttendance."""

from __future__ import annotations

import time

import pytest
from flask.testing import FlaskClient
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User

TEST_CSRF_TOKEN = "test-csrf-token"
TEST_PASSWORD = "correct-horse-battery"

# pytest copies each test ID into the PYTEST_CURRENT_TEST environment variable.
# Windows rejects variables over 32,767 characters, and very long IDs also make
# terminal output unreadable. Failing early here catches the problem on every
# operating system, not only on Windows.
MAX_TEST_ID_LENGTH = 300


def pytest_collection_modifyitems(config, items):
    too_long = [item for item in items if len(item.nodeid) > MAX_TEST_ID_LENGTH]
    if too_long:
        names = "\n".join(f"  {item.nodeid[:100]}... ({len(item.nodeid):,} characters)" for item in too_long)
        raise pytest.UsageError(
            f"Test IDs longer than {MAX_TEST_ID_LENGTH} characters (give parametrized "
            f"tests short ids with pytest.param(..., id=...)):\n{names}"
        )


class CSRFClient(FlaskClient):
    """Test client that behaves like a browser form: it sends a valid token.

    CSRF protection stays switched ON in tests. This client simply puts a
    known token in the session and adds it to every POST. Pass
    ``csrf_token=None`` to send no token, or any other string to send a wrong one.
    """

    def post(self, *args, csrf_token: str | None = TEST_CSRF_TOKEN, **kwargs):
        with self.session_transaction() as session:
            session["csrf_token"] = TEST_CSRF_TOKEN
        if csrf_token is not None:
            headers = dict(kwargs.pop("headers", None) or {})
            headers.setdefault("X-CSRF-Token", csrf_token)
            kwargs["headers"] = headers
        return super().post(*args, **kwargs)


@pytest.fixture()
def app(tmp_path):
    """Create an isolated app with an in-memory database and temp biometric folder."""

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "BIOMETRIC_STORAGE_PATH": str(tmp_path / "biometrics"),
            # Empty on purpose: tests never depend on locally installed model
            # files. Recognition tests inject a controlled fake embedder.
            "RECOGNITION_MODEL_DIR": str(tmp_path / "models"),
        }
    )
    app.test_client_class = CSRFClient
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def make_user(app, username: str = "admin", role: str = "admin", password: str = TEST_PASSWORD) -> int:
    """Create a user quickly (cheap hash settings: tests only) and return its id."""

    with app.app_context():
        user = User(
            username=username,
            role=role,
            password_hash=generate_password_hash(password, method="pbkdf2:sha256:1000"),
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def sign_in_as(client: FlaskClient, user_id: int) -> None:
    """Put a signed-in session in the client's cookie (skips the sign-in form)."""

    now = int(time.time())
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["login_at"] = now
        session["last_seen"] = now


@pytest.fixture()
def anon_client(app):
    """A CSRF-aware client that is NOT signed in."""

    return app.test_client()


@pytest.fixture()
def client(app):
    """A CSRF-aware client signed in as an administrator.

    Most tests are about features, not sign-in, so they start signed in.
    """

    client = app.test_client()
    sign_in_as(client, make_user(app))
    return client


@pytest.fixture()
def kiosk_client(app):
    """A CSRF-aware client signed in with a check-in-only kiosk account."""

    client = app.test_client()
    sign_in_as(client, make_user(app, "kiosk", "kiosk"))
    return client
