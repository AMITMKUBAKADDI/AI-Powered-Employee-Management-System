# tests/test_employee_crud.py
"""Automated tests for Employee CRUD, filtering, pagination, and transactional integrity."""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, Employee
from src.schemas import EmployeeCreate
from src.repositories.employee_repository import EmployeeRepository


@pytest.fixture(scope="function")
def test_db_session():
    """Create an in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    # Seed initial test data
    samples = [
        Employee(employee_name="Rahul Sharma", manager_name="Priya Nair", city="Bangalore", date_of_joining=date(2023, 3, 15), is_active=True),
        Employee(employee_name="Priya Nair", manager_name="Vikram Malhotra", city="Bangalore", date_of_joining=date(2021, 6, 1), is_active=True),
        Employee(employee_name="Vikram Malhotra", manager_name=None, city="Mumbai", date_of_joining=date(2019, 1, 10), is_active=True),
        Employee(employee_name="Amit Verma", manager_name="Priya Nair", city="Mysore", date_of_joining=date(2025, 2, 1), is_active=True),
        Employee(employee_name="Deepak Rao", manager_name="Rahul Sharma", city="Bangalore", date_of_joining=date(2023, 8, 1), is_active=False),
        Employee(employee_name="Rahul Sharma", manager_name="Sneha Patel", city="Delhi", date_of_joining=date(2025, 4, 1), is_active=True),
    ]
    session.add_all(samples)
    session.commit()

    try:
        yield session
    finally:
        session.close()


def test_create_and_get_employee(test_db_session):
    """Test successful employee creation and retrieval."""
    dto = EmployeeCreate(
        employee_name="Kiran Kumar",
        manager_name="Priya Nair",
        city="Pune",
        date_of_joining=date(2024, 7, 1),
        is_active=True
    )
    created = EmployeeRepository.create_employee(test_db_session, dto)
    test_db_session.commit()

    assert created.employee_id is not None
    assert created.employee_name == "Kiran Kumar"
    assert created.city == "Pune"

    fetched = EmployeeRepository.get_employee(test_db_session, created.employee_id)
    assert fetched is not None
    assert fetched.employee_name == "Kiran Kumar"


def test_duplicate_name_disambiguation(test_db_session):
    """Test that searching by duplicate employee name returns both distinct records with IDs."""
    matches = EmployeeRepository.find_by_name(test_db_session, "Rahul Sharma")
    assert len(matches) == 2
    # Ensure they have distinct IDs and cities
    ids = {m["employee_id"] for m in matches}
    assert len(ids) == 2
    cities = {m["city"] for m in matches}
    assert "Bangalore" in cities
    assert "Delhi" in cities


def test_missing_employee_lookup(test_db_session):
    """Test searching for non-existent employee returns empty list."""
    matches = EmployeeRepository.find_by_name(test_db_session, "NonExistent Person")
    assert len(matches) == 0


def test_filter_by_city(test_db_session):
    """Test filtering employees by city."""
    items, count = EmployeeRepository.search_employees(test_db_session, city="Bangalore")
    assert count == 3
    for it in items:
        assert it["city"].lower() == "bangalore"


def test_filter_by_active_status(test_db_session):
    """Test filtering by active / inactive status."""
    active_items, active_count = EmployeeRepository.search_employees(test_db_session, active_only=True)
    inactive_items, inactive_count = EmployeeRepository.search_employees(test_db_session, active_only=False)

    assert active_count == 5
    assert inactive_count == 1
    assert inactive_items[0]["employee_name"] == "Deepak Rao"


def test_count_employees_aggregation(test_db_session):
    """Test SQL aggregation count directly."""
    total_active = EmployeeRepository.count_employees(test_db_session, active_only=True)
    assert total_active == 5

    bangalore_active = EmployeeRepository.count_employees(test_db_session, active_only=True, city="Bangalore")
    assert bangalore_active == 2


def test_filter_by_joining_date(test_db_session):
    """Test querying employees who joined after January 2025."""
    items, count = EmployeeRepository.search_employees(
        test_db_session,
        joining_date_from=date(2025, 1, 1)
    )
    assert count == 2  # Amit Verma (2025-02-01) and Rahul Sharma Delhi (2025-04-01)


def test_get_direct_reports(test_db_session):
    """Test retrieving direct reports for a manager."""
    reports = EmployeeRepository.get_direct_reports(test_db_session, "Priya Nair")
    names = [r["employee_name"] for r in reports]
    assert "Rahul Sharma" in names
    assert "Amit Verma" in names


def test_update_employee_fields(test_db_session):
    """Test updating employee fields such as city."""
    updated = EmployeeRepository.update_employee(test_db_session, 1, {"city": "Mysore"})
    test_db_session.commit()

    assert updated is not None
    assert updated.city == "Mysore"


def test_deactivate_employee(test_db_session):
    """Test soft-deactivation preserves data and flips is_active to False."""
    deactivated = EmployeeRepository.deactivate_employee(test_db_session, 2)
    test_db_session.commit()

    assert deactivated is not None
    assert deactivated.is_active is False

    # Check record still exists
    record = EmployeeRepository.get_employee(test_db_session, 2)
    assert record is not None
    assert record.is_active is False
