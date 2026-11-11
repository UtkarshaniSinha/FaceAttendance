"""Attendance database and service tests."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Attendance, Employee
from app.services.attendance_service import (
    AttendanceError,
    DuplicateAttendanceError,
    organization_today,
    record_attendance,
)


def test_attendance_record_has_employee_relationship(app):
    with app.app_context():
        employee = Employee(employee_code="EMP-101", full_name="Riya Singh")
        db.session.add(employee)
        db.session.commit()

        record = record_attendance(employee, recognition_method="manual")

        assert record.employee == employee
        assert record.attendance_date == organization_today()
        assert record.recognition_method == "manual"


def test_duplicate_daily_attendance_is_prevented(app):
    with app.app_context():
        employee = Employee(employee_code="EMP-101", full_name="Riya Singh")
        db.session.add(employee)
        db.session.commit()
        record_attendance(employee)

        with pytest.raises(DuplicateAttendanceError):
            record_attendance(employee)


def test_inactive_employee_cannot_receive_attendance(app):
    with app.app_context():
        employee = Employee(employee_code="EMP-101", full_name="Riya Singh", is_active=False)
        db.session.add(employee)
        db.session.commit()

        with pytest.raises(AttendanceError, match="inactive"):
            record_attendance(employee)


def test_database_rejects_an_invalid_employee_reference(app):
    with app.app_context():
        invalid = Attendance(
            employee_id=9999,
            attendance_date=date.today(),
            check_in_time=datetime.now(timezone.utc),
            recognition_method="manual",
        )
        db.session.add(invalid)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
