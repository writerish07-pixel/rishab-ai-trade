from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    total_investment: Mapped[float] = mapped_column(Float, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    available_margin: Mapped[float] = mapped_column(Float, default=0.0)
    used_margin: Mapped[float] = mapped_column(Float, default=0.0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    today_pnl: Mapped[float] = mapped_column(Float, default=0.0)

    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="portfolio")
    holdings: Mapped[list["Holding"]] = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    """Long-term delivery holdings."""
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    isin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    avg_buy_price: Mapped[float] = mapped_column(Float, default=0.0)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_percent: Mapped[float] = mapped_column(Float, default=0.0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="holdings")


class Position(Base):
    """Intraday / F&O open positions."""
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    product_type: Mapped[str] = mapped_column(String(20), default="INTRADAY")  # INTRADAY / FUTURES / OPTIONS
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    buy_qty: Mapped[int] = mapped_column(Integer, default=0)
    sell_qty: Mapped[int] = mapped_column(Integer, default=0)
    avg_buy_price: Mapped[float] = mapped_column(Float, default=0.0)
    avg_sell_price: Mapped[float] = mapped_column(Float, default=0.0)
    current_price: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

    # For F&O
    strike_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    option_type: Mapped[str | None] = mapped_column(String(5), nullable=True)  # CE / PE
    expiry_date: Mapped[str | None] = mapped_column(String(20), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
