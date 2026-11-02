"""Attendance database model."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Attendance(db.Model):
    """One daily attendance record per employee."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_day"),
        Index("ix_attendance_date", "attendance_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recognition_method: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="present", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    employee: Mapped["Employee"] = relationship(back_populates="attendances")

    def __repr__(self) -> str:
        return f"<Attendance employee={self.employee_id} date={self.attendance_date}>"
