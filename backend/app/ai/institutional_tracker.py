"""
Tracks institutional (FII/DII/MF) activity via:
- Bulk deals, Block deals
- Delivery volume analysis
- Open interest changes
- Large order flow detection
"""
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import aiohttp
import yfinance as yf

from app.core.redis_client import cache_get, cache_set
from app.schemas.market import InstitutionalActivity

logger = logging.getLogger(__name__)


class InstitutionalTracker:
    """
    Analyzes institutional investment patterns.
    Uses NSE bulk deal data and delivery volume percentages.
    """

    # NSE bulk deals API (public)
    NSE_BULK_DEALS_URL = "https://www.nseindia.com/api/bulk-deals"
    NSE_BLOCK_DEALS_URL = "https://www.nseindia.com/api/block-deals"

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            # NSE requires browser-like headers
            self._session = aiohttp.ClientSession(headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nseindia.com",
            })
        return self._session

    async def get_bulk_deals(self, date: str = None) -> List[dict]:
        """Fetch NSE bulk deals for a given date."""
        cache_key = f"bulk_deals:{date or 'today'}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        try:
            session = await self._get_session()
            # First hit NSE homepage to get cookies
            async with session.get("https://www.nseindia.com", timeout=aiohttp.ClientTimeout(total=10)) as _:
                pass
            params = {}
            if date:
                params["date"] = date
            async with session.get(
                self.NSE_BULK_DEALS_URL, params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    deals = data.get("data", [])
                    await cache_set(cache_key, deals, ttl=3600)
                    return deals
        except Exception as e:
            logger.warning(f"NSE bulk deals fetch failed: {e}. Using empty data.")
        return []

    async def get_block_deals(self) -> List[dict]:
        """Fetch NSE block deals."""
        cache_key = "block_deals:today"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        try:
            session = await self._get_session()
            async with session.get("https://www.nseindia.com", timeout=aiohttp.ClientTimeout(total=10)) as _:
                pass
            async with session.get(self.NSE_BLOCK_DEALS_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    deals = data.get("data", [])
                    await cache_set(cache_key, deals, ttl=3600)
                    return deals
        except Exception as e:
            logger.warning(f"NSE block deals fetch failed: {e}")
        return []

    async def analyze_symbol(self, symbol: str) -> InstitutionalActivity:
        """Full institutional activity analysis for a symbol."""
        cache_key = f"inst_activity:{symbol}"
        cached = await cache_get(cache_key)
        if cached:
            return InstitutionalActivity(**cached)

        bulk_deals = await self.get_bulk_deals()
        block_deals = await self.get_block_deals()
        delivery_data = await self._get_delivery_data(symbol)

        symbol_bulk = [d for d in bulk_deals if d.get("symbol", "").upper() == symbol.upper()]
        symbol_block = [d for d in block_deals if d.get("symbol", "").upper() == symbol.upper()]

        bulk_buy_qty = sum(int(d.get("quantity", 0)) for d in symbol_bulk if "B" in d.get("clientType", ""))
        bulk_sell_qty = sum(int(d.get("quantity", 0)) for d in symbol_bulk if "S" in d.get("clientType", ""))
        block_qty = sum(int(d.get("quantity", 0)) for d in symbol_block)

        delivery_pct = delivery_data.get("delivery_percent", 0.0)
        delivery_vol = delivery_data.get("delivery_volume", 0)

        # Determine FII/DII/MF signal
        fii_signal = self._classify_institutional_intent(symbol_bulk, "FII")
        dii_signal = self._classify_institutional_intent(symbol_bulk, "DII")

        # Overall institutional signal
        if bulk_buy_qty > bulk_sell_qty * 1.5 or delivery_pct > 70:
            overall_signal = "ACCUMULATION"
        elif bulk_sell_qty > bulk_buy_qty * 1.5:
            overall_signal = "DISTRIBUTION"
        else:
            overall_signal = "NEUTRAL"

        activity = InstitutionalActivity(
            symbol=symbol,
            bulk_deal_qty=bulk_buy_qty,
            block_deal_qty=block_qty,
            delivery_volume=delivery_vol,
            delivery_percent=delivery_pct,
            fii_activity=fii_signal,
            dii_activity=dii_signal,
            signal=overall_signal,
        )
        await cache_set(cache_key, activity.dict(), ttl=1800)
        return activity

    def _classify_institutional_intent(self, deals: List[dict], investor_type: str) -> str:
        """Classify buy/sell intent of a specific investor type."""
        relevant = [d for d in deals if investor_type.upper() in d.get("clientType", "").upper()]
        buy_qty = sum(int(d.get("quantity", 0)) for d in relevant if "B" in d.get("clientType", ""))
        sell_qty = sum(int(d.get("quantity", 0)) for d in relevant if "S" in d.get("clientType", ""))

        if buy_qty > sell_qty:
            return "BUYING"
        elif sell_qty > buy_qty:
            return "SELLING"
        return "NEUTRAL"

    async def _get_delivery_data(self, symbol: str) -> dict:
        """Get NSE delivery volume data."""
        cache_key = f"delivery:{symbol}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        try:
            session = await self._get_session()
            async with session.get("https://www.nseindia.com", timeout=aiohttp.ClientTimeout(total=5)) as _:
                pass
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}&section=trade_info"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    trade_info = data.get("securityWiseDP", {})
                    result = {
                        "delivery_volume": float(trade_info.get("deliveryQuantity", 0) or 0),
                        "delivery_percent": float(trade_info.get("deliveryToTradedQuantity", 0) or 0),
                    }
                    await cache_set(cache_key, result, ttl=3600)
                    return result
        except Exception as e:
            logger.debug(f"Delivery data fetch failed for {symbol}: {e}")
        return {"delivery_volume": 0.0, "delivery_percent": 0.0}

    async def get_top_institutional_stocks(self, limit: int = 10) -> List[dict]:
        """Get stocks with high institutional accumulation today."""
        bulk_deals = await self.get_bulk_deals()

        # Count net buying by symbol
        symbol_scores: Dict[str, int] = {}
        for deal in bulk_deals:
            sym = deal.get("symbol", "")
            qty = int(deal.get("quantity", 0))
            if "B" in deal.get("clientType", ""):
                symbol_scores[sym] = symbol_scores.get(sym, 0) + qty
            elif "S" in deal.get("clientType", ""):
                symbol_scores[sym] = symbol_scores.get(sym, 0) - qty

        top = sorted(symbol_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"symbol": s, "net_institutional_qty": q, "signal": "ACCUMULATION" if q > 0 else "DISTRIBUTION"}
                for s, q in top if q != 0]

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
