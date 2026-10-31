# tests/test_security.py
"""Automated security, permission, validation, and confirmation tests."""

import pytest
import json
from pydantic import ValidationError
from datetime import date
from src.auth import check_permission, Role
from src.schemas import EmployeeCreate, EmployeeUpdate
from src.ai.tools import create_employee_tool, update_employee_tool, deactivate_employee_tool


def test_rbac_user_permissions():
    """Verify ordinary users have read-only access and cannot write."""
    assert check_permission("user", "can_read") is True
    assert check_permission("user", "can_create") is False
    assert check_permission("user", "can_update") is False
    assert check_permission("user", "can_deactivate") is False


def test_rbac_admin_permissions():
    """Verify administrators have full read and write permissions."""
    assert check_permission("admin", "can_read") is True
    assert check_permission("admin", "can_create") is True
    assert check_permission("admin", "can_update") is True
    assert check_permission("admin", "can_deactivate") is True


def test_unauthorized_tool_execution():
    """Test that calling write tools as an ordinary user returns permission denied."""
    res_raw = update_employee_tool.invoke({
        "employee_id": 1,
        "fields": {"city": "Mysore"},
        "confirmed": True,
        "user_role": "user"
    })
    res = json.loads(res_raw)
    assert res.get("status") == "permission_denied"

    deact_raw = deactivate_employee_tool.invoke({
        "employee_id": 1,
        "confirmed": True,
        "user_role": "user"
    })
    deact = json.loads(deact_raw)
    assert deact.get("status") == "permission_denied"


def test_write_tool_requires_confirmation():
    """Test that an admin calling a write tool without confirmation receives a confirmation prompt."""
    res_raw = update_employee_tool.invoke({
        "employee_id": 1,
        "fields": {"city": "Mysore"},
        "confirmed": False,
        "user_role": "admin"
    })
    res = json.loads(res_raw)
    assert res.get("status") == "confirmation_required"
    assert "Confirmation required" in res.get("message")


def test_pydantic_validation_empty_name():
    """Test that empty or blank employee names are rejected."""
    with pytest.raises(ValidationError):
        EmployeeCreate(
            employee_name="   ",
            city="Bangalore",
            date_of_joining=date(2023, 1, 1),
            is_active=True
        )


def test_pydantic_allowlist_update():
    """Test that update schema only permits allowed fields."""
    update = EmployeeUpdate(city="New City", is_active=False)
    data = update.model_dump(exclude_unset=True)
    assert "city" in data
    assert "is_active" in data
    assert "employee_id" not in data
