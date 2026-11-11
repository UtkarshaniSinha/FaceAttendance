"""Phase 3 recognition tests.

What these tests prove and what they do not:

* Matching rules (cosine similarity, thresholds, unknown and ambiguous
  decisions) are tested with hand-made vectors whose answers are known.
* The service and routes are tested with a FakeEmbedder that returns chosen
  vectors, so each test controls who "looks like" whom.
* The REAL YuNet/SFace files are tested only for loading, embedding shape,
  determinism, and "no face in a synthetic image". No real faces are used
  (no approved face data exists), so these tests do NOT show that real
  people are recognised correctly. That needs a real webcam test.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pytest

from app.extensions import db
from app.models import Employee, FaceTemplate
from app.recognition.embedder import (
    EMBEDDING_SIZE,
    MODEL_NAME,
    RecognitionImageError,
    RecognitionUnavailable,
    SFaceEmbedder,
    embedding_from_bytes,
    embedding_to_bytes,
)
from app.recognition.matcher import MatchStatus, cosine_similarity, l2_normalize, match_embedding
from config import Config
from test_enrollment import FACE, StubDetector, make_image

THRESHOLD, MARGIN = 0.45, 0.05


def unit(index: int) -> np.ndarray:
    vector = np.zeros(EMBEDDING_SIZE, dtype=np.float32)
    vector[index] = 1.0
    return vector


def blend(a: np.ndarray, b: np.ndarray, weight_b: float) -> np.ndarray:
    return l2_normalize(a + weight_b * b)


class FakeEmbedder:
    """Stands in for SFace. Returns queued vectors; None means "no usable face"."""

    model_name = MODEL_NAME

    def __init__(self) -> None:
        self.vectors: list[np.ndarray | None] = []
        self.boxes = [FACE]

    def detect_boxes(self, _image):
        return list(self.boxes)

    def embed_single(self, _image):
        if not self.boxes:
            raise RecognitionImageError("No face was detected. Face the camera in good light.")
        if len(self.boxes) > 1:
            raise RecognitionImageError("More than one face is visible. Only one person should be in the frame.")
        vector = self.vectors.pop(0)
        if vector is None:
            raise RecognitionImageError("No face was detected. Face the camera in good light.")
        return l2_normalize(vector)


@pytest.fixture()
def fake(app):
    app.extensions["face_detector"] = StubDetector()  # enrolment upload checks
    embedder = FakeEmbedder()
    app.extensions["face_embedder"] = embedder
    return embedder


def add_employee(app, code: str, name: str) -> int:
    with app.app_context():
        employee = Employee(employee_code=code, full_name=name)
        db.session.add(employee)
        db.session.commit()
        return employee.id


def enrol(client, app, fake, code: str, name: str, vectors, *, complete: bool = True) -> int:
    employee_id = add_employee(app, code, name)
    base = f"/employees/{employee_id}/enrollment"
    client.post(f"{base}/consent", data={"affirm": "yes"})
    client.post(f"{base}/start")
    for _ in range(3):
        response = client.post(f"{base}/samples", data={"image": (BytesIO(make_image()), "c.jpg")},
                               content_type="multipart/form-data", headers={"Accept": "application/json"})
        assert response.status_code == 201
    if complete:
        fake.vectors = list(vectors)
        client.post(f"{base}/complete")
    return employee_id


def identify(client, image: bytes | None = None, **kwargs):
    return client.post("/recognition/identify",
                       data={"image": (BytesIO(image if image is not None else make_image()), "probe.jpg")},
                       content_type="multipart/form-data", headers={"Accept": "application/json"}, **kwargs)


def templates_for(app, employee_id: int) -> int:
    with app.app_context():
        return db.session.query(FaceTemplate).filter_by(employee_id=employee_id).count()


# ----------------------------------------------------------- cosine similarity


def test_cosine_similarity_known_values():
    a = unit(0)
    assert cosine_similarity(a, a) == pytest.approx(1.0)
    assert cosine_similarity(a, unit(1)) == pytest.approx(0.0)
    assert cosine_similarity(a, -a) == pytest.approx(-1.0)
    assert cosine_similarity(a, 7.5 * a) == pytest.approx(1.0)  # length does not matter
    assert cosine_similarity(a, blend(unit(0), unit(1), 1.0)) == pytest.approx(1 / np.sqrt(2))


def test_cosine_similarity_rejects_invalid_vectors():
    with pytest.raises(ValueError, match="non-zero"):
        cosine_similarity(np.zeros(EMBEDDING_SIZE), unit(0))
    with pytest.raises(ValueError, match="same length"):
        cosine_similarity(unit(0), np.ones(64))
    with pytest.raises(ValueError, match="finite"):
        cosine_similarity(np.full(EMBEDDING_SIZE, np.nan), unit(0))


# ----------------------------------------------------------- matching decisions


def test_closest_employee_above_threshold_is_matched():
    gallery = {1: [unit(0)], 2: [unit(1)]}
    result = match_embedding(blend(unit(0), unit(2), 0.3), gallery, threshold=THRESHOLD, ambiguity_margin=MARGIN)
    assert result.status is MatchStatus.MATCH and result.employee_id == 1
    assert result.best_score > THRESHOLD and result.runner_up_score == pytest.approx(0.0)


def test_unknown_face_below_threshold_is_rejected():
    result = match_embedding(unit(5), {1: [unit(0)], 2: [unit(1)]}, threshold=THRESHOLD, ambiguity_margin=MARGIN)
    assert result.status is MatchStatus.UNKNOWN and result.employee_id is None


def test_threshold_is_configurable():
    probe = blend(unit(0), unit(1), 1.0)  # similarity 0.707 to employee 1
    gallery = {1: [unit(0)]}
    assert match_embedding(probe, gallery, threshold=0.60, ambiguity_margin=MARGIN).status is MatchStatus.MATCH
    assert match_embedding(probe, gallery, threshold=0.80, ambiguity_margin=MARGIN).status is MatchStatus.UNKNOWN


def test_near_tie_between_two_employees_is_ambiguous_not_a_guess():
    gallery = {1: [unit(0)], 2: [blend(unit(0), unit(1), 0.1)]}  # 1.0 vs 0.995
    result = match_embedding(unit(0), gallery, threshold=THRESHOLD, ambiguity_margin=MARGIN)
    assert result.status is MatchStatus.AMBIGUOUS and result.employee_id is None
    relaxed = match_embedding(unit(0), gallery, threshold=THRESHOLD, ambiguity_margin=0.0)
    assert relaxed.status is MatchStatus.MATCH and relaxed.employee_id == 1


def test_employee_score_is_their_best_template():
    gallery = {1: [unit(3), unit(0)], 2: [blend(unit(0), unit(1), 1.0)]}
    result = match_embedding(unit(0), gallery, threshold=THRESHOLD, ambiguity_margin=MARGIN)
    assert result.employee_id == 1 and result.best_score == pytest.approx(1.0)


def test_empty_gallery_means_unknown():
    result = match_embedding(unit(0), {}, threshold=THRESHOLD, ambiguity_margin=MARGIN)
    assert result.status is MatchStatus.UNKNOWN and result.best_score is None


@pytest.mark.parametrize(("threshold", "margin"), [(1.5, 0.05), (-2.0, 0.05), (0.4, -0.1)],
                         ids=["threshold-too-high", "threshold-too-low", "negative-margin"])
def test_invalid_threshold_settings_are_refused(threshold, margin):
    with pytest.raises(ValueError):
        match_embedding(unit(0), {1: [unit(0)]}, threshold=threshold, ambiguity_margin=margin)


def test_embedding_storage_round_trip_and_size_check():
    vector = blend(unit(0), unit(9), 0.5)
    data = embedding_to_bytes(vector)
    assert len(data) == EMBEDDING_SIZE * 4
    assert np.allclose(embedding_from_bytes(data), vector)
    with pytest.raises(ValueError):
        embedding_from_bytes(data[:100])


# ----------------------------------------------------------- missing model files


def test_missing_model_files_give_a_clear_error_without_paths(tmp_path, app):
    config = dict(app.config, RECOGNITION_MODEL_DIR=str(tmp_path / "private-model-dir"))
    with pytest.raises(RecognitionUnavailable) as error:
        SFaceEmbedder(config)
    message = str(error.value)
    assert "face_recognition_sface_2021dec.onnx" in message and "face_detection_yunet_2023mar.onnx" in message
    assert "private-model-dir" not in message


def test_identify_returns_503_json_when_model_missing(client):
    response = identify(client)
    assert response.status_code == 503
    assert "not installed" in response.get_json()["error"]


def test_recognition_page_reports_missing_model(client):
    page = client.get("/recognition/")
    assert page.status_code == 200
    assert b"Model not installed" in page.data
    assert b"Face check-in" in page.data and b"Unknown or ambiguous faces never do" in page.data


def test_enrolment_still_completes_when_model_missing(client, app):
    app.extensions["face_detector"] = StubDetector()
    employee_id = add_employee(app, "EMP-1", "Asha Rao")
    base = f"/employees/{employee_id}/enrollment"
    client.post(f"{base}/consent", data={"affirm": "yes"})
    client.post(f"{base}/start")
    for _ in range(3):
        client.post(f"{base}/samples", data={"image": (BytesIO(make_image()), "c.jpg")},
                    content_type="multipart/form-data")
    response = client.post(f"{base}/complete", follow_redirects=True)
    assert b"Face enrolment is complete" in response.data
    assert b"Recognition templates were not generated" in response.data
    assert b"Successfully enrolled" in response.data
    assert templates_for(app, employee_id) == 0


# ----------------------------------------------------------- real model files

REAL_MODEL_DIR = Path(Config.RECOGNITION_MODEL_DIR)
REAL_MODELS_PRESENT = all((REAL_MODEL_DIR / name).is_file()
                          for name in (Config.FACE_DETECTOR_MODEL, Config.FACE_RECOGNIZER_MODEL))
needs_real_models = pytest.mark.skipif(
    not REAL_MODELS_PRESENT, reason="SFace/YuNet files are not installed in instance/models (see Setup in README.md)"
)


@pytest.fixture()
def real_embedder(app):
    return SFaceEmbedder(dict(app.config, RECOGNITION_MODEL_DIR=str(REAL_MODEL_DIR)))


@needs_real_models
def test_real_sface_model_produces_deterministic_unit_embeddings(real_embedder):
    image = np.random.default_rng(3).integers(0, 255, (300, 300, 3), dtype=np.uint8)
    # A plausible detection row: box, 5 landmarks (eyes, nose, mouth corners), score.
    row = np.array([50, 50, 200, 200, 110, 120, 190, 120, 150, 165, 115, 205, 185, 205, 0.99], dtype=np.float32)
    first, second = real_embedder.embed_face(image, row), real_embedder.embed_face(image, row)
    assert first.shape == (EMBEDDING_SIZE,)
    assert np.linalg.norm(first) == pytest.approx(1.0, abs=1e-5)
    assert cosine_similarity(first, second) == pytest.approx(1.0, abs=1e-6)


@needs_real_models
def test_real_yunet_detector_finds_no_face_in_synthetic_images(real_embedder):
    for kind in ("good", "flat"):
        image = np.asarray(__import__("PIL.Image", fromlist=["Image"]).open(BytesIO(make_image(kind))).convert("RGB"))[:, :, ::-1]
        assert real_embedder.detect_boxes(np.ascontiguousarray(image)) == []
        with pytest.raises(RecognitionImageError, match="No face"):
            real_embedder.embed_single(np.ascontiguousarray(image))


# ----------------------------------------------------------- templates and enrolment


def test_templates_are_generated_when_enrolment_completes(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    assert templates_for(app, employee_id) == 3
    with app.app_context():
        assert {t.model_name for t in db.session.query(FaceTemplate)} == {MODEL_NAME}
    page = client.get(f"/employees/{employee_id}/enrollment/").data
    assert b"3 of 3 images" in page


def test_images_the_recognition_detector_rejects_are_skipped(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0), None, unit(0)])
    assert templates_for(app, employee_id) == 2
    page = client.get(f"/employees/{employee_id}/enrollment/").data
    assert b"2 of 3 images" in page


def test_regenerating_templates_does_not_duplicate_them(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(1)] * 3
    response = client.post(f"/employees/{employee_id}/enrollment/templates", follow_redirects=True)
    assert b"generated for all 3 images" in response.data
    assert templates_for(app, employee_id) == 3


# ----------------------------------------------------------- identification


def test_enrolled_employee_is_identified_without_exposing_biometric_data(client, app, fake):
    asha = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    enrol(client, app, fake, "EMP-2", "Kiran Shah", [unit(1)] * 3)
    fake.vectors = [blend(unit(0), unit(7), 0.2)]

    response = identify(client)
    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == "match" and body["employee"] == {"id": asha, "full_name": "Asha Rao", "employee_code": "EMP-1"}
    assert body["similarity"] > THRESHOLD and body["gallery_size"] == 2
    assert set(body) == {"status", "message", "employee", "similarity", "runner_up", "gallery_size"}
    text = response.get_data(as_text=True)
    assert "embedding" not in text and ".jpg" not in text and "Kiran" not in text


def test_unknown_face_is_rejected(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(9)]
    body = identify(client).get_json()
    assert body["status"] == "unknown" and body["employee"] is None


def test_lookalike_employees_produce_ambiguous_result(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    enrol(client, app, fake, "EMP-2", "Kiran Shah", [blend(unit(0), unit(1), 0.1)] * 3)
    fake.vectors = [unit(0)]
    body = identify(client).get_json()
    assert body["status"] == "ambiguous" and body["employee"] is None


@pytest.mark.parametrize(
    ("image_kind", "boxes", "status", "message"),
    [
        pytest.param("good", [], 400, "No face was detected", id="no-face"),
        pytest.param("good", [FACE, (10, 10, 150, 150)], 400, "More than one face", id="two-faces"),
        pytest.param("dark", [FACE], 400, "too dark", id="dark"),
        pytest.param("blurry", [FACE], 400, "too blurry", id="blurry"),
        pytest.param("not-an-image", [FACE], 400, "not a valid image", id="not-an-image"),
    ],
)
def test_invalid_and_poor_quality_captures_are_rejected(client, app, fake, image_kind, boxes, status, message):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.boxes = boxes
    fake.vectors = [unit(0)]  # would match if the capture were accepted
    payload = b"not an image" if image_kind == "not-an-image" else make_image(image_kind)
    response = identify(client, payload)
    assert response.status_code == status
    assert message in response.get_json()["error"]


def test_identify_requires_a_valid_csrf_token(client, fake):
    assert identify(client, csrf_token="forged").status_code == 400


def test_logs_contain_the_outcome_only(client, app, fake, caplog):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]
    with caplog.at_level("INFO", logger=app.logger.name):
        identify(client)
    messages = [record.getMessage() for record in caplog.records if record.name == app.logger.name]
    assert messages == ["Recognition test: match"]


def test_identification_records_no_attendance(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]
    assert identify(client).get_json()["status"] == "match"
    assert b">0<" in client.get("/").data.split(b"Present today")[1][:80]


# ----------------------------------------------------------- consent compatibility


def test_withdrawing_consent_deletes_templates_and_stops_recognition(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    client.post(f"/employees/{employee_id}/enrollment/withdraw")
    assert templates_for(app, employee_id) == 0
    fake.vectors = [unit(0)]
    body = identify(client).get_json()
    assert body["status"] == "unknown" and body["gallery_size"] == 0


def test_deleting_face_images_deletes_templates(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    client.post(f"/employees/{employee_id}/enrollment/delete")
    assert templates_for(app, employee_id) == 0


def test_inactive_employee_is_not_recognised(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    client.post(f"/employees/{employee_id}/deactivate")
    fake.vectors = [unit(0)]
    assert identify(client).get_json()["status"] == "unknown"


def test_unfinished_enrolment_is_not_in_the_gallery(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [], complete=False)
    fake.vectors = [unit(0)]
    body = identify(client).get_json()
    assert body["status"] == "unknown" and body["gallery_size"] == 0


def test_templates_of_an_enrolment_that_is_not_complete_are_ignored(client, app, fake):
    # Normal use cannot reach this state; the gallery query must still be safe.
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    with app.app_context():
        db.session.get(Employee, employee_id).face_enrollment.status = "in_progress"
        db.session.commit()
    assert templates_for(app, employee_id) == 3
    fake.vectors = [unit(0)]
    body = identify(client).get_json()
    assert body["status"] == "unknown" and body["gallery_size"] == 0


# ---------------------------------------------- enrolment uses the same detector


def _start_capture(client, app, code="EMP-Y1", name="Yash Kale"):
    employee_id = add_employee(app, code, name)
    base = f"/employees/{employee_id}/enrollment"
    client.post(f"{base}/consent", data={"affirm": "yes"})
    client.post(f"{base}/start")
    return base


def _upload(client, base):
    return client.post(f"{base}/samples", data={"image": (BytesIO(make_image()), "c.jpg")},
                       content_type="multipart/form-data", headers={"Accept": "application/json"})


def test_enrolment_photos_are_checked_with_the_recognition_detector(client, app, fake):
    del app.extensions["face_detector"]  # no test stub: the app must pick the YuNet detector itself
    base = _start_capture(client, app)

    fake.boxes = [FACE, (20, 20, 160, 160)]  # YuNet sees a second face the old Haar check could miss
    two = _upload(client, base)
    assert two.status_code == 400 and "More than one face" in two.get_json()["error"]

    fake.boxes = []
    none = _upload(client, base)
    assert none.status_code == 400 and "No face was detected" in none.get_json()["error"]

    fake.boxes = [FACE]
    assert _upload(client, base).status_code == 201


def test_enrolment_falls_back_to_haar_when_models_are_missing(client, app):
    from app.utils.face_detector import HaarFaceDetector

    app.extensions.pop("face_detector", None)
    app.extensions.pop("face_embedder", None)  # model folder in tests is empty -> RecognitionUnavailable
    base = _start_capture(client, app, "EMP-Y2", "Meera Iyer")
    response = _upload(client, base)  # synthetic image has no real face
    assert response.status_code == 400 and "No face was detected" in response.get_json()["error"]
    assert isinstance(app.extensions["haar_face_detector"], HaarFaceDetector)


def test_installed_test_detector_still_takes_priority(client, app, fake):
    fake.boxes = []  # the embedder would say "no face" ...
    base = _start_capture(client, app, "EMP-Y3", "Kabir Shah")
    assert _upload(client, base).status_code == 201  # ... but the stub detector installed by the test wins
