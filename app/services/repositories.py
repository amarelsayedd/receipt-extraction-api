from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import api_key_prefix, hash_api_key
from app.models import ApiClient, ExtractionJob, ExtractionStatus


class ApiClientRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_key(self, api_key: str) -> ApiClient | None:
        return self.db.scalar(
            select(ApiClient).where(
                ApiClient.api_key_hash == hash_api_key(api_key),
                ApiClient.is_active.is_(True),
            )
        )

    def create(
        self,
        *,
        name: str,
        api_key: str,
        monthly_usage_limit: int,
        usage_month: str,
    ) -> ApiClient:
        client = ApiClient(
            name=name,
            api_key_hash=hash_api_key(api_key),
            api_key_prefix=api_key_prefix(api_key),
            monthly_usage_limit=monthly_usage_limit,
            current_usage_month=usage_month,
        )
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def ensure_demo_client(
        self, api_key: str, monthly_usage_limit: int, usage_month: str
    ) -> ApiClient:
        client = self.get_by_key(api_key)
        if client:
            return client
        return self.create(
            name="Local Demo Client",
            api_key=api_key,
            monthly_usage_limit=monthly_usage_limit,
            usage_month=usage_month,
        )

    def refresh_month_if_needed(self, client: ApiClient, usage_month: str) -> ApiClient:
        if client.current_usage_month != usage_month:
            client.current_usage_month = usage_month
            client.monthly_usage_count = 0
            self.db.commit()
            self.db.refresh(client)
        return client

    def increment_usage(self, client: ApiClient, usage_month: str) -> ApiClient:
        self.refresh_month_if_needed(client, usage_month)
        client.monthly_usage_count += 1
        client.total_usage_count += 1
        self.db.commit()
        self.db.refresh(client)
        return client


class ExtractionJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        api_client_id: str,
        original_filename: str,
        stored_filename: str,
        content_type: str,
        file_size: int,
    ) -> ExtractionJob:
        job = ExtractionJob(
            api_client_id=api_client_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            file_size=file_size,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_for_client(self, job_id: str, api_client_id: str) -> ExtractionJob | None:
        job = self.db.get(ExtractionJob, job_id)
        if job is None or job.api_client_id != api_client_id:
            return None
        return job

    def set_processing(self, job: ExtractionJob) -> ExtractionJob:
        job.status = ExtractionStatus.processing
        self.db.commit()
        self.db.refresh(job)
        return job

    def set_completed(self, job: ExtractionJob, result: dict) -> ExtractionJob:
        job.status = ExtractionStatus.completed
        job.result_json = result
        job.error_message = None
        self.db.commit()
        self.db.refresh(job)
        return job

    def set_failed(self, job: ExtractionJob, message: str) -> ExtractionJob:
        job.status = ExtractionStatus.failed
        job.error_message = message
        self.db.commit()
        self.db.refresh(job)
        return job
