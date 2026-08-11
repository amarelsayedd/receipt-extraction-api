from pathlib import Path

from app.extraction.confidence import ConfidenceScorer
from app.extraction.engine import ExtractionEngine
from app.extraction.ocr import OcrService
from app.extraction.parser import InvoiceReceiptParser
from app.extraction.validation import ExtractionValidator
from app.schemas.extraction import ExtractionResult


class BaselineExtractionEngine(ExtractionEngine):
    def __init__(
        self,
        ocr: OcrService | None = None,
        parser: InvoiceReceiptParser | None = None,
        validator: ExtractionValidator | None = None,
        scorer: ConfidenceScorer | None = None,
    ) -> None:
        self.ocr = ocr or OcrService()
        self.parser = parser or InvoiceReceiptParser()
        self.validator = validator or ExtractionValidator()
        self.scorer = scorer or ConfidenceScorer()

    def extract(self, file_path: Path, content_type: str) -> ExtractionResult:
        raw_text = self.ocr.extract_text(file_path, content_type)
        result = self.parser.parse(raw_text)
        result.warnings = self.validator.validate(result)
        result.confidence_score = self.scorer.score(result)
        return result
