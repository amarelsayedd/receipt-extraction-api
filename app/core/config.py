from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Invoice Receipt Extraction API"
    environment: str = "local"
    database_url: str = "sqlite:///./receipt_extraction.db"
    sync_database_url: str | None = None
    demo_api_key: str = "dev-demo-key"
    admin_api_key: str = "local-admin-key"
    default_monthly_usage_limit: int = 1000
    max_upload_size_mb: int = 10
    upload_dir: Path = Path("./uploads")
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    log_level: str = "INFO"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def sqlalchemy_url(self) -> str:
        return self.sync_database_url or self.database_url

    @property
    def is_test(self) -> bool:
        return self.environment.lower() == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
