"""
Authentication module for Polaris Computer
JWT-based authentication with refresh tokens
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserTier, RefreshToken

# ============================================================================
# CONFIGURATION
# ============================================================================

# JWT settings - use strong secrets in production
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

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

    class Config:
        from_attributes = True


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


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
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
    """
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user:
        user.last_active_at = datetime.utcnow()

    return user


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/signup", response_model=TokenResponse)
async def signup(
    request: SignupRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    Returns JWT tokens on success.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = User(
        email=request.email.lower(),
        password_hash=hash_password(request.password),
        name=request.name,
        tier=UserTier.FREE,
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
        device_info=req.headers.get("User-Agent", "")[:255],
        ip_address=req.client.host if req.client else None,
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
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate a user and return JWT tokens.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
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
        device_info=req.headers.get("User-Agent", "")[:255],
        ip_address=req.client.host if req.client else None,
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
async def refresh_tokens(
    request: RefreshRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh an access token using a refresh token.
    """
    token_hash = hash_token(request.refresh_token)

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
        device_info=req.headers.get("User-Agent", "")[:255],
        ip_address=req.client.host if req.client else None,
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
async def change_password(
    current_password: str,
    new_password: str = Field(min_length=8),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change the current user's password.
    """
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    user.password_hash = hash_password(new_password)

    # Revoke all refresh tokens (force re-login on all devices)
    await db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id)
        .values(is_revoked=True)
    )

    await db.commit()

    return {"success": True, "message": "Password changed successfully"}
