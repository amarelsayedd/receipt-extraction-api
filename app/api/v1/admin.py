from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin_key
from app.core.security import generate_api_key
from app.core.usage import current_usage_month
from app.db.session import get_db
from app.schemas.admin import ApiKeyCreateRequest, ApiKeyCreateResponse
from app.services.repositories import ApiClientRepository

router = APIRouter(prefix="/admin", tags=["admin"])
DbSession = Annotated[Session, Depends(get_db)]
AdminAuth = Annotated[None, Depends(require_admin_key)]


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=201)
def create_api_key(
    payload: ApiKeyCreateRequest,
    db: DbSession,
    _: AdminAuth,
) -> ApiKeyCreateResponse:
    api_key = generate_api_key()
    client = ApiClientRepository(db).create(
        name=payload.name,
        api_key=api_key,
        monthly_usage_limit=payload.monthly_usage_limit,
        usage_month=current_usage_month(),
    )
    return ApiKeyCreateResponse(
        id=client.id,
        name=client.name,
        api_key=api_key,
        api_key_prefix=client.api_key_prefix,
        monthly_usage_limit=client.monthly_usage_limit,
        created_at=client.created_at,
    )
