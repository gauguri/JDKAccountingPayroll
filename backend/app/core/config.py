"""Application configuration. All secrets come from the environment."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "JDK Books"
    # Default to a local SQLite file so the app/tests run with zero setup.
    # In Docker this is overridden by the Postgres DATABASE_URL in .env.
    database_url: str = "sqlite:///./jdkbooks.db"

    jwt_secret: str = "dev-only-insecure-secret-change-me"
    access_token_minutes: int = 60 * 12
    # 32-byte base64 key for field-level encryption (SSN/EIN/direct deposit).
    # A dev default is provided; production MUST override via env.
    field_encryption_key: str = "ZGV2LW9ubHktMzJieXRlLWtleS1ub3QtZm9yLXByb2Q="

    document_storage_path: str = "./data/documents"
    cookie_secure: bool = False  # True behind HTTPS in production
    default_state: str = "NJ"


@lru_cache
def get_settings() -> Settings:
    return Settings()
