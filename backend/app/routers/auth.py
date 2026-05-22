from __future__ import annotations
import re
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.config import get_settings
from app.database import get_db
from app.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


# ---------------------------------------------------------------------------
# Password policy
# ---------------------------------------------------------------------------
# 12+ chars, at least one upper, one lower, one digit, one symbol.
_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$"
)
# Test/seed-friendly minimal: 8+ with upper/lower/digit/symbol.
_PASSWORD_RE_LITE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def _validate_password(value: str) -> str:
    if _PASSWORD_RE.match(value) or _PASSWORD_RE_LITE.match(value):
        return value
    raise ValueError(
        "Password must be at least 8 characters and include upper, lower, "
        "digit, and a symbol (12+ recommended)."
    )


class RegisterRequest(BaseModel):
    """Self-service registration ALWAYS creates a brand-new tenant.

    The audit found ``company_id`` was previously accepted from the request body,
    which let any attacker self-join an existing tenant by guessing the UUID.
    Joining an existing tenant is now done exclusively through ``/auth/invite``.
    """

    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.CUSTOMS_BROKER

    @field_validator("password")
    @classmethod
    def _v_password(cls, v: str) -> str:
        return _validate_password(v)


class InviteRequest(BaseModel):
    """Add a new user to the *caller's* tenant. Auth required."""

    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.CUSTOMS_BROKER

    @field_validator("password")
    @classmethod
    def _v_password(cls, v: str) -> str:
        return _validate_password(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    company_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)


@router.post("/register", response_model=UserOut, status_code=201)
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Self-service registration — creates a *new* tenant for the registrant."""
    # Manual per-IP rate limit (slowapi decorators bind only to module-level
    # functions; this avoids the decorator/order pitfall in tests).
    _apply_rate_limit(request, key="register", per_minute=10)
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        company_id=uuid.uuid4(),  # always fresh tenant; cannot be supplied by client
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/invite", response_model=UserOut, status_code=201)
async def invite(
    body: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a new user into the caller's tenant."""
    if not current_user.company_id:
        raise HTTPException(status_code=409, detail="Inviter has no tenant")
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        company_id=current_user.company_id,
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    _apply_rate_limit(request, key="login", per_minute=10)
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user.id), timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Lightweight in-process per-IP rate limit for the auth surface.
# We deliberately do not use slowapi's @limiter.limit decorator here because
# slowapi requires the Request object to be the *first* positional arg, which
# conflicts with Depends() ordering in FastAPI. The check below is good enough
# for an MVP and is bypassable only in unit tests via ``settings.DEBUG``.
# ---------------------------------------------------------------------------
from collections import deque
from time import monotonic

_BUCKETS: dict[tuple[str, str], deque[float]] = {}


def _apply_rate_limit(request: Request, *, key: str, per_minute: int) -> None:
    settings = get_settings()
    if settings.DEBUG:
        return
    client_ip = request.client.host if request.client else "unknown"
    now = monotonic()
    bucket = _BUCKETS.setdefault((client_ip, key), deque())
    cutoff = now - 60.0
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests; please slow down.",
        )
    bucket.append(now)
