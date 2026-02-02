"""Add Supabase OAuth fields to users table

Revision ID: 002
Revises: 001
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new OAuth-related columns
    op.add_column('users', sa.Column('supabase_user_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(512), nullable=True))

    # Create unique index on supabase_user_id
    op.create_index('ix_users_supabase_user_id', 'users', ['supabase_user_id'], unique=True)

    # Make password_hash nullable (OAuth users don't have passwords)
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(255),
                    nullable=True)

    # Set auth_provider for existing users with passwords
    op.execute("UPDATE users SET auth_provider = 'email' WHERE password_hash IS NOT NULL")


def downgrade() -> None:
    # Set a placeholder password for OAuth-only users before making password_hash non-nullable
    # This is a destructive operation - OAuth-only users will lose access
    op.execute("UPDATE users SET password_hash = 'OAUTH_ONLY_PLACEHOLDER' WHERE password_hash IS NULL")

    # Make password_hash non-nullable again
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(255),
                    nullable=False)

    # Drop the index
    op.drop_index('ix_users_supabase_user_id', table_name='users')

    # Drop the columns
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'supabase_user_id')
