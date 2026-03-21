from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True
    )
    
    PROJECT_NAME: str = "Placement ERP API"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-for-dev" # Should be changed in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Google Auth
    GOOGLE_CLIENT_ID: str = "" # To be provided by user or set in .env
    
    # AI Choice (groq or openrouter)
    AI_CHOICE: str = "groq"
    
    # Groq AI
    GROQ_API_KEY: str = "" # Set in .env
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # OpenRouter AI
    OPENROUTER_API_KEY: str = "" # Set in .env
    OPENROUTER_MODEL: str = "openrouter/free"
    
    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017" # Default for local dev
    DATABASE_NAME: str = "placement_erp"

    # Email Settings
    SMTP_HOST: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = ""
    SMTP_PASSWORD: Optional[str] = ""
    EMAILS_FROM_EMAIL: Optional[str] = "noreply@matrix-erp.com"
    EMAILS_FROM_NAME: Optional[str] = "Matrix Placement Portal"

    # Storage Settings
    # Path relative to the app's root (where main.py is run)
    UPLOAD_DIR: str = "public"
    MAX_STORAGE_MB_PER_USER: int = 20
    
    # LLM Credits
    LLM_CREDITS_PER_HOUR: int = 20
    DEFAULT_MODEL: str = "llama-3.3-70b-versatile"
    
    # Credit costs per request for different models
    # Simplified mapping based on the provided list
    MODEL_CREDIT_COSTS: dict = {
        "llama-3.1-8b-instant": 1,
        "llama-3.3-70b-versatile": 2,
        "meta-llama/llama-4-scout-17b-16e-instruct": 3,
        "openai/gpt-oss-120b": 5,
        "openai/gpt-oss-20b": 2,
        "allam-2-7b": 1,
        "groq/compound": 4,
        "groq/compound-mini": 1,
        "moonshotai/kimi-k2-instruct": 3,
    }

settings = Settings()
