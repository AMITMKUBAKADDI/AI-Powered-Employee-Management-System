# src/ai/tools.py
"""LangChain tools for employee database operations with permission checks and confirmation gates."""

import json
from datetime import date, datetime
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.services.employee_service import EmployeeService
from src.schemas import EmployeeCreate
from src.auth import check_permission, Role


# --- Schemas for Tool Arguments ---

class FindEmployeeInput(BaseModel):
    employee_name: str = Field(..., description="Full name or partial name of the employee to find")


class SearchEmployeesInput(BaseModel):
    city: Optional[str] = Field(None, description="Filter by city name (e.g. 'Bangalore', 'Mumbai', 'Mysore')")
    active_only: Optional[bool] = Field(None, description="True for active only, False for inactive only, None for all")
    joining_date_from: Optional[str] = Field(None, description="ISO date YYYY-MM-DD for lower bound of joining date")
    joining_date_to: Optional[str] = Field(None, description="ISO date YYYY-MM-DD for upper bound of joining date")
    manager_name: Optional[str] = Field(None, description="Filter by manager name")
    page: int = Field(default=1, description="Page number for pagination")
    page_size: int = Field(default=10, description="Number of results per page (max 50)")


class CountEmployeesInput(BaseModel):
    active_only: Optional[bool] = Field(None, description="True for active only, False for inactive only, None for all")
    city: Optional[str] = Field(None, description="Filter by city name")
    joining_date_from: Optional[str] = Field(None, description="ISO date YYYY-MM-DD for lower bound of joining date")
    joining_date_to: Optional[str] = Field(None, description="ISO date YYYY-MM-DD for upper bound of joining date")


class GetDirectReportsInput(BaseModel):
    manager_name: str = Field(..., description="Name of the manager whose direct reports to retrieve")


class CreateEmployeeInput(BaseModel):
    employee_name: str = Field(..., description="Required full name of the employee")
    manager_name: Optional[str] = Field(None, description="Name of the manager")
    city: Optional[str] = Field(None, description="City location")
    date_of_joining: str = Field(..., description="Date of joining in YYYY-MM-DD format")
    is_active: bool = Field(default=True, description="Initial active status")
    confirmed: bool = Field(default=False, description="Set to True only if the user explicitly confirmed this creation")
    user_role: str = Field(default="user", description="The role of the current user ('admin' or 'user')")


class UpdateEmployeeInput(BaseModel):
    employee_id: int = Field(..., description="The unique integer ID of the employee to update")
    fields: Dict[str, Any] = Field(..., description="Dictionary of permitted fields to update (e.g. {'city': 'Mysore'})")
    confirmed: bool = Field(default=False, description="Set to True only if the user explicitly confirmed this update")
    user_role: str = Field(default="user", description="The role of the current user ('admin' or 'user')")


class DeactivateEmployeeInput(BaseModel):
    employee_id: int = Field(..., description="The unique integer ID of the employee to deactivate")
    confirmed: bool = Field(default=False, description="Set to True only if the user explicitly confirmed this deactivation")
    user_role: str = Field(default="user", description="The role of the current user ('admin' or 'user')")


# --- LangChain Tools Implementation ---

@tool("find_employee", args_schema=FindEmployeeInput)
def find_employee_tool(employee_name: str) -> str:
    """Retrieve employee details by name from PostgreSQL. Handles missing and duplicate matches safely."""
    res = EmployeeService.find_employee(employee_name)
    return json.dumps(res, indent=2)


@tool("search_employees", args_schema=SearchEmployeesInput)
def search_employees_tool(
    city: Optional[str] = None,
    active_only: Optional[bool] = None,
    joining_date_from: Optional[str] = None,
    joining_date_to: Optional[str] = None,
    manager_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> str:
    """Search and filter employee records by city, active status, joining date range, or manager."""
    d_from = date.fromisoformat(joining_date_from) if joining_date_from else None
    d_to = date.fromisoformat(joining_date_to) if joining_date_to else None

    res = EmployeeService.search_employees(
        city=city,
        active_only=active_only,
        joining_date_from=d_from,
        joining_date_to=d_to,
        manager_name=manager_name,
        page=page,
        page_size=min(page_size, 50)
    )
    return json.dumps(res, indent=2)


@tool("count_employees", args_schema=CountEmployeesInput)
def count_employees_tool(
    active_only: Optional[bool] = None,
    city: Optional[str] = None,
    joining_date_from: Optional[str] = None,
    joining_date_to: Optional[str] = None
) -> str:
    """Calculate the count of employees matching specific criteria directly in PostgreSQL."""
    d_from = date.fromisoformat(joining_date_from) if joining_date_from else None
    d_to = date.fromisoformat(joining_date_to) if joining_date_to else None

    cnt = EmployeeService.count_employees(
        active_only=active_only,
        city=city,
        joining_date_from=d_from,
        joining_date_to=d_to
    )
    return json.dumps({"count": cnt}, indent=2)


@tool("get_direct_reports", args_schema=GetDirectReportsInput)
def get_direct_reports_tool(manager_name: str) -> str:
    """Return all employees who directly report to a given manager."""
    reports = EmployeeService.get_direct_reports(manager_name)
    return json.dumps({"manager_name": manager_name, "direct_reports": reports, "total": len(reports)}, indent=2)


@tool("create_employee", args_schema=CreateEmployeeInput)
def create_employee_tool(
    employee_name: str,
    date_of_joining: str,
    manager_name: Optional[str] = None,
    city: Optional[str] = None,
    is_active: bool = True,
    confirmed: bool = False,
    user_role: str = "user"
) -> str:
    """Create a new employee record. Requires administrator role and explicit confirmation."""
    if not check_permission(user_role, "can_create"):
        return json.dumps({
            "status": "permission_denied",
            "message": "Permission Denied: Ordinary users have read-only access. Administrator role is required to create an employee."
        })

    if not confirmed:
        return json.dumps({
            "status": "confirmation_required",
            "message": f"Confirmation required to create employee '{employee_name}'. Details: Manager='{manager_name}', City='{city}', Joined='{date_of_joining}', Active={is_active}. Please confirm to proceed.",
            "action": "create_employee",
            "payload": {
                "employee_name": employee_name,
                "manager_name": manager_name,
                "city": city,
                "date_of_joining": date_of_joining,
                "is_active": is_active
            }
        })

    try:
        dto = EmployeeCreate(
            employee_name=employee_name,
            manager_name=manager_name,
            city=city,
            date_of_joining=date.fromisoformat(date_of_joining),
            is_active=is_active
        )
        res = EmployeeService.create_employee(dto, actor=f"admin ({user_role})")
        return json.dumps({"status": "success", "message": f"Successfully created employee '{employee_name}' with ID {res['employee_id']}.", "employee": res})
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Validation or database error: {str(exc)}"})


@tool("update_employee", args_schema=UpdateEmployeeInput)
def update_employee_tool(
    employee_id: int,
    fields: Dict[str, Any],
    confirmed: bool = False,
    user_role: str = "user"
) -> str:
    """Update explicitly permitted fields of an existing employee by ID. Requires administrator role and confirmation."""
    if not check_permission(user_role, "can_update"):
        return json.dumps({
            "status": "permission_denied",
            "message": "Permission Denied: Administrator role is required to update employee records."
        })

    if not confirmed:
        return json.dumps({
            "status": "confirmation_required",
            "message": f"Confirmation required to update employee ID {employee_id} with changes: {fields}. Please confirm to proceed.",
            "action": "update_employee",
            "employee_id": employee_id,
            "fields": fields
        })

    # If date_of_joining is in fields, convert from string if necessary
    if "date_of_joining" in fields and isinstance(fields["date_of_joining"], str):
        fields["date_of_joining"] = date.fromisoformat(fields["date_of_joining"])

    res = EmployeeService.update_employee(employee_id, fields, actor=f"admin ({user_role})")
    return json.dumps(res, indent=2)


@tool("deactivate_employee", args_schema=DeactivateEmployeeInput)
def deactivate_employee_tool(
    employee_id: int,
    confirmed: bool = False,
    user_role: str = "user"
) -> str:
    """Deactivate an employee by ID without deleting data. Requires administrator role and confirmation."""
    if not check_permission(user_role, "can_deactivate"):
        return json.dumps({
            "status": "permission_denied",
            "message": "Permission Denied: Administrator role is required to deactivate employee records."
        })

    if not confirmed:
        return json.dumps({
            "status": "confirmation_required",
            "message": f"Confirmation required to deactivate employee ID {employee_id}. Please confirm to proceed.",
            "action": "deactivate_employee",
            "employee_id": employee_id
        })

    res = EmployeeService.deactivate_employee(employee_id, actor=f"admin ({user_role})")
    return json.dumps(res, indent=2)


# Available tools export
ALL_TOOLS = [
    find_employee_tool,
    search_employees_tool,
    count_employees_tool,
    get_direct_reports_tool,
    create_employee_tool,
    update_employee_tool,
    deactivate_employee_tool
]

READ_ONLY_TOOLS = [
    find_employee_tool,
    search_employees_tool,
    count_employees_tool,
    get_direct_reports_tool
]
