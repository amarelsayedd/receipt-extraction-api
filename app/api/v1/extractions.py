from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_current_client
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import get_db
from app.extraction import BaselineExtractionEngine
from app.models import ApiClient
from app.schemas.extraction import (
    ExtractionJobCreated,
    ExtractionJobResponse,
    ExtractionResult,
    ResponseMeta,
    SyncExtractionResponse,
    UsageMeta,
)
from app.services.extraction_service import ExtractionService
from app.services.file_storage import FileStorageService
from app.services.repositories import ApiClientRepository, ExtractionJobRepository
from app.services.usage_service import UsageService

router = APIRouter(prefix="/extractions", tags=["extractions"])
CurrentClient = Annotated[ApiClient, Depends(get_current_client)]
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]


def usage_meta(client: ApiClient) -> UsageMeta:
    remaining = max(client.monthly_usage_limit - client.monthly_usage_count, 0)
    return UsageMeta(
        monthly_limit=client.monthly_usage_limit,
        monthly_used=client.monthly_usage_count,
        monthly_remaining=remaining,
    )


@router.post("", response_model=ExtractionJobCreated, status_code=202)
async def create_extraction(
    file: UploadFile,
    client: CurrentClient,
    db: DbSession,
    settings: AppSettings,
) -> ExtractionJobCreated:
    client = UsageService(ApiClientRepository(db)).consume_extraction(client)
    storage = FileStorageService(settings)
    file_path, stored_name, size = await storage.save_upload(file)
    repository = ExtractionJobRepository(db)
    job = repository.create(
        api_client_id=client.id,
        original_filename=Path(file.filename or stored_name).name,
        stored_filename=stored_name,
        content_type=file.content_type or "application/octet-stream",
        file_size=size,
    )
    service = ExtractionService(repository, BaselineExtractionEngine())
    service.process_job(job, file_path)
    return ExtractionJobCreated(
        job_id=job.id,
        status=job.status.value,
        meta=ResponseMeta(
            usage=usage_meta(client),
            warnings_count=len(job.result_json.get("warnings", [])) if job.result_json else 0,
        ),
    )


@router.post("/sync", response_model=SyncExtractionResponse)
async def create_sync_extraction(
    file: UploadFile,
    client: CurrentClient,
    db: DbSession,
    settings: AppSettings,
) -> SyncExtractionResponse:
    client = UsageService(ApiClientRepository(db)).consume_extraction(client)
    storage = FileStorageService(settings)
    file_path, _, _ = await storage.save_upload(file)
    try:
        service = ExtractionService(
            ExtractionJobRepositoryPlaceholder(), BaselineExtractionEngine()
        )
        result = service.process_sync(file_path, file.content_type or "application/octet-stream")
        return SyncExtractionResponse(
            data=result,
            meta=ResponseMeta(
                usage=usage_meta(client),
                warnings_count=len(result.warnings),
            ),
        )
    finally:
        Path(file_path).unlink(missing_ok=True)


@router.get("/{job_id}", response_model=ExtractionJobResponse)
def get_extraction(
    job_id: str,
    client: CurrentClient,
    db: DbSession,
) -> ExtractionJobResponse:
    job = ExtractionJobRepository(db).get_for_client(job_id, client.id)
    if job is None:
        raise AppError(404, "job_not_found", "Extraction job was not found.")
    result = ExtractionResult.model_validate(job.result_json) if job.result_json else None
    return ExtractionJobResponse(
        job_id=job.id,
        status=job.status.value,
        result=result,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        meta=ResponseMeta(warnings_count=len(result.warnings) if result else 0),
    )


class ExtractionJobRepositoryPlaceholder:
    def set_processing(self, job: object) -> object:
        return job

    def set_completed(self, job: object, result: dict) -> object:
        return job

    def set_failed(self, job: object, message: str) -> object:
        return job
