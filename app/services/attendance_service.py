"""Business rules for daily attendance records."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Attendance, Employee


class AttendanceError(ValueError):
    """Raised when attendance cannot be recorded."""


class DuplicateAttendanceError(AttendanceError):
    """Raised when attendance already exists for an employee/day."""


def record_attendance(
    employee: Employee,
    *,
    attendance_date: date | None = None,
    checked_in_at: datetime | None = None,
    recognition_method: str = "manual",
) -> Attendance:
    """Create one attendance record for an active employee on a date."""

    if not employee.is_active:
        raise AttendanceError("Attendance cannot be recorded for an inactive employee.")

    timestamp = checked_in_at or datetime.now(timezone.utc)
    # Attendance is a local business-day record. A UTC timestamp near midnight
    # must not silently move the record to the previous local calendar date.
    day = attendance_date or date.today()
    existing = db.session.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee.id, Attendance.attendance_date == day
        )
    )
    if existing:
        raise DuplicateAttendanceError("Attendance has already been recorded for this employee today.")

    record = Attendance(
        employee=employee,
        attendance_date=day,
        check_in_time=timestamp,
        recognition_method=recognition_method,
    )
    db.session.add(record)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise DuplicateAttendanceError(
            "Attendance has already been recorded for this employee today."
        ) from error
    return record
