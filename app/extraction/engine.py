from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.extraction import ExtractionResult


class ExtractionEngine(ABC):
    @abstractmethod
    def extract(self, file_path: Path, content_type: str) -> ExtractionResult:
        """Extract structured invoice or receipt data from a file."""
