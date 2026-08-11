from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.rate_limit import InMemoryRateLimiter
from app.core.usage import current_usage_month
from app.db.session import get_db
from app.models import ApiClient
from app.services.repositories import ApiClientRepository

settings = get_settings()
rate_limiter = InMemoryRateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)


DbSession = Annotated[Session, Depends(get_db)]
ApiKeyHeader = Annotated[str | None, Header(alias="X-API-Key")]


def get_current_client(
    db: DbSession,
    x_api_key: ApiKeyHeader = None,
) -> ApiClient:
    if not x_api_key:
        raise AppError(401, "missing_api_key", "X-API-Key header is required.")
    repository = ApiClientRepository(db)
    client = repository.get_by_key(x_api_key)
    if client is None and x_api_key == settings.demo_api_key:
        client = repository.ensure_demo_client(
            x_api_key,
            settings.default_monthly_usage_limit,
            current_usage_month(),
        )
    if client is None:
        raise AppError(401, "invalid_api_key", "Invalid API key.")
    rate_limiter.check(client.id)
    repository.refresh_month_if_needed(client, current_usage_month())
    return client


def get_app_settings() -> Settings:
    return get_settings()


AdminKeyHeader = Annotated[str | None, Header(alias="X-Admin-API-Key")]


def require_admin_key(
    x_admin_api_key: AdminKeyHeader = None,
) -> None:
    if not x_admin_api_key or x_admin_api_key != settings.admin_api_key:
        raise AppError(401, "invalid_admin_key", "A valid admin API key is required.")
