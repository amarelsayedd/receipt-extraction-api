from fastapi.testclient import TestClient


def upload(
    client: TestClient,
    headers: dict[str, str],
    body: bytes,
    content_type: str = "image/jpeg",
):
    return client.post(
        "/v1/extractions/sync",
        headers=headers,
        files={"file": ("receipt.jpg", body, content_type)},
    )


def test_api_key_required(api_client: TestClient, receipt_text: bytes) -> None:
    response = api_client.post(
        "/v1/extractions/sync",
        files={"file": ("receipt.jpg", receipt_text, "image/jpeg")},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_api_key"


def test_invalid_file_upload(api_client: TestClient, auth_headers: dict[str, str]) -> None:
    response = api_client.post(
        "/v1/extractions/sync",
        headers=auth_headers,
        files={"file": ("receipt.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_successful_sync_extraction(
    api_client: TestClient, auth_headers: dict[str, str], receipt_text: bytes
) -> None:
    response = upload(api_client, auth_headers, receipt_text)
    assert response.status_code == 200
    data = response.json()
    result = data["data"]
    assert result["vendor_name"] == "Acme Supplies LLC"
    assert result["invoice_number"] == "INV-1007"
    assert result["currency"] == "USD"
    assert result["total_amount"] == 210.0
    assert result["warnings"] == []
    assert result["confidence_score"] > 0.8
    assert data["meta"]["usage"]["monthly_used"] == 1


def test_missing_fields_create_warnings(
    api_client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = upload(api_client, auth_headers, b"Small Shop\nTotal: 12.50\n")
    assert response.status_code == 200
    warnings = response.json()["data"]["warnings"]
    assert "currency_missing" in warnings
    assert "document_number_missing" in warnings
    assert "issue_date_missing" in warnings


def test_total_validation_warning(api_client: TestClient, auth_headers: dict[str, str]) -> None:
    body = b"""Store
Receipt No: R-1
Date: 2026-08-10
USD
Subtotal: 100.00
Tax: 10.00
Discount: 0.00
Total: 200.00
"""
    response = upload(api_client, auth_headers, body)
    assert response.status_code == 200
    assert "total_mismatch" in response.json()["data"]["warnings"]


def test_status_endpoint(
    api_client: TestClient, auth_headers: dict[str, str], receipt_text: bytes
) -> None:
    create_response = api_client.post(
        "/v1/extractions",
        headers=auth_headers,
        files={"file": ("receipt.jpg", receipt_text, "image/jpeg")},
    )
    assert create_response.status_code == 202
    job_id = create_response.json()["job_id"]
    status_response = api_client.get(f"/v1/extractions/{job_id}", headers=auth_headers)
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "completed"
    assert data["result"]["invoice_number"] == "INV-1007"


def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_admin_can_create_api_key(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    response = api_client.post(
        "/v1/admin/api-keys",
        headers=admin_headers,
        json={"name": "Paid Customer", "monthly_usage_limit": 25},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["api_key"].startswith("rk_live_")
    assert data["monthly_usage_limit"] == 25


def test_admin_key_required(api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/admin/api-keys",
        json={"name": "Paid Customer", "monthly_usage_limit": 25},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_admin_key"


def test_monthly_limit_is_enforced(
    api_client: TestClient, admin_headers: dict[str, str], receipt_text: bytes
) -> None:
    create_key = api_client.post(
        "/v1/admin/api-keys",
        headers=admin_headers,
        json={"name": "Tiny Plan", "monthly_usage_limit": 1},
    )
    api_key = create_key.json()["api_key"]
    headers = {"X-API-Key": api_key}
    first = upload(api_client, headers, receipt_text)
    second = upload(api_client, headers, receipt_text)
    assert first.status_code == 200
    assert second.status_code == 402
    assert second.json()["error"]["code"] == "monthly_limit_exceeded"
