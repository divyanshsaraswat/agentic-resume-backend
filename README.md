# Placement ERP Backend

This is the backend for the Placement ERP + AI Resume Intelligence Platform, built with FastAPI and MongoDB.

## Features

- **FastAPI**: Modern, fast (high-performance), web framework for building APIs with Python.
- **uv**: Ultra-fast Python package manager and project coordinator.
- **MongoDB**: Async database integration using Motor.
- **Pydantic**: Data validation and settings management using Python type annotations.
- **Google SSO**: Secure authentication for `@mnit.ac.in` users.
- **LaTeX Compilation**: Integrated service for generating PDFs from LaTeX templates securely.
- **AI Integration**: AI-powered resume enhancement and scoring using Groq or OpenRouter (dynamically switchable).

## Project Structure

```
backend/
├── app/
│   ├── api/            # API endpoints (versioned)
│   ├── core/           # Configuration and security
│   ├── db/             # Database connection and session management
│   ├── models/         # Pydantic schemas and MongoDB models
│   ├── services/       # Business logic and external integrations
│   ├── utils/          # Helper functions
│   └── main.py         # Entry point
├── tests/              # Pytest suite
├── scripts/            # Helper scripts (e.g. LaTeX setup)
├── pyproject.toml      # Project dependencies and metadata
└── uv.lock             # Deterministic dependency lock file
```

## API Documentation

The full interactive API documentation is available at `/docs` (Swagger UI) when the server is running.

### 1. Authentication
#### `POST /api/v1/auth/login/google`
Authenticates a user via Google SSO.
- **Request**: `{"id_token": "string"}`
- **Response**: `{"access_token": "string", "token_type": "bearer"}`

#### `GET /api/v1/auth/me`
Returns the current authenticated user's profile.

### 2. Resume Management
#### `POST /api/v1/resumes/`
Creates a new resume.
- **Request**: `{"type": "string", "initial_latex": "string"}`
- **Response**: Full Resume object with initialized versions.

#### `POST /api/v1/resumes/{resume_id}/version`
Adds a new version to an existing resume.
- **Request**: `{"type": "string", "latex_code": "string"}`

#### `PATCH /api/v1/resumes/{resume_id}/versions/{version_id}/status`
Updates version status (Faculty/Admin only).
- **Request**: `{"status": "APPROVED" | "REJECTED" | "PENDING"}`

### 3. LaTeX Compilation
#### `POST /api/v1/latex/compile`
Compiles LaTeX code to PDF.
- **Request**: `{"latex_code": "string"}`
- **Response**: `{"success": bool, "job_id": "string", "pdf_available": bool}`

### 4. AI Intelligence (Groq)
#### `POST /api/v1/ai/improve-bullet`
Refines a resume bullet point.
- **Request**: `{"bullet": "string"}`
- **Response**: `{"original": "string", "improved": "string"}`

#### `POST /api/v1/ai/generate-section`
Generates a LaTeX section from context.
- **Request**: `{"section_name": "string", "user_context": "string"}`
- **Response**: `{"section_name": "string", "latex_code": "string"}`

#### `POST /api/v1/ai/score-resume`
Scores a resume and provides feedback.
- **Request**: `{"resume_text": "string"}`
- **Response**: `{"score": int, "impact_feedback": "string", "ats_feedback": "string", "improvement_suggestions": ["string"]}`

## Installation & Setup

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- MongoDB running locally or on Atlas.
- LaTeX (for PDF compilation). Run `uv run python scripts/setup_latex.py` for setup help.

### Installation
1. `uv sync`
2. Configure `.env` (see below).

### Running the App
```bash
uv run uvicorn app.main:app --reload
```

## Environment Variables
Create a `.env` file:
```env
# AI Provider Selection
AI_CHOICE="groq" # or "openrouter"

# Groq AI
GROQ_API_KEY="your-groq-api-key"

# OpenRouter AI
OPENROUTER_API_KEY="your-openrouter-key"
OPENROUTER_MODEL="openrouter/free" # Supported free models with reasoning enabled

# Infrastructure
SECRET_KEY="your-secret"
GOOGLE_CLIENT_ID="your-google-client-id"
MONGODB_URL="mongodb://localhost:27017"
DATABASE_NAME="placement_erp"
```

## Testing
Run the test suite:
```bash
$env:PYTHONPATH="."
uv run pytest
```
