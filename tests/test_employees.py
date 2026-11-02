"""Employee-management route and service tests."""

from app.extensions import db
from app.models import Employee


def test_employee_registration_succeeds(client, app):
    response = client.post(
        "/employees/new",
        data={"employee_code": "emp-101", "full_name": "Riya Singh", "department": "Engineering"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"was registered successfully" in response.data
    with app.app_context():
        employee = db.session.query(Employee).filter_by(employee_code="EMP-101").one()
        assert employee.full_name == "Riya Singh"
        assert employee.department == "Engineering"


def test_employee_registration_requires_a_name(client):
    response = client.post(
        "/employees/new", data={"employee_code": "EMP-101", "full_name": "", "department": ""}
    )

    assert response.status_code == 200
    assert b"Full name is required" in response.data


def test_duplicate_employee_code_is_rejected(client):
    client.post(
        "/employees/new",
        data={"employee_code": "EMP-101", "full_name": "Riya Singh", "department": "Engineering"},
    )

    response = client.post(
        "/employees/new",
        data={"employee_code": "emp-101", "full_name": "Another Person", "department": ""},
    )

    assert response.status_code == 200
    assert b"already registered" in response.data


def test_employee_listing_editing_and_deactivation(client, app):
    with app.app_context():
        employee = Employee(employee_code="EMP-101", full_name="Riya Singh", department="Engineering")
        db.session.add(employee)
        db.session.commit()
        employee_id = employee.id

    listing = client.get("/employees")
    assert listing.status_code == 200
    assert b"Riya Singh" in listing.data

    edited = client.post(
        f"/employees/{employee_id}/edit",
        data={"employee_code": "EMP-201", "full_name": "Riya Kapoor", "department": "Platform"},
        follow_redirects=True,
    )
    assert b"details were updated" in edited.data

    deactivated = client.post(f"/employees/{employee_id}/deactivate", follow_redirects=True)
    assert b"was deactivated" in deactivated.data
    with app.app_context():
        employee = db.session.get(Employee, employee_id)
        assert employee.employee_code == "EMP-201"
        assert employee.full_name == "Riya Kapoor"
        assert employee.is_active is False
