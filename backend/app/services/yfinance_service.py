"""
yFinance fallback service for historical and real-time data.
Handles Indian stocks via .NS (NSE) and .BO (BSE) suffixes.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import yfinance as yf

from app.schemas.market import QuoteData, OHLCData

logger = logging.getLogger(__name__)

EXCHANGE_SUFFIX = {"NSE": ".NS", "BSE": ".BO", "NFO": ".NS"}

INTERVAL_MAP = {
    "1m": "1m", "3m": "2m", "5m": "5m", "10m": "15m",
    "15m": "15m", "30m": "30m", "1h": "1h", "1d": "1d",
}

PERIOD_MAP = {1: "1d", 2: "2d", 5: "5d", 10: "10d", 30: "1mo", 90: "3mo"}


class YFinanceService:
    def _get_ticker(self, symbol: str, exchange: str) -> str:
        suffix = EXCHANGE_SUFFIX.get(exchange, ".NS")
        if symbol in ("NIFTY50", "^NSEI"):
            return "^NSEI"
        if symbol in ("BANKNIFTY", "^NSEBANK"):
            return "^NSEBANK"
        if symbol == "SENSEX":
            return "^BSESN"
        return f"{symbol}{suffix}"

    async def get_quote(self, symbol: str, exchange: str = "NSE") -> Optional[QuoteData]:
        ticker_sym = self._get_ticker(symbol, exchange)
        loop = asyncio.get_event_loop()
        try:
            ticker = await loop.run_in_executor(None, lambda: yf.Ticker(ticker_sym))
            info = await loop.run_in_executor(None, lambda: ticker.fast_info)

            ltp = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", 0) or 0
            prev_close = getattr(info, "previous_close", ltp) or ltp
            change = ltp - prev_close

            return QuoteData(
                symbol=symbol,
                exchange=exchange,
                ltp=round(ltp, 2),
                open=round(getattr(info, "open", ltp) or ltp, 2),
                high=round(getattr(info, "day_high", ltp) or ltp, 2),
                low=round(getattr(info, "day_low", ltp) or ltp, 2),
                close=round(prev_close, 2),
                change=round(change, 2),
                change_percent=round((change / prev_close * 100) if prev_close else 0, 2),
                volume=int(getattr(info, "three_month_average_volume", 0) or 0),
                avg_price=round(ltp, 2),
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.error(f"yFinance quote error for {ticker_sym}: {e}")
            return None

    async def get_candles(
        self, symbol: str, exchange: str = "NSE",
        interval: str = "5m", days: int = 1
    ) -> List[OHLCData]:
        ticker_sym = self._get_ticker(symbol, exchange)
        yf_interval = INTERVAL_MAP.get(interval, "5m")
        period = PERIOD_MAP.get(days, "1d")
        loop = asyncio.get_event_loop()
        try:
            ticker = yf.Ticker(ticker_sym)
            df = await loop.run_in_executor(
                None, lambda: ticker.history(period=period, interval=yf_interval)
            )
            if df is None or df.empty:
                return []

            candles = []
            for ts, row in df.iterrows():
                candles.append(OHLCData(
                    symbol=symbol,
                    timestamp=ts.isoformat(),
                    open=round(float(row["Open"]), 2),
                    high=round(float(row["High"]), 2),
                    low=round(float(row["Low"]), 2),
                    close=round(float(row["Close"]), 2),
                    volume=int(row["Volume"]),
                ))
            return candles
        except Exception as e:
            logger.error(f"yFinance candles error for {ticker_sym}: {e}")
            return []

    async def get_bulk_quotes(self, symbols: List[str], exchange: str = "NSE") -> dict:
        """Get quotes for multiple symbols at once (efficient batch)."""
        tickers = [self._get_ticker(s, exchange) for s in symbols]
        loop = asyncio.get_event_loop()
        results = {}
        try:
            data = await loop.run_in_executor(
                None, lambda: yf.download(tickers, period="1d", interval="1m", progress=False, group_by="ticker")
            )
            for i, sym in enumerate(symbols):
                ticker = tickers[i]
                try:
                    if len(symbols) > 1:
                        df = data[ticker] if ticker in data.columns.get_level_values(0) else None
                    else:
                        df = data
                    if df is not None and not df.empty:
                        last = df.iloc[-1]
                        results[sym] = {"ltp": round(float(last["Close"]), 2), "volume": int(last["Volume"])}
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Bulk quote error: {e}")
        return results
