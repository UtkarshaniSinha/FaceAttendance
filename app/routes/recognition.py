"""Face check-in page.

POST /recognition/check-in : identify a capture and, only for a confident,
                             eligible match, record today's attendance.
POST /recognition/identify : identify only, never records attendance
                             (diagnostic endpoint, kept from Phase 3).
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from sqlalchemy.exc import SQLAlchemyError

from app.recognition.service import (
    RecognitionImageError,
    RecognitionUnavailable,
    get_embedder,
    identify,
    load_gallery,
)
from app.services.check_in_service import CheckInError, check_in

recognition_bp = Blueprint("recognition", __name__, url_prefix="/recognition")


@recognition_bp.get("/")
def index():
    model_error = None
    gallery_size = 0
    try:
        gallery_size = len(load_gallery(get_embedder().model_name))
    except RecognitionUnavailable as error:
        model_error = str(error)
    return render_template(
        "recognition/index.html",
        model_error=model_error,
        gallery_size=gallery_size,
        threshold=current_app.config["RECOGNITION_MATCH_THRESHOLD"],
        margin=current_app.config["RECOGNITION_AMBIGUITY_MARGIN"],
        timezone=current_app.config["ORGANIZATION_TIMEZONE"],
    )


@recognition_bp.post("/identify")
def identify_capture():
    upload = request.files.get("image")
    if upload is None:
        return jsonify(error="No image was received."), 400
    try:
        result = identify(upload.read(), current_app.config)
    except RecognitionUnavailable as error:
        return jsonify(error=str(error)), 503
    except RecognitionImageError as error:
        return jsonify(error=str(error)), 400
    # Log the outcome only: never the image, the embedding or the scores of others.
    current_app.logger.info("Recognition test: %s", result.status.value)
    return jsonify(result.to_json())


@recognition_bp.post("/check-in")
def check_in_capture():
    upload = request.files.get("image")
    if upload is None:
        return jsonify(error="No image was received. No attendance recorded."), 400
    try:
        result = check_in(upload.read(), current_app.config)
    except RecognitionUnavailable as error:
        return jsonify(error=f"{error} No attendance recorded."), 503
    except RecognitionImageError as error:
        return jsonify(error=f"{error} No attendance recorded."), 400
    except (CheckInError, SQLAlchemyError) as error:
        # Error type only: database messages can contain SQL parameters.
        cause = error
        while cause.__cause__ is not None:  # report the root cause
            cause = cause.__cause__
        current_app.logger.error("Face check-in failed: %s", type(cause).__name__)
        return jsonify(error="A server error occurred. Attendance was NOT recorded; please try again."), 500
    # Outcome only: no names, scores, images or embeddings in the log.
    current_app.logger.info("Face check-in: %s", result.outcome.value)
    return jsonify(result.to_json()), (201 if result.recorded else 200)
