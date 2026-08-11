from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    monthly_usage_limit: int = Field(default=1000, ge=1, le=1_000_000)


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    api_key: str
    api_key_prefix: str
    monthly_usage_limit: int
    created_at: datetime


class ApiClientUsageResponse(BaseModel):
    id: str
    name: str
    api_key_prefix: str
    monthly_usage_limit: int
    current_usage_month: str
    monthly_usage_count: int
    total_usage_count: int
