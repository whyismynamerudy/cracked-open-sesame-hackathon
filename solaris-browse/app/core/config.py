from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings."""
    ALLOWED_ORIGINS: List[str] = ["*"]  # Default to allow all origins
    browserbase_api_key: str
    browserbase_project_id: str
    claude_api_key: str

    class Config:
        env_file = ".env"
