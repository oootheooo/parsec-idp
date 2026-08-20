"""Add configurable smart PDF processing."""

import sqlalchemy as sa
from alembic import op

revision = "0002_smart_pdf_processing"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("processing_mode", sa.String(length=20), nullable=False, server_default="smart"))
    op.add_column("documents", sa.Column("processing_route", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))


def downgrade():
    op.drop_column("documents", "processing_route")
    op.drop_column("documents", "processing_mode")
