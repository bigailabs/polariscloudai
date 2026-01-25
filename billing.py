"""
Billing System for Polaris Computer
Stripe integration for subscriptions and usage-based billing

Pricing:
- Free: $0/mo - 30 min compute, no storage
- Basic: $10/mo - 300 min compute, 10GB storage
- Premium: $20/mo - 1000 min compute, 100GB storage

Overage: $0.10 per compute minute beyond limit
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserTier
from auth import get_current_user

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    STRIPE_ENABLED = True
else:
    STRIPE_ENABLED = False

# Stripe Price IDs (configure in Stripe Dashboard)
PRICE_IDS = {
    UserTier.BASIC: os.getenv("STRIPE_PRICE_BASIC", "price_basic_monthly"),
    UserTier.PREMIUM: os.getenv("STRIPE_PRICE_PREMIUM", "price_premium_monthly"),
}

# Router for billing endpoints
router = APIRouter(prefix="/billing", tags=["billing"])


# ============================================================================
# SCHEMAS
# ============================================================================

class CheckoutRequest(BaseModel):
    """Request to create a checkout session"""
    tier: str  # "basic" or "premium"


class PortalRequest(BaseModel):
    """Request to create a billing portal session"""
    return_url: Optional[str] = None


class UsageReport(BaseModel):
    """Usage report for a billing period"""
    period_start: datetime
    period_end: datetime
    compute_minutes: int
    compute_cost: float
    storage_bytes: int
    storage_cost: float
    overage_minutes: int
    overage_cost: float
    total_cost: float


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_or_create_stripe_customer(user: User, db: AsyncSession) -> str:
    """Get or create a Stripe customer for a user"""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    # Create Stripe customer
    customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        metadata={
            "user_id": str(user.id),
            "tier": user.tier.value
        }
    )

    user.stripe_customer_id = customer.id
    await db.commit()

    return customer.id


def tier_from_string(tier_str: str) -> UserTier:
    """Convert string to UserTier enum"""
    tier_map = {
        "free": UserTier.FREE,
        "basic": UserTier.BASIC,
        "premium": UserTier.PREMIUM
    }
    tier = tier_map.get(tier_str.lower())
    if not tier:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier_str}")
    return tier


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/status")
async def get_billing_status(
    current_user: User = Depends(get_current_user)
):
    """Get billing status for the current user"""
    return {
        "enabled": STRIPE_ENABLED,
        "tier": current_user.tier.value,
        "stripe_customer_id": current_user.stripe_customer_id,
        "stripe_subscription_id": current_user.stripe_subscription_id,
        "compute_minutes_used": current_user.compute_minutes_used,
        "compute_minutes_limit": current_user.compute_minutes_limit,
        "storage_bytes_used": current_user.storage_bytes_used,
        "storage_bytes_limit": current_user.storage_bytes_limit,
        "prices": {
            "basic": {"amount": 1000, "currency": "usd", "interval": "month"},
            "premium": {"amount": 2000, "currency": "usd", "interval": "month"}
        }
    }


@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe Checkout session for subscription upgrade"""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    tier = tier_from_string(request.tier)

    if tier == UserTier.FREE:
        raise HTTPException(status_code=400, detail="Cannot checkout for free tier")

    if tier == current_user.tier:
        raise HTTPException(status_code=400, detail="Already on this tier")

    price_id = PRICE_IDS.get(tier)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"No price configured for {tier.value}")

    customer_id = await get_or_create_stripe_customer(current_user, db)

    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{
            "price": price_id,
            "quantity": 1
        }],
        success_url=f"{FRONTEND_URL}?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}?checkout=cancelled",
        metadata={
            "user_id": str(current_user.id),
            "tier": tier.value
        },
        subscription_data={
            "metadata": {
                "user_id": str(current_user.id),
                "tier": tier.value
            }
        }
    )

    return {
        "checkout_url": session.url,
        "session_id": session.id
    }


@router.post("/portal")
async def create_portal_session(
    request: PortalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe Billing Portal session for managing subscription"""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    return_url = request.return_url or f"{FRONTEND_URL}?tab=settings"

    session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=return_url
    )

    return {
        "portal_url": session.url
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events"""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(session, db)

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        await handle_subscription_updated(subscription, db)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await handle_subscription_deleted(subscription, db)

    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        await handle_payment_succeeded(invoice, db)

    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        await handle_payment_failed(invoice, db)

    return {"received": True}


async def handle_checkout_completed(session: dict, db: AsyncSession):
    """Handle successful checkout"""
    user_id = session.get("metadata", {}).get("user_id")
    tier_str = session.get("metadata", {}).get("tier")
    subscription_id = session.get("subscription")

    if not user_id or not tier_str:
        print(f"Missing metadata in checkout session: {session}")
        return

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        print(f"User not found: {user_id}")
        return

    # Update user tier and subscription
    user.tier = tier_from_string(tier_str)
    user.stripe_subscription_id = subscription_id

    # Reset usage counters for new billing period
    user.compute_minutes_used = 0

    await db.commit()
    print(f"User {user.email} upgraded to {user.tier.value}")


async def handle_subscription_updated(subscription: dict, db: AsyncSession):
    """Handle subscription update (e.g., plan change)"""
    customer_id = subscription.get("customer")
    status = subscription.get("status")

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        print(f"User not found for customer: {customer_id}")
        return

    # Get the tier from subscription items
    items = subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        # Map price ID back to tier
        for tier, pid in PRICE_IDS.items():
            if pid == price_id:
                user.tier = tier
                break

    user.stripe_subscription_id = subscription.get("id")
    await db.commit()


async def handle_subscription_deleted(subscription: dict, db: AsyncSession):
    """Handle subscription cancellation"""
    customer_id = subscription.get("customer")

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return

    # Downgrade to free tier
    user.tier = UserTier.FREE
    user.stripe_subscription_id = None
    await db.commit()
    print(f"User {user.email} downgraded to free tier")


async def handle_payment_succeeded(invoice: dict, db: AsyncSession):
    """Handle successful payment"""
    customer_id = invoice.get("customer")

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return

    # Reset monthly usage counters
    user.compute_minutes_used = 0
    await db.commit()


async def handle_payment_failed(invoice: dict, db: AsyncSession):
    """Handle failed payment"""
    customer_id = invoice.get("customer")

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return

    # TODO: Send notification email, consider grace period
    print(f"Payment failed for user {user.email}")


@router.get("/usage")
async def get_usage_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed usage report for current billing period"""
    from models import UsageRecord

    # Get current month's usage
    current_month = datetime.now().strftime("%Y-%m")

    result = await db.execute(
        select(UsageRecord)
        .where(UsageRecord.user_id == current_user.id)
        .where(UsageRecord.billing_month == current_month)
    )
    records = result.scalars().all()

    total_minutes = sum(r.minutes for r in records)
    total_cost = sum(float(r.cost_usd) for r in records)

    # Calculate overage
    limit = current_user.compute_minutes_limit
    overage_minutes = max(0, total_minutes - limit)
    overage_cost = overage_minutes * 0.10  # $0.10 per minute overage

    # Storage (simplified - would need actual calculation)
    storage_cost = 0.0

    return {
        "billing_period": current_month,
        "tier": current_user.tier.value,
        "compute": {
            "minutes_used": total_minutes,
            "minutes_limit": limit,
            "minutes_remaining": max(0, limit - total_minutes),
            "base_cost": total_cost - overage_cost
        },
        "storage": {
            "bytes_used": current_user.storage_bytes_used,
            "bytes_limit": current_user.storage_bytes_limit,
            "cost": storage_cost
        },
        "overage": {
            "minutes": overage_minutes,
            "cost": overage_cost
        },
        "total_cost": total_cost + storage_cost,
        "records_count": len(records)
    }


@router.post("/downgrade")
async def downgrade_to_free(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel subscription and downgrade to free tier"""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    if current_user.tier == UserTier.FREE:
        raise HTTPException(status_code=400, detail="Already on free tier")

    if current_user.stripe_subscription_id:
        try:
            # Cancel at period end (user keeps access until end of billing period)
            stripe.Subscription.modify(
                current_user.stripe_subscription_id,
                cancel_at_period_end=True
            )
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {
        "success": True,
        "message": "Subscription will be cancelled at end of billing period"
    }
