from app.core.errors import AppError
from app.core.usage import current_usage_month
from app.models import ApiClient
from app.services.repositories import ApiClientRepository


class UsageService:
    def __init__(self, repository: ApiClientRepository) -> None:
        self.repository = repository

    def consume_extraction(self, client: ApiClient) -> ApiClient:
        usage_month = current_usage_month()
        client = self.repository.refresh_month_if_needed(client, usage_month)
        if client.monthly_usage_count >= client.monthly_usage_limit:
            raise AppError(
                402,
                "monthly_limit_exceeded",
                "Monthly extraction limit exceeded for this API key.",
            )
        return self.repository.increment_usage(client, usage_month)
