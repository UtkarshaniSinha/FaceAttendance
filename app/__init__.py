"""Application factory for FaceAttendance."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from flask import Flask

from config import Config

from .extensions import db


def create_app(test_config: Mapping[str, object] | None = None) -> Flask:
    """Create and configure a Flask application instance."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    # Import models before create_all so SQLAlchemy knows every table.
    from . import models  # noqa: F401
    from .routes.main import main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
