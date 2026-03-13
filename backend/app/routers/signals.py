import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.signal import Signal
from app.ai.signal_engine import SignalEngine, NIFTY_50_SYMBOLS
from app.services.market_data import MarketDataService
from app.schemas.signal import SignalResponse, MarketSignalSummary
from app.core.redis_client import cache_get, cache_set

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/signals", tags=["AI Signals"])

signal_engine = SignalEngine()
market_svc = MarketDataService()


def _get_angel_service(user: User):
    if not user.angel_one_api_key:
        return None
    from app.services.angel_one import get_angel_one_service
    return get_angel_one_service(
        user.id, user.angel_one_api_key,
        user.angel_one_client_id, user.angel_one_password,
        user.angel_one_totp_secret
    )


@router.get("/analyze/{symbol}")
async def analyze_symbol(
    symbol: str,
    exchange: str = Query("NSE"),
    interval: str = Query("5m"),
    days: int = Query(3, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run AI analysis on a single symbol.
    Returns signal with entry, SL, targets and confidence.
    """
    angel = _get_angel_service(current_user)
    candles = await market_svc.get_candles(symbol.upper(), exchange, interval, days, angel)

    if not candles or len(candles) < 30:
        raise HTTPException(status_code=400, detail=f"Insufficient data for {symbol}. Need at least 30 candles.")

    signal_data = await signal_engine.generate_signal(symbol.upper(), candles, exchange)
    if not signal_data:
        return {
            "symbol": symbol,
            "exchange": exchange,
            "signal": "HOLD",
            "message": "No clear signal detected. Conditions not favorable for intraday trade.",
            "confidence": 0.0,
        }

    # Save signal to DB
    from app.ai.indicators import build_dataframe, calculate_all_indicators
    signal_record = Signal(
        symbol=signal_data["symbol"],
        exchange=signal_data["exchange"],
        signal_type=signal_data["signal_type"],
        strength=signal_data["strength"],
        confidence=signal_data["confidence"],
        entry_price=signal_data["entry_price"],
        stop_loss=signal_data["stop_loss"],
        target_1=signal_data["target_1"],
        target_2=signal_data.get("target_2"),
        target_3=signal_data.get("target_3"),
        risk_reward_ratio=signal_data["risk_reward_ratio"],
        rsi=signal_data.get("rsi"),
        macd=signal_data.get("macd"),
        macd_signal=signal_data.get("macd_signal"),
        vwap=signal_data.get("vwap"),
        ema_9=signal_data.get("ema_9"),
        ema_21=signal_data.get("ema_21"),
        ema_50=signal_data.get("ema_50"),
        volume_spike=signal_data.get("volume_spike", False),
        pattern_detected=signal_data.get("pattern_detected"),
        trend=signal_data.get("trend"),
        reasons=signal_data.get("reasons"),
    )
    db.add(signal_record)
    await db.commit()
    await db.refresh(signal_record)

    return {**signal_data, "id": signal_record.id}


@router.get("/scan/market")
async def scan_market(
    limit: int = Query(10, ge=1, le=50),
    exchange: str = Query("NSE"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
):
    """
    Scan the entire Nifty 50 watchlist for trading signals.
    Returns top N signals sorted by confidence.
    """
    cache_key = f"market_scan:{exchange}"
    cached = await cache_get(cache_key)
    if cached:
        return {"signals": cached[:limit], "source": "cache"}

    angel = _get_angel_service(current_user)
    symbols_to_scan = NIFTY_50_SYMBOLS[:20]  # Start with top 20 for speed

    # Fetch candles in parallel
    candle_tasks = [
        market_svc.get_candles(sym, exchange, "5m", 3, angel)
        for sym in symbols_to_scan
    ]
    all_candles = await asyncio.gather(*candle_tasks, return_exceptions=True)

    candles_by_symbol = {}
    for i, sym in enumerate(symbols_to_scan):
        candles = all_candles[i]
        if isinstance(candles, list) and len(candles) >= 30:
            candles_by_symbol[sym] = candles

    signals = await signal_engine.scan_market(candles_by_symbol, exchange)

    if signals:
        await cache_set(cache_key, signals, ttl=300)  # 5 min cache

    return {
        "signals": signals[:limit],
        "total_scanned": len(candles_by_symbol),
        "total_signals": len(signals),
        "source": "live",
    }


@router.get("/summary", response_model=MarketSignalSummary)
async def get_signal_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get today's signal summary."""
    from datetime import date
    today_start = date.today()

    result = await db.execute(
        select(Signal)
        .where(Signal.created_at >= str(today_start))
        .order_by(Signal.confidence.desc())
        .limit(50)
    )
    all_signals = result.scalars().all()

    buy_signals = [s for s in all_signals if s.signal_type == "BUY"]
    sell_signals = [s for s in all_signals if s.signal_type == "SELL"]

    angel = _get_angel_service(current_user)
    nifty_candles = await market_svc.get_candles("NIFTY50", "NSE", "5m", 2, angel)
    bn_candles = await market_svc.get_candles("BANKNIFTY", "NSE", "5m", 2, angel)
    sentiment_data = await signal_engine.get_market_sentiment(nifty_candles, bn_candles)

    return MarketSignalSummary(
        total_buy_signals=len(buy_signals),
        total_sell_signals=len(sell_signals),
        top_signals=all_signals[:5],
        market_sentiment=sentiment_data["market_sentiment"],
        nifty_trend=sentiment_data["nifty_trend"],
        bank_nifty_trend=sentiment_data["bank_nifty_trend"],
    )


@router.get("/history", response_model=List[SignalResponse])
async def get_signal_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Signal).order_by(Signal.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/institutional")
async def get_institutional_activity(
    symbols: str = Query(..., description="Comma-separated symbols"),
    current_user: User = Depends(get_current_user),
):
    """Get institutional activity for given symbols."""
    sym_list = [s.strip().upper() for s in symbols.split(",")][:10]
    results = []
    for sym in sym_list:
        activity = await signal_engine.institutional_tracker.analyze_symbol(sym)
        results.append(activity.model_dump())
    return {"data": results}
