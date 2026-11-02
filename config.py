"""Configuration for the FaceAttendance Flask application."""

from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = BASE_DIR / "instance" / "face_attendance.db"


class Config:
    """Base configuration shared by development and tests."""

    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ORGANIZATION_TIMEZONE = os.getenv("ORGANIZATION_TIMEZONE", "Asia/Kolkata")
