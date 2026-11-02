"""Shared pytest fixtures for FaceAttendance."""

from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    """Create an isolated in-memory application database."""

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
        }
    )
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Return the Flask test client."""

    return app.test_client()
