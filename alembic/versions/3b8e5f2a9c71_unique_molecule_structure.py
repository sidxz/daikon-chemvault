"""one molecule per structure: unique smiles_canonical for new registrations

Revision ID: 3b8e5f2a9c71
Revises: 790324258c05
Create Date: 2026-10-29 00:00:00.000000

Registration treats smiles_canonical as a molecule's identity, but nothing enforced it, so concurrent
registrations of one structure could both insert. Duplicates that already exist stay as they are, because
DAIKON (MLogix) stores molecule IDs: the oldest row of each structure counts, and the unique index exempts
the others by ID (listed in its definition). Once those are resolved, recreate the index without the list.
"""
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b8e5f2a9c71'
down_revision: Union[str, None] = '790324258c05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    # Hold off writes, so no duplicate is inserted between the query below and the index.
    op.execute("LOCK TABLE molecules IN SHARE MODE")
    duplicates = op.get_bind().execute(sa.text("""
        SELECT id FROM (
            SELECT id, row_number() OVER (
                PARTITION BY smiles_canonical ORDER BY _created_at NULLS LAST, id
            ) AS n
            FROM molecules WHERE smiles_canonical IS NOT NULL
        ) ranked
        WHERE n > 1
    """)).scalars().all()

    exempt = None
    if duplicates:
        log.warning(f"{len(duplicates)} existing duplicate molecules are exempt from uq_molecules_smiles_canonical")
        exempt = sa.text(f"id NOT IN ({', '.join(f"'{id_}'" for id_ in duplicates)})")  # UUIDs from the id column
    # A new index: ix_molecules_smiles_canonical stays for lookups, which can't use a partial index.
    op.create_index("uq_molecules_smiles_canonical", "molecules", ["smiles_canonical"], unique=True,
                    postgresql_where=exempt)


def downgrade() -> None:
    op.drop_index("uq_molecules_smiles_canonical", table_name="molecules")
