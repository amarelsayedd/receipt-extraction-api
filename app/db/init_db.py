from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.usage import current_usage_month
from app.services.repositories import ApiClientRepository


def seed_demo_client(db: Session, settings: Settings) -> None:
    ApiClientRepository(db).ensure_demo_client(
        settings.demo_api_key,
        settings.default_monthly_usage_limit,
        current_usage_month(),
    )
