"""Application factory and dashboard tests."""

from datetime import date, datetime, timezone

from sqlalchemy import inspect

from app.extensions import db
from app.models import Attendance, Employee


def test_application_initializes_database(app):
    with app.app_context():
        table_names = inspect(db.engine).get_table_names()
        assert Employee.__table__.name in table_names
        assert Attendance.__table__.name in table_names


def test_configuration_can_be_overridden_for_tests(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"


def test_dashboard_handles_an_empty_database(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Total employees" in response.data
    assert b"No attendance yet" in response.data
    assert b">0<" in response.data


def test_dashboard_uses_database_statistics(client, app):
    with app.app_context():
        active = Employee(employee_code="EMP-001", full_name="Asha Rao", department="People")
        inactive = Employee(employee_code="EMP-002", full_name="Kiran Shah", is_active=False)
        db.session.add_all([active, inactive])
        db.session.commit()
        db.session.add(
            Attendance(
                employee=active,
                attendance_date=date.today(),
                check_in_time=datetime.now(timezone.utc),
                recognition_method="manual",
            )
        )
        db.session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Asha Rao" in response.data
    assert b"EMP-001" in response.data
    assert b">2<" in response.data
    assert b">1<" in response.data
