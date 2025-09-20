"""add_tpm_secureboot_fields_back

Revision ID: b409b4d99c50
Revises: e6dce6c7ac0a
Create Date: 2025-09-20 00:46:55.036354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b409b4d99c50'
down_revision: Union[str, None] = 'e6dce6c7ac0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add TPM and SecureBoot fields back to device_snapshot table
    op.add_column('device_snapshot', sa.Column('has_tpm', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('tpm_enabled', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('tpm_version', sa.String(length=100), nullable=True))
    op.add_column('device_snapshot', sa.Column('secure_boot_available', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('secure_boot_enabled', sa.Boolean(), nullable=True))
    
    # Add indexes for the new fields
    op.create_index('idx_device_snapshot_has_tpm', 'device_snapshot', ['has_tpm'], unique=False)
    op.create_index('idx_device_snapshot_tpm_enabled', 'device_snapshot', ['tpm_enabled'], unique=False)
    op.create_index('idx_device_snapshot_tpm_version', 'device_snapshot', ['tpm_version'], unique=False)
    op.create_index('idx_device_snapshot_secure_boot_available', 'device_snapshot', ['secure_boot_available'], unique=False)
    op.create_index('idx_device_snapshot_secure_boot_enabled', 'device_snapshot', ['secure_boot_enabled'], unique=False)


def downgrade() -> None:
    # Remove indexes first
    op.drop_index('idx_device_snapshot_secure_boot_enabled', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_secure_boot_available', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_tpm_version', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_tpm_enabled', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_has_tpm', table_name='device_snapshot')
    
    # Remove TPM and SecureBoot fields
    op.drop_column('device_snapshot', 'secure_boot_enabled')
    op.drop_column('device_snapshot', 'secure_boot_available')
    op.drop_column('device_snapshot', 'tpm_version')
    op.drop_column('device_snapshot', 'tpm_enabled')
    op.drop_column('device_snapshot', 'has_tpm')
