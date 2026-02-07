"""
SQLAlchemy models for Polaris Computer multi-tenant platform
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey,
    Enum, Text, Numeric, BigInteger, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from database import Base


# ============================================================================
# ENUMS
# ============================================================================

class UserTier(str, PyEnum):
    """Subscription tiers"""
    FREE = "free"
    BASIC = "basic"      # $10/mo
    PREMIUM = "premium"  # $20/mo


class DeploymentStatus(str, PyEnum):
    """Deployment lifecycle states"""
    PENDING = "pending"
    WARMING = "warming"
    PROVISIONING = "provisioning"
    INSTALLING = "installing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class ComputeProvider(str, PyEnum):
    """Available compute providers"""
    VERDA = "verda"
    TARGON = "targon"
    LOCAL = "local"


class StorageProvider(str, PyEnum):
    """Available storage providers"""
    STORJ = "storj"
    HIPPIUS = "hippius"
    LOCAL = "local"


class WarmSlotStatus(str, PyEnum):
    """Warm slot lifecycle states"""
    PREPARING = "preparing"
    READY = "ready"
    CLAIMED = "claimed"
    EXPIRED = "expired"


# ============================================================================
# MODELS
# ============================================================================

class User(Base):
    """
    User accounts with subscription tiers
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # OAuth / Supabase
    supabase_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    clerk_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    auth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Email verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Profile
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Subscription
    tier: Mapped[UserTier] = mapped_column(
        Enum(UserTier, values_callable=lambda x: [e.value for e in x]), default=UserTier.FREE, nullable=False
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Storage
    storage_bucket_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Usage tracking (denormalized for quick access)
    compute_minutes_used: Mapped[int] = mapped_column(Integer, default=0)
    storage_bytes_used: Mapped[int] = mapped_column(BigInteger, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    deployments: Mapped[List["Deployment"]] = relationship(
        "Deployment", back_populates="user", cascade="all, delete-orphan"
    )
    usage_records: Mapped[List["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="user", cascade="all, delete-orphan"
    )
    storage_volumes: Mapped[List["StorageVolume"]] = relationship(
        "StorageVolume", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email} ({self.tier.value})>"

    @property
    def compute_minutes_limit(self) -> int:
        """Get compute minutes limit based on tier"""
        limits = {
            UserTier.FREE: 30,
            UserTier.BASIC: 300,
            UserTier.PREMIUM: 1000,
        }
        return limits.get(self.tier, 30)

    @property
    def storage_bytes_limit(self) -> int:
        """Get storage limit in bytes based on tier"""
        limits = {
            UserTier.FREE: 0,  # No persistent storage
            UserTier.BASIC: 10 * 1024 * 1024 * 1024,  # 10 GB
            UserTier.PREMIUM: 100 * 1024 * 1024 * 1024,  # 100 GB
        }
        return limits.get(self.tier, 0)


class Deployment(Base):
    """
    User deployments with tenant isolation
    """
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Template info
    template_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, values_callable=lambda x: [e.value for e in x]), default=DeploymentStatus.PENDING
    )

    # Provider info
    provider: Mapped[ComputeProvider] = mapped_column(
        Enum(ComputeProvider, values_callable=lambda x: [e.value for e in x]), default=ComputeProvider.VERDA
    )
    provider_instance_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Machine info
    machine_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    access_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Configuration (stores template parameters, credentials, etc.)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Storage path for user data
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Error info
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="deployments")
    usage_records: Mapped[List["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="deployment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_deployments_user_status", "user_id", "status"),
    )

    def __repr__(self):
        return f"<Deployment {self.name} ({self.status.value})>"


class UsageRecord(Base):
    """
    Track compute usage for billing
    """
    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deployment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True
    )

    # Provider and machine info
    provider: Mapped[ComputeProvider] = mapped_column(Enum(ComputeProvider, values_callable=lambda x: [e.value for e in x]))
    machine_type: Mapped[str] = mapped_column(String(100))

    # Time tracking
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Computed fields (updated when ended_at is set)
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0000"))

    # Billing period (for aggregation)
    billing_month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_records")
    deployment: Mapped[Optional["Deployment"]] = relationship("Deployment", back_populates="usage_records")

    __table_args__ = (
        Index("ix_usage_records_user_month", "user_id", "billing_month"),
    )

    def __repr__(self):
        return f"<UsageRecord {self.minutes}min ${self.cost_usd}>"


class StorageVolume(Base):
    """
    Track storage volumes per user
    """
    __tablename__ = "storage_volumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Provider info
    provider: Mapped[StorageProvider] = mapped_column(
        Enum(StorageProvider, values_callable=lambda x: [e.value for e in x]), default=StorageProvider.STORJ
    )
    bucket_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Path within the bucket
    path: Mapped[str] = mapped_column(String(512), default="/")

    # Size tracking
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="storage_volumes")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "bucket_name", name="uq_storage_volume"),
    )

    def __repr__(self):
        return f"<StorageVolume {self.bucket_name} ({self.size_bytes} bytes)>"


class WarmSlot(Base):
    """
    Pre-warmed container slots for fast deployment
    Ephemeral - cleaned up after expiration
    """
    __tablename__ = "warm_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Template info
    template_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Provider info
    provider: Mapped[ComputeProvider] = mapped_column(Enum(ComputeProvider, values_callable=lambda x: [e.value for e in x]))
    provider_instance_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[WarmSlotStatus] = mapped_column(
        Enum(WarmSlotStatus, values_callable=lambda x: [e.value for e in x]), default=WarmSlotStatus.PREPARING
    )

    # Connection info (populated when ready)
    host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ready_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_warm_slots_user_template", "user_id", "template_id"),
        Index("ix_warm_slots_status_expires", "status", "expires_at"),
    )

    def __repr__(self):
        return f"<WarmSlot {self.template_id} ({self.status.value})>"


class APIKey(Base):
    """
    User API keys for programmatic access
    """
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Key info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # The actual key (hashed for security, prefix stored for identification)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # First 8 chars
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Usage tracking
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.name} ({self.key_prefix}...)>"


class RefreshToken(Base):
    """
    JWT refresh tokens for session management
    """
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Token info (hashed)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Device/session info
    device_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Status
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_refresh_tokens_user_revoked", "user_id", "is_revoked"),
    )

    def __repr__(self):
        return f"<RefreshToken user={self.user_id}>"
