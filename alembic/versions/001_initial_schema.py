"""Initial schema - users, deployments, usage tracking

Revision ID: 001
Revises:
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE usertier AS ENUM ('free', 'basic', 'premium')")
    op.execute("CREATE TYPE deploymentstatus AS ENUM ('pending', 'warming', 'provisioning', 'installing', 'running', 'stopping', 'stopped', 'failed')")
    op.execute("CREATE TYPE computeprovider AS ENUM ('verda', 'targon', 'local')")
    op.execute("CREATE TYPE storageprovider AS ENUM ('storj', 'hippius', 'local')")
    op.execute("CREATE TYPE warmslotstatus AS ENUM ('preparing', 'ready', 'claimed', 'expired')")

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('tier', postgresql.ENUM('free', 'basic', 'premium', name='usertier', create_type=False),
                  nullable=False, server_default='free'),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('storage_bucket_id', sa.String(255), nullable=True),
        sa.Column('compute_minutes_used', sa.Integer, server_default='0'),
        sa.Column('storage_bytes_used', sa.BigInteger, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('last_active_at', sa.DateTime, nullable=True),
    )

    # Deployments table
    op.create_table(
        'deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('template_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'warming', 'provisioning', 'installing',
                                           'running', 'stopping', 'stopped', 'failed',
                                           name='deploymentstatus', create_type=False),
                  server_default='pending'),
        sa.Column('provider', postgresql.ENUM('verda', 'targon', 'local',
                                             name='computeprovider', create_type=False),
                  server_default='verda'),
        sa.Column('provider_instance_id', sa.String(255), nullable=True),
        sa.Column('machine_type', sa.String(100), nullable=True),
        sa.Column('host', sa.String(255), nullable=True),
        sa.Column('port', sa.Integer, nullable=True),
        sa.Column('access_url', sa.String(512), nullable=True),
        sa.Column('config', postgresql.JSONB, nullable=True),
        sa.Column('storage_path', sa.String(512), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('stopped_at', sa.DateTime, nullable=True),
        sa.Column('last_accessed_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_deployments_user_status', 'deployments', ['user_id', 'status'])

    # Usage records table
    op.create_table(
        'usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('deployments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', postgresql.ENUM('verda', 'targon', 'local',
                                             name='computeprovider', create_type=False)),
        sa.Column('machine_type', sa.String(100)),
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('ended_at', sa.DateTime, nullable=True),
        sa.Column('minutes', sa.Integer, server_default='0'),
        sa.Column('cost_usd', sa.Numeric(10, 4), server_default='0.0000'),
        sa.Column('billing_month', sa.String(7), nullable=False),
    )
    op.create_index('ix_usage_records_user_month', 'usage_records', ['user_id', 'billing_month'])

    # Storage volumes table
    op.create_table(
        'storage_volumes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('provider', postgresql.ENUM('storj', 'hippius', 'local',
                                             name='storageprovider', create_type=False),
                  server_default='storj'),
        sa.Column('bucket_name', sa.String(255), nullable=False),
        sa.Column('path', sa.String(512), server_default='/'),
        sa.Column('size_bytes', sa.BigInteger, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('last_synced_at', sa.DateTime, nullable=True),
    )
    op.create_unique_constraint('uq_storage_volume', 'storage_volumes',
                                ['user_id', 'provider', 'bucket_name'])

    # Warm slots table
    op.create_table(
        'warm_slots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('template_id', sa.String(50), nullable=False),
        sa.Column('provider', postgresql.ENUM('verda', 'targon', 'local',
                                             name='computeprovider', create_type=False)),
        sa.Column('provider_instance_id', sa.String(255), nullable=True),
        sa.Column('status', postgresql.ENUM('preparing', 'ready', 'claimed', 'expired',
                                           name='warmslotstatus', create_type=False),
                  server_default='preparing'),
        sa.Column('host', sa.String(255), nullable=True),
        sa.Column('port', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('ready_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('claimed_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_warm_slots_user_template', 'warm_slots', ['user_id', 'template_id'])
    op.create_index('ix_warm_slots_status_expires', 'warm_slots', ['status', 'expires_at'])

    # API keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('key_prefix', sa.String(12), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('request_count', sa.Integer, server_default='0'),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=True),
    )

    # Refresh tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('device_info', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('is_revoked', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_refresh_tokens_user_revoked', 'refresh_tokens', ['user_id', 'is_revoked'])


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_table('api_keys')
    op.drop_table('warm_slots')
    op.drop_table('storage_volumes')
    op.drop_table('usage_records')
    op.drop_table('deployments')
    op.drop_table('users')

    op.execute("DROP TYPE warmslotstatus")
    op.execute("DROP TYPE storageprovider")
    op.execute("DROP TYPE computeprovider")
    op.execute("DROP TYPE deploymentstatus")
    op.execute("DROP TYPE usertier")
