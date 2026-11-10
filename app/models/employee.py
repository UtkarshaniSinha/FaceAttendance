"""Employee database model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Employee(db.Model):
    """An employee who may have attendance records."""

    __tablename__ = "employees"
    __table_args__ = (Index("ix_employees_active_name", "is_active", "full_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    attendances: Mapped[list["Attendance"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    biometric_consent: Mapped["BiometricConsent | None"] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    face_enrollment: Mapped["FaceEnrollment | None"] = relationship(
        back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Employee {self.employee_code}>"
