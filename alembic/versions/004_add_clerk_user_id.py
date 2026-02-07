"""Add Clerk user ID field to users table

Revision ID: 004
Revises: 003
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Clerk user ID column
    op.add_column('users', sa.Column('clerk_user_id', sa.String(255), nullable=True))

    # Create unique index for Clerk user ID lookups
    op.create_index('ix_users_clerk_user_id', 'users', ['clerk_user_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_clerk_user_id', table_name='users')
    op.drop_column('users', 'clerk_user_id')
