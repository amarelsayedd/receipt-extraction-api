from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class LineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    tax: float | None = None
    total: float | None = None


class ExtractionResult(BaseModel):
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    invoice_number: str | None = None
    receipt_number: str | None = None
    issue_date: date | None = None
    due_date: date | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    discount: float | None = None
    total_amount: float | None = None
    payment_method: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1, default=0)
    raw_text: str = ""
    warnings: list[str] = Field(default_factory=list)


class UsageMeta(BaseModel):
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int


class ResponseMeta(BaseModel):
    usage: UsageMeta | None = None
    warnings_count: int = 0


class ExtractionJobCreated(BaseModel):
    job_id: str
    status: JobStatus
    meta: ResponseMeta | None = None


class ExtractionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: JobStatus
    result: ExtractionResult | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    meta: ResponseMeta | None = None


class SyncExtractionResponse(BaseModel):
    data: ExtractionResult
    meta: ResponseMeta


class ErrorResponse(BaseModel):
    error: dict[str, Any]
