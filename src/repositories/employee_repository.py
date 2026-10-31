# src/repositories/employee_repository.py
"""Repository layer handling all parameterized database queries for employees."""

import logging
from datetime import date
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from src.models import Employee
from src.schemas import EmployeeCreate, EmployeeUpdate

logger = logging.getLogger(__name__)


class EmployeeRepository:
    """Encapsulates data access and queries for the Employee entity."""

    @staticmethod
    def create_employee(session: Session, data: EmployeeCreate) -> Employee:
        """Insert a new employee record using validated input."""
        emp = Employee(
            employee_name=data.employee_name,
            manager_name=data.manager_name,
            city=data.city,
            date_of_joining=data.date_of_joining,
            is_active=data.is_active,
        )
        session.add(emp)
        session.flush()
        session.refresh(emp)
        logger.info("Created employee with ID %s (%s)", emp.employee_id, emp.employee_name)
        return emp

    @staticmethod
    def get_employee(session: Session, employee_id: int) -> Optional[Employee]:
        """Retrieve a single employee by their primary key."""
        return session.query(Employee).filter(Employee.employee_id == employee_id).first()

    @staticmethod
    def find_by_name(session: Session, employee_name: str) -> List[Dict[str, Any]]:
        """
        Find employees matching a name (case-insensitive).
        Returns a list of dicts to handle single and duplicate matches safely.
        """
        query_str = employee_name.strip().lower()
        employees = (
            session.query(
                Employee.employee_id,
                Employee.employee_name,
                Employee.manager_name,
                Employee.city,
                Employee.date_of_joining,
                Employee.is_active,
                Employee.created_on,
                Employee.modified_on
            )
            .filter(func.lower(Employee.employee_name) == query_str)
            .all()
        )

        # If exact match yields 0, try a wildcard/partial match
        if not employees:
            employees = (
                session.query(
                    Employee.employee_id,
                    Employee.employee_name,
                    Employee.manager_name,
                    Employee.city,
                    Employee.date_of_joining,
                    Employee.is_active,
                    Employee.created_on,
                    Employee.modified_on
                )
                .filter(func.lower(Employee.employee_name).like(f"%{query_str}%"))
                .all()
            )

        return [
            {
                "employee_id": row.employee_id,
                "employee_name": row.employee_name,
                "manager_name": row.manager_name,
                "city": row.city,
                "date_of_joining": row.date_of_joining.isoformat() if isinstance(row.date_of_joining, date) else str(row.date_of_joining),
                "is_active": row.is_active,
                "created_on": row.created_on.isoformat() if row.created_on else None,
                "modified_on": row.modified_on.isoformat() if row.modified_on else None,
            }
            for row in employees
        ]

    @staticmethod
    def search_employees(
        session: Session,
        city: Optional[str] = None,
        active_only: Optional[bool] = None,
        joining_date_from: Optional[date] = None,
        joining_date_to: Optional[date] = None,
        manager_name: Optional[str] = None,
        name_query: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Filter records based on criteria with bounded result size and pagination.
        Returns a tuple of (items_list, total_count).
        """
        filters = []

        if city:
            filters.append(func.lower(Employee.city) == city.strip().lower())
        if active_only is not None:
            filters.append(Employee.is_active == active_only)
        if joining_date_from:
            filters.append(Employee.date_of_joining >= joining_date_from)
        if joining_date_to:
            filters.append(Employee.date_of_joining <= joining_date_to)
        if manager_name:
            filters.append(func.lower(Employee.manager_name) == manager_name.strip().lower())
        if name_query:
            filters.append(func.lower(Employee.employee_name).like(f"%{name_query.strip().lower()}%"))

        base_query = session.query(Employee).filter(and_(*filters) if filters else True)
        total_count = base_query.count()

        rows = (
            session.query(
                Employee.employee_id,
                Employee.employee_name,
                Employee.manager_name,
                Employee.city,
                Employee.date_of_joining,
                Employee.is_active,
                Employee.created_on,
                Employee.modified_on
            )
            .filter(and_(*filters) if filters else True)
            .order_by(Employee.employee_id.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        results = [
            {
                "employee_id": row.employee_id,
                "employee_name": row.employee_name,
                "manager_name": row.manager_name,
                "city": row.city,
                "date_of_joining": row.date_of_joining.isoformat() if isinstance(row.date_of_joining, date) else str(row.date_of_joining),
                "is_active": row.is_active,
                "created_on": row.created_on.isoformat() if row.created_on else None,
                "modified_on": row.modified_on.isoformat() if row.modified_on else None,
            }
            for row in rows
        ]

        return results, total_count

    @staticmethod
    def count_employees(
        session: Session,
        active_only: Optional[bool] = None,
        city: Optional[str] = None,
        joining_date_from: Optional[date] = None,
        joining_date_to: Optional[date] = None
    ) -> int:
        """Direct SQL count aggregation on PostgreSQL."""
        filters = []
        if active_only is not None:
            filters.append(Employee.is_active == active_only)
        if city:
            filters.append(func.lower(Employee.city) == city.strip().lower())
        if joining_date_from:
            filters.append(Employee.date_of_joining >= joining_date_from)
        if joining_date_to:
            filters.append(Employee.date_of_joining <= joining_date_to)

        count = session.query(func.count(Employee.employee_id)).filter(and_(*filters) if filters else True).scalar()
        return count or 0

    @staticmethod
    def get_direct_reports(session: Session, manager_name: str) -> List[Dict[str, Any]]:
        """Return all employees who report directly to a manager."""
        query_str = manager_name.strip().lower()
        rows = (
            session.query(
                Employee.employee_id,
                Employee.employee_name,
                Employee.city,
                Employee.date_of_joining,
                Employee.is_active
            )
            .filter(func.lower(Employee.manager_name) == query_str)
            .order_by(Employee.employee_name.asc())
            .all()
        )

        return [
            {
                "employee_id": row.employee_id,
                "employee_name": row.employee_name,
                "city": row.city,
                "date_of_joining": row.date_of_joining.isoformat() if isinstance(row.date_of_joining, date) else str(row.date_of_joining),
                "is_active": row.is_active,
            }
            for row in rows
        ]

    @staticmethod
    def update_employee(session: Session, employee_id: int, fields: Dict[str, Any]) -> Optional[Employee]:
        """Update explicitly permitted fields and refresh modified_on."""
        emp = session.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not emp:
            return None

        # Allowlist check
        allowed_fields = {"employee_name", "manager_name", "city", "date_of_joining", "is_active"}
        for k, v in fields.items():
            if k in allowed_fields:
                setattr(emp, k, v)

        # Trigger updated timestamp
        emp.modified_on = func.now()
        session.flush()
        session.refresh(emp)
        logger.info("Updated employee %s with fields %s", employee_id, list(fields.keys()))
        return emp

    @staticmethod
    def deactivate_employee(session: Session, employee_id: int) -> Optional[Employee]:
        """Soft-deactivate an employee without permanently deleting the record."""
        emp = session.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not emp:
            return None

        emp.is_active = False
        emp.modified_on = func.now()
        session.flush()
        session.refresh(emp)
        logger.info("Deactivated employee %s", employee_id)
        return emp
