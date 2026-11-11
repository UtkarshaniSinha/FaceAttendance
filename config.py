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

    # Signs session cookies. If unset, create_app() generates a random key and
    # keeps it in instance/secret_key (private, ignored by Git).
    SECRET_KEY = os.getenv("SECRET_KEY") or None
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Keep SQL parameter values (names, face embeddings) out of error messages
    # and server logs; the SQL statement itself is still shown for debugging.
    SQLALCHEMY_ENGINE_OPTIONS = {"hide_parameters": True}
    # CSRF protection is always on; tests switch it off only when they say so.
    CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Sign-in and sessions. Admin sessions end after 30 idle minutes; a kiosk
    # (check-in only, much less power) may stay signed in through a work day.
    SESSION_IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "30"))
    KIOSK_SESSION_IDLE_MINUTES = int(os.getenv("KIOSK_SESSION_IDLE_MINUTES", "720"))
    SESSION_MAX_HOURS = int(os.getenv("SESSION_MAX_HOURS", "12"))
    LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
    PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "10"))
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
    # Phase 3 face recognition (OpenCV Zoo YuNet + SFace; files are not in Git).
    RECOGNITION_MODEL_DIR = os.getenv("RECOGNITION_MODEL_DIR", str(BASE_DIR / "instance" / "models"))
    FACE_DETECTOR_MODEL = os.getenv("FACE_DETECTOR_MODEL", "face_detection_yunet_2023mar.onnx")
    FACE_RECOGNIZER_MODEL = os.getenv("FACE_RECOGNIZER_MODEL", "face_recognition_sface_2021dec.onnx")
    RECOGNITION_DETECTION_SCORE = float(os.getenv("RECOGNITION_DETECTION_SCORE", "0.9"))
    # Starting values, NOT calibrated: OpenCV's 0.363 is a 1:1 verification
    # point; 1:N identification needs a stricter value to limit false matches.
    RECOGNITION_MATCH_THRESHOLD = float(os.getenv("RECOGNITION_MATCH_THRESHOLD", "0.45"))
    RECOGNITION_AMBIGUITY_MARGIN = float(os.getenv("RECOGNITION_AMBIGUITY_MARGIN", "0.05"))
    # Change this whenever the notice text changes. Consent given to an older
    # version is NOT treated as consent to the new one (the employee must agree again).
    # v1: photos only. v2 (10 Nov 2026): also discloses face embeddings.
    CONSENT_NOTICE_VERSION = os.getenv("CONSENT_NOTICE_VERSION", "portfolio-v2")
