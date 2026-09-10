"""Application configuration settings using pydantic-settings."""
import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "Intelligent Document Extraction Platform"
    API_V1_STR: str = "/api/v1"
    
    # Storage and Database paths
    UPLOAD_DIR: str = str(BASE_DIR / "backend" / "uploads")
    DATA_DIR: str = str(BASE_DIR / "backend" / "data")
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/backend/data/documents.db"
    
    # Document Processing Limits
    MAX_PAGE_LIMIT: int = 3
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png"]
    MAX_UPLOAD_SIZE_MB: int = 25
    
    # AI / LLM Configuration
    # Options: 'gemini', 'openai', 'mock'
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Financial Calculation Tolerance (variance threshold)
    FINANCIAL_TOLERANCE: float = 1.00

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
