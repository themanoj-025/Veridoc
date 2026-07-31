"""Authentication API routes — uses UserRepository for data access."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_jti,
    get_token_exp,
)
from app.models.user import User
from app.repositories import UserRepository
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefresh,
    PasswordChange,
)
from app.services.email_sender import send_verification_email, send_password_reset_email, get_dev_email_sender

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="auth_register",
)
@limiter.limit("5/minute")
async def register(request: Request, body: UserCreate, session: AsyncSession = Depends(get_session)):
    """Register a new user with email and password."""
    user_repo = UserRepository(session)

    # Check if email already exists
    existing = await user_repo.find_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    await user_repo.create(user)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    await session.close()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, operation_id="auth_login")
@limiter.limit("5/minute")
async def login(request: Request, body: UserLogin, session: AsyncSession = Depends(get_session)):
    """Authenticate a user and return JWT tokens."""
    user_repo = UserRepository(session)
    user = await user_repo.find_by_email(body.email)

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    await session.close()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse, operation_id="auth_refresh")
async def refresh(
    body: TokenRefresh,
    session: AsyncSession = Depends(get_session),
):
    """Refresh an expired access token using a refresh token (rotation mode)."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    uid = uuid.UUID(user_id)

    # Refresh-token rotation
    from app.core.token_store import validate_and_consume
    jti = get_token_jti(payload)
    exp = get_token_exp(payload)
    if not jti or not await validate_and_consume(jti, user_id, expires_at=exp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has already been used. Please log in again.",
        )

    # Fetch the user from DB to return full user info
    user_repo = UserRepository(session)
    user = await user_repo.find_by_id(uid)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    access_token = create_access_token(uid)
    new_refresh_token = create_refresh_token(uid)

    await session.close()
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, operation_id="auth_get_me")
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get the currently authenticated user's profile."""
    result = UserResponse.model_validate(user)
    await session.close()
    return result


@router.post("/logout", operation_id="auth_logout")
async def logout(
    body: TokenRefresh,
    user: User = Depends(get_current_user),
):
    """Logout by revoking the current refresh token."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    from app.core.token_store import revoke_token
    jti = get_token_jti(payload)
    exp = get_token_exp(payload)
    if jti:
        await revoke_token(jti, user_id=str(user.id), expires_at=exp)

    return {"message": "Logged out successfully"}


@router.post("/change-password", operation_id="auth_change_password")
async def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Change the current user's password."""
    if not user.hashed_password or not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    user.hashed_password = hash_password(body.new_password)
    user_repo = UserRepository(session)
    await user_repo.update(user)
    await session.close()
    return {"message": "Password changed successfully"}


# ── F4: Email Verification ──────────────────────────────


@router.post("/request-verification-email", operation_id="auth_request_verification_email")
async def request_verification_email(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Send a verification email to the current user."""
    if user.is_verified:
        return {"message": "Email is already verified"}

    token = secrets.token_urlsafe(32)
    from datetime import datetime, timedelta, timezone
    user.verification_token = token
    user.verification_token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
    user_repo = UserRepository(session)
    await user_repo.update(user)
    await session.close()

    await send_verification_email(user.email, token)
    return {"message": "Verification email sent"}


@router.post("/verify-email", operation_id="auth_verify_email")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    """Verify a user's email address using a verification token."""
    from datetime import datetime, timezone

    user_repo = UserRepository(session)
    user = await user_repo.find_by_verification_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # F4: verification tokens expire after 24h (never replay old links)
    if user.verification_token_expiry is None or user.verification_token_expiry < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Request a new one.",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expiry = None
    await user_repo.update(user)
    await session.close()
    return {"message": "Email verified successfully"}


# ── F4: Password Reset ──────────────────────────────────


@router.post("/request-password-reset", operation_id="auth_request_password_reset")
async def request_password_reset(
    email: str,
    session: AsyncSession = Depends(get_session),
):
    """Request a password reset email. Always returns success to avoid email enumeration."""
    user_repo = UserRepository(session)
    user = await user_repo.find_by_email(email)

    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        from datetime import datetime, timedelta, timezone
        user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        await user_repo.update(user)
        await send_password_reset_email(email, token)

    await session.close()
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password", operation_id="auth_reset_password")
async def reset_password(
    token: str,
    new_password: str,
    session: AsyncSession = Depends(get_session),
):
    """Reset a user's password using a reset token."""
    from datetime import datetime, timezone

    from app.core.security import validate_password_complexity
    err = validate_password_complexity(new_password)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    user_repo = UserRepository(session)
    user = await user_repo.find_by_reset_token(token)
    if not user or not user.reset_token_expiry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if user.reset_token_expiry < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    await user_repo.update(user)
    await session.close()
    return {"message": "Password reset successfully"}
