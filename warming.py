"""
Predictive Warming System for Polaris Computer

Pre-warms containers when user shows intent to deploy, enabling near-instant starts.

Trigger signals:
1. User logs in
2. User clicks on an app card (hover or click)
3. User opens deployment config modal

Warm slot lifecycle:
1. PREPARING - Container being provisioned
2. READY - Container ready, waiting for claim
3. CLAIMED - User deployed, slot converted to deployment
4. EXPIRED - TTL exceeded, resources cleaned up

Default TTL: 3 minutes
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from uuid import UUID
import secrets

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models import WarmSlot, WarmSlotStatus, ComputeProvider, User


# Configuration
WARM_SLOT_TTL_SECONDS = 180  # 3 minutes
MAX_WARM_SLOTS_PER_USER = 2  # Max concurrent warm slots per user
CLEANUP_INTERVAL_SECONDS = 30  # How often to clean expired slots


class WarmingManager:
    """
    Manages predictive warming of containers.
    """

    def __init__(self):
        self._cleanup_task: Optional[asyncio.Task] = None
        self._active = False

    async def start(self):
        """Start the warming manager background tasks"""
        self._active = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        print("Warming manager started")

    async def stop(self):
        """Stop the warming manager"""
        self._active = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        print("Warming manager stopped")

    async def _cleanup_loop(self):
        """Background task to clean up expired warm slots"""
        while self._active:
            try:
                await self._cleanup_expired_slots()
            except Exception as e:
                print(f"Error in warming cleanup: {e}")

            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

    async def _cleanup_expired_slots(self):
        """Clean up expired warm slots and release their resources"""
        from database import get_db_context

        async with get_db_context() as db:
            # Find expired slots
            now = datetime.utcnow()
            result = await db.execute(
                select(WarmSlot).where(
                    and_(
                        WarmSlot.status.in_([WarmSlotStatus.PREPARING, WarmSlotStatus.READY]),
                        WarmSlot.expires_at < now
                    )
                )
            )
            expired_slots = result.scalars().all()

            for slot in expired_slots:
                # Clean up the actual container/instance
                await self._release_warm_slot_resources(slot)

                # Mark as expired
                slot.status = WarmSlotStatus.EXPIRED

            if expired_slots:
                await db.commit()
                print(f"Cleaned up {len(expired_slots)} expired warm slots")

    async def _release_warm_slot_resources(self, slot: WarmSlot):
        """Release compute resources for a warm slot"""
        if not slot.provider_instance_id:
            return

        try:
            if slot.provider == ComputeProvider.VERDA:
                # Import here to avoid circular dependency
                from verda_deploy import VerdaClient, VERDA_CLIENT_ID, VERDA_CLIENT_SECRET
                client = VerdaClient(VERDA_CLIENT_ID, VERDA_CLIENT_SECRET)
                client.delete_instance(slot.provider_instance_id)
            elif slot.provider == ComputeProvider.LOCAL:
                # Stop local Docker container
                import docker
                docker_client = docker.from_env()
                try:
                    container = docker_client.containers.get(slot.provider_instance_id)
                    container.stop(timeout=5)
                    container.remove()
                except docker.errors.NotFound:
                    pass
        except Exception as e:
            print(f"Failed to release warm slot resources: {e}")

    async def trigger_warming(
        self,
        user_id: UUID,
        template_id: str,
        db: AsyncSession,
        signal: str = "click"  # "login", "click", "hover", "config"
    ) -> Optional[Dict]:
        """
        Trigger warming for a user/template combination.
        Returns the warm slot info if created, None if warming not needed.

        Args:
            user_id: User's UUID
            template_id: Template to warm (e.g., "ollama", "jupyter")
            db: Database session
            signal: What triggered the warming
        """
        # Check if user already has an active warm slot for this template
        existing = await db.execute(
            select(WarmSlot).where(
                and_(
                    WarmSlot.user_id == user_id,
                    WarmSlot.template_id == template_id,
                    WarmSlot.status.in_([WarmSlotStatus.PREPARING, WarmSlotStatus.READY])
                )
            )
        )
        existing_slot = existing.scalar_one_or_none()

        if existing_slot:
            # Extend TTL on existing slot
            existing_slot.expires_at = datetime.utcnow() + timedelta(seconds=WARM_SLOT_TTL_SECONDS)
            await db.commit()

            return {
                "slot_id": str(existing_slot.id),
                "status": existing_slot.status.value,
                "extended": True,
                "expires_at": existing_slot.expires_at.isoformat()
            }

        # Check max warm slots per user
        count_result = await db.execute(
            select(WarmSlot).where(
                and_(
                    WarmSlot.user_id == user_id,
                    WarmSlot.status.in_([WarmSlotStatus.PREPARING, WarmSlotStatus.READY])
                )
            )
        )
        active_count = len(count_result.scalars().all())

        if active_count >= MAX_WARM_SLOTS_PER_USER:
            return {
                "error": "Max warm slots reached",
                "max_slots": MAX_WARM_SLOTS_PER_USER
            }

        # Create new warm slot
        expires_at = datetime.utcnow() + timedelta(seconds=WARM_SLOT_TTL_SECONDS)

        warm_slot = WarmSlot(
            user_id=user_id,
            template_id=template_id,
            provider=ComputeProvider.VERDA,
            status=WarmSlotStatus.PREPARING,
            expires_at=expires_at
        )
        db.add(warm_slot)
        await db.flush()

        slot_id = str(warm_slot.id)

        # Start warming in background
        asyncio.create_task(
            self._warm_container(slot_id, user_id, template_id)
        )

        await db.commit()

        return {
            "slot_id": slot_id,
            "status": "preparing",
            "template_id": template_id,
            "expires_at": expires_at.isoformat(),
            "signal": signal
        }

    async def _warm_container(
        self,
        slot_id: str,
        user_id: UUID,
        template_id: str
    ):
        """
        Background task to actually warm/provision the container.
        """
        from database import get_db_context

        try:
            # Simulate container preparation (in production, this would provision actual containers)
            # For templates like Ollama, this might mean:
            # 1. Starting a container with the base image
            # 2. Pre-loading the model
            # 3. Getting it ready to accept connections

            print(f"Warming container for user={user_id}, template={template_id}")

            # Simulate warmup time
            await asyncio.sleep(5)

            async with get_db_context() as db:
                result = await db.execute(
                    select(WarmSlot).where(WarmSlot.id == UUID(slot_id))
                )
                slot = result.scalar_one_or_none()

                if not slot:
                    return

                if slot.status == WarmSlotStatus.EXPIRED:
                    # Slot expired while we were warming
                    return

                # Mark as ready
                slot.status = WarmSlotStatus.READY
                slot.ready_at = datetime.utcnow()

                # In production, set actual host/port from provisioned container
                slot.host = "warm-" + secrets.token_hex(4)
                slot.port = 8080

                await db.commit()
                print(f"Warm slot ready: {slot_id}")

        except Exception as e:
            print(f"Failed to warm container: {e}")

            # Mark slot as expired on failure
            try:
                async with get_db_context() as db:
                    result = await db.execute(
                        select(WarmSlot).where(WarmSlot.id == UUID(slot_id))
                    )
                    slot = result.scalar_one_or_none()
                    if slot:
                        slot.status = WarmSlotStatus.EXPIRED
                        await db.commit()
            except Exception:
                pass

    async def claim_warm_slot(
        self,
        user_id: UUID,
        template_id: str,
        db: AsyncSession
    ) -> Optional[WarmSlot]:
        """
        Try to claim an existing warm slot for deployment.
        Returns the slot if available, None otherwise.
        """
        result = await db.execute(
            select(WarmSlot).where(
                and_(
                    WarmSlot.user_id == user_id,
                    WarmSlot.template_id == template_id,
                    WarmSlot.status == WarmSlotStatus.READY,
                    WarmSlot.expires_at > datetime.utcnow()
                )
            )
        )
        slot = result.scalar_one_or_none()

        if slot:
            slot.status = WarmSlotStatus.CLAIMED
            slot.claimed_at = datetime.utcnow()
            await db.flush()

        return slot

    async def get_user_warm_slots(
        self,
        user_id: UUID,
        db: AsyncSession
    ) -> List[Dict]:
        """Get all active warm slots for a user"""
        result = await db.execute(
            select(WarmSlot).where(
                and_(
                    WarmSlot.user_id == user_id,
                    WarmSlot.status.in_([WarmSlotStatus.PREPARING, WarmSlotStatus.READY])
                )
            )
        )
        slots = result.scalars().all()

        return [
            {
                "slot_id": str(s.id),
                "template_id": s.template_id,
                "status": s.status.value,
                "host": s.host,
                "port": s.port,
                "created_at": s.created_at.isoformat(),
                "ready_at": s.ready_at.isoformat() if s.ready_at else None,
                "expires_at": s.expires_at.isoformat(),
                "seconds_remaining": max(0, int((s.expires_at - datetime.utcnow()).total_seconds()))
            }
            for s in slots
        ]


# Global warming manager instance
warming_manager = WarmingManager()


async def start_warming_manager():
    """Start the global warming manager"""
    await warming_manager.start()


async def stop_warming_manager():
    """Stop the global warming manager"""
    await warming_manager.stop()
