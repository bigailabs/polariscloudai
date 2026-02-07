"""
Authentication module for Polaris Computer
JWT-based authentication with refresh tokens
"""

import os
import time
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt, jwk
from jose.utils import base64url_decode
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from models import User, UserTier, RefreshToken

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

# ============================================================================
# CONFIGURATION
# ============================================================================

# JWT settings - MUST be set in production
def get_jwt_secret():
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        if os.getenv("ENVIRONMENT") == "production":
            raise RuntimeError("JWT_SECRET_KEY must be set in production")
        # Only allow random secret in development
        import warnings
        warnings.warn("Using random JWT_SECRET_KEY - sessions will not persist across restarts")
        return secrets.token_urlsafe(32)
    return secret

SECRET_KEY = get_jwt_secret()
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY") or (SECRET_KEY + "_refresh")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Clerk settings
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")

# JWKS cache (keys + timestamp)
_clerk_jwks_cache: dict = {"keys": None, "fetched_at": 0}
CLERK_JWKS_CACHE_TTL = 3600  # 1 hour

# Supabase settings (for OAuth — legacy, kept during migration)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)

# Router for auth endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# SCHEMAS
# ============================================================================

class SignupRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    name: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str = Field(min_length=8, description="Minimum 8 characters")


class PasswordResetRequest(BaseModel):
    """Request password reset"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token"""
    token: str
    new_password: str = Field(min_length=8)


class UserResponse(BaseModel):
    """User info response"""
    id: str
    email: str
    name: Optional[str]
    tier: str
    compute_minutes_used: int
    compute_minutes_limit: int
    storage_bytes_used: int
    storage_bytes_limit: int
    created_at: datetime
    auth_provider: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request from frontend"""
    access_token: str  # Supabase access token


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_token(token: str) -> str:
    """Hash a refresh token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: UUID, email: str) -> Tuple[str, datetime]:
    """Create a JWT access token"""
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": expires,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expires


def create_refresh_token(user_id: UUID) -> Tuple[str, datetime]:
    """Create a refresh token"""
    expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token = secrets.token_urlsafe(64)
    return token, expires


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate an access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_supabase_token(token: str) -> Optional[dict]:
    """Decode and validate a Supabase JWT token"""
    if not SUPABASE_JWT_SECRET:
        return None
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError:
        return None


async def get_clerk_jwks() -> Optional[dict]:
    """Fetch and cache Clerk's JWKS public keys (1hr TTL)."""
    if not CLERK_JWKS_URL:
        return None

    now = time.time()
    if _clerk_jwks_cache["keys"] and (now - _clerk_jwks_cache["fetched_at"]) < CLERK_JWKS_CACHE_TTL:
        return _clerk_jwks_cache["keys"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(CLERK_JWKS_URL)
            resp.raise_for_status()
            jwks = resp.json()
            _clerk_jwks_cache["keys"] = jwks
            _clerk_jwks_cache["fetched_at"] = now
            return jwks
    except Exception as e:
        logger.warning(f"Failed to fetch Clerk JWKS: {e}")
        # Return stale cache if available
        if _clerk_jwks_cache["keys"]:
            return _clerk_jwks_cache["keys"]
        return None


def decode_clerk_token(token: str, jwks: dict) -> Optional[dict]:
    """Decode and validate a Clerk RS256 JWT using JWKS public keys."""
    try:
        # Get the key ID from the token header
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")
        if not kid:
            return None

        # Find matching key in JWKS
        matching_key = None
        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                matching_key = key_data
                break

        if not matching_key:
            return None

        # Decode and verify the token with the public key
        payload = jwt.decode(
            token,
            matching_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk tokens don't always set audience
        )
        return payload
    except JWTError:
        return None


async def get_or_create_clerk_user(
    db: AsyncSession,
    clerk_user_id: str,
    email: str,
    payload: dict,
) -> User:
    """
    Find user by clerk_user_id, link by email, or create new user.
    Follows same pattern as create_or_link_oauth_user.
    """
    # 1. Check if user already exists with this clerk_user_id
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        user.last_active_at = datetime.utcnow()
        return user

    # 2. Check if user exists with same email (link accounts)
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    user = result.scalar_one_or_none()

    if user:
        # Link existing account to Clerk
        user.clerk_user_id = clerk_user_id
        if not user.auth_provider:
            user.auth_provider = "clerk"
        user.last_active_at = datetime.utcnow()
        # Update avatar/name from Clerk if not already set
        name = payload.get("name") or payload.get("first_name")
        avatar = payload.get("image_url") or payload.get("profile_image_url")
        if name and not user.name:
            user.name = name
        if avatar and not user.avatar_url:
            user.avatar_url = avatar
        return user

    # 3. Create new user
    name = payload.get("name") or payload.get("first_name")
    avatar = payload.get("image_url") or payload.get("profile_image_url")

    user = User(
        email=email.lower(),
        clerk_user_id=clerk_user_id,
        auth_provider="clerk",
        name=name,
        avatar_url=avatar,
        tier=UserTier.FREE,
    )
    db.add(user)
    await db.flush()

    return user


async def create_or_link_oauth_user(
    db: AsyncSession,
    supabase_user_id: str,
    email: str,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    provider: str = "google"
) -> User:
    """
    Create a new user from OAuth or link to existing user with same email.
    """
    # First, check if user already exists with this supabase_user_id
    result = await db.execute(
        select(User).where(User.supabase_user_id == supabase_user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update user info from OAuth provider
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        if name and not user.name:
            user.name = name
        user.last_active_at = datetime.utcnow()
        return user

    # Check if user exists with same email (link accounts)
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    user = result.scalar_one_or_none()

    if user:
        # Link existing account to Supabase
        user.supabase_user_id = supabase_user_id
        user.auth_provider = user.auth_provider or provider  # Keep original if set
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        user.last_active_at = datetime.utcnow()
        return user

    # Create new user
    user = User(
        email=email.lower(),
        supabase_user_id=supabase_user_id,
        auth_provider=provider,
        name=name,
        avatar_url=avatar_url,
        tier=UserTier.FREE,
    )
    db.add(user)
    await db.flush()

    return user


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Tries auth methods in order: Clerk JWT → custom JWT → Supabase JWT.
    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user = None

    # 1. Try Clerk JWT first (primary auth method)
    jwks = await get_clerk_jwks()
    if jwks:
        clerk_payload = decode_clerk_token(token, jwks)
        if clerk_payload:
            clerk_user_id = clerk_payload.get("sub")
            email = clerk_payload.get("email")
            if clerk_user_id and email:
                user = await get_or_create_clerk_user(db, clerk_user_id, email, clerk_payload)

    # 2. Try custom JWT (legacy, kept during migration)
    if not user:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == UUID(user_id)))
                user = result.scalar_one_or_none()

    # 3. Try Supabase JWT (legacy, kept during migration)
    if not user:
        supabase_payload = decode_supabase_token(token)
        if supabase_payload:
            supabase_user_id = supabase_payload.get("sub")
            if supabase_user_id:
                result = await db.execute(
                    select(User).where(User.supabase_user_id == supabase_user_id)
                )
                user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last active timestamp
    user.last_active_at = datetime.utcnow()

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get the current user if authenticated, or None.
    Does not raise an error if not authenticated.
    Tries: Clerk JWT → custom JWT.
    """
    if not credentials:
        return None

    token = credentials.credentials
    user = None

    # 1. Try Clerk JWT first
    jwks = await get_clerk_jwks()
    if jwks:
        clerk_payload = decode_clerk_token(token, jwks)
        if clerk_payload:
            clerk_user_id = clerk_payload.get("sub")
            email = clerk_payload.get("email")
            if clerk_user_id and email:
                user = await get_or_create_clerk_user(db, clerk_user_id, email, clerk_payload)

    # 2. Try custom JWT (legacy)
    if not user:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == UUID(user_id)))
                user = result.scalar_one_or_none()

    if user:
        user.last_active_at = datetime.utcnow()

    return user


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/signup", response_model=TokenResponse)
@limiter.limit("5/minute")
async def signup(
    signup_data: SignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    Returns JWT tokens on success.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == signup_data.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = User(
        email=signup_data.email.lower(),
        password_hash=hash_password(signup_data.password),
        name=signup_data.name,
        tier=UserTier.FREE,
        auth_provider="email",
    )
    db.add(user)
    await db.flush()  # Get the user ID

    # Create tokens
    access_token, access_expires = create_access_token(user.id, user.email)
    refresh_token, refresh_expires = create_refresh_token(user.id)

    # Store refresh token
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=request.client.host if request.client else None,
        expires_at=refresh_expires,
    )
    db.add(refresh_token_record)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate a user and return JWT tokens.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == login_data.email.lower()))
    user = result.scalar_one_or_none()

    # Check if user exists and has a password (OAuth-only users can't login with password)
    if not user or not user.password_hash or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Update last active
    user.last_active_at = datetime.utcnow()

    # Create tokens
    access_token, access_expires = create_access_token(user.id, user.email)
    refresh_token, refresh_expires = create_refresh_token(user.id)

    # Store refresh token
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=request.client.host if request.client else None,
        expires_at=refresh_expires,
    )
    db.add(refresh_token_record)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def refresh_tokens(
    refresh_data: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh an access token using a refresh token.
    """
    token_hash = hash_token(refresh_data.refresh_token)

    # Find the refresh token
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .where(RefreshToken.is_revoked == False)
        .where(RefreshToken.expires_at > datetime.utcnow())
    )
    refresh_token_record = result.scalar_one_or_none()

    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Get the user
    result = await db.execute(select(User).where(User.id == refresh_token_record.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Revoke old refresh token
    refresh_token_record.is_revoked = True
    refresh_token_record.last_used_at = datetime.utcnow()

    # Create new tokens
    access_token, access_expires = create_access_token(user.id, user.email)
    new_refresh_token, refresh_expires = create_refresh_token(user.id)

    # Store new refresh token
    new_refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=request.client.host if request.client else None,
        expires_at=refresh_expires,
    )
    db.add(new_refresh_token_record)

    # Update last active
    user.last_active_at = datetime.utcnow()

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Logout by revoking the refresh token.
    """
    token_hash = hash_token(request.refresh_token)

    # Find and revoke the refresh token
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    refresh_token_record = result.scalar_one_or_none()

    if refresh_token_record:
        refresh_token_record.is_revoked = True
        await db.commit()

    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """
    Get the current user's profile.
    """
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        tier=user.tier.value,
        compute_minutes_used=user.compute_minutes_used,
        compute_minutes_limit=user.compute_minutes_limit,
        storage_bytes_used=user.storage_bytes_used,
        storage_bytes_limit=user.storage_bytes_limit,
        created_at=user.created_at,
        auth_provider=user.auth_provider,
        avatar_url=user.avatar_url,
    )


@router.put("/me")
async def update_me(
    name: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's profile.
    """
    if name is not None:
        user.name = name

    await db.commit()

    return {"success": True, "message": "Profile updated"}


@router.post("/change-password")
@limiter.limit("3/minute")
async def change_password(
    password_data: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change the current user's password.
    """
    # OAuth-only users don't have a password
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth-only accounts"
        )

    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    user.password_hash = hash_password(password_data.new_password)

    # Revoke all refresh tokens (force re-login on all devices)
    await db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id)
        .values(is_revoked=True)
    )

    await db.commit()

    return {"success": True, "message": "Password changed successfully"}


@router.post("/oauth/callback", response_model=TokenResponse)
async def oauth_callback(
    oauth_data: OAuthCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange a Supabase token for local JWT tokens.
    Called by frontend after successful OAuth login.
    """
    # Decode the Supabase token
    payload = decode_supabase_token(oauth_data.access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Supabase token"
        )

    supabase_user_id = payload.get("sub")
    email = payload.get("email")

    if not supabase_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Extract user metadata from Supabase token
    user_metadata = payload.get("user_metadata", {})
    name = user_metadata.get("full_name") or user_metadata.get("name")
    avatar_url = user_metadata.get("avatar_url") or user_metadata.get("picture")

    # Determine provider from app_metadata
    app_metadata = payload.get("app_metadata", {})
    provider = app_metadata.get("provider", "google")

    # Create or link user
    user = await create_or_link_oauth_user(
        db=db,
        supabase_user_id=supabase_user_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        provider=provider
    )

    # Create local JWT tokens
    access_token, access_expires = create_access_token(user.id, user.email)
    refresh_token, refresh_expires = create_refresh_token(user.id)

    # Store refresh token
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=request.client.host if request.client else None,
        expires_at=refresh_expires,
    )
    db.add(refresh_token_record)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    reset_req: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Request a password reset email"""
    # Find user by email
    result = await db.execute(select(User).where(User.email == reset_req.email.lower()))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return {"success": True, "message": "If the email exists, a reset link will be sent"}

    # Generate reset token (expires in 1 hour)
    reset_token = secrets.token_urlsafe(32)
    reset_expires = datetime.utcnow() + timedelta(hours=1)

    # Store hashed token in user record
    user.password_reset_token = hash_token(reset_token)
    user.password_reset_expires = reset_expires
    await db.commit()

    # TODO: Send email with reset link
    # For now, log the token (remove in production)
    print(f"Password reset token for {user.email}: {reset_token}")

    return {"success": True, "message": "If the email exists, a reset link will be sent"}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    reset_confirm: PasswordResetConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using token"""
    token_hash = hash_token(reset_confirm.token)

    # Find user with valid reset token
    result = await db.execute(
        select(User)
        .where(User.password_reset_token == token_hash)
        .where(User.password_reset_expires > datetime.utcnow())
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Update password and clear reset token
    user.password_hash = hash_password(reset_confirm.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None

    # Revoke all refresh tokens
    await db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id)
        .values(is_revoked=True)
    )

    await db.commit()

    return {"success": True, "message": "Password reset successfully"}