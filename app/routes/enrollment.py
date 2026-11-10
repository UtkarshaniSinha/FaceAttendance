"""Consent, capture and enrolment management routes."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import NotFound

from app.extensions import db
from app.models import Employee
from app.services.face_enrollment_service import (
    EnrollmentError,
    add_sample,
    begin_enrollment,
    complete_enrollment,
    delete_biometric_data,
    enrollment_status,
    grant_consent,
    remove_sample,
    withdraw_consent,
)
from app.utils.biometric_storage import BiometricStorage
from app.utils.face_detector import HaarFaceDetector
from app.utils.image_validator import ImageValidationError, ImageValidator


enrollment_bp = Blueprint("enrollment", __name__, url_prefix="/employees/<int:employee_id>/enrollment")


def _employee(employee_id: int) -> Employee:
    employee = db.session.get(Employee, employee_id)
    if employee is None:
        raise NotFound("Employee not found.")
    return employee


def _storage() -> BiometricStorage:
    return BiometricStorage(current_app.config["BIOMETRIC_STORAGE_PATH"])


def _validator() -> ImageValidator:
    # The detector is loaded once per app and reused (tests may replace it).
    detector = current_app.extensions.get("face_detector")
    if detector is None:
        detector = current_app.extensions["face_detector"] = HaarFaceDetector()
    return ImageValidator(current_app.config, detector=detector)


def _back(employee: Employee):
    return redirect(url_for("enrollment.index", employee_id=employee.id))


@enrollment_bp.get("/")
def index(employee_id: int):
    employee = _employee(employee_id)
    return render_template(
        "enrollment/index.html",
        employee=employee,
        status=enrollment_status(employee),
        minimum_samples=current_app.config["ENROLLMENT_MIN_SAMPLES"],
        notice_version=current_app.config["CONSENT_NOTICE_VERSION"],
    )


@enrollment_bp.post("/consent")
def consent(employee_id: int):
    employee = _employee(employee_id)
    if request.form.get("affirm") != "yes":
        flash("Consent was not recorded. Tick the box to give explicit consent.", "error")
        return _back(employee)
    try:
        grant_consent(employee, current_app.config["CONSENT_NOTICE_VERSION"])
        flash("Biometric consent was recorded.", "success")
    except EnrollmentError as error:
        flash(str(error), "error")
    return _back(employee)


@enrollment_bp.post("/start")
def start(employee_id: int):
    employee = _employee(employee_id)
    try:
        begin_enrollment(employee)
    except EnrollmentError as error:
        flash(str(error), "error")
        return _back(employee)
    return redirect(url_for("enrollment.capture", employee_id=employee.id))


@enrollment_bp.get("/capture")
def capture(employee_id: int):
    employee = _employee(employee_id)
    enrollment = employee.face_enrollment
    if not enrollment or enrollment.status != "in_progress" or not employee.biometric_consent.is_valid:
        flash("Start the enrolment from this page before opening the camera.", "error")
        return _back(employee)
    return render_template(
        "enrollment/capture.html",
        employee=employee,
        samples=sorted(enrollment.samples, key=lambda s: s.id),
        minimum_samples=current_app.config["ENROLLMENT_MIN_SAMPLES"],
        maximum_samples=current_app.config["ENROLLMENT_MAX_SAMPLES"],
    )


@enrollment_bp.post("/samples")
def upload_sample(employee_id: int):
    employee = _employee(employee_id)
    upload = request.files.get("image")
    if upload is None:
        return jsonify(error="No image was received."), 400
    try:
        sample, quality = add_sample(
            employee,
            upload.read(),
            _validator(),
            _storage(),
            current_app.config["ENROLLMENT_MAX_SAMPLES"],
        )
    except (EnrollmentError, ImageValidationError) as error:
        return jsonify(error=str(error)), 400
    # The reply never contains file names or paths, only an opaque database id.
    return (
        jsonify(
            sample_id=sample.id,
            accepted_sample_count=employee.face_enrollment.accepted_sample_count,
            quality={
                "brightness": quality.brightness,
                "contrast": quality.contrast,
                "sharpness": quality.sharpness,
                "face_width": quality.face_width,
            },
            message="Image accepted.",
        ),
        201,
    )


@enrollment_bp.post("/samples/<int:sample_id>/delete")
def discard_sample(employee_id: int, sample_id: int):
    employee = _employee(employee_id)
    try:
        count = remove_sample(employee, sample_id, _storage())
    except EnrollmentError as error:
        return jsonify(error=str(error)), 400
    return jsonify(accepted_sample_count=count, message="Image removed.")


@enrollment_bp.post("/complete")
def complete(employee_id: int):
    employee = _employee(employee_id)
    try:
        complete_enrollment(employee, current_app.config["ENROLLMENT_MIN_SAMPLES"])
    except EnrollmentError as error:
        flash(str(error), "error")
        return redirect(url_for("enrollment.capture", employee_id=employee.id))
    flash("Face enrolment is complete.", "success")
    return _back(employee)


@enrollment_bp.post("/withdraw")
def withdraw(employee_id: int):
    employee = _employee(employee_id)
    try:
        removed = withdraw_consent(employee, _storage())
        flash(f"Consent was withdrawn and {removed} stored face image(s) were deleted. Attendance history is kept.", "success")
    except EnrollmentError as error:
        flash(str(error), "error")
    return _back(employee)


@enrollment_bp.post("/delete")
def delete_data(employee_id: int):
    employee = _employee(employee_id)
    removed = delete_biometric_data(employee, _storage())
    flash(f"{removed} stored face image(s) were deleted. Consent remains recorded.", "success")
    return _back(employee)
