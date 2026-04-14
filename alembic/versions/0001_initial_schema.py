"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-15

Creates all tables from current ORM metadata. Idempotent — uses
``checkfirst=True`` so existing databases that were bootstrapped via
``Base.metadata.create_all`` can be stamped at this revision without
re-creating tables.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from infrastructure.database import Base
    import core.models  # noqa: F401 — register models
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    from infrastructure.database import Base
    import core.models  # noqa: F401
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
