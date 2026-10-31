# tests/conftest.py
"""Pytest fixtures for isolating tests using an in-memory test database."""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import src.db as db_module
from src.models import Base, Employee


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Automatically creates an in-memory SQLite database for all unit tests,
    ensuring tests do not require live PostgreSQL or external credentials.
    """
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Seed sample records for test assertions
    with TestingSession() as session:
        samples = [
            Employee(employee_id=1, employee_name="Rahul Sharma", manager_name="Priya Nair", city="Bangalore", date_of_joining=date(2023, 3, 15), is_active=True),
            Employee(employee_id=2, employee_name="Priya Nair", manager_name="Vikram Malhotra", city="Bangalore", date_of_joining=date(2021, 6, 1), is_active=True),
            Employee(employee_id=3, employee_name="Vikram Malhotra", manager_name=None, city="Mumbai", date_of_joining=date(2019, 1, 10), is_active=True),
            Employee(employee_id=4, employee_name="Ananya Iyer", manager_name="Priya Nair", city="Bangalore", date_of_joining=date(2024, 2, 20), is_active=True),
            Employee(employee_id=5, employee_name="Amit Verma", manager_name="Priya Nair", city="Mysore", date_of_joining=date(2025, 2, 1), is_active=True),
            Employee(employee_id=6, employee_name="Sneha Patel", manager_name="Vikram Malhotra", city="Mumbai", date_of_joining=date(2022, 11, 12), is_active=True),
            Employee(employee_id=7, employee_name="Rohan Kulkarni", manager_name="Sneha Patel", city="Pune", date_of_joining=date(2025, 3, 10), is_active=True),
            Employee(employee_id=8, employee_name="Deepak Rao", manager_name="Rahul Sharma", city="Bangalore", date_of_joining=date(2023, 8, 1), is_active=False),
            Employee(employee_id=9, employee_name="Kavita Singh", manager_name="Sneha Patel", city="Delhi", date_of_joining=date(2024, 10, 5), is_active=True),
            Employee(employee_id=10, employee_name="Arjun Reddy", manager_name="Vikram Malhotra", city="Hyderabad", date_of_joining=date(2025, 1, 15), is_active=True),
            Employee(employee_id=11, employee_name="Meera Joshi", manager_name="Arjun Reddy", city="Hyderabad", date_of_joining=date(2024, 5, 18), is_active=False),
            Employee(employee_id=12, employee_name="Rahul Sharma", manager_name="Sneha Patel", city="Delhi", date_of_joining=date(2025, 4, 1), is_active=True),
        ]
        session.add_all(samples)
        session.commit()

    # Monkeypatch db_module engine and SessionLocal
    orig_engine = db_module.engine
    orig_sessionlocal = db_module.SessionLocal
    db_module.engine = test_engine
    db_module.SessionLocal = TestingSession

    yield

    db_module.engine = orig_engine
    db_module.SessionLocal = orig_sessionlocal
