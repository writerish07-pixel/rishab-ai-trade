from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SignalResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    signal_type: str
    strength: str
    confidence: float
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: Optional[float]
    target_3: Optional[float]
    risk_reward_ratio: float
    rsi: Optional[float]
    macd: Optional[float]
    vwap: Optional[float]
    ema_9: Optional[float]
    ema_21: Optional[float]
    volume_spike: bool
    pattern_detected: Optional[str]
    trend: Optional[str]
    reasons: Optional[dict]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MarketSignalSummary(BaseModel):
    total_buy_signals: int
    total_sell_signals: int
    top_signals: List[SignalResponse]
    market_sentiment: str  # BULLISH / BEARISH / NEUTRAL
    nifty_trend: str
    bank_nifty_trend: str
