from app.schemas.extraction import ExtractionResult


class ConfidenceScorer:
    FIELD_WEIGHTS = {
        "vendor_name": 0.12,
        "document_number": 0.16,
        "issue_date": 0.14,
        "currency": 0.1,
        "subtotal": 0.08,
        "tax_amount": 0.06,
        "total_amount": 0.18,
        "line_items": 0.08,
        "raw_text": 0.08,
    }

    def score(self, result: ExtractionResult) -> float:
        score = 0.0
        score += self.FIELD_WEIGHTS["vendor_name"] if result.vendor_name else 0
        score += self.FIELD_WEIGHTS["document_number"] if self._has_document_number(result) else 0
        score += self.FIELD_WEIGHTS["issue_date"] if result.issue_date else 0
        score += self.FIELD_WEIGHTS["currency"] if result.currency else 0
        score += self.FIELD_WEIGHTS["subtotal"] if result.subtotal is not None else 0
        score += self.FIELD_WEIGHTS["tax_amount"] if result.tax_amount is not None else 0
        score += self.FIELD_WEIGHTS["total_amount"] if result.total_amount is not None else 0
        score += self.FIELD_WEIGHTS["line_items"] if result.line_items else 0
        score += self.FIELD_WEIGHTS["raw_text"] if len(result.raw_text) >= 20 else 0

        if "total_mismatch" in result.warnings:
            score -= 0.2
        score -= min(0.05 * len(result.warnings), 0.25)
        return round(max(0.0, min(1.0, score)), 2)

    def _has_document_number(self, result: ExtractionResult) -> bool:
        return bool(result.invoice_number or result.receipt_number)
