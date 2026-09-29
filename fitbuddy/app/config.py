from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    Values can be supplied through environment variables
    or a .env file.
    """

    app_name: str = "FitBuddy - AI Fitness Plan Generator"
    app_version: str = "1.0.0"
    debug: bool = True

    database_url: str = "sqlite:///./fitbuddy.db"

    gemini_api_key: str = ""

    # These are configurable so the application can be adapted
    # if Google changes model availability.
    gemini_workout_model: str = "gemini-3.1-pro-preview"
    gemini_tip_model: str = "gemini-3.8-flash"

    # When true, FitBuddy works without an API key.
    # Useful for development/testing.
    demo_mode: bool = False

    # Optional admin token.
    # Leave empty for local development.
    admin_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()