"""Polygon.io market data service (primarily for US stocks, used as fallback)."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import aiohttp

from app.core.config import settings
from app.schemas.market import QuoteData, OHLCData

logger = logging.getLogger(__name__)
BASE_URL = "https://api.polygon.io"


class PolygonService:
    def __init__(self):
        self.api_key = settings.POLYGON_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        if not self.api_key:
            return None
        session = await self._get_session()
        p = params or {}
        p["apiKey"] = self.api_key
        try:
            async with session.get(f"{BASE_URL}{endpoint}", params=p, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"Polygon {endpoint} returned {resp.status}")
        except Exception as e:
            logger.error(f"Polygon request error: {e}")
        return None

    async def get_quote(self, symbol: str) -> Optional[QuoteData]:
        data = await self._get(f"/v2/last/trade/{symbol}")
        if not data or data.get("status") != "OK":
            return None
        result = data.get("result", {})
        price = float(result.get("p", 0))

        # Get prev close for change calc
        prev = await self._get(f"/v2/aggs/ticker/{symbol}/prev")
        prev_close = 0.0
        if prev and prev.get("results"):
            prev_close = float(prev["results"][0].get("c", price))

        change = price - prev_close
        return QuoteData(
            symbol=symbol,
            exchange="US",
            ltp=price,
            open=prev_close,
            high=price,
            low=price,
            close=prev_close,
            change=round(change, 2),
            change_percent=round((change / prev_close * 100) if prev_close else 0, 2),
            volume=int(result.get("s", 0)),
            avg_price=price,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def get_candles(self, symbol: str, interval: str = "5m", days: int = 1) -> List[OHLCData]:
        multiplier, timespan = self._parse_interval(interval)
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")
        data = await self._get(
            f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}",
            {"adjusted": "true", "sort": "asc", "limit": 50000}
        )
        if not data or not data.get("results"):
            return []
        candles = []
        for r in data["results"]:
            ts = datetime.fromtimestamp(r["t"] / 1000).isoformat()
            candles.append(OHLCData(
                symbol=symbol,
                timestamp=ts,
                open=float(r["o"]),
                high=float(r["h"]),
                low=float(r["l"]),
                close=float(r["c"]),
                volume=int(r["v"]),
            ))
        return candles

    def _parse_interval(self, interval: str):
        map_ = {
            "1m": (1, "minute"), "5m": (5, "minute"), "15m": (15, "minute"),
            "30m": (30, "minute"), "1h": (1, "hour"), "1d": (1, "day"),
        }
        return map_.get(interval, (5, "minute"))

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
