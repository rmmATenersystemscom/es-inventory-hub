"""add_site_alias_table

Revision ID: 0002
Revises: 0001
Create Date: 2024-03-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    # Create site_aliases table
    op.create_table('site_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('alias_name', sa.String(length=255), nullable=False),
        sa.Column('alias_type', sa.String(length=50), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_site_alias_type_id', 'site_aliases', ['alias_type', 'external_id'], unique=False)
    op.create_index('idx_site_alias_site', 'site_aliases', ['site_id'], unique=False)
    
    # Create unique constraint
    op.create_unique_constraint('uq_site_alias_type_id', 'site_aliases', ['alias_type', 'external_id'])
    
    # Remove old columns from sites table
    op.drop_column('sites', 'ninja_site_id')
    op.drop_column('sites', 'threatlocker_tenant_id')


def downgrade():
    # Add back old columns to sites table
    op.add_column('sites', sa.Column('ninja_site_id', sa.String(length=100), nullable=True))
    op.add_column('sites', sa.Column('threatlocker_tenant_id', sa.String(length=100), nullable=True))
    
    # Drop site_aliases table
    op.drop_constraint('uq_site_alias_type_id', 'site_aliases', type_='unique')
    op.drop_index('idx_site_alias_site', table_name='site_aliases')
    op.drop_index('idx_site_alias_type_id', table_name='site_aliases')
    op.drop_table('site_aliases')
