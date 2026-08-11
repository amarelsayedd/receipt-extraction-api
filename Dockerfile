FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev,ocr]"

COPY . .

CMD ["sh", "-c", "alembic upgrade head && python -m app.cli && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
