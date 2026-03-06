import enum
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class OrderType(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"
    BRACKET = "BRACKET"


class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class ProductType(str, enum.Enum):
    INTRADAY = "INTRADAY"    # MIS
    DELIVERY = "DELIVERY"    # CNC
    FUTURES = "FUTURES"      # NRML
    OPTIONS = "OPTIONS"      # NRML


class Exchange(str, enum.Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"   # F&O
    BFO = "BFO"
    MCX = "MCX"


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Order details
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    order_type: Mapped[str] = mapped_column(String(30), default=OrderType.MARKET)
    order_side: Mapped[str] = mapped_column(String(10), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), default=ProductType.INTRADAY)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    trigger_price: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING)

    # Execution details
    angel_one_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    executed_price: Mapped[float] = mapped_column(Float, default=0.0)
    executed_qty: Mapped[int] = mapped_column(Integer, default=0)

    # P&L
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    charges: Mapped[float] = mapped_column(Float, default=0.0)  # brokerage + taxes

    # Signal reference
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    is_algo_order: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="trades")
