import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"] = "test"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DEMO_API_KEY"] = "test-api-key"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="receipt-api-tests-")
os.environ["RATE_LIMIT_REQUESTS"] = "1000"

from app.core.security import api_key_prefix, hash_api_key  # noqa: E402
from app.core.usage import current_usage_month  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import ApiClient  # noqa: E402


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as session:
        client = ApiClient(
            name="Test Client",
            api_key_hash=hash_api_key("test-api-key"),
            api_key_prefix=api_key_prefix("test-api-key"),
            monthly_usage_limit=1000,
            current_usage_month=current_usage_month(),
        )
        session.add(client)
        session.commit()
        yield session


@pytest.fixture()
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": "test-api-key"}


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return {"X-Admin-API-Key": "test-admin-key"}


@pytest.fixture()
def receipt_text() -> bytes:
    return b"""Acme Supplies LLC
Invoice No: INV-1007
Issue Date: 2026-08-01
Due Date: 2026-08-31
Currency: USD
Tax ID: US-123456789
Consulting Services 2 100.00 200.00
Subtotal: 200.00
Tax: 20.00
Discount: 10.00
Total: 210.00
Payment Method: Credit Card
"""
