"""Dashboard and employee management routes."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func, select
from werkzeug.exceptions import NotFound

from app.extensions import db
from app.models import Attendance, Employee, FaceEnrollment
from app.services.employee_service import (
    EmployeeValidationError,
    create_employee,
    deactivate_employee,
    list_employees,
    update_employee,
)


main_bp = Blueprint("main", __name__)


def _get_employee_or_404(employee_id: int) -> Employee:
    employee = db.session.get(Employee, employee_id)
    if employee is None:
        raise NotFound("Employee not found.")
    return employee


@main_bp.get("/")
def dashboard():
    """Render database-backed dashboard statistics."""

    today = date.today()
    total_employees = db.session.scalar(select(func.count()).select_from(Employee)) or 0
    active_employees = db.session.scalar(
        select(func.count()).select_from(Employee).where(Employee.is_active.is_(True))
    ) or 0
    today_attendance = db.session.scalar(
        select(func.count()).select_from(Attendance).where(Attendance.attendance_date == today)
    ) or 0
    enrolled_employees = db.session.scalar(
        select(func.count()).select_from(FaceEnrollment).where(FaceEnrollment.status == "complete")
    ) or 0
    recent_attendance = list(
        db.session.scalars(
            select(Attendance).order_by(Attendance.check_in_time.desc()).limit(8)
        )
    )
    return render_template(
        "dashboard.html",
        total_employees=total_employees,
        active_employees=active_employees,
        today_attendance=today_attendance,
        enrolled_employees=enrolled_employees,
        recent_attendance=recent_attendance,
    )


@main_bp.get("/employees")
def employees():
    """Show all registered employees."""

    return render_template("employees.html", employees=list_employees())


@main_bp.route("/employees/new", methods=["GET", "POST"])
def create_employee_view():
    """Display and process employee registration."""

    if request.method == "POST":
        try:
            employee = create_employee(
                request.form.get("employee_code"),
                request.form.get("full_name"),
                request.form.get("department"),
            )
        except EmployeeValidationError as error:
            flash(str(error), "error")
        else:
            flash(f"{employee.full_name} was registered successfully.", "success")
            return redirect(url_for("main.employee_detail", employee_id=employee.id))
    return render_template("employee_form.html", employee=None)


@main_bp.get("/employees/<int:employee_id>")
def employee_detail(employee_id: int):
    """Show one employee and their latest attendance records."""

    employee = _get_employee_or_404(employee_id)
    attendance_records = list(
        db.session.scalars(
            select(Attendance)
            .where(Attendance.employee_id == employee.id)
            .order_by(Attendance.check_in_time.desc())
        )
    )
    return render_template(
        "employee_detail.html", employee=employee, attendance_records=attendance_records
    )


@main_bp.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
def edit_employee(employee_id: int):
    """Display and process employee updates."""

    employee = _get_employee_or_404(employee_id)
    if request.method == "POST":
        try:
            update_employee(
                employee,
                request.form.get("employee_code"),
                request.form.get("full_name"),
                request.form.get("department"),
            )
        except EmployeeValidationError as error:
            flash(str(error), "error")
        else:
            flash(f"{employee.full_name}'s details were updated.", "success")
            return redirect(url_for("main.employee_detail", employee_id=employee.id))
    return render_template("employee_form.html", employee=employee)


@main_bp.post("/employees/<int:employee_id>/deactivate")
def deactivate_employee_view(employee_id: int):
    """Deactivate an employee without deleting their history."""

    employee = _get_employee_or_404(employee_id)
    if employee.is_active:
        deactivate_employee(employee)
        flash(f"{employee.full_name} was deactivated.", "success")
    else:
        flash(f"{employee.full_name} is already inactive.", "error")
    return redirect(url_for("main.employee_detail", employee_id=employee.id))
