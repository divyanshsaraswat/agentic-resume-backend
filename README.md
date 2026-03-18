# Placement ERP Backend

This is the high-performance backend for the **Placement ERP + AI Resume Intelligence Platform**, built with **FastAPI** and **MongoDB**. It features secure LaTeX compilation, Google SSO, and multi-provider AI intelligence.

## 🚀 Key Features

- **FastAPI**: Modern, high-performance web framework.
- **Multi-Provider AI**: Integrated support for **Groq** and **OpenRouter** (reasoning-enabled) for resume scoring and enhancement.
- **Secure LaTeX Service**: Integrated PDF compilation using `pdflatex` with security guards.
- **Google SSO**: Domain-restricted (`@mnit.ac.in`) authentication.
- **Modern Tooling**: Powered by `uv` for ultra-fast package management.
- **Async Database**: Full MongoDB integration via `motor`.

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/            # API endpoints (Auth, Resumes, Users, AI, LaTeX)
│   ├── core/           # Config (Pydantic v2) and Security (JWT)
│   ├── db/             # MongoDB async bridge
│   ├── models/         # Pydantic schemas & MongoDB models
│   ├── services/       # Business logic (AI switching, LaTeX, Resumes)
│   └── main.py         # App entry point
├── scripts/            # Cross-platform LaTeX setup helpers
├── pyproject.toml      # Modern dependency management
└── uv.lock             # Deterministic lockfile
```

## 🛠️ API & AI Intelligence Reference

Full interactive docs available at `/docs` (Swagger UI).

### 1. Authentication
#### `POST /api/v1/auth/login/google`
Authenticates a user via Google SSO.
- **Request (Query)**: `token` (String) - Google ID Token
- **Response**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
    "token_type": "bearer"
  }
  ```

#### `GET /api/v1/auth/me`
Returns the current authenticated user's profile.
- **Response (`UserInDB`)**:
  ```json
  {
    "_id": "65f1...",
    "name": "John Doe",
    "email": "2020ucp1234@mnit.ac.in",
    "role": "student",
    "is_superadmin": false,
    "department": "Computer Science",
    "assigned_students": [],
    "created_at": "2024-03-17T12:00:00",
    "updated_at": "2024-03-17T12:00:00"
  }
  ```

### 2. User Management
#### `GET /api/v1/users/`
(Admin only) List all users.
- **Response**: `List[UserInDB]`

#### `PATCH /api/v1/users/{user_id}`
Updates user details.
- **Request (`UserUpdate`)**:
  ```json
  {
    "name": "Updated Name",
    "role": "faculty",
    "department": "Department Name"
  }
  ```
- **Response**: `UserInDB`

### 3. Resume Management
#### `POST /api/v1/resumes/`
Create a new resume with an initial version.
- **Request (`ResumeCreate`)**:
  ```json
  {
    "user_id": "65f1...",
    "type": "SDE",
    "initial_latex": "\\documentclass{...}"
  }
  ```
- **Response (`ResumeInDB`)**:
  ```json
  {
    "_id": "65f2...",
    "user_id": "65f1...",
    "versions": [
      {
        "version_id": "65f3...",
        "type": "SDE",
        "latex_code": "...",
        "status": "draft",
        "updated_at": "..."
      }
    ],
    "created_at": "..."
  }
  ```

#### `POST /api/v1/resumes/{resume_id}/version`
Add a new version to an existing resume.
- **Request (`ResumeVersion`)**:
  ```json
  {
    "type": "Core",
    "latex_code": "\\documentclass{...}"
  }
  ```

#### `PATCH /api/v1/resumes/{resume_id}/versions/{version_id}/status`
(Faculty/Admin only) Approve or Reject a resume version.
- **Request (Query)**: `status` (Enum: `approved`, `rejected`, `pending`, `draft`)
- **Response**: `true` (Boolean)

### 4. LaTeX Compilation
#### `POST /api/v1/latex/compile`
Compiles LaTeX code to PDF.
- **Request (`LatexCompileRequest`)**:
  ```json
  {
    "latex_code": "\\documentclass{article}\\begin{document}Hello World\\end{document}"
  }
  ```
- **Response (`LatexCompileResponse`)**:
  ```json
  {
    "success": true,
    "job_id": "65f4...",
    "pdf_available": true,
    "log": "...",
    "error": null
  }
  ```

### 5. AI Intelligence (Switchable)
Endpoints switch behavior based on `AI_CHOICE` (Groq/OpenRouter).

#### `POST /api/v1/ai/improve-bullet`
Refines a resume bullet point.
- **Request**: `{"bullet": "Built a website"}`
- **Response**:
  ```json
  {
    "original": "Built a website",
    "improved": "Architected and deployed a full-stack responsive web application using React and FastAPI..."
  }
  ```

#### `POST /api/v1/ai/score-resume`
Scores a resume and provides feedback.
- **Request**: `{"resume_text": "..."}`
- **Response**:
  ```json
  {
    "score": 85,
    "impact_feedback": "Strong use of action verbs...",
    "ats_feedback": "Clean structure, easily parsed...",
    "improvement_suggestions": ["Include more quantifiable metrics", "..."]
  }
  ```

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- MongoDB (Local or Atlas)
- LaTeX (for PDF generation)

### Installation
1. `uv syn c`
2. `uv run python scripts/setup_latex.py` (optional)
3. Create `.env` based on the template below.

## 🔑 Environment Variables
```env
AI_CHOICE="openrouter" # "groq" or "openrouter"
GROQ_API_KEY="gsk_..."
OPENROUTER_API_KEY="sk-or-v1-..."
OPENROUTER_MODEL="openrouter/free"
SECRET_KEY="your-jwt-secret"
GOOGLE_CLIENT_ID="your-google-client-id"
MONGO_URI="mongodb://localhost:27017"
DATABASE_NAME="placement_erp"
```

## 📜 License
MIT
