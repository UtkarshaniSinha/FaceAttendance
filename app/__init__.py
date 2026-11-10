"""Application factory for FaceAttendance."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config

from .csrf import CSRFError, get_csrf_token, protect_state_changes
from .extensions import db


def _wants_json() -> bool:
    """True for JavaScript (fetch) requests that expect a JSON reply."""

    return request.accept_mimetypes.best == "application/json"


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        message = "Your session expired or the form was out of date. Reload the page and try again."
        if _wants_json():
            return jsonify(error=message), 400
        return render_template("error.html", title="Form expired", message=message), 400

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        message = "The image is larger than the upload limit."
        if _wants_json():
            return jsonify(error=message), 413
        return render_template("error.html", title="Upload too large", message=message), 413


def _register_time_filter(app: Flask) -> None:
    """Times are stored in UTC; show them in the organisation's timezone."""

    try:
        local_zone = ZoneInfo(app.config["ORGANIZATION_TIMEZONE"])
    except (ZoneInfoNotFoundError, ValueError):
        # Windows has no built-in timezone database: `pip install tzdata` fixes this.
        app.logger.warning("Timezone %s unavailable; showing UTC.", app.config["ORGANIZATION_TIMEZONE"])
        local_zone = timezone.utc

    @app.template_filter("localtime")
    def localtime(value: datetime | None, fmt: str = "%d %b %Y, %H:%M") -> str:
        if value is None:
            return "—"
        if value.tzinfo is None:  # SQLite returns stored UTC values without tzinfo
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(local_zone).strftime(fmt)


def create_app(test_config: Mapping[str, object] | None = None) -> Flask:
    """Create and configure a Flask application instance."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["BIOMETRIC_STORAGE_PATH"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    app.before_request(protect_state_changes)
    app.jinja_env.globals["csrf_token"] = get_csrf_token
    _register_error_handlers(app)
    _register_time_filter(app)

    # Import models before create_all so SQLAlchemy knows every table.
    from . import models  # noqa: F401
    from .routes.enrollment import enrollment_bp
    from .routes.main import main_bp
    from .services.face_enrollment_service import enrollment_badge, enrollment_status

    app.jinja_env.globals["enrollment_status"] = enrollment_status
    app.jinja_env.globals["enrollment_badge"] = enrollment_badge

    app.register_blueprint(main_bp)
    app.register_blueprint(enrollment_bp)

    with app.app_context():
        db.create_all()

    return app
