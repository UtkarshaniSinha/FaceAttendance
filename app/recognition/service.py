"""Recognition service: templates from consented enrolments, identification of captures.

Who is in the gallery (the set of people a capture is compared against)?
Only employees who are ALL of: active, holding valid consent, with a
completed enrolment, and with templates made by the current model.
Withdrawing consent or deleting images removes templates entirely.

This service never records attendance (that is a later phase).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import cv2
import numpy as np
from flask import current_app
from sqlalchemy import select

from app.extensions import db
from app.models import BiometricConsent, Employee, EnrollmentSample, FaceEnrollment, FaceTemplate
from app.recognition.embedder import (
    EmbedderBoxDetector,
    RecognitionImageError,
    RecognitionUnavailable,
    SFaceEmbedder,
    embedding_from_bytes,
    embedding_to_bytes,
)
from app.recognition.matcher import MatchStatus, match_embedding
from app.services.face_enrollment_service import current_notice_version, has_current_consent
from app.utils.biometric_storage import BiometricStorage
from app.utils.image_validator import ImageValidationError, ImageValidator

__all__ = [
    "RecognitionImageError",
    "RecognitionUnavailable",
    "TemplateReport",
    "IdentificationResult",
    "get_embedder",
    "build_templates",
    "template_count",
    "load_gallery",
    "identify",
]


def get_embedder():
    """Load the models once per app. A failure is not cached, so installing
    the model files later works without restarting the server."""

    embedder = current_app.extensions.get("face_embedder")
    if embedder is None:
        embedder = SFaceEmbedder(current_app.config)
        current_app.extensions["face_embedder"] = embedder
    return embedder


def _decode(image_bytes: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise RecognitionImageError("The image could not be read.")
    return image


@dataclass(frozen=True)
class TemplateReport:
    created: int
    skipped: int  # stored images in which the recognition detector found no single face

    @property
    def total(self) -> int:
        return self.created + self.skipped


def build_templates(employee: Employee, storage: BiometricStorage, embedder=None) -> TemplateReport:
    """Create (or refresh) one template per accepted enrolment image."""

    enrollment = employee.face_enrollment
    if not enrollment or enrollment.status != "complete":
        raise RecognitionImageError("Templates can only be generated for a completed enrolment.")
    if not has_current_consent(employee) or not employee.is_active:
        raise RecognitionImageError("Valid consent to the current notice from an active employee is required.")

    embedder = embedder or get_embedder()
    created = skipped = 0
    for sample in sorted(enrollment.samples, key=lambda s: s.id):
        try:
            embedding = embedder.embed_single(_decode(storage.read(sample.storage_name)))
        except (RecognitionImageError, FileNotFoundError):
            skipped += 1
            if sample.template is not None:
                sample.template = None  # an outdated template must not stay usable
            continue
        if sample.template is None:
            sample.template = FaceTemplate(employee_id=employee.id, model_name=embedder.model_name,
                                           embedding=embedding_to_bytes(embedding))
        else:
            sample.template.model_name = embedder.model_name
            sample.template.embedding = embedding_to_bytes(embedding)
        created += 1
    db.session.commit()
    return TemplateReport(created=created, skipped=skipped)


def template_count(employee: Employee, model_name: str | None = None) -> int:
    query = select(FaceTemplate).where(FaceTemplate.employee_id == employee.id)
    if model_name:
        query = query.where(FaceTemplate.model_name == model_name)
    return len(list(db.session.scalars(query)))


def load_gallery(model_name: str) -> dict[int, list[np.ndarray]]:
    """Templates of every employee who may currently be recognised:
    active, consent to the CURRENT notice, completed enrolment, same model."""

    rows = db.session.execute(
        select(FaceTemplate.employee_id, FaceTemplate.embedding)
        .join(EnrollmentSample, EnrollmentSample.id == FaceTemplate.sample_id)
        .join(FaceEnrollment, FaceEnrollment.id == EnrollmentSample.enrollment_id)
        .join(Employee, Employee.id == FaceTemplate.employee_id)
        .join(BiometricConsent, BiometricConsent.employee_id == Employee.id)
        .where(
            FaceTemplate.model_name == model_name,
            FaceEnrollment.status == "complete",
            Employee.is_active.is_(True),
            BiometricConsent.status == "granted",
            BiometricConsent.withdrawn_at.is_(None),
            # Consent to an older notice (which did not mention embeddings) does not count.
            BiometricConsent.notice_version == current_notice_version(),
        )
    )
    gallery: dict[int, list[np.ndarray]] = {}
    for employee_id, data in rows:
        gallery.setdefault(employee_id, []).append(embedding_from_bytes(data))
    return gallery


@dataclass(frozen=True)
class IdentificationResult:
    status: MatchStatus
    employee: Employee | None
    similarity: float | None
    runner_up: float | None
    gallery_size: int

    @property
    def message(self) -> str:
        if self.status is MatchStatus.MATCH:
            return f"Recognised {self.employee.full_name}."
        if self.status is MatchStatus.AMBIGUOUS:
            return "Two enrolled employees are too similar to this capture. No identity was chosen."
        if self.gallery_size == 0:
            return "No employees have recognition templates yet."
        return "This face does not match any enrolled employee closely enough."

    def to_json(self) -> dict:
        """Safe for the browser: no embeddings, no file names, no other employees."""

        return {
            "status": self.status.value,
            "message": self.message,
            "employee": None if self.employee is None else {
                "id": self.employee.id,
                "full_name": self.employee.full_name,
                "employee_code": self.employee.employee_code,
            },
            "similarity": None if self.similarity is None else round(self.similarity, 3),
            "runner_up": None if self.runner_up is None else round(self.runner_up, 3),
            "gallery_size": self.gallery_size,
        }


def identify(image_bytes: bytes, config: Mapping[str, object], embedder=None) -> IdentificationResult:
    """Validate a capture, embed it and compare it with the gallery."""

    embedder = embedder or get_embedder()
    # Same format, size and quality rules as enrolment, but faces are counted
    # and measured with the recognition detector (YuNet).
    try:
        validated = ImageValidator(config, detector=EmbedderBoxDetector(embedder)).validate(image_bytes)
    except ImageValidationError as error:
        raise RecognitionImageError(str(error)) from error
    probe = embedder.embed_single(_decode(validated.data))

    gallery = load_gallery(embedder.model_name)
    result = match_embedding(
        probe,
        gallery,
        threshold=float(config["RECOGNITION_MATCH_THRESHOLD"]),
        ambiguity_margin=float(config["RECOGNITION_AMBIGUITY_MARGIN"]),
    )
    employee = db.session.get(Employee, result.employee_id) if result.employee_id else None
    return IdentificationResult(result.status, employee, result.best_score, result.runner_up_score, len(gallery))
