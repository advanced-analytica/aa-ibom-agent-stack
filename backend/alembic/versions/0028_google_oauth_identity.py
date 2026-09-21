"""add Google OAuth identity field

Revision ID: 0028_google_oauth_identity
Revises: 0027_user_magic_link_epoch
Create Date: 2026-09-21T10:15:00+00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "0028_google_oauth_identity"
down_revision = "0027_user_magic_link_epoch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.create_index("users_google_sub_idx", "users", ["google_sub"], unique=True)


def downgrade() -> None:
    op.drop_index("users_google_sub_idx", table_name="users")
    op.drop_column("users", "google_sub")
