"""workspace owner session

Revision ID: 0003_workspace_owner_session
Revises: 0002_chunk_fts_index
Create Date: 2026-05-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_workspace_owner_session"
down_revision: str | None = "0002_chunk_fts_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column(
            "owner_session_id",
            sa.String(length=128),
            nullable=False,
            server_default="local-anonymous",
        ),
    )
    op.create_index(
        "ix_workspaces_owner_session_id",
        "workspaces",
        ["owner_session_id"],
    )
    op.alter_column("workspaces", "owner_session_id", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_workspaces_owner_session_id", table_name="workspaces")
    op.drop_column("workspaces", "owner_session_id")
