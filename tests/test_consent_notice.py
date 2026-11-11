"""Consent notice content and notice-version behaviour.

Rule under test: consent given to an OLDER notice version is not consent to
the current notice. Until the employee consents again, no capture, no new
embeddings and no recognition happen. Existing photos and embeddings are
kept (not silently deleted), and the employee can still withdraw.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from app.extensions import db
from app.models import BiometricConsent, Employee, FaceEnrollment, FaceTemplate
from config import Config
from test_enrollment import make_image
from test_recognition import add_employee, enrol, fake, identify, templates_for, unit  # noqa: F401 (fixture)

CURRENT = "portfolio-v2"
REVISED = "portfolio-v3"  # simulates a future notice change


def page(client, employee_id: int) -> bytes:
    return client.get(f"/employees/{employee_id}/enrollment/").data


def stored_files(app) -> int:
    folder = Path(app.config["BIOMETRIC_STORAGE_PATH"])
    return len(list(folder.iterdir())) if folder.exists() else 0


def revise_notice(app) -> None:
    app.config["CONSENT_NOTICE_VERSION"] = REVISED


def test_current_notice_version_is_v2():
    assert Config.CONSENT_NOTICE_VERSION == CURRENT


def test_notice_discloses_embeddings_and_where_they_are_stored(client, app):
    employee_id = add_employee(app, "EMP-1", "Asha Rao")
    html = page(client, employee_id).decode()
    assert "face embedding" in html and "128 numbers" in html
    assert "biometric data" in html
    assert "face embeddings in the app's private local database" in html
    assert "every face embedding made from them" in html  # withdrawal deletes them
    assert f"Notice version: {CURRENT}" in html


def test_new_consent_records_the_current_notice_version(client, app):
    employee_id = add_employee(app, "EMP-1", "Asha Rao")
    client.post(f"/employees/{employee_id}/enrollment/consent", data={"affirm": "yes"})
    with app.app_context():
        assert db.session.query(BiometricConsent).one().notice_version == CURRENT


def test_consent_to_an_older_notice_is_not_treated_as_current(client, app):
    employee_id = add_employee(app, "EMP-1", "Asha Rao")
    with app.app_context():
        db.session.add(BiometricConsent(employee_id=employee_id, notice_version="portfolio-v1"))
        db.session.commit()

    html = page(client, employee_id)
    assert b"Consent update required" in html
    assert b"to an earlier notice (portfolio-v1)" in html
    assert b"Record consent" in html  # the employee is asked again
    assert b"Start enrolment" not in html
    assert b"Consent update required" in client.get("/employees").data

    response = client.post(f"/employees/{employee_id}/enrollment/start", follow_redirects=True)
    assert b"The consent notice has changed" in response.data
    assert client.get(f"/employees/{employee_id}/enrollment/capture").status_code == 302
    with app.app_context():
        assert db.session.query(FaceEnrollment).count() == 0
        assert db.session.query(BiometricConsent).one().notice_version == "portfolio-v1"  # record untouched


def test_revised_notice_stops_recognition_but_keeps_stored_data(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    fake.vectors = [unit(0)]
    assert identify(client).get_json()["status"] == "match"

    revise_notice(app)
    fake.vectors = [unit(0)]
    body = identify(client).get_json()
    assert body["status"] == "unknown" and body["gallery_size"] == 0

    response = client.post(f"/employees/{employee_id}/enrollment/templates", follow_redirects=True)
    assert b"consent to the current notice" in response.data
    assert b"Consent update required" in response.data
    assert templates_for(app, employee_id) == 3 and stored_files(app) == 3  # nothing silently deleted


def test_revised_notice_blocks_further_capture(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [], complete=False)
    revise_notice(app)
    base = f"/employees/{employee_id}/enrollment"
    upload = client.post(f"{base}/samples", data={"image": (BytesIO(make_image()), "c.jpg")},
                         content_type="multipart/form-data", headers={"Accept": "application/json"})
    assert upload.status_code == 400 and "current notice" in upload.get_json()["error"]
    complete = client.post(f"{base}/complete", follow_redirects=True)
    assert b"current notice" in complete.data
    assert stored_files(app) == 3


def test_consenting_again_to_the_revised_notice_restores_recognition(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    with app.app_context():
        original = db.session.query(BiometricConsent).one()
        consent_id, first_granted = original.id, original.granted_at
    revise_notice(app)

    not_ticked = client.post(f"/employees/{employee_id}/enrollment/consent", data={}, follow_redirects=True)
    assert b"Consent was not recorded" in not_ticked.data and b"Consent update required" in not_ticked.data

    client.post(f"/employees/{employee_id}/enrollment/consent", data={"affirm": "yes"})
    with app.app_context():
        consent = db.session.query(BiometricConsent).one()
        assert consent.id == consent_id and consent.notice_version == REVISED
        assert consent.granted_at >= first_granted
    assert b"Successfully enrolled" in page(client, employee_id)
    fake.vectors = [unit(0)]
    assert identify(client).get_json()["status"] == "match"


def test_outdated_consent_can_still_be_withdrawn(client, app, fake):
    employee_id = enrol(client, app, fake, "EMP-1", "Asha Rao", [unit(0)] * 3)
    revise_notice(app)
    response = client.post(f"/employees/{employee_id}/enrollment/withdraw", follow_redirects=True)
    assert b"Consent was withdrawn" in response.data
    assert templates_for(app, employee_id) == 0 and stored_files(app) == 0
    with app.app_context():
        assert db.session.query(FaceTemplate).count() == 0
        assert db.session.get(Employee, employee_id).biometric_consent.status == "withdrawn"
