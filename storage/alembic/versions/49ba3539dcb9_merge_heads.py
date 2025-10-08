"""merge heads

Revision ID: 49ba3539dcb9
Revises: faa2c03ac557, add_job_batches_and_runs
Create Date: 2025-10-06 10:12:46.345381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49ba3539dcb9'
down_revision: Union[str, None] = ('faa2c03ac557', 'add_job_batches_and_runs')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
