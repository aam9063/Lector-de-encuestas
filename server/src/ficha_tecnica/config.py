"""Application settings. NAN_KEY lives only in the repo-root .env, never in code."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nan_key: str = ""
    nan_base_url: str = "https://api.nan.builders"
    provider: str = "mock"
    checklist_version: int = 1
    questionnaire_version: int = 1


def get_settings() -> Settings:
    return Settings()
