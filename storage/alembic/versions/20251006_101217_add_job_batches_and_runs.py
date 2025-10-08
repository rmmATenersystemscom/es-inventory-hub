"""Add job batches and runs tables for collector tracking

Revision ID: add_job_batches_and_runs
Revises: 
Create Date: 2025-10-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_job_batches_and_runs"
down_revision = "faa2c03ac557"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create job_batches table
    op.create_table("job_batches",
        sa.Column("batch_id", sa.String(50), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, default="normal"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_percent", sa.Integer, nullable=True),
        sa.Column("estimated_completion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
    )
    
    # Create job_runs table
    op.create_table("job_runs",
        sa.Column("job_id", sa.String(50), primary_key=True),
        sa.Column("batch_id", sa.String(50), nullable=False),
        sa.Column("job_name", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_percent", sa.Integer, nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["job_batches.batch_id"], ondelete="CASCADE"),
    )
    
    # Create indexes
    op.create_index("idx_job_batches_status", "job_batches", ["status"])
    op.create_index("idx_job_batches_created_at", "job_batches", ["created_at"])
    op.create_index("idx_job_runs_batch_id", "job_runs", ["batch_id"])
    op.create_index("idx_job_runs_job_name", "job_runs", ["job_name"])
    op.create_index("idx_job_runs_status", "job_runs", ["status"])
    op.create_index("idx_job_runs_started_at", "job_runs", ["started_at"])


def downgrade() -> None:
    op.drop_table("job_runs")
    op.drop_table("job_batches")
