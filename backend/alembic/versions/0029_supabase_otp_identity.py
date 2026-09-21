"""add Supabase Auth identity field

Revision ID: 0029_supabase_otp_identity
Revises: 0028_google_oauth_identity
Create Date: 2026-09-21T10:45:00+00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "0029_supabase_otp_identity"
down_revision = "0028_google_oauth_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("supabase_auth_user_id", sa.String(length=255), nullable=True))
    op.create_index(
        "users_supabase_auth_user_id_idx",
        "users",
        ["supabase_auth_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("users_supabase_auth_user_id_idx", table_name="users")
    op.drop_column("users", "supabase_auth_user_id")
