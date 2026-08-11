# Invoice / Receipt Extraction API

A FastAPI backend for extracting structured JSON from invoices and receipts. It accepts PDF, PNG, JPG, and JPEG uploads, validates files, stores extraction jobs in PostgreSQL, protects endpoints with API keys, and exposes OpenAPI docs at `/docs`.

The first extraction engine is a baseline implementation using PDF text extraction, optional Tesseract OCR for images, and layout-agnostic regex heuristics. The `ExtractionEngine` interface is intentionally small so an LLM or vendor OCR engine can be added later without changing the API surface.

## Features

- `POST /v1/extractions` creates an extraction job and stores the result.
- `GET /v1/extractions/{job_id}` returns `pending`, `processing`, `completed`, or `failed`.
- `POST /v1/extractions/sync` returns extracted JSON directly for demos and tests.
- Extracts vendor, tax ID, invoice/receipt numbers, dates, currency, subtotal, tax, discount, total, payment method, line items, confidence, raw text, and warnings.
- Validates totals and missing critical fields.
- API key auth via `X-API-Key`.
- Admin API-key creation via `X-Admin-API-Key`.
- Monthly usage tracking and monthly extraction limits per API key.
- In-memory per-key rate limiting, designed to swap for Redis later.
- Health check endpoint at `/v1/health`.
- Alembic migrations, Docker Compose, pytest, and Ruff.

## Project Structure

```text
app/
  api/              FastAPI routes and dependencies
  core/             config, errors, security-adjacent utilities
  db/               SQLAlchemy base/session and seed helper
  extraction/       ExtractionEngine abstraction and baseline parser
  models/           SQLAlchemy models
  schemas/          Pydantic v2 schemas
  services/         storage, repositories, orchestration services
alembic/            database migrations
tests/              pytest coverage and fixtures
```

## Environment

Copy the example file and adjust values as needed:

```bash
cp .env.example .env
```

Important variables:

- `DATABASE_URL`: PostgreSQL SQLAlchemy URL.
- `DEMO_API_KEY`: local development API key, default `dev-demo-key`.
- `ADMIN_API_KEY`: local admin key for creating customer API keys.
- `DEFAULT_MONTHLY_USAGE_LIMIT`: default monthly quota for the demo API key.
- `MAX_UPLOAD_SIZE_MB`: maximum upload size.
- `UPLOAD_DIR`: where uploaded files are stored.
- `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`: in-memory limiter settings.

## Run With Docker

```bash
docker compose up --build
```

The API will be available at:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

The container runs Alembic migrations and seeds the demo API key automatically.

## Health Check

```bash
curl "http://localhost:8000/v1/health"
```

Response:

```json
{
  "status": "ok",
  "database": "ok"
}
```

## Create A Customer API Key

Use the admin key only from trusted internal tools.

```bash
curl -X POST "http://localhost:8000/v1/admin/api-keys" \
  -H "X-Admin-API-Key: local-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Accounting","monthly_usage_limit":5000}'
```

Response:

```json
{
  "id": "2f3e4f0f-1ff2-47d1-8b75-9c78d0f8a601",
  "name": "Acme Accounting",
  "api_key": "rk_live_...",
  "api_key_prefix": "rk_live_abcd",
  "monthly_usage_limit": 5000,
  "created_at": "2026-08-11T20:21:48.123456"
}
```

The full API key is returned only once. Store it securely.

## Local Development

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev,ocr]"
copy .env.example .env
alembic upgrade head
python -m app.cli
uvicorn app.main:app --reload
```

On macOS/Linux, use `source .venv/bin/activate` instead of the Windows activation command.

## API Examples

Create an async extraction job:

```bash
curl -X POST "http://localhost:8000/v1/extractions" \
  -H "X-API-Key: dev-demo-key" \
  -F "file=@sample-receipt.pdf"
```

Response:

```json
{
  "job_id": "6b4f5d68-d12f-40ee-bdb0-251f5e3cc0c8",
  "status": "completed"
}
```

Check job status:

```bash
curl "http://localhost:8000/v1/extractions/6b4f5d68-d12f-40ee-bdb0-251f5e3cc0c8" \
  -H "X-API-Key: dev-demo-key"
```

Synchronous demo extraction:

```bash
curl -X POST "http://localhost:8000/v1/extractions/sync" \
  -H "X-API-Key: dev-demo-key" \
  -F "file=@receipt.jpg"
```

Example completed result:

```json
{
  "data": {
    "vendor_name": "Acme Supplies LLC",
    "vendor_tax_id": "US-123456789",
    "invoice_number": "INV-1007",
    "receipt_number": null,
    "issue_date": "2026-08-01",
    "due_date": "2026-08-31",
    "currency": "USD",
    "subtotal": 200.0,
    "tax_amount": 20.0,
    "discount": 10.0,
    "total_amount": 210.0,
    "payment_method": "Credit Card",
    "line_items": [
      {
        "description": "Consulting Services",
        "quantity": 2.0,
        "unit_price": 100.0,
        "tax": null,
        "total": 200.0
      }
    ],
    "confidence_score": 1.0,
    "raw_text": "...",
    "warnings": []
  },
  "meta": {
    "usage": {
      "monthly_limit": 1000,
      "monthly_used": 1,
      "monthly_remaining": 999
    },
    "warnings_count": 0
  }
}
```

When a customer exceeds their monthly limit, the API returns:

```json
{
  "error": {
    "code": "monthly_limit_exceeded",
    "message": "Monthly extraction limit exceeded for this API key."
  }
}
```

## OCR Notes

PDFs with embedded text are parsed directly. Scanned PDFs are rendered page-by-page with `pypdfium2` and passed through optional Tesseract OCR. Images are normalized with EXIF rotation, grayscale conversion, contrast adjustment, and upscaling before OCR.

For commercial quality, use clear images or text PDFs. The baseline engine is useful for MVP demos and common layouts, but the `ExtractionEngine` boundary is ready for a stronger OCR or LLM-backed extractor.

## Tests And Quality

```bash
pytest
ruff check .
```

The test suite covers API key auth, admin auth, health checks, invalid uploads, successful extraction, missing-field warnings, total validation warnings, status lookup, usage tracking, and monthly quota enforcement.

## SaaS Notes

Natural next steps for a paid API are Redis-backed distributed rate limits, queued background workers, object storage for uploads, webhook callbacks, audit logs, customer billing integration, API-key rotation, and an LLM extraction engine behind the existing `ExtractionEngine` interface.
