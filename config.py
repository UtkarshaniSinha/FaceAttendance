"""Configuration for the FaceAttendance Flask application."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = BASE_DIR / "instance" / "face_attendance.db"

# Read local settings from .env (never committed). Real environment variables win.
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration shared by development and tests."""

    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # CSRF protection is always on; tests switch it off only when they say so.
    CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    ORGANIZATION_TIMEZONE = os.getenv("ORGANIZATION_TIMEZONE", "Asia/Kolkata")
    BIOMETRIC_STORAGE_PATH = os.getenv(
        "BIOMETRIC_STORAGE_PATH", str(BASE_DIR / "instance" / "biometrics")
    )
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
    ENROLLMENT_MIN_SAMPLES = int(os.getenv("ENROLLMENT_MIN_SAMPLES", "3"))
    ENROLLMENT_MAX_SAMPLES = int(os.getenv("ENROLLMENT_MAX_SAMPLES", "10"))
    # Rejects "decompression bomb" images: tiny files that expand to huge pixel grids.
    ENROLLMENT_MAX_IMAGE_PIXELS = int(os.getenv("ENROLLMENT_MAX_IMAGE_PIXELS", str(4096 * 4096)))
    ENROLLMENT_MIN_FACE_WIDTH = int(os.getenv("ENROLLMENT_MIN_FACE_WIDTH", "120"))
    ENROLLMENT_MIN_SHARPNESS = float(os.getenv("ENROLLMENT_MIN_SHARPNESS", "45"))
    ENROLLMENT_MIN_BRIGHTNESS = float(os.getenv("ENROLLMENT_MIN_BRIGHTNESS", "45"))
    ENROLLMENT_MAX_BRIGHTNESS = float(os.getenv("ENROLLMENT_MAX_BRIGHTNESS", "215"))
    ENROLLMENT_MIN_CONTRAST = float(os.getenv("ENROLLMENT_MIN_CONTRAST", "18"))
    CONSENT_NOTICE_VERSION = os.getenv("CONSENT_NOTICE_VERSION", "portfolio-v1")
