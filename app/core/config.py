"""Application settings, loaded from environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Students Database CRUD API"
    app_version: str = "1.0.0"

    # SQLite file stored inside the project by default (persistent, git-ignored).
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'students.db'}"

    # Optional bonus: local AI assistant backed by Ollama.
    ai_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout_seconds: float = Field(60.0, gt=0)
    ai_max_records: int = Field(25, ge=1, le=100)
    ai_max_question_length: int = Field(500, ge=10, le=2000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
