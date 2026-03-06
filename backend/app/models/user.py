from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Angel One credentials (encrypted in production)
    angel_one_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    angel_one_client_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    angel_one_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    angel_one_totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Angel One session
    angel_one_jwt_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    angel_one_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    angel_one_token_expiry: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="user", lazy="select")
    portfolio: Mapped["Portfolio | None"] = relationship("Portfolio", back_populates="user", uselist=False)
