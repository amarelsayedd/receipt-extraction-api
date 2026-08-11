from app.schemas.extraction import ExtractionResult


class ExtractionValidator:
    def validate(self, result: ExtractionResult) -> list[str]:
        warnings: list[str] = []
        if not result.raw_text:
            warnings.append("raw_text_empty")
        if not result.currency:
            warnings.append("currency_missing")
        if not result.invoice_number and not result.receipt_number:
            warnings.append("document_number_missing")
        if not result.issue_date:
            warnings.append("issue_date_missing")
        if result.total_amount is None:
            warnings.append("total_amount_missing")
        if result.total_amount is not None and result.subtotal is not None:
            expected = result.subtotal + (result.tax_amount or 0) - (result.discount or 0)
            tolerance = max(0.05, abs(result.total_amount) * 0.02)
            if abs(expected - result.total_amount) > tolerance:
                warnings.append("total_mismatch")
        return warnings
