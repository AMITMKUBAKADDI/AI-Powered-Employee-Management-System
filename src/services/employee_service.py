# src/services/employee_service.py
"""Business logic service layer with validation, transactions, and audit logging."""

import logging
from datetime import date
from typing import Optional, List, Dict, Any, Tuple
from src.db import get_db_session
from src.repositories.employee_repository import EmployeeRepository
from src.schemas import EmployeeCreate, EmployeeUpdate, EmployeeResponse, PaginatedEmployees

logger = logging.getLogger("audit")
logger.setLevel(logging.INFO)


class EmployeeService:
    """Provides high-level business operations on employee records."""

    @classmethod
    def create_employee(cls, data: EmployeeCreate, actor: str = "system") -> Dict[str, Any]:
        """Validate, insert new employee, and log audit event."""
        with get_db_session() as session:
            emp = EmployeeRepository.create_employee(session, data)
            result = emp.to_dict()

        logger.info("[AUDIT] CREATE: Employee ID %s (%s) created by %s", result["employee_id"], result["employee_name"], actor)
        return result

    @classmethod
    def get_employee(cls, employee_id: int) -> Optional[Dict[str, Any]]:
        """Fetch employee by primary key."""
        with get_db_session() as session:
            emp = EmployeeRepository.get_employee(session, employee_id)
            return emp.to_dict() if emp else None

    @classmethod
    def find_employee(cls, employee_name: str) -> Dict[str, Any]:
        """
        Find employee by name.
        Handles missing records and duplicate names safely.
        """
        with get_db_session() as session:
            matches = EmployeeRepository.find_by_name(session, employee_name)

        if not matches:
            return {
                "status": "not_found",
                "message": f"No employee found with name matching '{employee_name}'.",
                "matches": []
            }

        if len(matches) > 1:
            return {
                "status": "multiple_matches",
                "message": f"Multiple ({len(matches)}) employees found with name matching '{employee_name}'. Please specify by employee ID.",
                "matches": matches
            }

        return {
            "status": "success",
            "message": "Employee found.",
            "employee": matches[0]
        }

    @classmethod
    def search_employees(
        cls,
        city: Optional[str] = None,
        active_only: Optional[bool] = None,
        joining_date_from: Optional[date] = None,
        joining_date_to: Optional[date] = None,
        manager_name: Optional[str] = None,
        name_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """Search and paginate employees with bounded output."""
        offset = (page - 1) * page_size
        with get_db_session() as session:
            items, total = EmployeeRepository.search_employees(
                session,
                city=city,
                active_only=active_only,
                joining_date_from=joining_date_from,
                joining_date_to=joining_date_to,
                manager_name=manager_name,
                name_query=name_query,
                limit=page_size,
                offset=offset
            )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return {
            "items": items,
            "total_count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    @classmethod
    def count_employees(
        cls,
        active_only: Optional[bool] = None,
        city: Optional[str] = None,
        joining_date_from: Optional[date] = None,
        joining_date_to: Optional[date] = None
    ) -> int:
        """Count employees directly in database."""
        with get_db_session() as session:
            return EmployeeRepository.count_employees(
                session,
                active_only=active_only,
                city=city,
                joining_date_from=joining_date_from,
                joining_date_to=joining_date_to
            )

    @classmethod
    def get_direct_reports(cls, manager_name: str) -> List[Dict[str, Any]]:
        """Fetch list of direct reports for a manager."""
        with get_db_session() as session:
            return EmployeeRepository.get_direct_reports(session, manager_name)

    @classmethod
    def update_employee(cls, employee_id: int, fields: Dict[str, Any], actor: str = "system") -> Dict[str, Any]:
        """Update allowed fields of an employee and log audit event."""
        # Validate allowed fields
        allowed = {"employee_name", "manager_name", "city", "date_of_joining", "is_active"}
        filtered_fields = {k: v for k, v in fields.items() if k in allowed and v is not None}

        if not filtered_fields:
            return {"status": "error", "message": "No valid updatable fields provided."}

        with get_db_session() as session:
            updated = EmployeeRepository.update_employee(session, employee_id, filtered_fields)
            if not updated:
                return {"status": "not_found", "message": f"Employee ID {employee_id} not found."}
            result = updated.to_dict()

        logger.info("[AUDIT] UPDATE: Employee ID %s updated with %s by %s", employee_id, filtered_fields, actor)
        return {"status": "success", "message": f"Employee ID {employee_id} updated successfully.", "employee": result}

    @classmethod
    def deactivate_employee(cls, employee_id: int, actor: str = "system") -> Dict[str, Any]:
        """Soft-deactivate an employee without deleting the record and log audit event."""
        with get_db_session() as session:
            deactivated = EmployeeRepository.deactivate_employee(session, employee_id)
            if not deactivated:
                return {"status": "not_found", "message": f"Employee ID {employee_id} not found."}
            result = deactivated.to_dict()

        logger.info("[AUDIT] DEACTIVATE: Employee ID %s deactivated by %s", employee_id, actor)
        return {"status": "success", "message": f"Employee ID {employee_id} has been deactivated.", "employee": result}
