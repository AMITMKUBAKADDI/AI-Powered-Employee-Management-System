# src/schemas.py
"""Pydantic schemas for data validation and API serialization."""

from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class EmployeeBase(BaseModel):
    """Base schema for employee fields."""
    employee_name: str = Field(..., min_length=1, max_length=150, description="Full name of the employee")
    manager_name: Optional[str] = Field(None, max_length=150, description="Full name of manager")
    city: Optional[str] = Field(None, max_length=100, description="City location")
    date_of_joining: date = Field(..., description="Date when employee joined")
    is_active: bool = Field(default=True, description="Active status")

    @field_validator("employee_name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Employee name cannot be empty or whitespace.")
        return trimmed

    @field_validator("city", "manager_name")
    @classmethod
    def sanitize_optional_string(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        return trimmed if trimmed else None


class EmployeeCreate(EmployeeBase):
    """Schema for adding a new employee."""
    pass


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee with allowlisted fields."""
    employee_name: Optional[str] = Field(None, min_length=1, max_length=150)
    manager_name: Optional[str] = Field(None, max_length=150)
    city: Optional[str] = Field(None, max_length=100)
    date_of_joining: Optional[date] = None
    is_active: Optional[bool] = None

    @field_validator("employee_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Employee name cannot be empty string.")
            return trimmed
        return v


class EmployeeResponse(EmployeeBase):
    """Schema for returning employee data."""
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    created_on: Optional[datetime] = None
    modified_on: Optional[datetime] = None


class EmployeeFilter(BaseModel):
    """Filter parameters for querying employees."""
    city: Optional[str] = None
    active_only: Optional[bool] = None
    joining_date_from: Optional[date] = None
    joining_date_to: Optional[date] = None
    manager_name: Optional[str] = None
    name_query: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class PaginatedEmployees(BaseModel):
    """Paginated list of employees with total record count."""
    items: List[EmployeeResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class WriteConfirmation(BaseModel):
    """Schema for operations requiring explicit confirmation."""
    action_type: Literal["create", "update", "deactivate"]
    employee_id: Optional[int] = None
    details: dict
    confirmed: bool = False
