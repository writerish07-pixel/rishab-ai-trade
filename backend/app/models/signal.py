import enum
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStrength(str, enum.Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")

    signal_type: Mapped[str] = mapped_column(String(10), nullable=False)
    strength: Mapped[str] = mapped_column(String(20), default=SignalStrength.MODERATE)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 1.0

    # Price levels
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    target_1: Mapped[float] = mapped_column(Float, nullable=False)
    target_2: Mapped[float] = mapped_column(Float, nullable=True)
    target_3: Mapped[float] = mapped_column(Float, nullable=True)
    risk_reward_ratio: Mapped[float] = mapped_column(Float, nullable=False)

    # Indicator values at signal generation
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    vwap: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_9: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_21: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_50: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_spike: Mapped[bool] = mapped_column(Boolean, default=False)

    # AI reasoning
    reasons: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pattern_detected: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trend: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hit_target: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hit_stoploss: Mapped[bool] = mapped_column(Boolean, default=False)
    actual_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
