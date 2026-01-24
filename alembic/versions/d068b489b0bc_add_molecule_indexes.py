"""Add molecule indexes

Revision ID: d068b489b0bc
Revises: e442c0029ef0
Create Date: 2025-11-13 13:48:33.882722

"""

from typing import Sequence, Union
import app
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d068b489b0bc"
down_revision: Union[str, None] = "e442c0029ef0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')

    # Functional index on lower(name)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_molecules_name_lower
        ON molecules ((lower(name)));
        """
    )

    # GIN trigram index on normalized synonyms
    # NOTE: use || instead of concat() to keep expression IMMUTABLE
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_molecules_synonyms_norm_trgm
        ON molecules
        USING gin (
            (
                ',' ||
                replace(lower(coalesce(synonyms, '')), ' ', '') ||
                ','
            ) gin_trgm_ops
        );
        """
    )


def downgrade():
    # Drop indexes (extensions are usually left in place, but you *can* drop them if needed)
    op.execute("DROP INDEX IF EXISTS ix_molecules_synonyms_norm_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_molecules_name_lower;")
