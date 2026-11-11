"""Consent, enrolment state and private-sample lifecycle rules.

Enrolment is a small state machine:

    Consent required --consent--> Not enrolled --start--> In progress
        --(>= minimum accepted images) complete--> Successfully enrolled

    notice revised     : consent becomes "update required"; capture, templates
                         and recognition stop until the employee consents again
    delete data        : any state -> Not enrolled   (images removed, consent kept)
    withdraw consent   : any state -> Consent withdrawn (images removed)

Attendance history is never touched by these actions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import select

from app.extensions import db
from app.models import BiometricConsent, Employee, EnrollmentSample, FaceEnrollment
from app.utils.biometric_storage import BiometricStorage
from app.utils.image_validator import FaceQuality, ImageValidator


class EnrollmentError(ValueError):
    """Raised when an enrolment action is not allowed."""


def current_notice_version() -> str:
    return str(current_app.config["CONSENT_NOTICE_VERSION"])


def has_current_consent(employee: Employee) -> bool:
    """Consent is granted, not withdrawn, and was given to the CURRENT notice.

    Consent to an older notice version does not count: that notice may not
    have described everything that is now collected.
    """
    consent = employee.biometric_consent
    return bool(consent and consent.covers(current_notice_version()))


def consent_needs_update(employee: Employee) -> bool:
    consent = employee.biometric_consent
    return bool(consent and consent.is_valid and not consent.covers(current_notice_version()))


def _has_valid_consent(employee: Employee) -> bool:
    """Granted and not withdrawn, any version (used only for withdrawal)."""
    return bool(employee.biometric_consent and employee.biometric_consent.is_valid)


def grant_consent(employee: Employee, notice_version: str) -> BiometricConsent:
    if not employee.is_active:
        raise EnrollmentError("Inactive employees cannot provide enrolment consent.")
    consent = employee.biometric_consent
    if consent and consent.covers(notice_version):
        return consent
    if consent:  # consent again: after a withdrawal, or to a revised notice
        consent.status, consent.notice_version = "granted", notice_version
        consent.granted_at, consent.withdrawn_at = datetime.now(timezone.utc), None
    else:
        consent = BiometricConsent(employee=employee, notice_version=notice_version)
        db.session.add(consent)
    db.session.commit()
    return consent


def begin_enrollment(employee: Employee) -> FaceEnrollment:
    if not employee.is_active:
        raise EnrollmentError("Inactive employees cannot be enrolled.")
    if consent_needs_update(employee):
        raise EnrollmentError("The consent notice has changed. The employee must read it and consent again before capture.")
    if not has_current_consent(employee):
        raise EnrollmentError("Explicit biometric consent is required before capture.")
    enrollment = employee.face_enrollment
    if enrollment and enrollment.status == "complete":
        raise EnrollmentError("This employee is already enrolled. Delete the enrolment before replacing it.")
    if enrollment is None:
        enrollment = FaceEnrollment(employee=employee, consent=employee.biometric_consent, status="in_progress")
        db.session.add(enrollment)
    else:
        enrollment.status, enrollment.consent = "in_progress", employee.biometric_consent
    db.session.commit()
    return enrollment


def _active_enrollment(employee: Employee) -> FaceEnrollment:
    enrollment = employee.face_enrollment
    if not enrollment or enrollment.status != "in_progress":
        raise EnrollmentError("Start an enrolment before capturing images.")
    if not employee.is_active or not has_current_consent(employee):
        raise EnrollmentError("Valid consent to the current notice is required before capture.")
    return enrollment


def add_sample(
    employee: Employee,
    image_data: bytes,
    validator: ImageValidator,
    storage: BiometricStorage,
    maximum_samples: int,
) -> tuple[EnrollmentSample, FaceQuality]:
    """Validate an image, store it privately and link it to the enrolment."""

    enrollment = _active_enrollment(employee)
    if enrollment.accepted_sample_count >= maximum_samples:
        raise EnrollmentError(f"The maximum of {maximum_samples} images has been reached. Remove one to retake it.")
    validated = validator.validate(image_data)

    # File first, then database row. If the database step fails, the file is
    # removed again so no unrecorded biometric file is left behind.
    storage_name = storage.store(validated.data, validated.image_format)
    try:
        sample = EnrollmentSample(enrollment=enrollment, storage_name=storage_name, image_format=validated.image_format)
        db.session.add(sample)
        enrollment.accepted_sample_count = len(enrollment.samples)
        db.session.commit()
    except Exception:
        db.session.rollback()
        storage.delete(storage_name)
        raise
    return sample, validated.quality


def remove_sample(employee: Employee, sample_id: int, storage: BiometricStorage) -> int:
    """Discard one accepted image (used for "retake"). Returns the new count."""

    enrollment = _active_enrollment(employee)
    sample = db.session.scalar(
        select(EnrollmentSample).where(
            EnrollmentSample.id == sample_id, EnrollmentSample.enrollment_id == enrollment.id
        )
    )
    if sample is None:
        raise EnrollmentError("That image does not belong to this enrolment.")
    # File first: deleting is safe to repeat, so a failed database step can be retried.
    storage.delete(sample.storage_name)
    enrollment.samples.remove(sample)  # "delete-orphan" cascade deletes the row
    enrollment.accepted_sample_count = len(enrollment.samples)
    db.session.commit()
    return enrollment.accepted_sample_count


def complete_enrollment(employee: Employee, minimum_samples: int) -> FaceEnrollment:
    enrollment = _active_enrollment(employee)
    if enrollment.accepted_sample_count < minimum_samples:
        raise EnrollmentError(f"At least {minimum_samples} accepted images are required before completion.")
    enrollment.status = "complete"
    db.session.commit()
    return enrollment


def delete_biometric_data(employee: Employee, storage: BiometricStorage, *, withdrawn: bool = False) -> int:
    """Delete every stored enrolment image and its records. Returns files removed."""

    removed = 0
    enrollment = employee.face_enrollment
    try:
        if enrollment:
            for sample in list(enrollment.samples):
                storage.delete(sample.storage_name)
                removed += 1
            db.session.delete(enrollment)
        if withdrawn and employee.biometric_consent:
            employee.biometric_consent.status = "withdrawn"
            employee.biometric_consent.withdrawn_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return removed


def withdraw_consent(employee: Employee, storage: BiometricStorage) -> int:
    if not _has_valid_consent(employee):
        raise EnrollmentError("There is no active biometric consent to withdraw.")
    return delete_biometric_data(employee, storage, withdrawn=True)


def enrollment_status(employee: Employee) -> str:
    consent = employee.biometric_consent
    if consent and not consent.is_valid:
        return "Consent withdrawn"
    if not consent:
        return "Consent required"
    if consent_needs_update(employee):
        return "Consent update required"
    if not employee.face_enrollment:
        return "Not enrolled"
    return {"in_progress": "In progress", "complete": "Successfully enrolled"}.get(
        employee.face_enrollment.status, "Failed"
    )


def enrollment_badge(employee: Employee) -> str:
    """CSS class for the status badge."""

    return {
        "Successfully enrolled": "",
        "In progress": "badge-warning",
        "Consent update required": "badge-warning",
        "Consent withdrawn": "badge-danger",
        "Failed": "badge-danger",
    }.get(enrollment_status(employee), "badge-muted")
