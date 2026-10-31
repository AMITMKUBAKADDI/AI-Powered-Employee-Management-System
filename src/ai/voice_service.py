# src/ai/voice_service.py
"""Voice command processing and multimodal Gemini extraction for Jarvis assistant across all functions."""

import json
import logging
import re
from datetime import date, datetime
from typing import Optional, Dict, Any, List

from google import genai
from google.genai import types

from src.config import get_settings
from src.schemas import EmployeeCreate
from src.services.employee_service import EmployeeService

logger = logging.getLogger(__name__)


class VoiceService:
    """Service to handle voice-driven employee operations via Google Gemini multimodal processing."""

    def __init__(self, client: Optional[genai.Client] = None):
        self.settings = get_settings()
        if client:
            self.client = client
        else:
            api_key = self.settings.gemini_api_key
            if api_key and api_key != "your_gemini_api_key_here":
                self.client = genai.Client(api_key=api_key)
            else:
                self.client = None
                logger.warning("GEMINI_API_KEY is missing or invalid. Voice extraction will run in mock mode.")

    # -------------------------------------------------------------------------
    # 1. ADD EMPLOYEE VOICE PROCESSING
    # -------------------------------------------------------------------------
    def process_voice_command(
        self,
        audio_bytes: Optional[bytes] = None,
        mime_type: str = "audio/wav",
        text_fallback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user speech or natural text into structured EmployeeCreate data.
        """
        today_str = date.today().isoformat()
        
        system_prompt = (
            f"You are Jarvis, an intelligent and polite employee management voice AI assistant.\n"
            f"Today's date is {today_str}.\n"
            f"Listen to the audio (or read text) and extract details for employee registration.\n"
            f"Output a valid JSON object matching this schema:\n"
            f"{{\n"
            f'  "transcription": "exact transcription of what the user spoke",\n'
            f'  "employee_name": "full name of employee or null if missing",\n'
            f'  "manager_name": "manager full name or null",\n'
            f'  "city": "city location or null",\n'
            f'  "date_of_joining": "YYYY-MM-DD. Resolve relative dates like \'today\', \'yesterday\', or \'next Monday\' relative to {today_str}. If unspecified, use {today_str}",\n'
            f'  "is_active": true,\n'
            f'  "spoken_response": "Crisp, courteous Jarvis voice response acknowledging the intent",\n'
            f'  "is_valid": true,\n'
            f'  "missing_fields": []\n'
            f"}}\n"
            f"Rules:\n"
            f"1. If employee_name is missing or unclear, set is_valid to false and add 'employee_name' to missing_fields.\n"
            f"2. Format date_of_joining strictly as YYYY-MM-DD.\n"
            f"3. Maintain a professional, Jarvis-style persona in 'spoken_response'."
        )

        if not self.client:
            return {
                "success": False,
                "error": "Google Gemini client is not initialized. Check GEMINI_API_KEY in .env.",
                "transcription": text_fallback or "Audio provided (no API key)",
                "dto": None,
                "spoken_response": "I apologize, but my Gemini voice engine is not configured with an API key."
            }

        try:
            contents = [system_prompt]
            if audio_bytes:
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                contents.append(audio_part)
            elif text_fallback:
                contents.append(f"User Command: {text_fallback}")
            else:
                return {
                    "success": False,
                    "error": "No audio or text input was provided.",
                    "transcription": "",
                    "dto": None,
                    "spoken_response": "I did not detect any audio input. Please speak or type your request."
                }

            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )

            raw_text = response.text.strip()
            data = json.loads(raw_text)

            transcription = data.get("transcription") or text_fallback or "Voice command processed"
            emp_name = data.get("employee_name")
            missing_fields = data.get("missing_fields") or []

            if not emp_name or not str(emp_name).strip():
                if "employee_name" not in missing_fields:
                    missing_fields.append("employee_name")
                return {
                    "success": False,
                    "transcription": transcription,
                    "dto": None,
                    "missing_fields": missing_fields,
                    "spoken_response": (
                        data.get("spoken_response") or 
                        "I heard your request, but I was unable to detect the employee's name. Please provide their full name."
                    ),
                    "raw_data": data
                }

            # Parse date safely
            raw_doj = data.get("date_of_joining") or today_str
            try:
                parsed_doj = date.fromisoformat(str(raw_doj).split("T")[0])
            except Exception:
                parsed_doj = date.today()

            # Construct validated Pydantic DTO
            dto = EmployeeCreate(
                employee_name=str(emp_name).strip(),
                manager_name=str(data.get("manager_name")).strip() if data.get("manager_name") else None,
                city=str(data.get("city")).strip() if data.get("city") else None,
                date_of_joining=parsed_doj,
                is_active=bool(data.get("is_active", True))
            )

            spoken_resp = data.get("spoken_response")
            if not spoken_resp:
                spoken_resp = f"Registering employee {dto.employee_name} in {dto.city or 'unspecified location'}."

            return {
                "success": True,
                "transcription": transcription,
                "dto": dto,
                "missing_fields": [],
                "spoken_response": spoken_resp,
                "raw_data": data
            }

        except Exception as exc:
            logger.error("Error processing voice command with Gemini: %s", exc, exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "transcription": text_fallback or "",
                "dto": None,
                "spoken_response": f"I encountered an issue processing your request: {str(exc)}"
            }

    @staticmethod
    def execute_registration(dto: EmployeeCreate, actor: str = "Jarvis Voice") -> Dict[str, Any]:
        """
        Persist the validated employee DTO directly to PostgreSQL.
        """
        try:
            created = EmployeeService.create_employee(dto, actor=actor)
            spoken = (
                f"Affirmative! Employee {created['employee_name']} has been successfully registered "
                f"with Employee ID {created['employee_id']}."
            )
            return {
                "success": True,
                "employee": created,
                "spoken_response": spoken,
                "message": f"Successfully registered {created['employee_name']} (ID: {created['employee_id']})"
            }
        except Exception as exc:
            logger.error("Failed to persist voice-registered employee: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "spoken_response": f"Registration failed due to a database error: {str(exc)}"
            }

    # -------------------------------------------------------------------------
    # 2. EDIT EMPLOYEE VOICE PROCESSING
    # -------------------------------------------------------------------------
    def process_edit_command(
        self,
        audio_bytes: Optional[bytes] = None,
        mime_type: str = "audio/wav",
        text_fallback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process speech or natural text into structured parameters for editing an employee.
        """
        today_str = date.today().isoformat()
        system_prompt = (
            f"You are Jarvis, an intelligent and polite employee management voice AI assistant.\n"
            f"Today's date is {today_str}.\n"
            f"Listen to the audio (or read text) and extract details for updating an existing employee record.\n"
            f"The user may identify the employee by numeric ID (e.g., 'employee 3', 'ID 5') or by employee name (e.g., 'Priya Nair', 'Rahul').\n"
            f"The user may request changes to one or more of: employee_name, manager_name, city, date_of_joining, is_active.\n"
            f"Output a valid JSON object matching this schema:\n"
            f"{{\n"
            f'  "transcription": "exact transcription of what the user spoke",\n'
            f'  "employee_id": 123,\n'
            f'  "target_employee_name": "name of target employee or null if ID was provided",\n'
            f'  "fields": {{\n'
            f'    "employee_name": "new name or null",\n'
            f'    "manager_name": "new manager name or null",\n'
            f'    "city": "new city or null",\n'
            f'    "date_of_joining": "YYYY-MM-DD or null. Resolve relative dates like \'today\', \'yesterday\' relative to {today_str}",\n'
            f'    "is_active": true/false or null\n'
            f'  }},\n'
            f'  "spoken_response": "Crisp, courteous Jarvis voice response acknowledging the update intent",\n'
            f'  "is_valid": true,\n'
            f'  "missing_fields": []\n'
            f"}}\n"
            f"Rules:\n"
            f"1. At least one identifier (employee_id or target_employee_name) must be present. If neither is present, set is_valid to false and add 'identifier' to missing_fields.\n"
            f"2. At least one field in 'fields' must be specified (not null). If no fields are changed, set is_valid to false and add 'fields' to missing_fields.\n"
            f"3. Format date_of_joining strictly as YYYY-MM-DD if provided.\n"
            f"4. Maintain a professional, Jarvis-style persona in 'spoken_response'."
        )

        if not self.client:
            return {
                "success": False,
                "error": "Google Gemini client is not initialized. Check GEMINI_API_KEY in .env.",
                "transcription": text_fallback or "Audio provided (no API key)",
                "employee_id": None,
                "target_employee_name": None,
                "fields": {},
                "spoken_response": "I apologize, but my Gemini voice engine is not configured with an API key."
            }

        try:
            contents = [system_prompt]
            if audio_bytes:
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                contents.append(audio_part)
            elif text_fallback:
                contents.append(f"User Command: {text_fallback}")
            else:
                return {
                    "success": False,
                    "error": "No audio or text input was provided.",
                    "transcription": "",
                    "employee_id": None,
                    "target_employee_name": None,
                    "fields": {},
                    "spoken_response": "I did not detect any audio input. Please speak or type your request."
                }

            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )

            raw_text = response.text.strip()
            data = json.loads(raw_text)

            transcription = data.get("transcription") or text_fallback or "Voice command processed"
            emp_id = data.get("employee_id")
            target_name = data.get("target_employee_name")
            raw_fields = data.get("fields") or {}
            missing_fields = data.get("missing_fields") or []

            # Clean fields dictionary of None or empty string values
            cleaned_fields = {}
            for k, v in raw_fields.items():
                if v is not None and v != "":
                    if k == "date_of_joining":
                        try:
                            cleaned_fields[k] = date.fromisoformat(str(v).split("T")[0])
                        except Exception:
                            cleaned_fields[k] = date.today()
                    else:
                        cleaned_fields[k] = v

            # Validate target identifier
            if not emp_id and not target_name:
                if "identifier" not in missing_fields:
                    missing_fields.append("identifier")
                return {
                    "success": False,
                    "transcription": transcription,
                    "employee_id": None,
                    "target_employee_name": None,
                    "fields": cleaned_fields,
                    "missing_fields": missing_fields,
                    "spoken_response": data.get("spoken_response") or "Please specify which employee you would like to edit by name or ID.",
                    "raw_data": data
                }

            if not cleaned_fields:
                if "fields" not in missing_fields:
                    missing_fields.append("fields")
                return {
                    "success": False,
                    "transcription": transcription,
                    "employee_id": emp_id,
                    "target_employee_name": target_name,
                    "fields": {},
                    "missing_fields": missing_fields,
                    "spoken_response": data.get("spoken_response") or "Please specify which details you wish to update, such as city, manager, or status.",
                    "raw_data": data
                }

            spoken_resp = data.get("spoken_response") or f"Preparing updates for employee {emp_id or target_name}."

            return {
                "success": True,
                "transcription": transcription,
                "employee_id": int(emp_id) if emp_id is not None else None,
                "target_employee_name": str(target_name).strip() if target_name else None,
                "fields": cleaned_fields,
                "missing_fields": [],
                "spoken_response": spoken_resp,
                "raw_data": data
            }

        except Exception as exc:
            logger.error("Error processing edit voice command with Gemini: %s", exc, exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "transcription": text_fallback or "",
                "employee_id": None,
                "target_employee_name": None,
                "fields": {},
                "spoken_response": f"I encountered an issue processing your edit request: {str(exc)}"
            }

    @staticmethod
    def execute_update(
        employee_id: Optional[int] = None,
        target_name: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        actor: str = "Jarvis Voice"
    ) -> Dict[str, Any]:
        """
        Resolve employee target and apply updates to PostgreSQL database.
        """
        if not fields:
            return {
                "success": False,
                "error": "No update fields provided.",
                "spoken_response": "I could not find any fields to update."
            }

        target_emp_id = None
        target_emp_name = None

        if employee_id:
            emp = EmployeeService.get_employee(int(employee_id))
            if not emp:
                return {
                    "success": False,
                    "error": f"Employee ID {employee_id} not found.",
                    "spoken_response": f"I apologize, but employee ID {employee_id} does not exist in the database."
                }
            target_emp_id = emp["employee_id"]
            target_emp_name = emp["employee_name"]
        elif target_name:
            search_res = EmployeeService.find_employee(target_name.strip())
            if search_res["status"] == "not_found":
                return {
                    "success": False,
                    "error": search_res["message"],
                    "spoken_response": f"I could not locate an employee named {target_name}."
                }
            elif search_res["status"] == "multiple_matches":
                matches = search_res["matches"]
                match_summary = ", ".join([f"ID {m['employee_id']} ({m['employee_name']})" for m in matches[:3]])
                return {
                    "success": False,
                    "error": search_res["message"],
                    "spoken_response": f"I found multiple employees matching {target_name}: {match_summary}. Please specify by ID."
                }
            else:
                emp = search_res["employee"]
                target_emp_id = emp["employee_id"]
                target_emp_name = emp["employee_name"]
        else:
            return {
                "success": False,
                "error": "Neither employee ID nor name was specified.",
                "spoken_response": "Please identify the employee by ID or name."
            }

        try:
            res = EmployeeService.update_employee(target_emp_id, fields, actor=actor)
            if res["status"] == "success":
                updated_desc = ", ".join([f"{k.replace('_', ' ')} to {v}" for k, v in fields.items()])
                spoken = f"Affirmative. I have updated {target_emp_name}'s record: {updated_desc}."
                return {
                    "success": True,
                    "employee_id": target_emp_id,
                    "employee": res["employee"],
                    "spoken_response": spoken,
                    "message": f"Successfully updated {target_emp_name} (ID: {target_emp_id})"
                }
            else:
                return {
                    "success": False,
                    "error": res["message"],
                    "spoken_response": f"Update failed: {res['message']}"
                }
        except Exception as exc:
            logger.error("Failed to execute voice update: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "spoken_response": f"An error occurred while updating the record: {str(exc)}"
            }

    # -------------------------------------------------------------------------
    # 3. DEACTIVATE EMPLOYEE VOICE PROCESSING
    # -------------------------------------------------------------------------
    def process_deactivate_command(
        self,
        audio_bytes: Optional[bytes] = None,
        mime_type: str = "audio/wav",
        text_fallback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process speech or natural text into structured parameters for deactivating an employee.
        """
        today_str = date.today().isoformat()
        system_prompt = (
            f"You are Jarvis, an intelligent and polite employee management voice AI assistant.\n"
            f"Today's date is {today_str}.\n"
            f"Listen to the audio (or read text) and extract details to deactivate an employee record.\n"
            f"The user will indicate which employee to deactivate by numeric ID (e.g., 'deactivate employee 3', 'ID 5') or by name (e.g., 'deactivate Priya Nair', 'disable Rahul Sharma').\n"
            f"Output a valid JSON object matching this schema:\n"
            f"{{\n"
            f'  "transcription": "exact transcription of what the user spoke",\n'
            f'  "employee_id": 123,\n'
            f'  "target_employee_name": "name of target employee or null if ID was provided",\n'
            f'  "spoken_response": "Crisp, courteous Jarvis voice response acknowledging the deactivation intent",\n'
            f'  "is_valid": true,\n'
            f'  "missing_fields": []\n'
            f"}}\n"
            f"Rules:\n"
            f"1. At least one identifier (employee_id or target_employee_name) must be present. If neither is detected, set is_valid to false and add 'identifier' to missing_fields.\n"
            f"2. Maintain a professional, courteous Jarvis-style persona in 'spoken_response'."
        )

        if not self.client:
            return {
                "success": False,
                "error": "Google Gemini client is not initialized. Check GEMINI_API_KEY in .env.",
                "transcription": text_fallback or "Audio provided (no API key)",
                "employee_id": None,
                "target_employee_name": None,
                "spoken_response": "I apologize, but my Gemini voice engine is not configured with an API key."
            }

        try:
            contents = [system_prompt]
            if audio_bytes:
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                contents.append(audio_part)
            elif text_fallback:
                contents.append(f"User Command: {text_fallback}")
            else:
                return {
                    "success": False,
                    "error": "No audio or text input was provided.",
                    "transcription": "",
                    "employee_id": None,
                    "target_employee_name": None,
                    "spoken_response": "I did not detect any audio input. Please speak or type your request."
                }

            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )

            raw_text = response.text.strip()
            data = json.loads(raw_text)

            transcription = data.get("transcription") or text_fallback or "Voice command processed"
            emp_id = data.get("employee_id")
            target_name = data.get("target_employee_name")
            missing_fields = data.get("missing_fields") or []

            if not emp_id and not target_name:
                if "identifier" not in missing_fields:
                    missing_fields.append("identifier")
                return {
                    "success": False,
                    "transcription": transcription,
                    "employee_id": None,
                    "target_employee_name": None,
                    "missing_fields": missing_fields,
                    "spoken_response": data.get("spoken_response") or "Please specify which employee you would like to deactivate by name or ID.",
                    "raw_data": data
                }

            spoken_resp = data.get("spoken_response") or f"Preparing deactivation for employee {emp_id or target_name}."

            return {
                "success": True,
                "transcription": transcription,
                "employee_id": int(emp_id) if emp_id is not None else None,
                "target_employee_name": str(target_name).strip() if target_name else None,
                "missing_fields": [],
                "spoken_response": spoken_resp,
                "raw_data": data
            }

        except Exception as exc:
            logger.error("Error processing deactivation voice command with Gemini: %s", exc, exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "transcription": text_fallback or "",
                "employee_id": None,
                "target_employee_name": None,
                "spoken_response": f"I encountered an issue processing your deactivation request: {str(exc)}"
            }

    @staticmethod
    def execute_deactivation(
        employee_id: Optional[int] = None,
        target_name: Optional[str] = None,
        actor: str = "Jarvis Voice"
    ) -> Dict[str, Any]:
        """
        Resolve employee target and apply soft-deactivation in PostgreSQL database.
        """
        target_emp_id = None
        target_emp_name = None

        if employee_id:
            emp = EmployeeService.get_employee(int(employee_id))
            if not emp:
                return {
                    "success": False,
                    "error": f"Employee ID {employee_id} not found.",
                    "spoken_response": f"I apologize, but employee ID {employee_id} does not exist in the database."
                }
            target_emp_id = emp["employee_id"]
            target_emp_name = emp["employee_name"]
        elif target_name:
            search_res = EmployeeService.find_employee(target_name.strip())
            if search_res["status"] == "not_found":
                return {
                    "success": False,
                    "error": search_res["message"],
                    "spoken_response": f"I could not locate an employee named {target_name}."
                }
            elif search_res["status"] == "multiple_matches":
                matches = search_res["matches"]
                match_summary = ", ".join([f"ID {m['employee_id']} ({m['employee_name']})" for m in matches[:3]])
                return {
                    "success": False,
                    "error": search_res["message"],
                    "spoken_response": f"I found multiple employees matching {target_name}: {match_summary}. Please specify by ID."
                }
            else:
                emp = search_res["employee"]
                target_emp_id = emp["employee_id"]
                target_emp_name = emp["employee_name"]
        else:
            return {
                "success": False,
                "error": "Neither employee ID nor name was specified.",
                "spoken_response": "Please identify the employee to deactivate by ID or name."
            }

        try:
            res = EmployeeService.deactivate_employee(target_emp_id, actor=actor)
            if res["status"] == "success":
                spoken = f"Affirmative. Employee {target_emp_name} with ID {target_emp_id} has been deactivated."
                return {
                    "success": True,
                    "employee_id": target_emp_id,
                    "employee": res["employee"],
                    "spoken_response": spoken,
                    "message": f"Successfully deactivated {target_emp_name} (ID: {target_emp_id})"
                }
            else:
                return {
                    "success": False,
                    "error": res["message"],
                    "spoken_response": f"Deactivation failed: {res['message']}"
                }
        except Exception as exc:
            logger.error("Failed to execute voice deactivation: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "spoken_response": f"An error occurred while deactivating the record: {str(exc)}"
            }

    # -------------------------------------------------------------------------
    # 4. AI CHATBOT MULTIMODAL VOICE TRANSCRIPTION
    # -------------------------------------------------------------------------
    def transcribe_chat_audio(
        self,
        audio_bytes: Optional[bytes] = None,
        mime_type: str = "audio/wav",
        text_fallback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe speech from microphone into plain English question for AI Chatbot workflow.
        """
        if text_fallback:
            return {
                "success": True,
                "transcription": text_fallback.strip(),
                "spoken_response": "Processing your query."
            }

        if not audio_bytes:
            return {
                "success": False,
                "error": "No audio input was provided.",
                "transcription": "",
                "spoken_response": "I did not detect any speech."
            }

        if not self.client:
            return {
                "success": False,
                "error": "Google Gemini client is not initialized. Check GEMINI_API_KEY in .env.",
                "transcription": "",
                "spoken_response": "Voice transcription engine is not configured with an API key."
            }

        system_prompt = (
            "You are Jarvis, an audio transcription assistant for an Employee Management Chatbot.\n"
            "Listen to the audio and transcribe the user's spoken question or command accurately into English text.\n"
            "Ensure proper punctuation, spelling of Indian and international names, and clarity.\n"
            "Output a valid JSON object matching this schema:\n"
            "{\n"
            '  "transcription": "the full, verbatim transcription of what the user asked",\n'
            '  "spoken_response": "Understood. Consulting the employee database."\n'
            "}\n"
        )

        try:
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=[system_prompt, audio_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )

            raw_text = response.text.strip()
            data = json.loads(raw_text)
            transcription = data.get("transcription", "").strip()

            if not transcription:
                return {
                    "success": False,
                    "error": "Transcription was empty.",
                    "transcription": "",
                    "spoken_response": "I could not make out any words. Could you please repeat that?"
                }

            return {
                "success": True,
                "transcription": transcription,
                "spoken_response": data.get("spoken_response") or "Processing your voice query."
            }

        except Exception as exc:
            logger.error("Error transcribing chat audio with Gemini: %s", exc, exc_info=True)
            return {
                "success": False,
                "error": str(exc),
                "transcription": "",
                "spoken_response": f"Voice transcription encountered an error: {str(exc)}"
            }
