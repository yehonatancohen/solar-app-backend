from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import EmailStr
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
import jwt

from app.db import get_session
from app.models import User
from app.schemas import RegisterIn, LoginIn, TokenOut, UserOut
from app.config import settings

router = APIRouter()

ph = PasswordHasher()

def create_access_token(sub: str, expires_minutes: int = None):
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": sub, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(session: AsyncSession = Depends(get_session), token: str = None):
    # Expect token via Authorization header from dependency in routers, simplified here.
    raise NotImplementedError("Use 'auth_required' dependency from routers to inject current user.")

@router.post("/register", response_model=UserOut)
async def register(payload: RegisterIn, session: AsyncSession = Depends(get_session)):
    # Check existing
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=payload.name,
        email=str(payload.email),
        password_hash=ph.hash(payload.password),
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    try:
        ph.verify(user.password_hash, payload.password)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(sub=str(user.id))
    return TokenOut(access_token=token)
