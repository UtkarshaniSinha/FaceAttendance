"""Face check-in: recognition result -> eligibility -> attendance record.

    capture ──recognition.identify──> MATCH / UNKNOWN / AMBIGUOUS
        UNKNOWN or AMBIGUOUS            -> stop, nothing recorded
        MATCH below the threshold       -> stop (defence in depth)
        MATCH ──check_eligibility──> not eligible -> stop, nothing recorded
              ──record_attendance──> recorded / already recorded today

This module is the only place where recognition and attendance meet.
The recognition package itself never imports the attendance service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from enum import Enum
from typing import Mapping

from app.models import Attendance, Employee
from app.recognition import service as recognition_service
from app.recognition.matcher import MatchStatus
from app.services.attendance_eligibility import Ineligibility, check_eligibility
from app.services.attendance_service import (
    AttendanceError,
    AttendanceStorageError,
    DuplicateAttendanceError,
    organization_timezone,
    record_attendance,
)

RECOGNITION_METHOD = "face"


class CheckInOutcome(str, Enum):
    RECORDED = "recorded"
    ALREADY_RECORDED = "already_recorded"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    CONSENT_REQUIRED = "consent_required"
    INACTIVE = "inactive"
    ENROLMENT_INCOMPLETE = "enrolment_incomplete"


class CheckInError(RuntimeError):
    """Processing failed after recognition; attendance was NOT recorded."""


_INELIGIBLE = {
    Ineligibility.INACTIVE: CheckInOutcome.INACTIVE,
    Ineligibility.CONSENT_OUTDATED: CheckInOutcome.CONSENT_REQUIRED,
    Ineligibility.CONSENT_REQUIRED: CheckInOutcome.CONSENT_REQUIRED,
    Ineligibility.ENROLMENT_INCOMPLETE: CheckInOutcome.ENROLMENT_INCOMPLETE,
    Ineligibility.NO_TEMPLATES: CheckInOutcome.ENROLMENT_INCOMPLETE,
}

_MESSAGES = {
    CheckInOutcome.RECORDED: "Attendance recorded.",
    CheckInOutcome.ALREADY_RECORDED: "Attendance was already recorded today. Nothing new was recorded.",
    CheckInOutcome.UNKNOWN: "This face does not match any enrolled employee closely enough. No attendance recorded.",
    CheckInOutcome.AMBIGUOUS: "Two enrolled employees are too similar to this capture. No identity was chosen and no attendance recorded.",
    CheckInOutcome.CONSENT_REQUIRED: "Valid consent to the current notice is required. No attendance recorded.",
    CheckInOutcome.INACTIVE: "This employee is inactive. No attendance recorded.",
    CheckInOutcome.ENROLMENT_INCOMPLETE: "Face enrolment is incomplete or has no usable templates. No attendance recorded.",
}


@dataclass(frozen=True)
class CheckInResult:
    outcome: CheckInOutcome
    employee: Employee | None = None
    attendance: Attendance | None = None
    similarity: float | None = None

    @property
    def message(self) -> str:
        return _MESSAGES[self.outcome]

    @property
    def recorded(self) -> bool:
        return self.outcome is CheckInOutcome.RECORDED

    def to_json(self) -> dict:
        """Only what the screen needs: no embeddings, templates or file names."""

        attendance = None
        if self.attendance is not None:
            local = self.attendance.check_in_time
            if local.tzinfo is None:  # SQLite returns stored UTC values without tzinfo
                local = local.replace(tzinfo=timezone.utc)
            local = local.astimezone(organization_timezone())
            attendance = {
                "date": self.attendance.attendance_date.isoformat(),
                "time": local.strftime("%H:%M"),
            }
        return {
            "outcome": self.outcome.value,
            "recorded": self.recorded,
            "message": self.message,
            "employee": None if self.employee is None else {
                "full_name": self.employee.full_name,
                "employee_code": self.employee.employee_code,
            },
            "attendance": attendance,
            "similarity": None if self.similarity is None else round(self.similarity, 3),
        }


def check_in(image_bytes: bytes, config: Mapping[str, object], embedder=None) -> CheckInResult:
    """Identify one capture and, only for a confident eligible match, record attendance.

    Raises RecognitionImageError / RecognitionUnavailable (nothing recorded) for
    unusable images or missing models, and CheckInError if saving fails.
    """

    embedder = embedder or recognition_service.get_embedder()
    result = recognition_service.identify(image_bytes, config, embedder=embedder)

    if result.status is MatchStatus.AMBIGUOUS:
        return CheckInResult(CheckInOutcome.AMBIGUOUS, similarity=result.similarity)
    threshold = float(config["RECOGNITION_MATCH_THRESHOLD"])
    if (
        result.status is not MatchStatus.MATCH
        or result.employee is None
        or result.similarity is None
        or result.similarity < threshold
    ):
        return CheckInResult(CheckInOutcome.UNKNOWN, similarity=result.similarity)

    employee = result.employee
    reason = check_eligibility(employee, embedder.model_name)
    if reason is not None:
        return CheckInResult(_INELIGIBLE[reason], employee=employee, similarity=result.similarity)

    try:
        record = record_attendance(employee, recognition_method=RECOGNITION_METHOD)
    except DuplicateAttendanceError as duplicate:
        return CheckInResult(CheckInOutcome.ALREADY_RECORDED, employee, duplicate.existing, result.similarity)
    except AttendanceError:  # became inactive between the checks
        return CheckInResult(CheckInOutcome.INACTIVE, employee=employee, similarity=result.similarity)
    except AttendanceStorageError as error:
        raise CheckInError("Attendance could not be saved. Nothing was recorded; please try again.") from error
    return CheckInResult(CheckInOutcome.RECORDED, employee, record, result.similarity)
