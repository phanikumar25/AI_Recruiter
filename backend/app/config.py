from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "profiles.json - Flexiple Engineering Challenge sample data"


class Settings(BaseSettings):
    app_name: str = "AI Recruiter"
    environment: str = "development"
    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GROQ_API_KEY", "GOOGLE_API_KEY"),
    )
    groq_model: str = "openai/gpt-oss-20b"
    llm_temperature: float = 0.0
    dataset_path: Path = DEFAULT_DATASET_PATH
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
