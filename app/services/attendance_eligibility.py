"""Who may have attendance recorded by face recognition.

Kept separate from both the recognition engine (which only answers "who
does this face resemble?") and the attendance service (which only stores
records). Every rule is checked again here, even though the recognition
gallery already excludes ineligible employees, because the employee's state
can change between recognition and recording (for example, consent withdrawn
a moment earlier).
"""

from __future__ import annotations

from enum import Enum

from app.models import Employee
from app.recognition.service import template_count
from app.services.face_enrollment_service import consent_needs_update, has_current_consent


class Ineligibility(str, Enum):
    INACTIVE = "inactive"
    CONSENT_OUTDATED = "consent_outdated"  # consented to an older notice
    CONSENT_REQUIRED = "consent_required"  # never consented, or withdrawn
    ENROLMENT_INCOMPLETE = "enrolment_incomplete"
    NO_TEMPLATES = "no_templates"  # enrolled, but no usable templates for this model


def check_eligibility(employee: Employee, model_name: str) -> Ineligibility | None:
    """Return the first reason the employee may not check in, or None if eligible."""

    if not employee.is_active:
        return Ineligibility.INACTIVE
    if consent_needs_update(employee):
        return Ineligibility.CONSENT_OUTDATED
    if not has_current_consent(employee):
        return Ineligibility.CONSENT_REQUIRED
    enrollment = employee.face_enrollment
    if enrollment is None or enrollment.status != "complete":
        return Ineligibility.ENROLMENT_INCOMPLETE
    if template_count(employee, model_name) == 0:
        return Ineligibility.NO_TEMPLATES
    return None
