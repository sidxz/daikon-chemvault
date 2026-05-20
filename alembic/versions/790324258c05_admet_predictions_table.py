"""admet_predictions_table

Revision ID: 790324258c05
Revises: d068b489b0bc
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '790324258c05'
down_revision: Union[str, None] = 'd068b489b0bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'admet_predictions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('_deleted_at', sa.DateTime(), nullable=True),
        sa.Column('_created_by', sa.UUID(), nullable=True),
        sa.Column('_updated_by', sa.UUID(), nullable=True),
        sa.Column('_deleted_by', sa.UUID(), nullable=True),
        sa.Column('_is_deleted', sa.Boolean(), nullable=True),
        sa.Column('_status', sa.String(), nullable=True),
        sa.Column('_version', sa.Integer(), nullable=True),
        sa.Column('_owner_id', sa.UUID(), nullable=True),
        sa.Column('_tenant_id', sa.UUID(), nullable=True),
        sa.Column('_tags', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['molecules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_admet_predictions_id'),
        'admet_predictions',
        ['id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_admet_predictions_id'), table_name='admet_predictions')
    op.drop_table('admet_predictions')
