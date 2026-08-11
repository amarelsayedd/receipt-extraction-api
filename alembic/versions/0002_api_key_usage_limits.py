"""api key hashing and usage limits

Revision ID: 0002_api_key_usage_limits
Revises: 0001_initial_schema
Create Date: 2026-08-11
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256

import sqlalchemy as sa

from alembic import op

revision: str = "0002_api_key_usage_limits"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("api_clients", sa.Column("api_key_hash", sa.String(length=64), nullable=True))
    op.add_column("api_clients", sa.Column("api_key_prefix", sa.String(length=16), nullable=True))
    op.add_column(
        "api_clients",
        sa.Column("monthly_usage_limit", sa.Integer(), nullable=False, server_default="1000"),
    )
    op.add_column(
        "api_clients",
        sa.Column("current_usage_month", sa.String(length=7), nullable=True),
    )
    op.add_column(
        "api_clients",
        sa.Column("monthly_usage_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "api_clients",
        sa.Column("total_usage_count", sa.Integer(), nullable=False, server_default="0"),
    )

    connection = op.get_bind()
    usage_month = datetime.now(UTC).strftime("%Y-%m")
    clients = connection.execute(sa.text("SELECT id, api_key FROM api_clients")).mappings()
    for client in clients:
        api_key = client["api_key"]
        connection.execute(
            sa.text(
                """
                UPDATE api_clients
                SET api_key_hash = :api_key_hash,
                    api_key_prefix = :api_key_prefix,
                    current_usage_month = :usage_month
                WHERE id = :client_id
                """
            ),
            {
                "api_key_hash": sha256(api_key.encode("utf-8")).hexdigest(),
                "api_key_prefix": api_key[:12],
                "usage_month": usage_month,
                "client_id": client["id"],
            },
        )

    op.alter_column("api_clients", "api_key_hash", nullable=False)
    op.alter_column("api_clients", "api_key_prefix", nullable=False)
    op.alter_column("api_clients", "current_usage_month", nullable=False)
    op.drop_index(op.f("ix_api_clients_api_key"), table_name="api_clients")
    op.create_index(
        op.f("ix_api_clients_api_key_hash"),
        "api_clients",
        ["api_key_hash"],
        unique=True,
    )
    op.drop_column("api_clients", "api_key")


def downgrade() -> None:
    op.add_column("api_clients", sa.Column("api_key", sa.String(length=255), nullable=True))
    connection = op.get_bind()
    clients = connection.execute(sa.text("SELECT id, api_key_prefix FROM api_clients")).mappings()
    for client in clients:
        connection.execute(
            sa.text("UPDATE api_clients SET api_key = :api_key WHERE id = :client_id"),
            {
                "api_key": f"rotated-{client['api_key_prefix']}",
                "client_id": client["id"],
            },
        )
    op.alter_column("api_clients", "api_key", nullable=False)
    op.drop_index(op.f("ix_api_clients_api_key_hash"), table_name="api_clients")
    op.create_index(op.f("ix_api_clients_api_key"), "api_clients", ["api_key"], unique=True)
    op.drop_column("api_clients", "total_usage_count")
    op.drop_column("api_clients", "monthly_usage_count")
    op.drop_column("api_clients", "current_usage_month")
    op.drop_column("api_clients", "monthly_usage_limit")
    op.drop_column("api_clients", "api_key_prefix")
    op.drop_column("api_clients", "api_key_hash")
