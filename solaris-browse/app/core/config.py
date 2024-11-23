from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings."""
    # API Settings
    DEBUG: bool = False
    
    # Security
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # External Service API Keys
    BROWSERBASE_API_KEY: str
    BROWSERBASE_PROJECT_ID: str
    CLAUDE_API_KEY: str
    OPENAI_API_KEY: str
    
    # Langfuse settings
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"
        case_sensitive = True

# Cache the settings instance
@lru_cache
def get_settings() -> Settings:
    return Settings()
