from datetime import UTC, datetime


def current_usage_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")
