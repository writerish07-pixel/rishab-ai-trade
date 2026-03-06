"""Alpaca market data service (US stocks / paper trading)."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import aiohttp

from app.core.config import settings
from app.schemas.market import QuoteData, OHLCData

logger = logging.getLogger(__name__)
DATA_URL = "https://data.alpaca.markets"


class AlpacaService:
    def __init__(self):
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def _headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session

    async def _get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        if not self.api_key or not self.secret_key:
            return None
        session = await self._get_session()
        try:
            async with session.get(
                f"{DATA_URL}{endpoint}", params=params,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"Alpaca {endpoint} status {resp.status}")
        except Exception as e:
            logger.error(f"Alpaca request error: {e}")
        return None

    async def get_quote(self, symbol: str) -> Optional[QuoteData]:
        data = await self._get(f"/v2/stocks/{symbol}/quotes/latest")
        if not data:
            return None
        q = data.get("quote", {})
        # Get latest trade for LTP
        trade_data = await self._get(f"/v2/stocks/{symbol}/trades/latest")
        ltp = float(trade_data.get("trade", {}).get("p", 0)) if trade_data else 0.0

        # Get prev close via bars
        bars_data = await self._get(f"/v2/stocks/{symbol}/bars/latest")
        bar = bars_data.get("bar", {}) if bars_data else {}
        prev_close = float(bar.get("c", ltp))
        change = ltp - prev_close

        return QuoteData(
            symbol=symbol,
            exchange="US",
            ltp=round(ltp, 2),
            open=round(float(bar.get("o", ltp)), 2),
            high=round(float(bar.get("h", ltp)), 2),
            low=round(float(bar.get("l", ltp)), 2),
            close=round(prev_close, 2),
            change=round(change, 2),
            change_percent=round((change / prev_close * 100) if prev_close else 0, 2),
            volume=int(bar.get("v", 0)),
            avg_price=round(float(bar.get("vw", ltp)), 2),
            bid=float(q.get("bp", 0)) or None,
            ask=float(q.get("ap", 0)) or None,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def get_candles(self, symbol: str, interval: str = "5m", days: int = 1) -> List[OHLCData]:
        tf_map = {
            "1m": "1Min", "5m": "5Min", "15m": "15Min",
            "30m": "30Min", "1h": "1Hour", "1d": "1Day",
        }
        timeframe = tf_map.get(interval, "5Min")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        data = await self._get(f"/v2/stocks/{symbol}/bars", {
            "timeframe": timeframe, "start": start, "end": end, "limit": 10000
        })
        if not data or not data.get("bars"):
            return []

        return [
            OHLCData(
                symbol=symbol,
                timestamp=b["t"],
                open=float(b["o"]),
                high=float(b["h"]),
                low=float(b["l"]),
                close=float(b["c"]),
                volume=int(b["v"]),
            )
            for b in data["bars"]
        ]

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
