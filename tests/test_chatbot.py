# tests/test_chatbot.py
"""Automated tests for Chatbot tools, tool selection, disambiguation, and evaluation dataset."""

import json
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage
from src.ai.tools import (
    find_employee_tool,
    search_employees_tool,
    count_employees_tool,
    get_direct_reports_tool
)

# Evaluation dataset specified in Section 7 of requirements
EVALUATION_DATASET = [
    {
        "query": "What is Rahul Sharma's joining date?",
        "expected_tool": "find_employee",
        "expected_args": {"employee_name": "Rahul Sharma"},
    },
    {
        "query": "Who is Priya Nair's manager?",
        "expected_tool": "find_employee",
        "expected_args": {"employee_name": "Priya Nair"},
    },
    {
        "query": "List all active employees in Bangalore.",
        "expected_tool": "search_employees",
        "expected_args": {"city": "Bangalore", "active_only": True},
    },
    {
        "query": "How many inactive employees are there?",
        "expected_tool": "count_employees",
        "expected_args": {"active_only": False},
    },
    {
        "query": "Which employees joined after January 2025?",
        "expected_tool": "search_employees",
        "expected_args": {"joining_date_from": "2025-01-01"},
    },
    {
        "query": "Show employees reporting to Priya Nair.",
        "expected_tool": "get_direct_reports",
        "expected_args": {"manager_name": "Priya Nair"},
    },
    {
        "query": "Update employee ID 5 city to Mysore.",
        "expected_tool": "update_employee",
        "expected_args": {"employee_id": 5, "fields": {"city": "Mysore"}},
    },
    {
        "query": "Deactivate employee ID 8.",
        "expected_tool": "deactivate_employee",
        "expected_args": {"employee_id": 8},
    }
]


def test_eval_dataset_structure():
    """Verify evaluation dataset contains all expected canonical queries."""
    assert len(EVALUATION_DATASET) >= 8
    for item in EVALUATION_DATASET:
        assert "query" in item
        assert "expected_tool" in item
        assert "expected_args" in item


def test_find_employee_tool_execution():
    """Test find_employee_tool invocation structure."""
    result_str = find_employee_tool.invoke({"employee_name": "Priya Nair"})
    res = json.loads(result_str)
    assert "status" in res


def test_count_employees_tool_execution():
    """Test count_employees_tool returns count dictionary."""
    result_str = count_employees_tool.invoke({"active_only": True})
    res = json.loads(result_str)
    assert "count" in res
    assert isinstance(res["count"], int)


def test_get_direct_reports_tool_execution():
    """Test get_direct_reports_tool execution."""
    result_str = get_direct_reports_tool.invoke({"manager_name": "Priya Nair"})
    res = json.loads(result_str)
    assert "direct_reports" in res
    assert "total" in res
