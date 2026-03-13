from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from app.core.security import get_current_user
from app.models.user import User
from app.services.market_data import MarketDataService
from app.services.yfinance_service import YFinanceService
from app.schemas.market import QuoteData, OHLCData, MarketStatus, MarketOverview, TopMover
from app.core.redis_client import cache_get, cache_set

router = APIRouter(prefix="/market", tags=["Market Data"])
market_svc = MarketDataService()
yf_svc = YFinanceService()


def _get_angel_service(user: User):
    if not user.angel_one_api_key:
        return None
    from app.services.angel_one import get_angel_one_service
    return get_angel_one_service(
        user.id, user.angel_one_api_key,
        user.angel_one_client_id, user.angel_one_password,
        user.angel_one_totp_secret
    )


@router.get("/status", response_model=MarketStatus)
async def get_market_status():
    return await market_svc.get_market_status()


@router.get("/quote/{symbol}", response_model=QuoteData)
async def get_quote(
    symbol: str,
    exchange: str = Query("NSE", description="NSE | BSE | NFO"),
    current_user: User = Depends(get_current_user),
):
    angel = _get_angel_service(current_user)
    quote = await market_svc.get_quote(symbol.upper(), exchange, angel)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote not available for {symbol}")
    return quote


@router.get("/quotes", response_model=List[QuoteData])
async def get_bulk_quotes(
    symbols: str = Query(..., description="Comma-separated symbols e.g. RELIANCE,TCS,INFY"),
    exchange: str = Query("NSE"),
    current_user: User = Depends(get_current_user),
):
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    angel = _get_angel_service(current_user)
    results = []
    for sym in symbol_list[:20]:  # Limit to 20
        quote = await market_svc.get_quote(sym, exchange, angel)
        if quote:
            results.append(quote)
    return results


@router.get("/candles/{symbol}", response_model=List[OHLCData])
async def get_candles(
    symbol: str,
    exchange: str = Query("NSE"),
    interval: str = Query("5m", description="1m|5m|15m|30m|1h|1d"),
    days: int = Query(1, ge=1, le=365),
    token: Optional[str] = Query(None, description="Angel One symbol token"),
    current_user: User = Depends(get_current_user),
):
    angel = _get_angel_service(current_user)
    candles = await market_svc.get_candles(symbol.upper(), exchange, interval, days, angel, token)
    if not candles:
        raise HTTPException(status_code=404, detail=f"No candle data for {symbol}")
    return candles


@router.get("/overview", response_model=MarketOverview)
async def get_market_overview(current_user: User = Depends(get_current_user)):
    """Get overall market overview: indices, gainers, losers, most active."""
    cache_key = "market_overview"
    cached = await cache_get(cache_key)
    if cached:
        return MarketOverview(**cached)

    angel = _get_angel_service(current_user)

    # Fetch indices
    nifty = await market_svc.get_quote("NIFTY50", "NSE", angel)
    bank_nifty = await market_svc.get_quote("BANKNIFTY", "NSE", angel)
    sensex = await market_svc.get_quote("SENSEX", "BSE", angel)

    # Use yFinance for gainers/losers (fallback)
    nifty_symbols = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "BHARTIARTL", "SBIN", "LT", "AXISBANK", "WIPRO",
        "SUNPHARMA", "TATAMOTORS", "BAJFINANCE", "MARUTI", "NTPC",
        "ONGC", "COALINDIA", "TATASTEEL", "JSWSTEEL", "HINDALCO"
    ]

    quotes = {}
    for sym in nifty_symbols:
        q = await market_svc.get_quote(sym, "NSE", angel)
        if q:
            quotes[sym] = q

    movers = [
        TopMover(
            symbol=q.symbol,
            ltp=q.ltp,
            change=q.change,
            change_percent=q.change_percent,
            volume=q.volume,
        )
        for q in quotes.values()
    ]

    gainers = sorted(movers, key=lambda x: x.change_percent, reverse=True)[:5]
    losers = sorted(movers, key=lambda x: x.change_percent)[:5]
    most_active = sorted(movers, key=lambda x: x.volume, reverse=True)[:5]

    total = len(movers)
    advances = sum(1 for m in movers if m.change > 0)
    declines = total - advances
    adr = round(advances / declines, 2) if declines > 0 else 99.0

    overview = MarketOverview(
        nifty50=nifty or QuoteData(symbol="NIFTY50", exchange="NSE", ltp=0, open=0, high=0, low=0, close=0, change=0, change_percent=0, volume=0, avg_price=0, timestamp=""),
        bank_nifty=bank_nifty or QuoteData(symbol="BANKNIFTY", exchange="NSE", ltp=0, open=0, high=0, low=0, close=0, change=0, change_percent=0, volume=0, avg_price=0, timestamp=""),
        sensex=sensex or QuoteData(symbol="SENSEX", exchange="BSE", ltp=0, open=0, high=0, low=0, close=0, change=0, change_percent=0, volume=0, avg_price=0, timestamp=""),
        top_gainers=gainers,
        top_losers=losers,
        most_active=most_active,
        advance_decline_ratio=adr,
        market_breadth="POSITIVE" if adr > 1.2 else "NEGATIVE" if adr < 0.8 else "NEUTRAL",
    )

    await cache_set(cache_key, overview.model_dump(), ttl=60)
    return overview


@router.get("/search/{query}")
async def search_symbol(
    query: str,
    exchange: str = Query("NSE"),
    current_user: User = Depends(get_current_user),
):
    """Search for a stock symbol."""
    angel = _get_angel_service(current_user)
    if angel:
        results = await angel.search_scrip(exchange, query.upper())
        return {"results": results[:10]}
    return {"results": []}


@router.get("/option-chain/{symbol}")
async def get_option_chain(
    symbol: str,
    expiry_date: str = Query(..., description="DD-MMM-YYYY format e.g. 27-Mar-2025"),
    strike_price: float = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Fetch option chain data for a symbol."""
    angel = _get_angel_service(current_user)
    if not angel:
        raise HTTPException(status_code=400, detail="Angel One connection required for option chain")
    data = await angel.get_option_chain(symbol.upper(), expiry_date, strike_price)
    return data
