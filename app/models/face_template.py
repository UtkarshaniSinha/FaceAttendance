"""Face templates: the embedding generated from one accepted enrolment image."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class FaceTemplate(db.Model):
    """Biometric data: 128 float32 numbers derived from a face image.

    One template per enrolment sample. Deleting the sample (delete images,
    withdraw consent) deletes the template too, through both the ORM cascade
    and the database foreign key. Templates are never sent to the browser.
    """

    __tablename__ = "face_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_id: Mapped[int] = mapped_column(
        ForeignKey("enrollment_samples.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    sample: Mapped["EnrollmentSample"] = relationship(back_populates="template")

    def __repr__(self) -> str:  # never include the embedding itself
        return f"<FaceTemplate sample={self.sample_id} model={self.model_name}>"
