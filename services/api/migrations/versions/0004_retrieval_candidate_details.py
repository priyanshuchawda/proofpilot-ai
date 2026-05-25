"""retrieval candidate details

Revision ID: 0004_retrieval_candidate_details
Revises: 0003_workspace_owner_session
Create Date: 2026-05-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_retrieval_candidate_details"
down_revision: str | None = "0003_workspace_owner_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "retrieval_candidates",
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.alter_column("retrieval_candidates", "details", server_default=None)


def downgrade() -> None:
    op.drop_column("retrieval_candidates", "details")
