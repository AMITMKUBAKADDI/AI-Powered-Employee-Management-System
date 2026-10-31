# tests/test_voice_service.py
"""Automated tests for VoiceService multimodal extraction and voice-driven operations across all functions."""

import pytest
from datetime import date
from unittest.mock import MagicMock
from src.ai.voice_service import VoiceService
from src.schemas import EmployeeCreate
from src.services.employee_service import EmployeeService


def test_voice_service_initialization():
    """Verify VoiceService initializes with valid config."""
    vs = VoiceService()
    assert vs is not None
    assert vs.settings is not None


def test_voice_service_no_input():
    """Verify appropriate response when no audio or text input is supplied."""
    vs = VoiceService()
    res = vs.process_voice_command(audio_bytes=None, text_fallback=None)
    assert res["success"] is False
    assert "No audio or text" in res["error"]


def test_voice_service_text_command_extraction():
    """Test extracting structured employee fields from natural language text command (Add)."""
    vs = VoiceService()
    prompt = "Jarvis, register Johnathan Smith in Bangalore reporting to Priya Nair joining today"
    res = vs.process_voice_command(text_fallback=prompt)
    
    assert res["success"] is True
    assert res["dto"] is not None
    assert "Johnathan Smith" in res["dto"].employee_name
    assert res["dto"].city == "Bangalore"
    assert res["dto"].manager_name == "Priya Nair"
    assert res["dto"].date_of_joining == date.today()
    assert res["dto"].is_active is True
    assert "spoken_response" in res


def test_voice_service_missing_employee_name():
    """Test that missing mandatory name field returns failure with polite guidance."""
    vs = VoiceService()
    prompt = "Jarvis, register a new employee in Mumbai joining today reporting to Priya Nair"
    res = vs.process_voice_command(text_fallback=prompt)
    
    assert res["success"] is False
    assert "employee_name" in res.get("missing_fields", [])
    assert res["dto"] is None
    assert len(res["spoken_response"]) > 0


def test_voice_registration_persistence():
    """Test persisting a voice-created DTO to the database."""
    dto = EmployeeCreate(
        employee_name="Jarvis Test Subject",
        manager_name="Priya Nair",
        city="Hyderabad",
        date_of_joining=date(2026, 10, 24),
        is_active=True
    )
    res = VoiceService.execute_registration(dto, actor="Test Runner")
    assert res["success"] is True
    assert res["employee"]["employee_id"] > 0
    assert res["employee"]["employee_name"] == "Jarvis Test Subject"
    assert "Affirmative" in res["spoken_response"]


def test_voice_service_edit_command_extraction():
    """Test extracting update fields from voice/text command for Edit Employee."""
    vs = VoiceService()
    prompt = "Jarvis, update employee 2: change city to Pune and manager to Rahul Sharma"
    res = vs.process_edit_command(text_fallback=prompt)

    assert res["success"] is True
    assert res["employee_id"] == 2
    assert "city" in res["fields"] or "manager_name" in res["fields"]
    assert "spoken_response" in res


def test_voice_service_edit_execution():
    """Test applying voice-driven updates directly to the database."""
    # First create a test employee to edit
    dto = EmployeeCreate(
        employee_name="Edit Test Subject",
        manager_name="Priya Nair",
        city="Delhi",
        date_of_joining=date(2026, 1, 15),
        is_active=True
    )
    created = EmployeeService.create_employee(dto, actor="Test Setup")
    emp_id = created["employee_id"]

    # Execute update via VoiceService
    res = VoiceService.execute_update(
        employee_id=emp_id,
        fields={"city": "Kolkata", "manager_name": "Vikram Malhotra"},
        actor="Jarvis Voice Test"
    )

    assert res["success"] is True
    assert res["employee"]["city"] == "Kolkata"
    assert res["employee"]["manager_name"] == "Vikram Malhotra"
    assert "Affirmative" in res["spoken_response"]


def test_voice_service_deactivate_command_extraction():
    """Test extracting deactivation target from voice/text command."""
    vs = VoiceService()
    prompt = "Jarvis, please deactivate employee 3"
    res = vs.process_deactivate_command(text_fallback=prompt)

    assert res["success"] is True
    assert res["employee_id"] == 3
    assert "spoken_response" in res


def test_voice_service_deactivate_execution():
    """Test applying voice-driven deactivation directly to the database."""
    # First create a test employee to deactivate
    dto = EmployeeCreate(
        employee_name="Deactivate Test Subject",
        manager_name="Priya Nair",
        city="Chennai",
        date_of_joining=date(2026, 2, 1),
        is_active=True
    )
    created = EmployeeService.create_employee(dto, actor="Test Setup")
    emp_id = created["employee_id"]

    # Execute deactivation via VoiceService
    res = VoiceService.execute_deactivation(
        employee_id=emp_id,
        actor="Jarvis Voice Test"
    )

    assert res["success"] is True
    assert res["employee"]["is_active"] is False
    assert "Affirmative" in res["spoken_response"]


def test_voice_service_chat_transcription():
    """Test chatbot audio transcription endpoint with text fallback."""
    vs = VoiceService()
    res = vs.transcribe_chat_audio(text_fallback="What is Priya Nair's joining date?")
    assert res["success"] is True
    assert res["transcription"] == "What is Priya Nair's joining date?"
    assert "spoken_response" in res
