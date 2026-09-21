"""expand user avatar URL length

Revision ID: 0030_expand_user_avatar_url
Revises: 0029_supabase_otp_identity
Create Date: 2026-09-21T11:05:00+00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "0030_expand_user_avatar_url"
down_revision = "0029_supabase_otp_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "avatar_url",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "avatar_url",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
