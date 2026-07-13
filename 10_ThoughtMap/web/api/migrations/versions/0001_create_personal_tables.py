from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_create_personal_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email_hash", name="uq_users_email_hash"),
    )
    op.create_index("ix_users_email_hash", "users", ["email_hash"], unique=True)

    op.create_table(
        "saved_works",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_id", sa.Text(), nullable=False),
        sa.Column("original_doc_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("author", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.Text(), nullable=False, server_default=""),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("parameters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("saved_at", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "doc_id", name="uq_saved_works_user_doc_id"),
    )
    op.create_index("ix_saved_works_user_id", "saved_works", ["user_id"])
    op.create_index("ix_saved_works_doc_id", "saved_works", ["doc_id"])

    op.create_table(
        "saved_embeddings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_id", sa.Text(), nullable=False),
        sa.Column("embedding_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("saved_at", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "doc_id", name="uq_saved_embeddings_user_doc_id"),
    )
    op.create_index("ix_saved_embeddings_user_id", "saved_embeddings", ["user_id"])
    op.create_index("ix_saved_embeddings_doc_id", "saved_embeddings", ["doc_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_embeddings_doc_id", table_name="saved_embeddings")
    op.drop_index("ix_saved_embeddings_user_id", table_name="saved_embeddings")
    op.drop_table("saved_embeddings")
    op.drop_index("ix_saved_works_doc_id", table_name="saved_works")
    op.drop_index("ix_saved_works_user_id", table_name="saved_works")
    op.drop_table("saved_works")
    op.drop_index("ix_users_email_hash", table_name="users")
    op.drop_table("users")
