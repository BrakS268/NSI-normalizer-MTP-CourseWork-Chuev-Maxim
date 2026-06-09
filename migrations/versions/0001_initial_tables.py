"""Initial tables: raw_records, normalized_records, record_clusters, normalization_jobs

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "raw_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("record_type", sa.String(50), nullable=False),
        sa.Column("raw_id", sa.String(255)),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_raw_records_source", "raw_records", ["source"])
    op.create_index("ix_raw_records_record_type", "raw_records", ["record_type"])

    op.create_table(
        "record_clusters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("record_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_record_clusters_record_type", "record_clusters", ["record_type"])

    op.create_table(
        "normalized_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("raw_record_id", UUID(as_uuid=True), sa.ForeignKey("raw_records.id")),
        sa.Column("cluster_id", UUID(as_uuid=True), sa.ForeignKey("record_clusters.id")),
        sa.Column("record_type", sa.String(50), nullable=False),
        sa.Column("canonical_name", sa.Text, nullable=False),
        sa.Column("canonical_code", sa.String(50)),
        sa.Column("normalized_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_normalized_records_record_type", "normalized_records", ["record_type"])
    op.create_index(
        "ix_normalized_records_canonical_code", "normalized_records", ["canonical_code"]
    )
    op.create_index("ix_normalized_records_raw_record_id", "normalized_records", ["raw_record_id"])
    op.create_index("ix_normalized_records_cluster_id", "normalized_records", ["cluster_id"])

    op.create_table(
        "normalization_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("record_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("total_records", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_records", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text),
        sa.Column("llm_tokens_used", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_normalization_jobs_status", "normalization_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("normalization_jobs")
    op.drop_table("normalized_records")
    op.drop_table("record_clusters")
    op.drop_table("raw_records")
