"""expand institution_type_enum with university/research_lab/industry

Revision ID: b3f7a1d9c264
Revises: e7ba2d30e484
Create Date: 2026-08-07 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b3f7a1d9c264'
down_revision: Union[str, None] = 'e7ba2d30e484'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive only — Postgres enums support adding new labels in place.
    # Each ADD VALUE must be its own statement (can't be combined into one).
    op.execute("ALTER TYPE institution_type_enum ADD VALUE IF NOT EXISTS 'university'")
    op.execute("ALTER TYPE institution_type_enum ADD VALUE IF NOT EXISTS 'research_lab'")
    op.execute("ALTER TYPE institution_type_enum ADD VALUE IF NOT EXISTS 'industry'")


def downgrade() -> None:
    # Postgres has no `DROP VALUE` for enums — removing one requires rebuilding
    # the type and every dependent column/constraint. Not needed for an
    # additive-only change; left as a no-op rather than a destructive rebuild.
    pass
