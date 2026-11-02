"""Business rules for employee management."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Employee


class EmployeeValidationError(ValueError):
    """Raised when employee input cannot be accepted."""


class DuplicateEmployeeCodeError(EmployeeValidationError):
    """Raised when an employee code is already in use."""


def _clean_required(value: str | None, label: str, maximum: int) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise EmployeeValidationError(f"{label} is required.")
    if len(cleaned) > maximum:
        raise EmployeeValidationError(f"{label} must be {maximum} characters or fewer.")
    return cleaned


def _clean_optional(value: str | None, label: str, maximum: int) -> str | None:
    cleaned = (value or "").strip()
    if len(cleaned) > maximum:
        raise EmployeeValidationError(f"{label} must be {maximum} characters or fewer.")
    return cleaned or None


def list_employees() -> list[Employee]:
    """Return employees ordered for the management screen."""

    return list(db.session.scalars(select(Employee).order_by(Employee.full_name, Employee.employee_code)))


def create_employee(employee_code: str | None, full_name: str | None, department: str | None) -> Employee:
    """Validate and persist a new employee."""

    code = _clean_required(employee_code, "Employee ID", 32).upper()
    name = _clean_required(full_name, "Full name", 120)
    department_value = _clean_optional(department, "Department", 120)

    if db.session.scalar(select(Employee).where(Employee.employee_code == code)):
        raise DuplicateEmployeeCodeError("That employee ID is already registered.")

    employee = Employee(employee_code=code, full_name=name, department=department_value)
    db.session.add(employee)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise DuplicateEmployeeCodeError("That employee ID is already registered.") from error
    return employee


def update_employee(
    employee: Employee, employee_code: str | None, full_name: str | None, department: str | None
) -> Employee:
    """Validate and persist employee details."""

    code = _clean_required(employee_code, "Employee ID", 32).upper()
    duplicate = db.session.scalar(
        select(Employee).where(Employee.employee_code == code, Employee.id != employee.id)
    )
    if duplicate:
        raise DuplicateEmployeeCodeError("That employee ID is already registered.")

    employee.employee_code = code
    employee.full_name = _clean_required(full_name, "Full name", 120)
    employee.department = _clean_optional(department, "Department", 120)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise DuplicateEmployeeCodeError("That employee ID is already registered.") from error
    return employee


def deactivate_employee(employee: Employee) -> None:
    """Deactivate an employee without deleting attendance history."""

    employee.is_active = False
    db.session.commit()
