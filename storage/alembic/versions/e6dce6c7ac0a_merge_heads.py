"""merge_heads

Revision ID: e6dce6c7ac0a
Revises: 238f92b595c4, ceb4bd0ca93e
Create Date: 2025-09-20 00:46:52.195309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6dce6c7ac0a'
down_revision: Union[str, None] = ('238f92b595c4', 'ceb4bd0ca93e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
