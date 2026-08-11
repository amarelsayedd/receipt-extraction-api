import logging
from pathlib import Path

from app.extraction import ExtractionEngine
from app.models import ExtractionJob
from app.schemas.extraction import ExtractionResult
from app.services.repositories import ExtractionJobRepository

logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(self, repository: ExtractionJobRepository, engine: ExtractionEngine) -> None:
        self.repository = repository
        self.engine = engine

    def process_job(self, job: ExtractionJob, file_path: Path) -> ExtractionJob:
        self.repository.set_processing(job)
        try:
            result = self.engine.extract(file_path, job.content_type)
            return self.repository.set_completed(job, result.model_dump(mode="json"))
        except Exception:
            logger.exception("Extraction failed for job %s", job.id)
            return self.repository.set_failed(job, "Extraction failed.")

    def process_sync(self, file_path: Path, content_type: str) -> ExtractionResult:
        return self.engine.extract(file_path, content_type)
