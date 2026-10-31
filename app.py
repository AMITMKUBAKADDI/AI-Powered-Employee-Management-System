# app.py
"""Streamlit User Interface for AI-Powered Employee Management System with Full Jarvis Voice Assistant."""

import os
import re
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime
from langchain_core.messages import HumanMessage, AIMessage

from src.config import get_settings
from src.db import check_connection, init_db
from src.schemas import EmployeeCreate
from src.services.employee_service import EmployeeService
from src.auth import Role, check_permission
from src.ai.graph import run_chatbot_workflow
from src.ai.voice_service import VoiceService

# Streamlit Page Configuration
st.set_page_config(
    page_title="AI Employee Management System",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #4b5563;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .badge-admin {
        background-color: #ef4444;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-user {
        background-color: #10b981;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-active {
        color: #059669;
        font-weight: 600;
    }
    .status-inactive {
        color: #dc2626;
        font-weight: 600;
    }
    .tool-pill {
        background: #f3f4f6;
        border-left: 3px solid #3b82f6;
        padding: 8px 12px;
        border-radius: 4px;
        margin-top: 6px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .jarvis-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .jarvis-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #38bdf8;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .jarvis-badge {
        background: #0284c7;
        color: white;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 9999px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .jarvis-speech-box {
        background: rgba(15, 23, 42, 0.7);
        border-left: 3px solid #38bdf8;
        padding: 10px 14px;
        border-radius: 6px;
        font-style: italic;
        color: #e2e8f0;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Settings & Voice Service initialization
settings = get_settings()
voice_service = VoiceService()

def speak_jarvis_response(text: str):
    """Execute client-side browser speech synthesis for Jarvis voice output."""
    if not text:
        return
    # Strip markdown code blocks, inline code, bold, italics, headers, links, and symbols
    clean_text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    clean_text = re.sub(r'`([^`]+)`', r'\1', clean_text)
    clean_text = re.sub(r'[*_~#]+', '', clean_text)
    clean_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_text)
    clean_text = clean_text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    if not clean_text:
        return
    components.html(
        f"""
        <script>
        (function() {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance('{clean_text}');
                utter.rate = 1.02;
                utter.pitch = 1.0;
                window.speechSynthesis.speak(utter);
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

# Auto-initialize database schema and seed data on first load
@st.cache_resource
def bootstrap_database():
    try:
        init_db(seed_sample_data=True)
        return True
    except Exception as exc:
        return False

bootstrap_database()

# Initialize session states
if "role" not in st.session_state:
    st.session_state.role = Role.ADMIN.value
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "langchain_history" not in st.session_state:
    st.session_state.langchain_history = []
if "pending_confirmation" not in st.session_state:
    st.session_state.pending_confirmation = None
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

# Jarvis Voice Session States - Add
if "jarvis_last_result" not in st.session_state:
    st.session_state.jarvis_last_result = None
if "jarvis_processed_audio_hash" not in st.session_state:
    st.session_state.jarvis_processed_audio_hash = None
if "jarvis_already_committed" not in st.session_state:
    st.session_state.jarvis_already_committed = False
if "jarvis_commit_res" not in st.session_state:
    st.session_state.jarvis_commit_res = None

# Jarvis Voice Session States - Edit
if "jarvis_edit_last_result" not in st.session_state:
    st.session_state.jarvis_edit_last_result = None
if "jarvis_edit_processed_audio_hash" not in st.session_state:
    st.session_state.jarvis_edit_processed_audio_hash = None
if "jarvis_edit_already_committed" not in st.session_state:
    st.session_state.jarvis_edit_already_committed = False
if "jarvis_edit_commit_res" not in st.session_state:
    st.session_state.jarvis_edit_commit_res = None
if "edit_emp_id" not in st.session_state:
    st.session_state.edit_emp_id = 1
if "edit_prefill_fields" not in st.session_state:
    st.session_state.edit_prefill_fields = {}

# Jarvis Voice Session States - Deactivate
if "jarvis_deact_last_result" not in st.session_state:
    st.session_state.jarvis_deact_last_result = None
if "jarvis_deact_processed_audio_hash" not in st.session_state:
    st.session_state.jarvis_deact_processed_audio_hash = None
if "jarvis_deact_already_committed" not in st.session_state:
    st.session_state.jarvis_deact_already_committed = False
if "jarvis_deact_commit_res" not in st.session_state:
    st.session_state.jarvis_deact_commit_res = None
if "deact_emp_id" not in st.session_state:
    st.session_state.deact_emp_id = 1

# Jarvis Voice Session States - Chatbot
if "jarvis_chat_processed_audio_hash" not in st.session_state:
    st.session_state.jarvis_chat_processed_audio_hash = None
if "chat_tts_enabled" not in st.session_state:
    st.session_state.chat_tts_enabled = True

# Sidebar
with st.sidebar:
    st.title("💼 Control Panel")
    st.markdown("Configure system access and roles.")

    # Role switcher
    selected_role = st.radio(
        "Current Active Role:",
        options=[Role.ADMIN.value, Role.USER.value],
        format_func=lambda r: f"🛡️ Administrator" if r == Role.ADMIN.value else "👤 Ordinary User",
        index=0 if st.session_state.role == Role.ADMIN.value else 1
    )
    st.session_state.role = selected_role

    st.markdown("---")
    st.subheader("Database Health")
    db_ok = check_connection()
    if db_ok:
        st.success("🟢 PostgreSQL Connected")
    else:
        st.warning("🟠 Database Disconnected / Using Local Fallback")
        st.caption("Check your database credentials in `.env` if PostgreSQL is running.")

    if st.button("🌱 Initialize / Seed Sample Data", use_container_width=True):
        try:
            init_db(seed_sample_data=True)
            st.success("Schema verified & sample records loaded!")
            st.session_state.refresh_counter += 1
            st.rerun()
        except Exception as e:
            st.error(f"Error seeding database: {e}")

    st.markdown("---")
    st.subheader("Gemini AI Status")
    if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here":
        st.success(f"🤖 Gemini Model: `{settings.gemini_model}`")
    else:
        st.info("⚠️ Add `GEMINI_API_KEY` in `.env` for AI Chatbot.")

    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.chat_messages = []
        st.session_state.langchain_history = []
        st.session_state.pending_confirmation = None
        st.rerun()

# Top Header
col_header, col_badge = st.columns([4, 1])
with col_header:
    st.markdown('<div class="main-header">AI Employee Management System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">PostgreSQL-backed employee directory with LangGraph & Google Gemini AI</div>', unsafe_allow_html=True)
with col_badge:
    badge_class = "badge-admin" if st.session_state.role == Role.ADMIN.value else "badge-user"
    st.markdown(f'<div style="text-align: right; padding-top: 15px;"><span class="{badge_class}">Role: {st.session_state.role.upper()}</span></div>', unsafe_allow_html=True)

# Main Navigation Tabs
tab_view, tab_add, tab_edit, tab_deactivate, tab_chat = st.tabs([
    "📋 View Employees",
    "➕ Add Employee",
    "✏️ Edit Employee",
    "🚫 Deactivate Employee",
    "💬 AI Chatbot"
])

# ==========================================
# TAB 1: VIEW EMPLOYEES
# ==========================================
with tab_view:
    st.subheader("Employee Directory")
    
    # Filter controls
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 1])
    with f_col1:
        name_search = st.text_input("🔍 Search Name:", placeholder="e.g. Rahul, Priya")
    with f_col2:
        city_filter = st.text_input("🏙️ Filter City:", placeholder="e.g. Bangalore, Mumbai")
    with f_col3:
        status_filter = st.selectbox("Status:", options=["All", "Active Only", "Inactive Only"])
    with f_col4:
        page_size = st.selectbox("Per Page:", options=[5, 10, 20, 50], index=1)

    active_param = None
    if status_filter == "Active Only":
        active_param = True
    elif status_filter == "Inactive Only":
        active_param = False

    # Pagination state
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

    # Fetch data
    try:
        result = EmployeeService.search_employees(
            city=city_filter if city_filter else None,
            active_only=active_param,
            name_query=name_search if name_search else None,
            page=st.session_state.current_page,
            page_size=page_size
        )
        total_records = result["total_count"]
        total_pages = result["total_pages"]
        items = result["items"]
        st.markdown(f"**Found {total_records} employee records** (Page {st.session_state.current_page} of {total_pages})")
    except Exception as fetch_err:
        st.error(f"Unable to query employee records: {str(fetch_err)}")
        if st.button("🔄 Initialize Schema and Retry"):
            init_db(seed_sample_data=True)
            st.rerun()
        items = []
        total_records = 0
        total_pages = 1

    if items:
        df = pd.DataFrame(items)
        df_display = df[[
            "employee_id", "employee_name", "manager_name", "city", 
            "date_of_joining", "is_active", "modified_on"
        ]].copy()
        
        # Friendly boolean column display
        df_display["is_active"] = df_display["is_active"].apply(lambda x: "Active" if x else "Inactive")
        
        st.dataframe(
            df_display,
            column_config={
                "employee_id": st.column_config.NumberColumn("ID", width="small"),
                "employee_name": st.column_config.TextColumn("Employee Name"),
                "manager_name": st.column_config.TextColumn("Manager"),
                "city": st.column_config.TextColumn("City"),
                "date_of_joining": st.column_config.DateColumn("Date Joined"),
                "is_active": st.column_config.TextColumn("Status"),
                "modified_on": st.column_config.TextColumn("Last Modified"),
            },
            hide_index=True,
            use_container_width=True
        )

        # Pagination buttons
        p_col1, p_col2, p_col3, p_col4 = st.columns([1, 1, 4, 2])
        with p_col1:
            if st.button("⬅️ Previous", disabled=(st.session_state.current_page <= 1)):
                st.session_state.current_page -= 1
                st.rerun()
        with p_col2:
            if st.button("Next ➡️", disabled=(st.session_state.current_page >= total_pages)):
                st.session_state.current_page += 1
                st.rerun()
                
        # Employee Detail Drawer
        st.markdown("---")
        st.subheader("🔎 View Employee Details by ID")
        detail_id = st.number_input("Enter Employee ID to view full details:", min_value=1, step=1)
        if st.button("Fetch Employee"):
            emp_detail = EmployeeService.get_employee(int(detail_id))
            if emp_detail:
                st.json(emp_detail)
            else:
                st.warning(f"No employee found with ID {detail_id}.")
    else:
        st.info("No employee records match the given criteria. Click 'Initialize / Seed Sample Data' in the sidebar if the table is empty.")

# ==========================================
# TAB 2: ADD EMPLOYEE
# ==========================================
with tab_add:
    st.subheader("➕ Register New Employee")

    # --- JARVIS VOICE ASSISTANT COMPONENT (ADD) ---
    st.markdown("""
    <div class="jarvis-card">
        <div class="jarvis-header">
            <span>🎙️ Jarvis Voice Assistant - Add Employee</span>
            <span class="jarvis-badge">AI Multimodal</span>
        </div>
        <p style="color: #cbd5e1; font-size: 0.9rem; margin-top: 6px; margin-bottom: 0;">
            Click the microphone below and speak naturally. For example: 
            <i>"Jarvis, add employee Anita Desai, manager Priya Nair, city Pune, joining today"</i>
        </p>
    </div>
    """, unsafe_allow_html=True)

    v_col1, v_col2 = st.columns([3, 2])
    with v_col1:
        voice_audio = st.audio_input("🎙️ Record Voice Command (Jarvis):", key="jarvis_add_employee_audio")
    with v_col2:
        auto_commit = st.toggle(
            "⚡ Autonomous Mode (Auto-Save directly to DB)", 
            value=True, 
            help="When ON, Jarvis extracts details and immediately creates the record in PostgreSQL without requiring manual form entry."
        )
        enable_tts = st.toggle(
            "🔊 Speak Response Aloud (Jarvis Voice)", 
            value=True, 
            help="Jarvis replies with an audio voice confirmation using browser speech synthesis."
        )
        if st.button("🔄 Reset Voice Assistant", key="reset_jarvis_add", use_container_width=True):
            st.session_state.jarvis_last_result = None
            st.session_state.jarvis_processed_audio_hash = None
            st.session_state.jarvis_already_committed = False
            st.session_state.jarvis_commit_res = None
            for k in ["add_name", "add_manager", "add_city", "add_doj", "add_active"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # Optional natural language text command
    with st.expander("💬 Or type natural language command for Jarvis:"):
        t_col1, t_col2 = st.columns([4, 1])
        with t_col1:
            natural_text = st.text_input(
                "Enter command:",
                placeholder="e.g. Add employee Anita Desai, manager Vikram Malhotra, city Pune, joining today",
                label_visibility="collapsed",
                key="jarvis_text_input"
            )
        with t_col2:
            submit_text_cmd = st.button("Run Jarvis", key="btn_run_jarvis_add", use_container_width=True)

    # Audio processing with deduplication check
    if voice_audio is not None:
        raw_audio = voice_audio.getvalue()
        audio_hash = hash(raw_audio)
        if st.session_state.jarvis_processed_audio_hash != audio_hash:
            st.session_state.jarvis_processed_audio_hash = audio_hash
            st.session_state.jarvis_already_committed = False
            st.session_state.jarvis_commit_res = None
            with st.spinner("🤖 Jarvis is analyzing your voice command with Google Gemini..."):
                res = voice_service.process_voice_command(
                    audio_bytes=raw_audio,
                    mime_type=voice_audio.type or "audio/wav"
                )
                st.session_state.jarvis_last_result = res

    # Text processing
    if submit_text_cmd and natural_text.strip():
        st.session_state.jarvis_already_committed = False
        st.session_state.jarvis_commit_res = None
        with st.spinner("🤖 Jarvis is parsing your text command..."):
            res = voice_service.process_voice_command(text_fallback=natural_text.strip())
            st.session_state.jarvis_last_result = res

    # Render Jarvis feedback
    if st.session_state.jarvis_last_result:
        v_res = st.session_state.jarvis_last_result
        if v_res.get("success"):
            st.markdown(f"**🎙️ What Jarvis Heard:** *\"{v_res.get('transcription')}\"*")
            st.markdown(
                f"<div class='jarvis-speech-box'>🤖 <b>Jarvis:</b> {v_res.get('spoken_response')}</div>", 
                unsafe_allow_html=True
            )

            dto = v_res.get("dto")
            if auto_commit:
                if not st.session_state.jarvis_already_committed:
                    commit_res = voice_service.execute_registration(
                        dto, 
                        actor=f"Jarvis Voice ({st.session_state.role})"
                    )
                    st.session_state.jarvis_commit_res = commit_res
                    st.session_state.jarvis_already_committed = True
                    st.session_state.refresh_counter += 1
                    if enable_tts:
                        speak_jarvis_response(commit_res.get("spoken_response", v_res.get("spoken_response")))

                if st.session_state.jarvis_commit_res:
                    c_res = st.session_state.jarvis_commit_res
                    if c_res.get("success"):
                        emp_rec = c_res.get("employee", {})
                        st.success(f"✅ {c_res.get('message')}")
                        with st.expander("📄 View Registered Employee Record in PostgreSQL", expanded=True):
                            st.json(emp_rec)
                    else:
                        st.error(f"❌ {c_res.get('error')}")
            else:
                # Pre-fill manual form for review
                st.session_state.add_name = dto.employee_name
                st.session_state.add_manager = dto.manager_name or ""
                st.session_state.add_city = dto.city or ""
                st.session_state.add_doj = dto.date_of_joining
                st.session_state.add_active = dto.is_active
                st.info("📋 Form fields below have been pre-filled by Jarvis. Please review and click Submit.")
                if enable_tts and not st.session_state.jarvis_already_committed:
                    speak_jarvis_response(v_res.get("spoken_response"))
                    st.session_state.jarvis_already_committed = True
        else:
            st.warning(f"⚠️ {v_res.get('spoken_response') or v_res.get('error')}")
            if enable_tts and not st.session_state.jarvis_already_committed:
                speak_jarvis_response(v_res.get("spoken_response"))
                st.session_state.jarvis_already_committed = True

    st.markdown("---")
    st.markdown("#### ✍️ Manual Registration Form")
    st.caption("You can also type and submit employee information directly:")

    with st.form("add_employee_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            emp_name = st.text_input("Employee Name *", value=st.session_state.get("add_name", ""), placeholder="Full legal name")
            emp_manager = st.text_input("Manager Name", value=st.session_state.get("add_manager", ""), placeholder="e.g. Priya Nair")
            emp_city = st.text_input("City", value=st.session_state.get("add_city", ""), placeholder="e.g. Bangalore, Hyderabad")
        with col_b:
            emp_doj = st.date_input("Date of Joining *", value=st.session_state.get("add_doj", date.today()))
            emp_active = st.checkbox("Active Status", value=st.session_state.get("add_active", True))

        submit_add = st.form_submit_button("Submit Employee Registration", use_container_width=True)

    if submit_add:
        if not emp_name.strip():
            st.error("Employee Name is required and cannot be empty.")
        else:
            try:
                dto = EmployeeCreate(
                    employee_name=emp_name.strip(),
                    manager_name=emp_manager.strip() if emp_manager.strip() else None,
                    city=emp_city.strip() if emp_city.strip() else None,
                    date_of_joining=emp_doj,
                    is_active=emp_active
                )
                created = EmployeeService.create_employee(dto, actor=f"UI Form ({st.session_state.role})")
                st.success(f"✅ Employee successfully created! Assigned Employee ID: {created['employee_id']}")
                st.session_state.refresh_counter += 1
                for k in ["add_name", "add_manager", "add_city", "add_doj", "add_active"]:
                    if k in st.session_state:
                        del st.session_state[k]
            except Exception as ex:
                st.error(f"Failed to create employee: {str(ex)}")

# ==========================================
# TAB 3: EDIT EMPLOYEE (Admin Only)
# ==========================================
with tab_edit:
    st.subheader("✏️ Update Employee Details")
    if not check_permission(st.session_state.role, "can_update"):
        st.warning("⚠️ Restricted: Administrator privileges are required to update employee records.")
    else:
        # --- JARVIS VOICE ASSISTANT COMPONENT (EDIT) ---
        st.markdown("""
        <div class="jarvis-card">
            <div class="jarvis-header">
                <span>🎙️ Jarvis Voice Assistant - Edit Employee</span>
                <span class="jarvis-badge">AI Multimodal</span>
            </div>
            <p style="color: #cbd5e1; font-size: 0.9rem; margin-top: 6px; margin-bottom: 0;">
                Click the microphone and speak naturally to update an employee. For example: 
                <i>"Jarvis, change Priya Nair's city to Hyderabad"</i> or 
                <i>"Update employee 2, set manager to Rahul Sharma and city to Pune"</i>
            </p>
        </div>
        """, unsafe_allow_html=True)

        e_col1, e_col2 = st.columns([3, 2])
        with e_col1:
            edit_voice_audio = st.audio_input("🎙️ Record Edit Voice Command (Jarvis):", key="jarvis_edit_employee_audio")
        with e_col2:
            edit_auto_commit = st.toggle(
                "⚡ Autonomous Mode (Auto-Update directly in DB)", 
                value=True, 
                help="When ON, Jarvis extracts employee updates and immediately applies them to PostgreSQL without manual form submission."
            )
            edit_enable_tts = st.toggle(
                "🔊 Speak Response Aloud (Jarvis Voice)", 
                value=True, 
                key="edit_tts_toggle",
                help="Jarvis replies with an audio voice confirmation using browser speech synthesis."
            )
            if st.button("🔄 Reset Voice Assistant", key="reset_jarvis_edit", use_container_width=True):
                st.session_state.jarvis_edit_last_result = None
                st.session_state.jarvis_edit_processed_audio_hash = None
                st.session_state.jarvis_edit_already_committed = False
                st.session_state.jarvis_edit_commit_res = None
                st.session_state.edit_prefill_fields = {}
                st.rerun()

        # Optional natural language text command
        with st.expander("💬 Or type natural language edit command for Jarvis:"):
            et_col1, et_col2 = st.columns([4, 1])
            with et_col1:
                edit_natural_text = st.text_input(
                    "Enter edit command:",
                    placeholder="e.g. Update Priya Nair's city to Mumbai or Change employee 2 manager to Rahul Sharma",
                    label_visibility="collapsed",
                    key="jarvis_edit_text_input"
                )
            with et_col2:
                submit_edit_text_cmd = st.button("Run Jarvis", key="btn_run_jarvis_edit", use_container_width=True)

        # Audio processing with deduplication check
        if edit_voice_audio is not None:
            raw_audio = edit_voice_audio.getvalue()
            audio_hash = hash(raw_audio)
            if st.session_state.jarvis_edit_processed_audio_hash != audio_hash:
                st.session_state.jarvis_edit_processed_audio_hash = audio_hash
                st.session_state.jarvis_edit_already_committed = False
                st.session_state.jarvis_edit_commit_res = None
                with st.spinner("🤖 Jarvis is analyzing your edit voice command with Google Gemini..."):
                    res = voice_service.process_edit_command(
                        audio_bytes=raw_audio,
                        mime_type=edit_voice_audio.type or "audio/wav"
                    )
                    st.session_state.jarvis_edit_last_result = res

        # Text processing
        if submit_edit_text_cmd and edit_natural_text.strip():
            st.session_state.jarvis_edit_already_committed = False
            st.session_state.jarvis_edit_commit_res = None
            with st.spinner("🤖 Jarvis is parsing your edit command..."):
                res = voice_service.process_edit_command(text_fallback=edit_natural_text.strip())
                st.session_state.jarvis_edit_last_result = res

        # Render Jarvis Edit feedback
        if st.session_state.jarvis_edit_last_result:
            e_res = st.session_state.jarvis_edit_last_result
            if e_res.get("success"):
                st.markdown(f"**🎙️ What Jarvis Heard:** *\"{e_res.get('transcription')}\"*")
                st.markdown(
                    f"<div class='jarvis-speech-box'>🤖 <b>Jarvis:</b> {e_res.get('spoken_response')}</div>", 
                    unsafe_allow_html=True
                )

                fields = e_res.get("fields", {})
                target_id = e_res.get("employee_id")
                target_name = e_res.get("target_employee_name")

                if edit_auto_commit:
                    if not st.session_state.jarvis_edit_already_committed:
                        commit_res = voice_service.execute_update(
                            employee_id=target_id,
                            target_name=target_name,
                            fields=fields,
                            actor=f"Jarvis Voice ({st.session_state.role})"
                        )
                        st.session_state.jarvis_edit_commit_res = commit_res
                        st.session_state.jarvis_edit_already_committed = True
                        st.session_state.refresh_counter += 1
                        if edit_enable_tts:
                            speak_jarvis_response(commit_res.get("spoken_response", e_res.get("spoken_response")))

                    if st.session_state.jarvis_edit_commit_res:
                        c_res = st.session_state.jarvis_edit_commit_res
                        if c_res.get("success"):
                            st.success(f"✅ {c_res.get('message')}")
                            with st.expander("📄 View Updated Employee Record in PostgreSQL", expanded=True):
                                st.json(c_res.get("employee", {}))
                        else:
                            st.error(f"❌ {c_res.get('error')}")
                else:
                    # Pre-fill manual form for review
                    resolved_id = target_id
                    if not resolved_id and target_name:
                        sr = EmployeeService.find_employee(target_name)
                        if sr["status"] == "success":
                            resolved_id = sr["employee"]["employee_id"]
                    if resolved_id:
                        st.session_state.edit_emp_id = int(resolved_id)
                    st.session_state.edit_prefill_fields = fields
                    st.info("📋 Target employee and updated fields have been pre-filled below. Please review and click 'Save Changes'.")
                    if edit_enable_tts and not st.session_state.jarvis_edit_already_committed:
                        speak_jarvis_response(e_res.get("spoken_response"))
                        st.session_state.jarvis_edit_already_committed = True
            else:
                st.warning(f"⚠️ {e_res.get('spoken_response') or e_res.get('error')}")
                if edit_enable_tts and not st.session_state.jarvis_edit_already_committed:
                    speak_jarvis_response(e_res.get("spoken_response"))
                    st.session_state.jarvis_edit_already_committed = True

        st.markdown("---")
        st.markdown("#### ✍️ Manual Edit Form")
        edit_id = st.number_input("Employee ID to edit:", min_value=1, step=1, key="edit_emp_id")
        emp_to_edit = EmployeeService.get_employee(int(edit_id))
        
        if emp_to_edit:
            prefills = st.session_state.get("edit_prefill_fields", {})
            st.info(f"Editing Record: **{emp_to_edit['employee_name']}** (Current City: {emp_to_edit['city']})")
            with st.form("edit_employee_form"):
                e_name = st.text_input("Employee Name", value=prefills.get("employee_name", emp_to_edit["employee_name"]))
                e_manager = st.text_input("Manager Name", value=prefills.get("manager_name", emp_to_edit["manager_name"] or ""))
                e_city = st.text_input("City", value=prefills.get("city", emp_to_edit["city"] or ""))
                
                # Parse existing date
                init_doj = prefills.get("date_of_joining")
                if not init_doj:
                    try:
                        init_doj = date.fromisoformat(emp_to_edit["date_of_joining"])
                    except Exception:
                        init_doj = date.today()
                    
                e_doj = st.date_input("Date of Joining", value=init_doj)
                e_active = st.checkbox("Is Active", value=prefills.get("is_active", emp_to_edit["is_active"]))
                
                submit_edit = st.form_submit_button("Save Changes", use_container_width=True)
                
            if submit_edit:
                fields = {
                    "employee_name": e_name.strip(),
                    "manager_name": e_manager.strip() if e_manager.strip() else None,
                    "city": e_city.strip() if e_city.strip() else None,
                    "date_of_joining": e_doj,
                    "is_active": e_active
                }
                res = EmployeeService.update_employee(int(edit_id), fields, actor=f"UI Admin ({st.session_state.role})")
                if res["status"] == "success":
                    st.success("✅ Employee record updated successfully! Automatic `modified_on` timestamp refreshed.")
                    st.session_state.edit_prefill_fields = {}
                    st.session_state.refresh_counter += 1
                else:
                    st.error(res["message"])
        else:
            st.caption(f"Enter a valid Employee ID above to load and edit details.")

# ==========================================
# TAB 4: DEACTIVATE EMPLOYEE (Admin Only)
# ==========================================
with tab_deactivate:
    st.subheader("🚫 Soft-Deactivate Employee")
    if not check_permission(st.session_state.role, "can_deactivate"):
        st.warning("⚠️ Restricted: Administrator privileges are required to deactivate employee records.")
    else:
        # --- JARVIS VOICE ASSISTANT COMPONENT (DEACTIVATE) ---
        st.markdown("""
        <div class="jarvis-card">
            <div class="jarvis-header">
                <span>🎙️ Jarvis Voice Assistant - Deactivate Employee</span>
                <span class="jarvis-badge">AI Multimodal</span>
            </div>
            <p style="color: #cbd5e1; font-size: 0.9rem; margin-top: 6px; margin-bottom: 0;">
                Click the microphone and speak naturally to soft-deactivate an employee record. For example: 
                <i>"Jarvis, deactivate employee Anita Desai"</i> or 
                <i>"Deactivate employee ID 3"</i>
            </p>
        </div>
        """, unsafe_allow_html=True)

        d_col1, d_col2 = st.columns([3, 2])
        with d_col1:
            deact_voice_audio = st.audio_input("🎙️ Record Deactivation Voice Command (Jarvis):", key="jarvis_deact_employee_audio")
        with d_col2:
            deact_auto_commit = st.toggle(
                "⚡ Autonomous Mode (Auto-Deactivate directly in DB)", 
                value=True, 
                help="When ON, Jarvis extracts the target employee and immediately applies soft-deactivation in PostgreSQL."
            )
            deact_enable_tts = st.toggle(
                "🔊 Speak Response Aloud (Jarvis Voice)", 
                value=True, 
                key="deact_tts_toggle",
                help="Jarvis replies with an audio voice confirmation using browser speech synthesis."
            )
            if st.button("🔄 Reset Voice Assistant", key="reset_jarvis_deact", use_container_width=True):
                st.session_state.jarvis_deact_last_result = None
                st.session_state.jarvis_deact_processed_audio_hash = None
                st.session_state.jarvis_deact_already_committed = False
                st.session_state.jarvis_deact_commit_res = None
                st.rerun()

        # Optional natural language text command
        with st.expander("💬 Or type natural language deactivation command for Jarvis:"):
            dt_col1, dt_col2 = st.columns([4, 1])
            with dt_col1:
                deact_natural_text = st.text_input(
                    "Enter deactivation command:",
                    placeholder="e.g. Deactivate employee Anita Desai or Deactivate employee ID 3",
                    label_visibility="collapsed",
                    key="jarvis_deact_text_input"
                )
            with dt_col2:
                submit_deact_text_cmd = st.button("Run Jarvis", key="btn_run_jarvis_deact", use_container_width=True)

        # Audio processing with deduplication check
        if deact_voice_audio is not None:
            raw_audio = deact_voice_audio.getvalue()
            audio_hash = hash(raw_audio)
            if st.session_state.jarvis_deact_processed_audio_hash != audio_hash:
                st.session_state.jarvis_deact_processed_audio_hash = audio_hash
                st.session_state.jarvis_deact_already_committed = False
                st.session_state.jarvis_deact_commit_res = None
                with st.spinner("🤖 Jarvis is analyzing your deactivation voice command with Google Gemini..."):
                    res = voice_service.process_deactivate_command(
                        audio_bytes=raw_audio,
                        mime_type=deact_voice_audio.type or "audio/wav"
                    )
                    st.session_state.jarvis_deact_last_result = res

        # Text processing
        if submit_deact_text_cmd and deact_natural_text.strip():
            st.session_state.jarvis_deact_already_committed = False
            st.session_state.jarvis_deact_commit_res = None
            with st.spinner("🤖 Jarvis is parsing your deactivation command..."):
                res = voice_service.process_deactivate_command(text_fallback=deact_natural_text.strip())
                st.session_state.jarvis_deact_last_result = res

        # Render Jarvis Deactivate feedback
        if st.session_state.jarvis_deact_last_result:
            d_res = st.session_state.jarvis_deact_last_result
            if d_res.get("success"):
                st.markdown(f"**🎙️ What Jarvis Heard:** *\"{d_res.get('transcription')}\"*")
                st.markdown(
                    f"<div class='jarvis-speech-box'>🤖 <b>Jarvis:</b> {d_res.get('spoken_response')}</div>", 
                    unsafe_allow_html=True
                )

                target_id = d_res.get("employee_id")
                target_name = d_res.get("target_employee_name")

                if deact_auto_commit:
                    if not st.session_state.jarvis_deact_already_committed:
                        commit_res = voice_service.execute_deactivation(
                            employee_id=target_id,
                            target_name=target_name,
                            actor=f"Jarvis Voice ({st.session_state.role})"
                        )
                        st.session_state.jarvis_deact_commit_res = commit_res
                        st.session_state.jarvis_deact_already_committed = True
                        st.session_state.refresh_counter += 1
                        if deact_enable_tts:
                            speak_jarvis_response(commit_res.get("spoken_response", d_res.get("spoken_response")))

                    if st.session_state.jarvis_deact_commit_res:
                        c_res = st.session_state.jarvis_deact_commit_res
                        if c_res.get("success"):
                            st.success(f"✅ {c_res.get('message')}")
                            with st.expander("📄 View Deactivated Employee Record in PostgreSQL", expanded=True):
                                st.json(c_res.get("employee", {}))
                        else:
                            st.error(f"❌ {c_res.get('error')}")
                else:
                    resolved_id = target_id
                    if not resolved_id and target_name:
                        sr = EmployeeService.find_employee(target_name)
                        if sr["status"] == "success":
                            resolved_id = sr["employee"]["employee_id"]
                    if resolved_id:
                        st.session_state.deact_emp_id = int(resolved_id)
                    st.info("📋 Target employee identified below. Please review and click 'Confirm Deactivation'.")
                    if deact_enable_tts and not st.session_state.jarvis_already_committed:
                        speak_jarvis_response(d_res.get("spoken_response"))
                        st.session_state.jarvis_deact_already_committed = True
            else:
                st.warning(f"⚠️ {d_res.get('spoken_response') or d_res.get('error')}")
                if deact_enable_tts and not st.session_state.jarvis_deact_already_committed:
                    speak_jarvis_response(d_res.get("spoken_response"))
                    st.session_state.jarvis_deact_already_committed = True

        st.markdown("---")
        st.markdown("#### ✍️ Manual Deactivation Review")
        st.markdown("Deactivating an employee sets their `is_active` flag to **False** without deleting historical data.")
        deact_id = st.number_input("Employee ID to deactivate:", min_value=1, step=1, key="deact_emp_id")
        
        target = EmployeeService.get_employee(int(deact_id))
        if target:
            status_text = "Active" if target["is_active"] else "Already Inactive"
            st.write(f"Target: **{target['employee_name']}** | Current Status: `{status_text}` | City: `{target['city']}`")
            
            if st.button("Confirm Deactivation", type="primary"):
                res = EmployeeService.deactivate_employee(int(deact_id), actor=f"UI Admin ({st.session_state.role})")
                if res["status"] == "success":
                    st.success(f"✅ Employee ID {deact_id} has been deactivated.")
                    st.session_state.refresh_counter += 1
                else:
                    st.error(res["message"])
        else:
            st.caption("Enter an Employee ID to view and deactivate.")

# ==========================================
# TAB 5: AI CHATBOT (Streamlit Chat Components with Jarvis Multimodal Voice)
# ==========================================
with tab_chat:
    st.subheader("💬 AI Employee Assistant")
    st.caption("Ask questions about employee dates, managers, counts, locations, or request updates.")

    # Confirmation Banner if LangGraph returned a pending write confirmation
    if st.session_state.pending_confirmation:
        conf = st.session_state.pending_confirmation
        st.warning(f"⚠️ **Action Confirmation Required:**\n\n{conf.get('message')}")
        conf_col1, conf_col2 = st.columns(2)
        with conf_col1:
            if st.button("✅ Yes, Confirm and Execute", use_container_width=True):
                # Trigger action with confirmation
                action = conf.get("action")
                if action == "update_employee":
                    emp_id = conf["employee_id"]
                    fields = conf["fields"]
                    res = EmployeeService.update_employee(emp_id, fields, actor="AI Confirmed")
                    st.success(f"Action executed: {res['message']}")
                elif action == "deactivate_employee":
                    emp_id = conf["employee_id"]
                    res = EmployeeService.deactivate_employee(emp_id, actor="AI Confirmed")
                    st.success(f"Action executed: {res['message']}")
                elif action == "create_employee":
                    payload = conf["payload"]
                    dto = EmployeeCreate(
                        employee_name=payload["employee_name"],
                        manager_name=payload.get("manager_name"),
                        city=payload.get("city"),
                        date_of_joining=date.fromisoformat(payload["date_of_joining"]),
                        is_active=payload.get("is_active", True)
                    )
                    res = EmployeeService.create_employee(dto, actor="AI Confirmed")
                    st.success(f"Created employee with ID {res['employee_id']}.")
                
                st.session_state.pending_confirmation = None
                st.rerun()
        with conf_col2:
            if st.button("❌ Cancel Action", use_container_width=True):
                st.session_state.pending_confirmation = None
                st.info("Action cancelled.")
                st.rerun()

    # --- JARVIS MULTIMODAL VOICE CHAT COMPONENT ---
    st.markdown("""
    <div class="jarvis-card">
        <div class="jarvis-header">
            <span>🎙️ Jarvis Multimodal Voice Chat</span>
            <span class="jarvis-badge">Voice In & Voice Out</span>
        </div>
        <p style="color: #cbd5e1; font-size: 0.9rem; margin-top: 6px; margin-bottom: 0;">
            Speak naturally to Jarvis using your microphone or type below. Ask questions about employee details, managers, dates, or search records.
        </p>
    </div>
    """, unsafe_allow_html=True)

    vc_col1, vc_col2 = st.columns([3, 2])
    with vc_col1:
        chat_voice_audio = st.audio_input("🎙️ Speak your question to Jarvis:", key="jarvis_chat_audio_input")
    with vc_col2:
        enable_chat_tts = st.toggle(
            "🔊 Speak AI Answers Aloud (Jarvis Voice)", 
            value=st.session_state.get("chat_tts_enabled", True),
            key="chat_tts_toggle",
            help="When active, Jarvis reads AI responses aloud using browser speech synthesis."
        )
        st.session_state.chat_tts_enabled = enable_chat_tts
        if st.button("🔄 Reset Voice Input", key="reset_chat_voice", use_container_width=True):
            st.session_state.jarvis_chat_processed_audio_hash = None
            st.rerun()

    # Handle incoming voice audio for chatbot
    voice_user_query = None
    if chat_voice_audio is not None:
        raw_audio = chat_voice_audio.getvalue()
        audio_hash = hash(raw_audio)
        if st.session_state.jarvis_chat_processed_audio_hash != audio_hash:
            st.session_state.jarvis_chat_processed_audio_hash = audio_hash
            with st.spinner("🤖 Jarvis is listening and transcribing your speech..."):
                t_res = voice_service.transcribe_chat_audio(
                    audio_bytes=raw_audio,
                    mime_type=chat_voice_audio.type or "audio/wav"
                )
                if t_res.get("success") and t_res.get("transcription"):
                    voice_user_query = t_res["transcription"]
                    st.info(f"🎙️ **Jarvis Heard:** *\"{voice_user_query}\"*")
                else:
                    st.warning(f"⚠️ {t_res.get('spoken_response') or t_res.get('error')}")
                    if enable_chat_tts:
                        speak_jarvis_response(t_res.get("spoken_response", "I could not understand the audio."))

    # Render previous messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "tool_calls" in msg and msg["tool_calls"]:
                with st.expander("🛠️ Tool Executions (PostgreSQL)"):
                    for tc in msg["tool_calls"]:
                        st.markdown(f"**Tool:** `{tc.get('name')}`")
                        st.json(tc.get("args"))

    # Chat Input (accepts typed question or voice transcribed question)
    text_user_query = st.chat_input("Ask a question, e.g.: 'What is Rahul Sharma's joining date?' or 'List employees in Bangalore'")
    active_query = voice_user_query or text_user_query

    if active_query:
        # Display human message
        st.session_state.chat_messages.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)

        # Run AI workflow
        with st.chat_message("assistant"):
            with st.spinner("Analyzing request and consulting PostgreSQL..."):
                response_data = run_chatbot_workflow(
                    user_prompt=active_query,
                    history=st.session_state.langchain_history,
                    user_role=st.session_state.role
                )
                
                answer_text = response_data["answer"]
                tool_calls = response_data.get("tool_calls_executed", [])
                st.markdown(answer_text)

                if tool_calls:
                    with st.expander("🛠️ Tool Executions (PostgreSQL)"):
                        for tc in tool_calls:
                            st.markdown(f"**Tool:** `{tc.get('name')}`")
                            st.json(tc.get("args"))

                # Update states
                st.session_state.pending_confirmation = response_data.get("pending_confirmation")
                st.session_state.langchain_history = response_data["history"]
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": answer_text,
                    "tool_calls": tool_calls
                })

                # Speak AI response aloud if enabled
                if enable_chat_tts:
                    speak_jarvis_response(answer_text)
                
                if st.session_state.pending_confirmation:
                    st.rerun()
