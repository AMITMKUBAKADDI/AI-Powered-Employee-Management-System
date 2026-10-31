# 💼 AI-Powered Employee Management System with Jarvis Voice AI

A modern, production-grade Employee Management Application and Conversational AI Assistant built with **Streamlit**, **Neon Cloud PostgreSQL**, **SQLAlchemy 2.0**, **LangGraph**, **LangChain**, and **Google Gemini (Multimodal Voice & Text)**.

---

## 🌟 Key Features

- **🎙️ Multimodal Jarvis Voice Assistant Across All Functions:**
  - **➕ Voice Add Employee:** Speak natural phrases to register employees (e.g., *"Jarvis, add employee Anita Desai, manager Priya Nair, city Pune, joining today"*).
  - **✏️ Voice Edit Employee:** Update records by name or ID (e.g., *"Jarvis, change Priya Nair's city to Hyderabad"*).
  - **🚫 Voice Deactivate Employee:** Soft-deactivate records by name or ID (e.g., *"Jarvis, deactivate employee Anita Desai"*).
  - **💬 Voice AI Chatbot:** Speak questions directly into the microphone; Jarvis transcribes speech and answers aloud using text-to-speech (TTS).
- **⚡ Dual Execution Modes (Autonomous vs. Review):**
  - **Autonomous Mode:** Jarvis extracts details and immediately commits transactions to PostgreSQL with audit logs.
  - **Review Mode:** Jarvis populates the manual form fields so administrators can verify details before submitting.
- **🧠 LangGraph Conversational Agent:**
  - Multi-turn conversation state machine with bounded loops.
  - Safe tool invocations with parameterized PostgreSQL queries.
  - Explicit confirmation guardrails for write operations (`create`, `update`, `deactivate`).
- **🛡️ Role-Based Access Control (RBAC):**
  - Switch between **Administrator** (full CRUD + Voice actions) and **Ordinary User** (read-only search, counts, directory).
- **☁️ Cloud & Local Database Support:**
  - Full support for **Neon Serverless PostgreSQL** (with PgBouncer connection pooling).
  - Automatic zero-config fallback to **SQLite** (`sqlite:///./local_employees.db`) if cloud or local PostgreSQL is unreachable.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | **Streamlit** (v1.35+) | Interactive web dashboard, audio widgets, tabs, role switcher |
| **Voice & Speech** | **Browser SpeechSynthesis API** | Client-side Jarvis text-to-speech (TTS) audio feedback |
| **Multimodal AI** | **Google GenAI SDK (`google-genai`)** | Multimodal audio transcription & structured parameter extraction |
| **AI Orchestration** | **LangGraph & LangChain** | StateGraph cyclic agent workflow, tool routing, conversation memory |
| **Large Language Model** | **Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`)** | Natural language reasoning, database tool calling, grounded answers |
| **Database** | **PostgreSQL 14+ / Neon Cloud PostgreSQL** | ACID-compliant relational data store with triggers & B-tree indexes |
| **Local Fallback DB** | **SQLite 3** | Automatic zero-configuration fallback for offline or quick demos |
| **ORM & Pooling** | **SQLAlchemy 2.0+** & **Psycopg2-binary** | Connection pooling (`QueuePool`), parameterized SQL execution |
| **Data Validation** | **Pydantic v2** & **Pydantic-Settings** | Strict DTO validation, field sanitization, environment settings |
| **Testing** | **pytest** | 30+ automated tests for CRUD, security, AI workflows, and voice services |

---

## 🏗️ Architecture & Query Lifecycle

```text
[User Voice Audio / Text Prompt]
             │
             ▼
    [Streamlit User Interface (app.py)]
             │
             ▼
    [Role Verification & Security Check] (src/auth.py)
             │
             ▼
    [Jarvis Voice Service / Multimodal Extraction] (src/ai/voice_service.py)
             │
             ▼
    [LangGraph Orchestrator] (src/ai/graph.py)
             │
             ▼
    [Google Gemini LLM with Bound Tools] (src/ai/tools.py)
       * find_employee(name)
       * search_employees(city, active, dates, manager)
       * count_employees(...)
       * get_direct_reports(manager)
       * create_employee(...)    [Requires Admin + Confirmation]
       * update_employee(...)    [Requires Admin + Confirmation]
       * deactivate_employee(...) [Requires Admin + Confirmation]
             │
             ▼
    [Service & Repository Layer] (src/services/ & src/repositories/)
             │
             ▼
    [SQLAlchemy Connection Pool] (src/db.py)
             │
             ▼
    [Neon Cloud PostgreSQL / SQLite Fallback]
             │
             ▼
    [Grounded Fact Response + Transparency Tool Call Log]
             │
             ▼
    [Jarvis Voice Output (Browser Speech Synthesis)]
```

---

## 📥 How to Download and Run the Project

Follow these step-by-step instructions to clone, install, configure, and launch the application on your computer.

### 1. Prerequisites
- **Python 3.10 to 3.14** installed on your system.
- **Git** installed on your system.
- A free **Google Gemini API Key** from [Google AI Studio](https://aistudio.google.com/).
- *(Optional)* A free cloud database from [Neon.tech](https://neon.tech/) or local PostgreSQL.

---

### 2. Clone or Download the Repository

Open your terminal (PowerShell, Command Prompt, or Bash) and clone the repository:

```bash
git clone https://github.com/<YOUR_USERNAME>/chatbot.git
cd chatbot
```

*(Or download and extract the ZIP file into a folder of your choice).*

---

### 3. Create and Activate a Virtual Environment

Isolate project dependencies inside a Python virtual environment:

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell shows an execution policy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once, then activate).*

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 4. Install Required Packages

Install all dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

### 5. Configure Environment Variables (`.env`)

Create a `.env` file in the project root directory:

```powershell
# Windows
cp .env.example .env
```
```bash
# macOS / Linux
cp .env.example .env
```

Open `.env` in any text editor and configure your settings:

```env
# ==========================================
# Database Configuration
# ==========================================
# OPTION A: Neon Cloud PostgreSQL (Recommended - Free)
DATABASE_URL="postgresql+psycopg2://neondb_owner:password@ep-xyz-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require"

# OPTION B: Local PostgreSQL (If running locally on port 5432)
# DB_HOST=localhost
# DB_PORT=5432
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_NAME=postgres

# OPTION C: Automatic SQLite Fallback
# (Leave DATABASE_URL blank or comment out DB settings to use local SQLite)

# ==========================================
# Google Gemini AI Configuration
# ==========================================
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# ==========================================
# Application Settings
# ==========================================
APP_ENV=development
LOG_LEVEL=INFO
DEFAULT_PAGE_SIZE=10
```

---

### 6. Initialize & Seed the Database

You can initialize the schema and populate sample data in two easy ways:

#### Option 1 (One-Click inside Streamlit):
Launch the app (Step 7 below), look at the sidebar on the left, and click **"🌱 Initialize / Seed Sample Data"**.

#### Option 2 (Via Python Command Line):
```bash
python -c "from src.db import init_db; init_db(seed_sample_data=True); print('Database initialized!')"
```

---

### 7. Run the Application

Launch the Streamlit web application:

```bash
streamlit run app.py
```

Your web browser will automatically open:
```text
Local URL: http://localhost:8501
Network URL: http://<your-ip>:8501
```

---

## 🧪 Running Automated Tests

To run the complete test suite verifying CRUD operations, RBAC security, LangGraph workflows, and multimodal voice services:

```bash
pytest -v
```

### Specific Test Modules:
- **Employee CRUD Tests:** `pytest tests/test_employee_crud.py`
- **Security & RBAC Tests:** `pytest tests/test_security.py`
- **Chatbot Workflow Tests:** `pytest tests/test_chatbot.py`
- **Jarvis Voice Tests:** `pytest tests/test_voice_service.py`

---

## ☁️ Deploying to Streamlit Community Cloud (Free)

This application is ready to deploy directly to **Streamlit Community Cloud**:

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Deploy AI Employee Management System"
   git push origin main
   ```
2. **Log into [share.streamlit.io](https://share.streamlit.io/):**
   - Click **"New app"**.
   - Select your repository, branch (`main`), and set Main file path to `app.py`.
3. **Configure Cloud Secrets:**
   - In **Advanced Settings ➔ Secrets**, paste your secrets:
     ```toml
     GEMINI_API_KEY = "your_gemini_api_key"
     GEMINI_MODEL = "gemini-2.5-flash"
     DATABASE_URL = "postgresql+psycopg2://neondb_owner:password@ep-xyz-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require"
     ```
4. **Click Deploy!** Streamlit Cloud installs `requirements.txt` and launches your live application with persistent cloud storage.

---

## 📁 Project Directory Structure

```text
chatbot/
│
├── app.py                      # Main Streamlit web application & Jarvis UI
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment variable template
├── .env                        # Local environment configuration (git-ignored)
├── README.md                   # Complete project documentation
│
├── database/
│   ├── schema.sql              # PostgreSQL DDL table schema, triggers & indexes
│   └── seed.sql                # Seed script with 12 employee records
│
├── src/
│   ├── auth.py                 # RBAC roles (Admin / User) and permissions
│   ├── config.py               # Pydantic Settings & Streamlit secrets loader
│   ├── db.py                   # SQLAlchemy engine, connection pool & session context
│   ├── models.py               # SQLAlchemy ORM Employee model
│   ├── schemas.py              # Pydantic schemas (EmployeeCreate, Update, Filter)
│   │
│   ├── ai/
│   │   ├── graph.py            # LangGraph StateGraph orchestration workflow
│   │   ├── llm.py              # Gemini LLM initialization
│   │   ├── prompts.py          # System prompts & behavioral constraints
│   │   ├── tools.py            # LangChain tool definitions with role guards
│   │   └── voice_service.py    # Jarvis multimodal voice processing & TTS execution
│   │
│   ├── repositories/
│   │   └── employee_repository.py # Direct SQL & ORM query executions
│   │
│   └── services/
│       └── employee_service.py    # High-level business logic, validation & audit
│
└── tests/
    ├── conftest.py             # Pytest fixtures and test database setup
    ├── test_employee_crud.py   # Unit tests for create, read, update, deactivate
    ├── test_security.py        # RBAC permissions and injection defense tests
    ├── test_chatbot.py         # AI LangGraph workflow and tool execution tests
    └── test_voice_service.py   # Voice extraction, updates, and transcription tests
```

---

## 🛡️ License

This project is licensed under the MIT License.
