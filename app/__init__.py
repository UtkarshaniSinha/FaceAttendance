"""Application factory for FaceAttendance."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import Forbidden, InternalServerError, NotFound, RequestEntityTooLarge

from config import Config

from .auth import current_user, require_login
from .csrf import CSRFError, get_csrf_token, protect_state_changes
from .extensions import db
from .security_headers import add_security_headers


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

    @app.errorhandler(Forbidden)
    def forbidden(error):
        message = error.description if error.description != Forbidden.description else "You are not allowed to do that."
        if _wants_json():
            return jsonify(error=message), 403
        return render_template("error.html", title="Not allowed", message=message), 403

    @app.errorhandler(NotFound)
    def not_found(error):
        message = error.description if error.description != NotFound.description else "This page does not exist."
        if _wants_json():
            return jsonify(error=message), 404
        return render_template("error.html", title="Not found", message=message), 404

    @app.errorhandler(InternalServerError)
    def server_error(_error):
        # Never show exception details (they could contain personal data).
        message = "Something went wrong on the server. Please try again. (Details are not shown, to protect personal data.)"
        if _wants_json():
            return jsonify(error=message), 500
        return render_template("error.html", title="Server error", message=message), 500


SECRET_KEY_FILENAME = "secret_key"
MIN_SECRET_KEY_LENGTH = 32
# Values published in this repository's history or examples. A key anyone can
# read is no secret, so these are ignored (a private random key is used instead).
PUBLIC_PLACEHOLDER_KEYS = frozenset({"development-only-change-me", "replace-with-a-long-random-local-secret"})


class SecretKeyError(RuntimeError):
    """The private secret-key file could not be read or created."""


def _write_private_file(path: Path, text: str, *, exclusive: bool) -> None:
    """Create a file readable only by its owner (where the OS supports it)."""

    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)


def load_or_create_secret_key(folder: Path) -> str:
    """Return a random secret key kept in a private file, creating it once.

    The key signs session cookies (which hold the CSRF token). It must be
    secret and must stay the same across restarts, otherwise every open form
    would fail with "Invalid CSRF token" after a restart. If the file cannot
    be read or written, the app refuses to start rather than using a weak key.
    """

    key_file = Path(folder) / SECRET_KEY_FILENAME
    hint = "Fix the permissions of instance/secret_key, or set SECRET_KEY in .env."
    try:
        existing = key_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        existing = None
    except (OSError, UnicodeDecodeError) as error:
        raise SecretKeyError(f"The secret key file could not be read ({type(error).__name__}). {hint}") from error
    if existing and len(existing) >= MIN_SECRET_KEY_LENGTH:
        return existing

    key = secrets.token_hex(32)  # 64 hex characters from the OS's secure random source
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if existing is None:
            try:
                _write_private_file(key_file, key, exclusive=True)
            except FileExistsError:  # another process created it a moment ago: use that one
                return load_or_create_secret_key(folder)
        else:  # empty or too short: replace it
            temporary = key_file.with_name(f"{SECRET_KEY_FILENAME}.{secrets.token_hex(4)}.tmp")
            _write_private_file(temporary, key, exclusive=True)
            os.replace(temporary, key_file)
    except OSError as error:
        raise SecretKeyError(f"The secret key file could not be created ({type(error).__name__}). {hint}") from error
    return key


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


def create_app(test_config: Mapping[str, object] | None = None, *, instance_path: str | None = None) -> Flask:
    """Create and configure a Flask application instance."""

    app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    if app.config.get("SECRET_KEY") in PUBLIC_PLACEHOLDER_KEYS:
        app.logger.warning("SECRET_KEY is a public example value and was ignored; using instance/secret_key.")
        app.config["SECRET_KEY"] = None
    if not app.config.get("SECRET_KEY"):
        # No SECRET_KEY in the environment or .env: use a random key stored in
        # the private instance/ folder (ignored by Git) instead of a public default.
        app.config["SECRET_KEY"] = load_or_create_secret_key(Path(app.instance_path))

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["BIOMETRIC_STORAGE_PATH"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    # Order matters: first "who are you?" (sign-in and role), then the CSRF check.
    app.before_request(require_login)
    app.before_request(protect_state_changes)
    app.after_request(add_security_headers)
    app.jinja_env.globals["csrf_token"] = get_csrf_token
    app.jinja_env.globals["current_user"] = current_user
    _register_error_handlers(app)
    _register_time_filter(app)

    # Import models before create_all so SQLAlchemy knows every table.
    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    from .routes.enrollment import enrollment_bp
    from .routes.main import main_bp
    from .routes.recognition import recognition_bp
    from .services.face_enrollment_service import enrollment_badge, enrollment_status

    app.jinja_env.globals["enrollment_status"] = enrollment_status
    app.jinja_env.globals["enrollment_badge"] = enrollment_badge

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(enrollment_bp)
    app.register_blueprint(recognition_bp)

    _register_cli(app)

    with app.app_context():
        db.create_all()

    return app


def _register_cli(app: Flask) -> None:
    import click

    @app.cli.command("reset-password")
    @click.argument("username")
    def reset_password(username: str) -> None:
        """Set a new password for USERNAME (and unlock it). For a forgotten admin password."""

        from .services.user_service import UserValidationError, find_user, set_password

        user = find_user(username)
        if user is None:
            raise click.ClickException(f"No user called {username!r}.")
        password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
        try:
            set_password(user, password, app.config)
        except UserValidationError as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"Password for {user.username} was changed and the account unlocked.")
