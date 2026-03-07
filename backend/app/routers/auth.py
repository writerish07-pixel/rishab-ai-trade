from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, get_current_user
)
from app.models.user import User
from app.models.portfolio import Portfolio
from app.schemas.user import UserCreate, UserResponse, UserUpdate, Token, AngelOneConnect
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    result2 = await db.execute(select(User).where(User.username == payload.username))
    if result2.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    await db.flush()

    # Create empty portfolio
    portfolio = Portfolio(user_id=user.id)
    db.add(portfolio)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer", user=user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/angel-one/connect")
async def connect_angel_one(
    payload: AngelOneConnect,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect and authenticate with Angel One SmartAPI."""
    from app.services.angel_one import AngelOneService, _angel_one_instances

    # Always create a fresh instance so new credentials are always used
    service = AngelOneService(payload.api_key, payload.client_id, payload.password, payload.totp_secret)
    _angel_one_instances[current_user.id] = service
    success = await service.login()

    if not success:
        raise HTTPException(status_code=400, detail="Angel One authentication failed. Check credentials.")

    # Save credentials
    current_user.angel_one_api_key = payload.api_key
    current_user.angel_one_client_id = payload.client_id
    current_user.angel_one_password = payload.password
    current_user.angel_one_totp_secret = payload.totp_secret
    db.add(current_user)
    await db.commit()

    return {"status": "connected", "client_id": payload.client_id, "message": "Angel One connected successfully"}


@router.get("/angel-one/status")
async def angel_one_status(current_user: User = Depends(get_current_user)):
    """Check Angel One connection status."""
    is_connected = bool(current_user.angel_one_api_key and current_user.angel_one_client_id)
    return {
        "is_connected": is_connected,
        "client_id": current_user.angel_one_client_id,
    }
