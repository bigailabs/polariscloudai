"""
Admin API routes for Polaris Computer platform
All routes require admin authentication (email in ADMIN_EMAILS)
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Deployment, UsageRecord, DeploymentStatus, ComputeProvider, UserTier
from auth import get_current_user

logger = logging.getLogger(__name__)

# Admin email whitelist - only these users can access admin routes
ADMIN_EMAILS = [
    "dreamboat@polariscomputer.com",
    "admin@polariscomputer.com",
]

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# AUTH HELPER
# ============================================================================

async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that checks if the current user is an admin."""
    if user.email not in ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ============================================================================
# SCHEMAS
# ============================================================================

class TierChangeRequest(BaseModel):
    tier: str


class AdminUserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    tier: str
    active_deployments: int
    compute_minutes_used: int
    last_active_at: Optional[str]
    created_at: str
    is_suspended: bool


class AdminDeploymentResponse(BaseModel):
    id: str
    user_email: str
    name: str
    template_id: str
    provider: str
    status: str
    created_at: str
    cost_usd: float


# ============================================================================
# ROUTES
# ============================================================================

@router.get("/stats")
async def get_platform_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get platform-wide statistics, activity feed, and system health."""

    # Total users by tier
    tier_counts = await db.execute(
        select(
            User.tier,
            func.count(User.id).label("count"),
        ).group_by(User.tier)
    )
    tier_map = {row.tier.value if hasattr(row.tier, "value") else row.tier: row.count for row in tier_counts}

    total_users = sum(tier_map.values())
    users_by_tier = {
        "free": tier_map.get("free", 0),
        "basic": tier_map.get("basic", 0),
        "premium": tier_map.get("premium", 0),
    }

    # Active deployments count
    active_result = await db.execute(
        select(func.count(Deployment.id)).where(
            Deployment.status == DeploymentStatus.RUNNING
        )
    )
    active_deployments = active_result.scalar() or 0

    # Deployments by status
    status_counts = await db.execute(
        select(
            Deployment.status,
            func.count(Deployment.id).label("count"),
        ).group_by(Deployment.status)
    )
    deployments_by_status = {
        row.status.value if hasattr(row.status, "value") else row.status: row.count
        for row in status_counts
    }

    # GPU hours today (from usage records)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    gpu_hours_result = await db.execute(
        select(func.coalesce(func.sum(UsageRecord.minutes), 0)).where(
            UsageRecord.started_at >= today_start
        )
    )
    gpu_minutes_today = gpu_hours_result.scalar() or 0
    gpu_hours_today = gpu_minutes_today / 60.0

    # Revenue this month
    current_month = datetime.utcnow().strftime("%Y-%m")
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(UsageRecord.cost_usd), Decimal("0"))).where(
            UsageRecord.billing_month == current_month
        )
    )
    revenue_this_month = float(revenue_result.scalar() or 0)

    # Recent activity (last 20 events: signups, deployments, errors)
    activity = []

    # Recent signups
    recent_signups = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(5)
    )
    for u in recent_signups.scalars():
        activity.append({
            "id": f"signup-{u.id}",
            "type": "signup",
            "message": f"New user signed up",
            "timestamp": u.created_at.isoformat() if u.created_at else datetime.utcnow().isoformat(),
            "user_email": u.email,
        })

    # Recent deployments
    recent_deployments = await db.execute(
        select(Deployment, User.email)
        .join(User, Deployment.user_id == User.id)
        .order_by(Deployment.created_at.desc())
        .limit(5)
    )
    for row in recent_deployments:
        d = row[0]
        email = row[1]
        activity.append({
            "id": f"deploy-{d.id}",
            "type": "error" if d.status == DeploymentStatus.FAILED else "deployment",
            "message": f"Deployment '{d.name}' {d.status.value}" if hasattr(d.status, "value") else f"Deployment '{d.name}' {d.status}",
            "timestamp": d.created_at.isoformat() if d.created_at else datetime.utcnow().isoformat(),
            "user_email": email,
        })

    # Sort activity by timestamp descending
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    activity = activity[:15]

    # System health (basic check)
    health = {
        "api": "healthy",
        "database": "healthy",
        "gpu_providers": {
            "verda": "healthy",
            "targon": "healthy",
            "local": "healthy",
        },
    }

    # Check database health
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
    except Exception:
        health["database"] = "down"

    return {
        "stats": {
            "total_users": total_users,
            "active_deployments": active_deployments,
            "gpu_hours_today": gpu_hours_today,
            "revenue_this_month": revenue_this_month,
            "users_by_tier": users_by_tier,
            "deployments_by_status": deployments_by_status,
        },
        "activity": activity,
        "health": health,
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with pagination, search, and tier filter."""

    query = select(User)
    count_query = select(func.count(User.id))

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        search_filter = User.email.ilike(search_pattern) | User.name.ilike(search_pattern)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Apply tier filter
    if tier and tier in ("free", "basic", "premium"):
        tier_enum = UserTier(tier)
        query = query.where(User.tier == tier_enum)
        count_query = count_query.where(User.tier == tier_enum)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated users
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()

    # Get active deployment counts for each user
    user_ids = [u.id for u in users]
    if user_ids:
        deploy_counts = await db.execute(
            select(
                Deployment.user_id,
                func.count(Deployment.id).label("count"),
            )
            .where(
                and_(
                    Deployment.user_id.in_(user_ids),
                    Deployment.status == DeploymentStatus.RUNNING,
                )
            )
            .group_by(Deployment.user_id)
        )
        deploy_map = {row.user_id: row.count for row in deploy_counts}
    else:
        deploy_map = {}

    users_out = []
    for u in users:
        users_out.append({
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "tier": u.tier.value if hasattr(u.tier, "value") else u.tier,
            "active_deployments": deploy_map.get(u.id, 0),
            "compute_minutes_used": u.compute_minutes_used,
            "last_active_at": u.last_active_at.isoformat() if u.last_active_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else "",
            "is_suspended": not u.email_verified if hasattr(u, "is_suspended") else False,
        })

    return {
        "users": users_out,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.put("/users/{user_id}/tier")
async def change_user_tier(
    user_id: str,
    body: TierChangeRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's subscription tier."""
    if body.tier not in ("free", "basic", "premium"):
        raise HTTPException(status_code=400, detail="Invalid tier")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.tier = UserTier(body.tier)
    logger.info(f"Admin {admin.email} changed tier for {target_user.email} to {body.tier}")

    return {"success": True, "message": f"Tier changed to {body.tier}"}


@router.put("/users/{user_id}/suspend")
async def toggle_suspend_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle suspend/activate a user."""
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Toggle email_verified as a suspension mechanism
    # In a production system you would have a dedicated is_suspended field
    target_user.email_verified = not target_user.email_verified
    is_now_suspended = not target_user.email_verified

    action = "suspended" if is_now_suspended else "activated"
    logger.info(f"Admin {admin.email} {action} user {target_user.email}")

    return {"success": True, "message": f"User {action}", "is_suspended": is_now_suspended}


@router.get("/deployments")
async def list_all_deployments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    provider: Optional[str] = Query(None),
    template_id: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all deployments across all users with filters."""

    query = select(Deployment, User.email).join(User, Deployment.user_id == User.id)
    count_query = select(func.count(Deployment.id))

    # Apply status filter
    if status_filter:
        try:
            status_enum = DeploymentStatus(status_filter)
            query = query.where(Deployment.status == status_enum)
            count_query = count_query.where(Deployment.status == status_enum)
        except ValueError:
            pass

    # Apply provider filter
    if provider:
        try:
            provider_enum = ComputeProvider(provider)
            query = query.where(Deployment.provider == provider_enum)
            count_query = count_query.where(Deployment.provider == provider_enum)
        except ValueError:
            pass

    # Apply template filter
    if template_id:
        query = query.where(Deployment.template_id == template_id)
        count_query = count_query.where(Deployment.template_id == template_id)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated deployments
    query = query.order_by(Deployment.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    rows = result.all()

    # Get cost data for each deployment
    deployment_ids = [row[0].id for row in rows]
    cost_map: dict = {}
    if deployment_ids:
        cost_result = await db.execute(
            select(
                UsageRecord.deployment_id,
                func.coalesce(func.sum(UsageRecord.cost_usd), Decimal("0")).label("total_cost"),
            )
            .where(UsageRecord.deployment_id.in_(deployment_ids))
            .group_by(UsageRecord.deployment_id)
        )
        cost_map = {row.deployment_id: float(row.total_cost) for row in cost_result}

    deployments_out = []
    for row in rows:
        d = row[0]
        email = row[1]
        deployments_out.append({
            "id": str(d.id),
            "user_email": email,
            "name": d.name,
            "template_id": d.template_id,
            "provider": d.provider.value if hasattr(d.provider, "value") else d.provider,
            "status": d.status.value if hasattr(d.status, "value") else d.status,
            "created_at": d.created_at.isoformat() if d.created_at else "",
            "cost_usd": cost_map.get(d.id, 0.0),
        })

    return {
        "deployments": deployments_out,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.put("/deployments/{deployment_id}/terminate")
async def terminate_deployment(
    deployment_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Force-terminate a deployment (admin action)."""
    result = await db.execute(
        select(Deployment).where(Deployment.id == UUID(deployment_id))
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment.status = DeploymentStatus.STOPPED
    deployment.stopped_at = datetime.utcnow()

    logger.info(f"Admin {admin.email} force-terminated deployment {deployment.name} ({deployment_id})")

    return {"success": True, "message": "Deployment terminated"}


@router.get("/resources")
async def get_resource_utilization(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get GPU resource utilization across providers and regions."""

    # Count running deployments by provider
    provider_counts = await db.execute(
        select(
            Deployment.provider,
            func.count(Deployment.id).label("count"),
        )
        .where(Deployment.status == DeploymentStatus.RUNNING)
        .group_by(Deployment.provider)
    )
    running_by_provider = {
        row.provider.value if hasattr(row.provider, "value") else row.provider: row.count
        for row in provider_counts
    }

    # Define provider capacity (this would come from provider APIs in production)
    provider_config = {
        "verda": {
            "total_gpus": 24,
            "gpu_types": [
                {"type": "A100 80GB", "total": 8, "in_use": 0},
                {"type": "A100 40GB", "total": 8, "in_use": 0},
                {"type": "RTX 4090", "total": 8, "in_use": 0},
            ],
        },
        "targon": {
            "total_gpus": 16,
            "gpu_types": [
                {"type": "H100 80GB", "total": 4, "in_use": 0},
                {"type": "A100 80GB", "total": 8, "in_use": 0},
                {"type": "RTX 4090", "total": 4, "in_use": 0},
            ],
        },
        "local": {
            "total_gpus": 4,
            "gpu_types": [
                {"type": "RTX 4090", "total": 4, "in_use": 0},
            ],
        },
    }

    providers = []
    total_gpus = 0
    total_in_use = 0

    for name, config in provider_config.items():
        in_use = running_by_provider.get(name, 0)
        total = config["total_gpus"]

        # Distribute in_use across GPU types proportionally
        gpu_types = []
        remaining = in_use
        for gpu in config["gpu_types"]:
            gpu_in_use = min(remaining, gpu["total"])
            remaining -= gpu_in_use
            gpu_types.append({
                "type": gpu["type"],
                "total": gpu["total"],
                "in_use": gpu_in_use,
            })

        providers.append({
            "name": name,
            "status": "healthy" if in_use < total else ("degraded" if total > 0 else "down"),
            "total_gpus": total,
            "in_use": in_use,
            "available": max(0, total - in_use),
            "gpu_types": gpu_types,
        })

        total_gpus += total
        total_in_use += in_use

    total_available = total_gpus - total_in_use
    utilization_pct = (total_in_use / total_gpus * 100) if total_gpus > 0 else 0

    # Regional breakdown
    regions = [
        {
            "region": "Lagos, Nigeria",
            "total_capacity": 4,
            "in_use": running_by_provider.get("local", 0),
            "available": max(0, 4 - running_by_provider.get("local", 0)),
            "providers": ["local"],
        },
        {
            "region": "Helsinki, Finland",
            "total_capacity": 40,
            "in_use": running_by_provider.get("verda", 0) + running_by_provider.get("targon", 0),
            "available": max(
                0,
                40
                - running_by_provider.get("verda", 0)
                - running_by_provider.get("targon", 0),
            ),
            "providers": ["verda", "targon"],
        },
    ]

    return {
        "providers": providers,
        "regions": regions,
        "totals": {
            "total_gpus": total_gpus,
            "in_use": total_in_use,
            "available": total_available,
            "utilization_pct": utilization_pct,
        },
    }
