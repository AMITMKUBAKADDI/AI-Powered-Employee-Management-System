# src/db.py
"""Database connection pooling, session management, and transaction handling."""

import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from src.config import get_settings
from src.models import Base

logger = logging.getLogger(__name__)

# Fetch application settings
settings = get_settings()

# Engine creation with connection pooling optimizations
# - pool_size: Keep persistent connections active
# - max_overflow: Additional connections during peak load
# - pool_pre_ping: Test connection liveness before usage
# - pool_recycle: Prevent stale connections
try:
    engine = create_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False
    )
except Exception as e:
    logger.warning("Could not initialize default PostgreSQL engine: %s. Falling back to SQLite memory/local.", e)
    engine = create_engine("sqlite:///./local_employees.db", echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_connection() -> bool:
    """Verify whether the database is accessible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database connection check failed: %s", e)
        return False


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session context with automatic rollback on error."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        logger.error("Database error during transaction, rolling back: %s", exc)
        raise exc
    except Exception as exc:
        session.rollback()
        logger.error("Unexpected error during transaction, rolling back: %s", exc)
        raise exc
    finally:
        session.close()


def init_db(seed_sample_data: bool = False) -> None:
    """Create tables if they don't exist and optionally seed sample data."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")

    if seed_sample_data:
        from src.models import Employee
        from datetime import date
        with get_db_session() as session:
            count = session.query(Employee).count()
            if count == 0:
                logger.info("Empty database detected, seeding 12 initial employee records...")
                sample_employees = [
                    Employee(employee_name="Rahul Sharma", manager_name="Priya Nair", city="Bangalore", date_of_joining=date(2023, 3, 15), is_active=True),
                    Employee(employee_name="Priya Nair", manager_name="Vikram Malhotra", city="Bangalore", date_of_joining=date(2021, 6, 1), is_active=True),
                    Employee(employee_name="Vikram Malhotra", manager_name=None, city="Mumbai", date_of_joining=date(2019, 1, 10), is_active=True),
                    Employee(employee_name="Ananya Iyer", manager_name="Priya Nair", city="Bangalore", date_of_joining=date(2024, 2, 20), is_active=True),
                    Employee(employee_name="Amit Verma", manager_name="Priya Nair", city="Mysore", date_of_joining=date(2025, 2, 1), is_active=True),
                    Employee(employee_name="Sneha Patel", manager_name="Vikram Malhotra", city="Mumbai", date_of_joining=date(2022, 11, 12), is_active=True),
                    Employee(employee_name="Rohan Kulkarni", manager_name="Sneha Patel", city="Pune", date_of_joining=date(2025, 3, 10), is_active=True),
                    Employee(employee_name="Deepak Rao", manager_name="Rahul Sharma", city="Bangalore", date_of_joining=date(2023, 8, 1), is_active=False),
                    Employee(employee_name="Kavita Singh", manager_name="Sneha Patel", city="Delhi", date_of_joining=date(2024, 10, 5), is_active=True),
                    Employee(employee_name="Arjun Reddy", manager_name="Vikram Malhotra", city="Hyderabad", date_of_joining=date(2025, 1, 15), is_active=True),
                    Employee(employee_name="Meera Joshi", manager_name="Arjun Reddy", city="Hyderabad", date_of_joining=date(2024, 5, 18), is_active=False),
                    Employee(employee_name="Rahul Sharma", manager_name="Sneha Patel", city="Delhi", date_of_joining=date(2025, 4, 1), is_active=True),
                ]
                session.add_all(sample_employees)
                logger.info("Successfully seeded 12 sample employees.")
