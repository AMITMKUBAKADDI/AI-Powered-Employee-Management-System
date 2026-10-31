# src/auth.py
"""Authentication and Role-Based Access Control (RBAC) definitions."""

from enum import Enum
from typing import Dict, Any


class Role(str, Enum):
    """User roles supported by the application."""
    ADMIN = "admin"
    USER = "user"


# Permissions mapping
ROLE_PERMISSIONS = {
    Role.USER: {
        "can_read": True,
        "can_create": False,
        "can_update": False,
        "can_deactivate": False,
    },
    Role.ADMIN: {
        "can_read": True,
        "can_create": True,
        "can_update": True,
        "can_deactivate": True,
    }
}


def check_permission(role: str, action: str) -> bool:
    """
    Programmatically verify if a given role is allowed to perform an action.
    Never relies solely on the LLM.
    """
    role_enum = Role.ADMIN if role.lower() == "admin" else Role.USER
    permissions = ROLE_PERMISSIONS.get(role_enum, {})
    return permissions.get(action, False)


def sanitize_input(value: str) -> str:
    """Basic string sanitizer to strip null bytes and excessive controls."""
    if not isinstance(value, str):
        return value
    return value.replace("\x00", "").strip()
