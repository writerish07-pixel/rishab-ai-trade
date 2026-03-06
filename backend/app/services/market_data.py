"""
Market data aggregator — selects lowest-latency source automatically.
Priority: Angel One → Polygon → Alpaca → yFinance
"""
import logging
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.redis_client import cache_get, cache_set
from app.schemas.market import QuoteData, OHLCData, MarketStatus

logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(self):
        self._latency_scores: Dict[str, float] = {
            "angel_one": 0.0,
            "polygon": 0.0,
            "alpaca": 0.0,
            "yfinance": 0.0,
        }

    async def get_quote(self, symbol: str, exchange: str = "NSE", angel_service=None) -> Optional[QuoteData]:
        """Get real-time quote from best available source."""
        cache_key = f"mkt_quote:{exchange}:{symbol}"
        cached = await cache_get(cache_key)
        if cached:
            try:
                return QuoteData(**cached)
            except Exception:
                pass  # Cache data malformed — fall through to live fetch

        # Try sources in order
        sources = self._get_source_order(exchange)
        for source in sources:
            try:
                quote = await self._fetch_quote(source, symbol, exchange, angel_service)
                if quote:
                    await cache_set(cache_key, quote.dict(), ttl=2)
                    return quote
            except Exception as e:
                logger.warning(f"Source {source} failed for {symbol}: {e}")
                continue
        return None

    async def get_candles(
        self, symbol: str, exchange: str = "NSE",
        interval: str = "1m", days: int = 1,
        angel_service=None, token: str = None
    ) -> List[OHLCData]:
        """Get OHLCV candle data."""
        cache_key = f"candles:{exchange}:{symbol}:{interval}:{days}"
        cached = await cache_get(cache_key)
        if cached:
            try:
                return [OHLCData(**c) for c in cached]
            except Exception:
                pass  # Cache data malformed — fall through to live fetch

        candles = []
        sources = self._get_source_order(exchange)
        for source in sources:
            try:
                candles = await self._fetch_candles(source, symbol, exchange, interval, days, angel_service, token)
                if candles:
                    ttl = 60 if interval == "1d" else 30
                    await cache_set(cache_key, [c.dict() for c in candles], ttl=ttl)
                    return candles
            except Exception as e:
                logger.warning(f"Candles from {source} failed: {e}")
                continue
        return candles

    def _get_source_order(self, exchange: str) -> List[str]:
        """Determine priority of data sources."""
        if exchange in ("NSE", "BSE", "NFO"):
            # Indian market: Angel One is primary
            primary = settings.MARKET_DATA_PRIMARY
            return [primary, "yfinance"] if primary == "angel_one" else ["angel_one", primary, "yfinance"]
        else:
            # US / international
            return ["alpaca", "polygon", "yfinance"]

    async def _fetch_quote(self, source: str, symbol: str, exchange: str, angel_service) -> Optional[QuoteData]:
        if source == "angel_one" and angel_service:
            return await self._angel_one_quote(angel_service, symbol, exchange)
        elif source == "polygon":
            from app.services.polygon_service import PolygonService
            return await PolygonService().get_quote(symbol)
        elif source == "alpaca":
            from app.services.alpaca_service import AlpacaService
            return await AlpacaService().get_quote(symbol)
        elif source == "yfinance":
            from app.services.yfinance_service import YFinanceService
            return await YFinanceService().get_quote(symbol, exchange)
        return None

    async def _fetch_candles(self, source: str, symbol: str, exchange: str, interval: str, days: int, angel_service, token) -> List[OHLCData]:
        if source == "angel_one" and angel_service and token:
            return await self._angel_one_candles(angel_service, symbol, exchange, token, interval, days)
        elif source == "yfinance":
            from app.services.yfinance_service import YFinanceService
            return await YFinanceService().get_candles(symbol, exchange, interval, days)
        elif source == "polygon":
            from app.services.polygon_service import PolygonService
            return await PolygonService().get_candles(symbol, interval, days)
        return []

    async def _angel_one_quote(self, angel_service, symbol: str, exchange: str) -> Optional[QuoteData]:
        # Look up token from cache/db
        token_cache_key = f"token:{exchange}:{symbol}"
        token_data = await cache_get(token_cache_key)
        if not token_data:
            results = await angel_service.search_scrip(exchange, symbol)
            if results:
                token_data = results[0]
                await cache_set(token_cache_key, token_data, ttl=86400)

        if not token_data:
            return None

        raw = await angel_service.get_quote(exchange, [token_data.get("symboltoken", "")])
        if not raw:
            return None

        # Parse Angel One response format
        fetched = raw.get("fetched", [])
        if not fetched:
            return None
        d = fetched[0]
        ltp = float(d.get("ltp", 0))
        close = float(d.get("close", ltp))
        change = ltp - close
        return QuoteData(
            symbol=symbol,
            exchange=exchange,
            ltp=ltp,
            open=float(d.get("open", 0)),
            high=float(d.get("high", 0)),
            low=float(d.get("low", 0)),
            close=close,
            change=change,
            change_percent=round((change / close * 100) if close else 0, 2),
            volume=int(d.get("tradedVolume", 0)),
            avg_price=float(d.get("averagePrice", ltp)),
            upper_circuit=float(d.get("upperCircuit", 0)) or None,
            lower_circuit=float(d.get("lowerCircuit", 0)) or None,
            bid=float(d.get("buyPrice1", 0)) or None,
            ask=float(d.get("sellPrice1", 0)) or None,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def _angel_one_candles(self, angel_service, symbol: str, exchange: str, token: str, interval: str, days: int) -> List[OHLCData]:
        interval_map = {
            "1m": "ONE_MINUTE", "3m": "THREE_MINUTE", "5m": "FIVE_MINUTE",
            "10m": "TEN_MINUTE", "15m": "FIFTEEN_MINUTE", "30m": "THIRTY_MINUTE",
            "1h": "ONE_HOUR", "1d": "ONE_DAY",
        }
        angel_interval = interval_map.get(interval, "FIVE_MINUTE")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        raw = await angel_service.get_candle_data(exchange, token, angel_interval, from_date, to_date)
        if not raw:
            return []
        # Angel One format: [timestamp, open, high, low, close, volume]
        candles = []
        for row in raw:
            candles.append(OHLCData(
                symbol=symbol,
                timestamp=row[0],
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=int(row[5]),
            ))
        return candles

    async def get_market_status(self) -> MarketStatus:
        """Check if Indian market is currently open."""
        now = datetime.now()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        is_weekday = weekday < 5

        open_time = datetime.strptime(settings.MARKET_OPEN_TIME, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        close_time = datetime.strptime(settings.MARKET_CLOSE_TIME, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )

        is_open = is_weekday and open_time <= now <= close_time

        if is_open:
            status, session = "OPEN", "Regular"
        elif is_weekday and now < open_time:
            status, session = "PRE_OPEN", "Pre-Market"
        else:
            status, session = "CLOSED", "After Hours"

        return MarketStatus(
            is_open=is_open,
            status=status,
            session=session,
            next_open=open_time.isoformat() if not is_open else None,
            next_close=close_time.isoformat() if is_open else None,
        )
