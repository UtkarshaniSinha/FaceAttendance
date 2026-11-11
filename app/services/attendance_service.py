"""Business rules for daily attendance records.

Rules:
- Attendance belongs to an *attendance day* in the organisation's timezone
  (``ORGANIZATION_TIMEZONE``, default Asia/Kolkata), not the server's own
  timezone and not UTC. Timestamps are stored in UTC.
- One record per employee per attendance day. The database enforces this
  with the unique constraint ``uq_attendance_employee_day``, so two requests
  arriving at the same moment still cannot both create a record.
- Inactive employees never receive attendance.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Attendance, Employee


class AttendanceError(ValueError):
    """Raised when attendance cannot be recorded."""


class DuplicateAttendanceError(AttendanceError):
    """Raised when attendance already exists for an employee/day."""

    def __init__(self, message: str, existing: Attendance | None = None) -> None:
        super().__init__(message)
        self.existing = existing


class AttendanceStorageError(RuntimeError):
    """The database could not save the record. Nothing was recorded."""


def organization_timezone():
    try:
        return ZoneInfo(str(current_app.config["ORGANIZATION_TIMEZONE"]))
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc  # same fallback as the display filter in app/__init__.py


def organization_today() -> date:
    """Today's attendance day in the organisation's timezone."""

    return datetime.now(timezone.utc).astimezone(organization_timezone()).date()


def attendance_day_for(moment: datetime) -> date:
    """The attendance day a UTC moment belongs to, in the organisation's timezone."""

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(organization_timezone()).date()


def _existing_record(employee: Employee, day: date) -> Attendance | None:
    return db.session.scalar(
        select(Attendance).where(Attendance.employee_id == employee.id, Attendance.attendance_date == day)
    )


def record_attendance(
    employee: Employee,
    *,
    attendance_date: date | None = None,
    checked_in_at: datetime | None = None,
    recognition_method: str = "manual",
) -> Attendance:
    """Create one attendance record for an active employee on an attendance day."""

    if not employee.is_active:
        raise AttendanceError("Attendance cannot be recorded for an inactive employee.")

    timestamp = checked_in_at or datetime.now(timezone.utc)
    # A UTC timestamp near midnight must not move the record to the wrong
    # local business day, so the day comes from the organisation's timezone.
    day = attendance_date or attendance_day_for(timestamp)

    existing = _existing_record(employee, day)
    if existing:
        raise DuplicateAttendanceError("Attendance has already been recorded for this employee today.", existing)

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
        # Another request saved a record between our check and our insert:
        # the unique constraint stopped the duplicate.
        db.session.rollback()
        existing = _existing_record(employee, day)
        if existing is None:  # some other integrity problem, not a duplicate
            raise AttendanceStorageError("Attendance could not be saved.") from error
        raise DuplicateAttendanceError(
            "Attendance has already been recorded for this employee today.", existing
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise AttendanceStorageError("Attendance could not be saved.") from error
    return record
