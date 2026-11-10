"""Shared pytest fixtures for FaceAttendance."""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db

TEST_CSRF_TOKEN = "test-csrf-token"


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
        }
    )
    app.test_client_class = CSRFClient
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Return the CSRF-aware Flask test client."""

    return app.test_client()
