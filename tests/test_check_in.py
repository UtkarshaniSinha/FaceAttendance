"""Phase 4: recognition -> eligibility -> attendance.

Synthetic embeddings (FakeEmbedder) and mocked recognition results make every
test deterministic. These tests prove the RULES, not real-world recognition
accuracy: no real faces are used.
"""

from __future__ import annotations

import ast
import threading
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from app import create_app
from app.extensions import db
from app.models import Attendance, Employee
from app.recognition.matcher import MatchStatus
from app.recognition.service import IdentificationResult
from app.services import attendance_service, check_in_service
from app.services.attendance_service import (
    DuplicateAttendanceError,
    attendance_day_for,
    organization_today,
    record_attendance,
)
from test_enrollment import make_image
from test_recognition import add_employee, blend, enrol, fake, unit  # noqa: F401 (fixture)

URL = "/recognition/check-in"


def check_in(client, image: bytes | None = None, **kwargs):
    return client.post(URL, data={"image": (BytesIO(image if image is not None else make_image()), "c.jpg")},
                       content_type="multipart/form-data", headers={"Accept": "application/json"}, **kwargs)


def attendance_rows(app) -> list[tuple[int, date, str]]:
    with app.app_context():
        return [(a.employee_id, a.attendance_date, a.recognition_method) for a in db.session.query(Attendance)]


def force_match(monkeypatch, app, employee_id: int, similarity: float = 0.95):
    """Mock the recognition result: pretend the engine returned MATCH for this employee."""

    def fake_identify(_image, _config, embedder=None):
        return IdentificationResult(MatchStatus.MATCH, db.session.get(Employee, employee_id), similarity, None, 1)

    monkeypatch.setattr(check_in_service.recognition_service, "identify", fake_identify)


# ------------------------------------------------------------ 1, 14: successful check-in


def test_confident_match_records_attendance_for_the_right_employee_and_day(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    kiran = enrol(client, app, fake, "EMP-2", "Kiran Shah", [unit(1)] * 3)
    fake.vectors = [blend(unit(1), unit(7), 0.2)]

    response = check_in(client)
    body = response.get_json()
    assert response.status_code == 201
    assert body["outcome"] == "recorded" and body["recorded"] is True
    assert body["employee"] == {"full_name": "Kiran Shah", "employee_code": "EMP-2"}
    with app.app_context():
        today = organization_today()
        record = db.session.query(Attendance).one()
        assert record.employee_id == kiran and record.attendance_date == today
        assert record.recognition_method == "face"
    assert body["attendance"]["date"] == today.isoformat()
    assert set(body) == {"outcome", "recorded", "message", "employee", "attendance", "similarity"}
    assert "embedding" not in response.get_data(as_text=True)


def test_attendance_day_uses_the_organisation_timezone(app):
    with app.app_context():
        # 20:00 UTC on 10 Nov is 01:30 on 11 Nov in Asia/Kolkata.
        assert attendance_day_for(datetime(2026, 11, 10, 20, 0, tzinfo=timezone.utc)) == date(2026, 11, 11)
        assert attendance_day_for(datetime(2026, 11, 10, 18, 29, tzinfo=timezone.utc)) == date(2026, 11, 10)
        employee = Employee(employee_code="EMP-9", full_name="Night Shift")
        db.session.add(employee)
        db.session.commit()
        record = record_attendance(employee, checked_in_at=datetime(2026, 11, 10, 20, 0, tzinfo=timezone.utc))
        assert record.attendance_date == date(2026, 11, 11)


# ------------------------------------------------------------ 2, 3: unknown and ambiguous


def test_unknown_face_records_no_attendance(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(9)]
    body = check_in(client).get_json()
    assert body["outcome"] == "unknown" and body["recorded"] is False and body["employee"] is None
    assert attendance_rows(app) == []


def test_ambiguous_match_records_no_attendance(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    enrol(client, app, fake, "EMP-2", "Kiran Shah", [blend(unit(0), unit(1), 0.1)] * 3)
    fake.vectors = [unit(0)]
    body = check_in(client).get_json()
    assert body["outcome"] == "ambiguous" and body["employee"] is None
    assert attendance_rows(app) == []


def test_low_confidence_match_is_rejected_even_if_reported_as_match(client, app, fake, monkeypatch):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    force_match(monkeypatch, app, employee_id, similarity=0.30)  # below the 0.45 threshold
    assert check_in(client).get_json()["outcome"] == "unknown"
    assert attendance_rows(app) == []


# ------------------------------------------------------------ 4-8: eligibility


def test_inactive_employee_cannot_check_in(client, app, fake, monkeypatch):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    client.post(f"/employees/{employee_id}/deactivate")
    fake.vectors = [unit(0)]
    assert check_in(client).get_json()["outcome"] == "unknown"  # real path: not in the gallery
    force_match(monkeypatch, app, employee_id)  # even if recognition said MATCH
    body = check_in(client).get_json()
    assert body["outcome"] == "inactive" and body["recorded"] is False
    assert attendance_rows(app) == []


def test_employee_without_consent_cannot_check_in(client, app, fake, monkeypatch):
    employee_id = add_employee(app, "EMP-1", "Asha Rao")
    force_match(monkeypatch, app, employee_id)
    assert check_in(client).get_json()["outcome"] == "consent_required"
    assert attendance_rows(app) == []


def test_employee_with_withdrawn_consent_cannot_check_in(client, app, fake, monkeypatch):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    client.post(f"/employees/{employee_id}/enrollment/withdraw")
    fake.vectors = [unit(0)]
    assert check_in(client).get_json()["outcome"] == "unknown"
    force_match(monkeypatch, app, employee_id)
    assert check_in(client).get_json()["outcome"] == "consent_required"
    assert attendance_rows(app) == []


def test_employee_with_outdated_consent_cannot_check_in(client, app, fake, monkeypatch):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    app.config["CONSENT_NOTICE_VERSION"] = "portfolio-v3"  # notice revised after consent
    fake.vectors = [unit(0)]
    assert check_in(client).get_json()["outcome"] == "unknown"
    force_match(monkeypatch, app, employee_id)
    assert check_in(client).get_json()["outcome"] == "consent_required"
    assert attendance_rows(app) == []


def test_employee_with_incomplete_enrolment_cannot_check_in(client, app, fake, monkeypatch):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [], complete=False)
    force_match(monkeypatch, app, employee_id)
    assert check_in(client).get_json()["outcome"] == "enrolment_incomplete"
    assert attendance_rows(app) == []


def test_employee_without_usable_templates_cannot_check_in(client, app, fake, monkeypatch):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [None, None, None])  # no usable face
    with app.app_context():
        assert db.session.get(Employee, employee_id).face_enrollment.status == "complete"
    force_match(monkeypatch, app, employee_id)
    assert check_in(client).get_json()["outcome"] == "enrolment_incomplete"
    assert attendance_rows(app) == []


def test_deleting_face_images_stops_future_check_ins(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    client.post(f"/employees/{employee_id}/enrollment/delete")
    fake.vectors = [unit(0)]
    assert check_in(client).get_json()["outcome"] == "unknown"
    assert attendance_rows(app) == []


# ------------------------------------------------------------ 9, 10: duplicates


def test_repeated_check_in_does_not_duplicate_attendance(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0), unit(0), unit(0)]
    first = check_in(client)
    second, third = check_in(client), check_in(client)
    assert first.status_code == 201
    for response in (second, third):
        body = response.get_json()
        assert response.status_code == 200
        assert body["outcome"] == "already_recorded" and body["recorded"] is False
        assert body["attendance"] == first.get_json()["attendance"]  # shows the original check-in time
    assert len(attendance_rows(app)) == 1


def test_race_past_the_duplicate_check_is_stopped_by_the_database(client, app, fake, monkeypatch):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0), unit(0)]
    assert check_in(client).status_code == 201
    # Simulate a second request whose duplicate check ran before the first one saved.
    real_lookup = attendance_service._existing_record
    calls = {"n": 0}

    def stale_then_real(employee, day):
        calls["n"] += 1
        return None if calls["n"] == 1 else real_lookup(employee, day)

    monkeypatch.setattr(attendance_service, "_existing_record", stale_then_real)
    body = check_in(client).get_json()
    assert body["outcome"] == "already_recorded"  # unique constraint caught it
    assert len(attendance_rows(app)) == 1


def test_concurrent_check_ins_create_exactly_one_record(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'race.db').as_posix()}",
        "SQLALCHEMY_ENGINE_OPTIONS": {"connect_args": {"timeout": 30}},
        "BIOMETRIC_STORAGE_PATH": str(tmp_path / "bio"),
        "RECOGNITION_MODEL_DIR": str(tmp_path / "models"),
    })
    with app.app_context():
        employee = Employee(employee_code="EMP-1", full_name="Asha Rao")
        db.session.add(employee)
        db.session.commit()
        employee_id = employee.id

    workers, barrier, outcomes = 8, threading.Barrier(8), []

    def attempt():
        with app.app_context():
            person = db.session.get(Employee, employee_id)
            barrier.wait()  # all threads try to record at the same moment
            try:
                record_attendance(person, recognition_method="face")
                outcomes.append("recorded")
            except DuplicateAttendanceError:
                outcomes.append("duplicate")
            except attendance_service.AttendanceStorageError:
                outcomes.append("storage-error")  # e.g. database locked: still not a success
            finally:
                db.session.remove()

    threads = [threading.Thread(target=attempt) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("recorded") == 1
    assert len(outcomes) == workers
    with app.app_context():
        assert db.session.query(Attendance).count() == 1
        db.session.remove()
        db.drop_all()


# ------------------------------------------------------------ 11, 12: failures


@pytest.mark.parametrize(
    ("setup", "status"),
    [
        pytest.param("no-face", 400, id="no-face"),
        pytest.param("two-faces", 400, id="two-faces"),
        pytest.param("not-an-image", 400, id="not-an-image"),
        pytest.param("dark", 400, id="dark"),
    ],
)
def test_failed_recognition_requests_record_nothing(client, app, fake, setup, status):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]  # would match if the capture were usable
    fake.boxes = {"no-face": [], "two-faces": [(200, 120, 240, 240), (10, 10, 150, 150)]}.get(setup, fake.boxes)
    payload = b"not an image" if setup == "not-an-image" else make_image("dark" if setup == "dark" else "good")
    response = check_in(client, payload)
    assert response.status_code == status
    assert "No attendance recorded" in response.get_json()["error"]
    assert attendance_rows(app) == []


def test_missing_model_records_nothing(client, app):
    response = check_in(client)
    assert response.status_code == 503 and "No attendance recorded" in response.get_json()["error"]
    assert attendance_rows(app) == []


def test_database_error_never_reports_success(client, app, fake, monkeypatch, caplog):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]

    def failing_commit():
        raise OperationalError("INSERT INTO attendance_records ...", {}, Exception("disk I/O error"))

    with app.app_context():
        monkeypatch.setattr(db.session, "commit", failing_commit)
        with caplog.at_level("ERROR", logger=app.logger.name):
            response = check_in(client)
    body = response.get_json()
    assert response.status_code == 500
    assert "NOT recorded" in body["error"] and "outcome" not in body and "recorded" not in body
    assert [r.getMessage() for r in caplog.records if r.name == app.logger.name] == ["Face check-in failed: OperationalError"]
    monkeypatch.undo()
    assert attendance_rows(app) == []


# ------------------------------------------------------------ 13: CSRF


def test_check_in_requires_a_valid_csrf_token(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]
    assert check_in(client, csrf_token="forged").status_code == 400
    assert check_in(client, csrf_token=None).status_code == 400
    assert attendance_rows(app) == []


# ------------------------------------------------------------ 15: separation and privacy


def test_recognition_package_never_imports_attendance_code():
    package = Path(__file__).resolve().parents[1] / "app" / "recognition"
    for source in package.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        imported += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not [m for m in imported if "attendance" in m or "check_in" in m], source.name


def test_identify_endpoint_still_records_nothing(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]
    response = client.post("/recognition/identify", data={"image": (BytesIO(make_image()), "c.jpg")},
                           content_type="multipart/form-data", headers={"Accept": "application/json"})
    assert response.get_json()["status"] == "match"
    assert attendance_rows(app) == []


def test_check_in_logs_the_outcome_only(client, app, fake, caplog):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]
    with caplog.at_level("INFO", logger=app.logger.name):
        check_in(client)
    assert [r.getMessage() for r in caplog.records if r.name == app.logger.name] == ["Face check-in: recorded"]


def test_dashboard_counts_face_check_ins_for_the_organisation_day(client, app, fake):
    enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]
    check_in(client)
    html = client.get("/").data
    assert b">1<" in html.split(b"Present today")[1][:80]
    assert b"face" in html  # recognition method shown as the source


def test_eligibility_reports_the_specific_reason(client, app, fake):
    from app.recognition.embedder import MODEL_NAME
    from app.services.attendance_eligibility import Ineligibility, check_eligibility

    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    with app.app_context():
        employee = db.session.get(Employee, employee_id)
        assert check_eligibility(employee, MODEL_NAME) is None
        assert check_eligibility(employee, "some-other-model") is Ineligibility.NO_TEMPLATES
        app.config["CONSENT_NOTICE_VERSION"] = "portfolio-v3"
        assert check_eligibility(employee, MODEL_NAME) is Ineligibility.CONSENT_OUTDATED
        app.config["CONSENT_NOTICE_VERSION"] = "portfolio-v2"
        employee.face_enrollment.status = "in_progress"
        assert check_eligibility(employee, MODEL_NAME) is Ineligibility.ENROLMENT_INCOMPLETE
        employee.is_active = False
        assert check_eligibility(employee, MODEL_NAME) is Ineligibility.INACTIVE
        db.session.rollback()
