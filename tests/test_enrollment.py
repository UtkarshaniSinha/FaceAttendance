"""Face-enrolment workflow tests.

No real face photos are used (the celebrity dataset is rejected and no new
data has been approved). Images are synthetic, and a stub detector stands in
for OpenCV so each test controls how many faces are "found" and where.
Separate tests check the real OpenCV detector on images without faces.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.extensions import db
from app.models import Attendance, BiometricConsent, Employee, EnrollmentSample, FaceEnrollment
from app.utils.biometric_storage import BiometricStorage
from app.utils.face_detector import HaarFaceDetector
from app.utils.image_validator import ImageValidationError, ImageValidator

FACE = (200, 120, 240, 240)  # x, y, width, height inside a 640x480 frame


class StubDetector:
    def __init__(self, boxes=(FACE,)):
        self.boxes = list(boxes)

    def detect(self, _image):
        return list(self.boxes)


def make_image(kind: str = "good", size=(640, 480), fmt: str = "JPEG", exif: bool = False) -> bytes:
    """Synthetic test images whose face region has known quality properties."""

    width, height = size
    rng = np.random.default_rng(7)
    if kind == "good":  # mid brightness, strong fine detail
        pixels = rng.integers(60, 190, (height, width), dtype=np.uint8)
    elif kind == "dark":
        pixels = rng.integers(0, 30, (height, width), dtype=np.uint8)
    elif kind == "bright":
        pixels = rng.integers(235, 256, (height, width), dtype=np.uint8)
    elif kind == "flat":  # almost no contrast
        pixels = rng.integers(124, 132, (height, width), dtype=np.uint8)
    elif kind == "blurry":  # strong but smooth light/dark waves, no fine detail
        x = np.arange(width)
        wave = 128 + 70 * np.sin(2 * np.pi * x / FACE[2])
        pixels = np.tile(wave, (height, 1)).astype(np.uint8)
    else:
        raise ValueError(kind)
    image = Image.fromarray(np.stack([pixels] * 3, axis=-1))
    buffer = BytesIO()
    if exif:
        metadata = Image.Exif()
        metadata[0x010F] = "SecretCameraMaker"  # EXIF "Make"
        image.save(buffer, fmt, exif=metadata)
    else:
        image.save(buffer, fmt)
    return buffer.getvalue()


@pytest.fixture()
def detector(app):
    stub = StubDetector()
    app.extensions["face_detector"] = stub
    return stub


@pytest.fixture()
def employee_id(app):
    with app.app_context():
        employee = Employee(employee_code="EMP-900", full_name="Neha Kulkarni", department="QA")
        db.session.add(employee)
        db.session.commit()
        return employee.id


def base(employee_id):
    return f"/employees/{employee_id}/enrollment"


def consent_and_start(client, employee_id):
    client.post(f"{base(employee_id)}/consent", data={"affirm": "yes"})
    return client.post(f"{base(employee_id)}/start")


def upload(client, employee_id, data: bytes, filename="capture.jpg"):
    return client.post(
        f"{base(employee_id)}/samples",
        data={"image": (BytesIO(data), filename)},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )


def stored_files(app) -> list[Path]:
    return sorted(Path(app.config["BIOMETRIC_STORAGE_PATH"]).iterdir())


# ---------------------------------------------------------------- consent


def test_new_employee_needs_consent(client, employee_id):
    page = client.get(f"{base(employee_id)}/")
    assert page.status_code == 200
    assert b"Consent required" in page.data
    assert b"What is collected" in page.data


def test_consent_requires_the_explicit_checkbox(client, app, employee_id):
    response = client.post(f"{base(employee_id)}/consent", data={}, follow_redirects=True)
    assert b"Consent was not recorded" in response.data
    with app.app_context():
        assert db.session.query(BiometricConsent).count() == 0


def test_capture_cannot_start_without_consent(client, app, employee_id):
    response = client.post(f"{base(employee_id)}/start", follow_redirects=True)
    assert b"consent is required" in response.data
    assert client.get(f"{base(employee_id)}/capture").status_code == 302
    with app.app_context():
        assert db.session.query(FaceEnrollment).count() == 0


def test_upload_is_refused_before_enrolment_starts(client, employee_id, detector):
    client.post(f"{base(employee_id)}/consent", data={"affirm": "yes"})
    response = upload(client, employee_id, make_image())
    assert response.status_code == 400
    assert "Start an enrolment" in response.get_json()["error"]


def test_inactive_employee_cannot_consent_or_enrol(client, app, employee_id):
    with app.app_context():
        db.session.get(Employee, employee_id).is_active = False
        db.session.commit()
    response = client.post(f"{base(employee_id)}/consent", data={"affirm": "yes"}, follow_redirects=True)
    assert b"Inactive employees cannot" in response.data


# ---------------------------------------------------------------- happy path


def test_full_enrolment_workflow(client, app, employee_id, detector):
    start = consent_and_start(client, employee_id)
    assert start.status_code == 302 and start.headers["Location"].endswith("/capture")

    capture_page = client.get(f"{base(employee_id)}/capture")
    assert capture_page.status_code == 200
    assert b"Start camera" in capture_page.data

    for expected_count in (1, 2, 3):
        response = upload(client, employee_id, make_image())
        assert response.status_code == 201, response.get_json()
        body = response.get_json()
        assert body["accepted_sample_count"] == expected_count
        assert set(body["quality"]) == {"brightness", "contrast", "sharpness", "face_width"}
        assert "storage" not in response.get_data(as_text=True)  # no file names or paths leak

    done = client.post(f"{base(employee_id)}/complete", follow_redirects=True)
    assert b"Face enrolment is complete" in done.data
    assert b"Successfully enrolled" in done.data

    with app.app_context():
        enrollment = db.session.query(FaceEnrollment).one()
        assert enrollment.status == "complete"
        assert enrollment.accepted_sample_count == 3
        names = {sample.storage_name for sample in enrollment.samples}

    files = stored_files(app)
    assert {f.name for f in files} == names
    assert all(len(f.stem) >= 30 and f.suffix == ".jpg" for f in files)  # random, unguessable names
    static_folder = Path(app.static_folder).resolve()
    assert all(static_folder not in f.resolve().parents for f in files)  # never publicly served

    assert b"Successfully enrolled" in client.get("/employees").data
    assert b"Successfully enrolled" in client.get(f"/employees/{employee_id}").data
    dashboard = client.get("/").data
    assert b"Faces enrolled" in dashboard and b">1<" in dashboard


def test_completion_requires_the_minimum_number_of_images(client, app, employee_id, detector):
    consent_and_start(client, employee_id)
    upload(client, employee_id, make_image())
    response = client.post(f"{base(employee_id)}/complete", follow_redirects=True)
    assert b"At least 3 accepted images" in response.data
    with app.app_context():
        assert db.session.query(FaceEnrollment).one().status == "in_progress"


def test_completed_enrolment_cannot_be_restarted_without_deleting(client, employee_id, detector):
    consent_and_start(client, employee_id)
    for _ in range(3):
        upload(client, employee_id, make_image())
    client.post(f"{base(employee_id)}/complete")
    response = client.post(f"{base(employee_id)}/start", follow_redirects=True)
    assert b"already enrolled" in response.data


def test_maximum_number_of_images_is_enforced(client, app, employee_id, detector):
    app.config["ENROLLMENT_MAX_SAMPLES"] = 2
    consent_and_start(client, employee_id)
    upload(client, employee_id, make_image())
    upload(client, employee_id, make_image())
    response = upload(client, employee_id, make_image())
    assert response.status_code == 400
    assert "maximum of 2" in response.get_json()["error"]
    assert len(stored_files(app)) == 2


# ---------------------------------------------------------------- image validation


@pytest.mark.parametrize(
    ("boxes", "kind", "message"),
    [
        ([], "good", "No face was detected"),
        ([FACE, (10, 10, 150, 150)], "good", "More than one face"),
        ([(10, 10, 80, 80)], "good", "too small"),
        ([FACE], "dark", "too dark"),
        ([FACE], "bright", "overexposed"),
        ([FACE], "flat", "too little contrast"),
        ([FACE], "blurry", "too blurry"),
    ],
)
def test_unsuitable_images_are_rejected_and_not_stored(client, app, employee_id, detector, boxes, kind, message):
    detector.boxes = boxes
    consent_and_start(client, employee_id)
    response = upload(client, employee_id, make_image(kind))
    assert response.status_code == 400
    assert message in response.get_json()["error"]
    assert stored_files(app) == []


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"", "empty"),
        (b"this is not an image at all", "not a valid image"),
        (make_image(fmt="GIF"), "Only JPEG and PNG"),
        (make_image(size=(100, 80)), "too small for reliable"),
        (make_image()[:400], "corrupt or unreadable"),
    ],
)
def test_invalid_files_are_rejected(client, app, employee_id, detector, payload, message):
    consent_and_start(client, employee_id)
    response = upload(client, employee_id, payload)
    assert response.status_code == 400
    assert message in response.get_json()["error"]
    assert stored_files(app) == []


def test_upload_over_the_size_limit_returns_json_413(client, app, employee_id, detector):
    app.config["MAX_CONTENT_LENGTH"] = 10_000
    consent_and_start(client, employee_id)
    response = upload(client, employee_id, make_image())
    assert response.status_code == 413
    assert "upload limit" in response.get_json()["error"]


def test_huge_resolution_is_rejected(app, detector):
    config = dict(app.config, ENROLLMENT_MAX_IMAGE_PIXELS=640 * 480 - 1)
    with pytest.raises(ImageValidationError, match="resolution is too large"):
        ImageValidator(config, detector=detector).validate(make_image())


def test_png_is_accepted_and_stored_as_metadata_free_jpeg(app, detector):
    validator = ImageValidator(app.config, detector=detector)
    for data in (make_image(fmt="PNG"), make_image(exif=True)):
        result = validator.validate(data)
        assert result.image_format == "jpg"
        with Image.open(BytesIO(result.data)) as stored:
            assert stored.format == "JPEG"
            assert "SecretCameraMaker" not in str(dict(stored.getexif()))


def test_real_opencv_detector_rejects_images_without_a_face(app):
    validator = ImageValidator(app.config, detector=HaarFaceDetector())
    for kind in ("good", "blurry"):
        with pytest.raises(ImageValidationError, match="No face was detected"):
            validator.validate(make_image(kind))


# ---------------------------------------------------------------- retake / delete / withdraw


def test_discarding_an_accepted_image_deletes_the_file(client, app, employee_id, detector):
    consent_and_start(client, employee_id)
    first = upload(client, employee_id, make_image()).get_json()["sample_id"]
    upload(client, employee_id, make_image())
    assert len(stored_files(app)) == 2

    response = client.post(f"{base(employee_id)}/samples/{first}/delete", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.get_json()["accepted_sample_count"] == 1
    assert len(stored_files(app)) == 1
    with app.app_context():
        assert db.session.get(EnrollmentSample, first) is None


def test_cannot_discard_another_employees_image(client, app, employee_id, detector):
    consent_and_start(client, employee_id)
    sample_id = upload(client, employee_id, make_image()).get_json()["sample_id"]
    with app.app_context():
        other = Employee(employee_code="EMP-901", full_name="Other Person")
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    consent_and_start(client, other_id)

    response = client.post(f"{base(other_id)}/samples/{sample_id}/delete", headers={"Accept": "application/json"})
    assert response.status_code == 400
    assert len(stored_files(app)) == 1


def test_delete_biometric_data_keeps_consent(client, app, employee_id, detector):
    consent_and_start(client, employee_id)
    for _ in range(3):
        upload(client, employee_id, make_image())
    response = client.post(f"{base(employee_id)}/delete", follow_redirects=True)
    assert b"3 stored face image(s) were deleted" in response.data
    assert b"Not enrolled" in response.data
    assert stored_files(app) == []
    with app.app_context():
        assert db.session.query(FaceEnrollment).count() == 0
        assert db.session.query(EnrollmentSample).count() == 0
        assert db.session.query(BiometricConsent).one().is_valid


def test_withdrawing_consent_deletes_images_but_keeps_attendance(client, app, employee_id, detector):
    with app.app_context():
        db.session.add(Attendance(employee_id=employee_id, attendance_date=date.today(),
                                  check_in_time=datetime.now(timezone.utc)))
        db.session.commit()
    consent_and_start(client, employee_id)
    for _ in range(3):
        upload(client, employee_id, make_image())
    client.post(f"{base(employee_id)}/complete")

    response = client.post(f"{base(employee_id)}/withdraw", follow_redirects=True)
    assert b"Consent was withdrawn" in response.data
    assert b"Consent withdrawn" in response.data
    assert stored_files(app) == []
    with app.app_context():
        consent = db.session.query(BiometricConsent).one()
        assert consent.status == "withdrawn" and consent.withdrawn_at is not None
        assert db.session.query(EnrollmentSample).count() == 0
        assert db.session.query(Attendance).count() == 1  # history preserved

    # Withdrawal blocks further capture until consent is given again.
    assert client.post(f"{base(employee_id)}/start").status_code == 302
    assert upload(client, employee_id, make_image()).status_code == 400
    regranted = client.post(f"{base(employee_id)}/consent", data={"affirm": "yes"}, follow_redirects=True)
    assert b"Biometric consent was recorded" in regranted.data


def test_failed_database_write_removes_the_stored_file(client, app, employee_id, detector, monkeypatch):
    consent_and_start(client, employee_id)

    def broken_commit():
        raise RuntimeError("simulated database failure")

    with app.app_context():
        monkeypatch.setattr(db.session, "commit", broken_commit)
        with pytest.raises(RuntimeError):
            upload(client, employee_id, make_image())
    assert stored_files(app) == []


# ---------------------------------------------------------------- storage safety


def test_storage_refuses_path_traversal_and_unknown_formats(tmp_path):
    storage = BiometricStorage(str(tmp_path / "private"))
    outside = tmp_path / "keep.txt"
    outside.write_text("must survive")

    storage.delete("../keep.txt")  # only the bare file name is ever used
    assert outside.exists()
    with pytest.raises(ValueError):
        storage.store(b"data", "exe")

    name = storage.store(b"bytes", "jpg")
    assert "/" not in name and "\\" not in name
    storage.delete(name)
    assert list((tmp_path / "private").iterdir()) == []
