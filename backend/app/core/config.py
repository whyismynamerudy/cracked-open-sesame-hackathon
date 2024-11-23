# app/core/config.py
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # External Service API Keys
    BROWSERBASE_API_KEY: str
    OPENAI_API_KEY: str
    
    # Optional Database Settings
    DATABASE_URL: str | None = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Cache the settings instance
@lru_cache
def get_settings() -> Settings:
    return Settings()