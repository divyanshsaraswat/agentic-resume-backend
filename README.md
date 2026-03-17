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

## 🛠️ API & AI Intelligence

Full interactive docs available at `/docs` (Swagger UI).

### AI Provider Switching
The backend supports dynamic switching between providers via `AI_CHOICE`.
- **Groq**: High-speed inference using Llama-3.
- **OpenRouter**: Access to `openrouter/free` models with **automated reasoning** enabled via `extra_body`.

### Key Endpoints
- `POST /api/v1/ai/improve-bullet`: Refines bullets with professional impact.
- `POST /api/v1/ai/score-resume`: Detailed ATS and professional feedback.
- `POST /api/v1/latex/compile`: Direct LaTeX-to-PDF compilation.

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- MongoDB (Local or Atlas)
- LaTeX (for PDF generation)

### Installation
1. **Clone & Install**:
   ```bash
   uv sync
   ```
2. **LaTeX Setup** (Optional but recommended for PDF support):
   ```bash
   uv run python scripts/setup_latex.py
   ```
3. **Configure Environment**:
   Create a `.env` file based on the template below.

### Running Development Server
```bash
uv run uvicorn app.main:app --reload
```

## 🔑 Environment Variables
Create a `.env` file in the `backend/` directory:
```env
# AI Toggle
AI_CHOICE="openrouter" # "groq" or "openrouter"

# API Keys
GROQ_API_KEY="gsk_..."
OPENROUTER_API_KEY="sk-or-v1-..."
OPENROUTER_MODEL="openrouter/free"

# Infrastructure
SECRET_KEY="your-jwt-secret"
GOOGLE_CLIENT_ID="your-google-client-id"
MONGODB_URL="mongodb://localhost:27017"
DATABASE_NAME="placement_erp"
```

## 📜 License
MIT
