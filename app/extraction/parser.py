import re
from datetime import date

from dateutil import parser as date_parser

from app.schemas.extraction import ExtractionResult, LineItem

CURRENCY_SYMBOLS = {"$": "USD", "\u20ac": "EUR", "\u00a3": "GBP", "\u00a5": "JPY"}
CURRENCY_CODES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "EGP", "AED", "SAR", "INR"}


class InvoiceReceiptParser:
    def parse(self, text: str) -> ExtractionResult:
        text = self._normalize_ocr_text(text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return ExtractionResult(
            vendor_name=self._vendor_name(lines),
            vendor_tax_id=self._match(
                text, r"(?:tax\s*id|vat|tin|gst)\s*[:#-]?\s*([A-Z0-9\- ]{5,30})"
            ),
            invoice_number=self._match(
                text, r"(?:invoice|inv)\s*(?:number|no\.?|#)\s*[:#-]?\s*([A-Z0-9\-\/]+)"
            ),
            receipt_number=self._match(
                text, r"(?:receipt|rcpt)\s*(?:number|no\.?|#)\s*[:#-]?\s*([A-Z0-9\-\/]+)"
            ),
            issue_date=self._date_match(
                text,
                r"(?:issue|invoice|receipt|date)\s*(?:date)?\s*[:#-]?"
                r"\s*([A-Za-z0-9,./\- ]{6,25})",
            ),
            due_date=self._date_match(
                text,
                r"(?:due\s*date|payment\s*due)\s*[:#-]?\s*([A-Za-z0-9,./\- ]{6,25})",
            ),
            currency=self._currency(text),
            subtotal=self._amount(text, ["subtotal", "sub total", "net amount"]),
            tax_amount=self._amount(text, ["tax", "vat", "sales tax"]),
            discount=self._amount(text, ["discount"]),
            total_amount=self._amount(text, ["total", "amount due", "balance due", "grand total"]),
            payment_method=self._match(
                text,
                r"(?:payment\s*method|paid\s*by|method)\s*[:#-]?\s*([A-Za-z ]{3,30})",
            ),
            line_items=self._line_items(lines),
            raw_text=text,
        )

    def _normalize_ocr_text(self, text: str) -> str:
        text = text.replace("N0:", "No:").replace("N0 ", "No ")
        text = re.sub(r"(?<=\d)\s+(?=\d{2}\b)", ".", text)
        return text

    def _vendor_name(self, lines: list[str]) -> str | None:
        ignored = re.compile(r"\b(invoice|receipt|tax|date|total|subtotal)\b", re.I)
        for line in lines[:8]:
            if len(line) >= 3 and not ignored.search(line):
                return line[:255]
        return lines[0][:255] if lines else None

    def _match(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.I)
        return re.sub(r"\s+", " ", match.group(1)).strip(" -:#") if match else None

    def _date_match(self, text: str, pattern: str) -> date | None:
        value = self._match(text, pattern)
        if not value:
            return None
        try:
            return date_parser.parse(value, fuzzy=True, dayfirst=False).date()
        except (ValueError, OverflowError):
            return None

    def _currency(self, text: str) -> str | None:
        for symbol, code in CURRENCY_SYMBOLS.items():
            if symbol in text:
                return code
        match = re.search(r"\b(USD|EUR|GBP|JPY|CAD|AUD|EGP|AED|SAR|INR)\b", text, re.I)
        if match and match.group(1).upper() in CURRENCY_CODES:
            return match.group(1).upper()
        return None

    def _amount(self, text: str, labels: list[str]) -> float | None:
        for label in labels:
            pattern = (
                rf"(?<![A-Za-z]){re.escape(label)}(?![A-Za-z])"
                rf"\s*[:#-]?\s*(?:[A-Z]{{3}}\s*)?[$\u20ac\u00a3\u00a5]?"
                rf"\s*(-?\d[\d,]*\.?\d*)"
            )
            match = re.search(pattern, text, re.I)
            if match:
                return self._to_float(match.group(1))
        return None

    def _to_float(self, value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return round(float(value.replace(",", "")), 2)
        except ValueError:
            return None

    def _line_items(self, lines: list[str]) -> list[LineItem]:
        items: list[LineItem] = []
        item_pattern = re.compile(
            r"^(.+?)\s+(\d+(?:\.\d+)?)\s+(-?\d[\d,]*\.?\d*)\s+(-?\d[\d,]*\.?\d*)$"
        )
        for line in lines:
            if re.search(r"\b(total|subtotal|tax|invoice|receipt)\b", line, re.I):
                continue
            match = item_pattern.match(line)
            if not match:
                continue
            items.append(
                LineItem(
                    description=match.group(1).strip(),
                    quantity=self._to_float(match.group(2)),
                    unit_price=self._to_float(match.group(3)),
                    total=self._to_float(match.group(4)),
                )
            )
        return items[:100]
