"""Add rendered-page reader selection.

Revision ID: 0003_visual_reader
Revises: 0002_smart_pdf_processing
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_visual_reader"
down_revision = "0002_smart_pdf_processing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("visual_reader", sa.String(length=20), nullable=False, server_default="vision"))


def downgrade() -> None:
    op.drop_column("documents", "visual_reader")
