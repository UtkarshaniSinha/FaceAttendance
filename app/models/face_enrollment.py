"""Consent and non-public biometric enrolment metadata models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BiometricConsent(db.Model):
    __tablename__ = "biometric_consents"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="granted", nullable=False)
    notice_version: Mapped[str] = mapped_column(String(80), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="biometric_consent")
    enrollment: Mapped["FaceEnrollment | None"] = relationship(back_populates="consent", uselist=False)

    @property
    def is_valid(self) -> bool:
        return self.status == "granted" and self.withdrawn_at is None


class FaceEnrollment(db.Model):
    __tablename__ = "face_enrollments"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), unique=True, nullable=False)
    consent_id: Mapped[int] = mapped_column(ForeignKey("biometric_consents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="in_progress", nullable=False, index=True)
    accepted_sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    employee: Mapped["Employee"] = relationship(back_populates="face_enrollment")
    consent: Mapped[BiometricConsent] = relationship(back_populates="enrollment")
    samples: Mapped[list["EnrollmentSample"]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )


class EnrollmentSample(db.Model):
    __tablename__ = "enrollment_samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("face_enrollments.id"), nullable=False, index=True)
    storage_name: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    image_format: Mapped[str] = mapped_column(String(12), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    enrollment: Mapped[FaceEnrollment] = relationship(back_populates="samples")
