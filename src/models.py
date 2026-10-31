# src/models.py
"""SQLAlchemy ORM models for Employee Management System."""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Boolean,
    DateTime,
    Index,
    func
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Employee(Base):
    """Employee entity mapping to the 'employees' table in PostgreSQL."""
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_name = Column(String(150), nullable=False)
    manager_name = Column(String(150), nullable=True)
    city = Column(String(100), nullable=True)
    date_of_joining = Column(Date, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_on = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    modified_on = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_employees_name_lower", func.lower(employee_name)),
        Index("idx_employees_city_lower", func.lower(city)),
        Index("idx_employees_is_active", is_active),
        Index("idx_employees_date_of_joining", date_of_joining),
        Index("idx_employees_manager_name_lower", func.lower(manager_name)),
    )

    def to_dict(self) -> dict:
        """Convert ORM object to serializable dictionary."""
        return {
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "manager_name": self.manager_name,
            "city": self.city,
            "date_of_joining": self.date_of_joining.isoformat() if isinstance(self.date_of_joining, (date, datetime)) else str(self.date_of_joining),
            "is_active": self.is_active,
            "created_on": self.created_on.isoformat() if self.created_on else None,
            "modified_on": self.modified_on.isoformat() if self.modified_on else None,
        }

    def __repr__(self) -> str:
        return f"<Employee(id={self.employee_id}, name='{self.employee_name}', city='{self.city}', active={self.is_active})>"
