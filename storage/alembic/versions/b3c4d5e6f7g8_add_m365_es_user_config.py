"""add_m365_es_user_config

Revision ID: b3c4d5e6f7g8
Revises: 778e975f453d
Create Date: 2026-01-26

Adds m365_es_user_config table to store per-organization ES User definition:
- Definition 1: Users with a functioning email mailbox (Exchange license)
- Definition 2: All M365 users with any paid M365 license

Seeds all 38 existing organizations with their verified definitions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP

# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7g8'
down_revision: Union[str, None] = '778e975f453d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Organization definitions verified by Dashboard AI team
# Definition 1 = Email Mailbox (Exchange license)
# Definition 2 = All M365 Licensed Users
DEFINITION_1_ORGS = [
    'Averill & Reaney Counselors at Law L.L.C.',
    'Capitelli Law Firm LLC',
    'Case Industries LLC',
    'Cornerstone Financial LLC',
    'LAMCO Construction LLC',
    'LANCO Construction Inc.',
    'Quality Plumbing Inc.',
    'RV Masters',
    'Siteco Construction',
    'St. Tammany Federation of Teachers and School Employees',
]

DEFINITION_2_ORGS = [
    'AEC',
    'BFM Corporation',
    'Certified Finance and Insurance',
    'ChillCo, Inc.',
    'Electro-Mechanical Recertifiers LLC',
    'Ener Systems',
    'Fleur de LA Imports',
    'Gulf Intracoastal Canal Association',
    'Gulf South Engineering and Testing Inc.',
    'Harris Investments, Ltd.',
    'Insurance Shield',
    'Joshua D. Allison, A Prof. Law Corp.',
    'Lakeside Medical Group',
    'Madcon Corp',
    'NNW, Inc.',
    'New Orleans Culinary & Hospitality Institute',
    'New Orleans Lawn Tennis Club',
    'North American Insurance Agency of LA',
    'OMNI Opti-com Manufacturing Network',
    'RIGBY FINANCIAL GROUP',
    'Saucier\'s Plumbing',
    'Sigma Risk Management Consulting',
    'Southern Retinal Institute',
    'Speedway',
    'Summergrove Farm DHF',
    'Tchefuncta Country Club',
    'ZTLAW',
    'Zeigler Tree & Timber Co.',
]


def upgrade() -> None:
    # Create m365_es_user_config table
    op.create_table(
        'm365_es_user_config',
        sa.Column('organization_name', sa.String(255), primary_key=True),
        sa.Column('es_user_definition', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('needs_review', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index('idx_m365_es_user_config_definition', 'm365_es_user_config', ['es_user_definition'])
    op.create_index('idx_m365_es_user_config_needs_review', 'm365_es_user_config', ['needs_review'])

    # Seed Definition 1 organizations (needs_review=false since verified)
    for org_name in DEFINITION_1_ORGS:
        op.execute(
            sa.text(
                "INSERT INTO m365_es_user_config (organization_name, es_user_definition, needs_review) "
                "VALUES (:org_name, 1, false)"
            ).bindparams(org_name=org_name)
        )

    # Seed Definition 2 organizations (needs_review=false since verified)
    for org_name in DEFINITION_2_ORGS:
        op.execute(
            sa.text(
                "INSERT INTO m365_es_user_config (organization_name, es_user_definition, needs_review) "
                "VALUES (:org_name, 2, false)"
            ).bindparams(org_name=org_name)
        )


def downgrade() -> None:
    op.drop_index('idx_m365_es_user_config_needs_review', 'm365_es_user_config')
    op.drop_index('idx_m365_es_user_config_definition', 'm365_es_user_config')
    op.drop_table('m365_es_user_config')
