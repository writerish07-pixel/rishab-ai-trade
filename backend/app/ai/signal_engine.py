"""
AI Signal Generation Engine.
Produces high-probability intraday trading signals with:
- Entry price, Stop Loss, Target 1/2/3
- Confidence score (0-1)
- Risk/Reward ratio
- Multi-indicator confirmation requirement
"""
import logging
import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timedelta

import pandas as pd

from app.ai.indicators import build_dataframe, calculate_all_indicators, get_latest_indicators, detect_trend
from app.ai.pattern_detector import PatternDetector
from app.ai.institutional_tracker import InstitutionalTracker
from app.core.config import settings
from app.core.redis_client import cache_get, cache_set

logger = logging.getLogger(__name__)

# Watchlist of stocks to scan for signals
NIFTY_50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "WIPRO", "MARUTI",
    "ULTRACEMCO", "BAJFINANCE", "HCLTECH", "ADANIENT", "NTPC",
    "SUNPHARMA", "TITAN", "POWERGRID", "TATAMOTORS", "NESTLEIND",
    "BAJAJFINSV", "TECHM", "GRASIM", "ONGC", "JSWSTEEL",
    "TATASTEEL", "COALINDIA", "ADANIPORTS", "DIVISLAB", "BPCL",
    "EICHERMOT", "CIPLA", "DRREDDY", "HINDALCO", "APOLLOHOSP",
    "HDFCLIFE", "SBILIFE", "TATACONSUM", "BRITANNIA", "INDUSINDBK",
    "UPL", "VEDL", "PIDILITIND", "SHREECEM", "HEROMOTOCO",
]


class SignalEngine:
    def __init__(self):
        self.institutional_tracker = InstitutionalTracker()
        self.min_confidence = settings.SIGNAL_CONFIDENCE_THRESHOLD
        self.min_rr_ratio = 1.5  # Minimum Risk/Reward ratio

    async def generate_signal(
        self,
        symbol: str,
        candles: list,
        exchange: str = "NSE",
        include_institutional: bool = True,
    ) -> Optional[dict]:
        """
        Generate a trading signal for the given symbol.
        Returns None if no valid signal found.
        """
        cache_key = f"signal:{exchange}:{symbol}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        if not candles or len(candles) < 30:
            logger.debug(f"Insufficient candles for {symbol}: {len(candles) if candles else 0}")
            return None

        # Build DataFrame and calculate indicators
        df = build_dataframe(candles)
        if df is None:
            return None
        df = calculate_all_indicators(df)
        indicators = get_latest_indicators(df)
        trend = detect_trend(df)

        # Pattern detection
        pattern_detector = PatternDetector(df)
        patterns = pattern_detector.detect_all()

        # Institutional analysis
        inst_activity = None
        if include_institutional:
            try:
                inst_activity = await asyncio.wait_for(
                    self.institutional_tracker.analyze_symbol(symbol), timeout=3.0
                )
            except asyncio.TimeoutError:
                pass

        # Scoring system
        buy_score, sell_score, reasons = self._score_signals(
            indicators, trend, patterns, inst_activity
        )

        signal_type, score = self._determine_signal_type(buy_score, sell_score)
        if signal_type is None:
            return None

        confidence = min(score / 10.0, 1.0)
        if confidence < self.min_confidence:
            return None

        # Calculate entry, SL, targets using ATR
        current_price = indicators.get("close", 0)
        if not current_price:
            return None

        atr = indicators.get("atr") or (current_price * 0.005)  # fallback 0.5%
        support, resistance = patterns.get("support", []), patterns.get("resistance", [])

        entry, sl, t1, t2, t3 = self._calculate_levels(
            signal_type, current_price, atr, support, resistance, indicators
        )
        rr_ratio = abs(t1 - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

        if rr_ratio < self.min_rr_ratio:
            return None

        signal = {
            "symbol": symbol,
            "exchange": exchange,
            "signal_type": signal_type,
            "strength": self._get_strength(confidence),
            "confidence": round(confidence, 4),
            "entry_price": round(entry, 2),
            "stop_loss": round(sl, 2),
            "target_1": round(t1, 2),
            "target_2": round(t2, 2) if t2 else None,
            "target_3": round(t3, 2) if t3 else None,
            "risk_reward_ratio": round(rr_ratio, 2),
            "rsi": indicators.get("rsi"),
            "macd": indicators.get("macd"),
            "macd_signal": indicators.get("macd_signal"),
            "vwap": indicators.get("vwap"),
            "ema_9": indicators.get("ema_9"),
            "ema_21": indicators.get("ema_21"),
            "ema_50": indicators.get("ema_50"),
            "adx": indicators.get("adx"),
            "volume_spike": (indicators.get("volume_ratio") or 0) > 1.5,
            "pattern_detected": patterns.get("primary_pattern"),
            "trend": trend,
            "reasons": reasons,
            "institutional_signal": getattr(inst_activity, 'signal', 'NEUTRAL') if inst_activity else "NEUTRAL",
            "generated_at": datetime.utcnow().isoformat(),
        }

        await cache_set(cache_key, signal, ttl=300)  # 5-minute cache
        return signal

    def _score_signals(self, ind: dict, trend: str, patterns: dict, inst_activity) -> tuple:
        """
        Score buy and sell signals based on multiple factors.
        Returns (buy_score, sell_score, reasons_dict).
        """
        buy_score = 0
        sell_score = 0
        reasons = {"buy": [], "sell": []}

        rsi = ind.get("rsi") or 50
        macd = ind.get("macd") or 0
        macd_signal = ind.get("macd_signal") or 0
        prev_macd = ind.get("prev_macd") or 0
        prev_macd_sig = ind.get("prev_macd_signal") or 0
        close = ind.get("close") or 0
        vwap = ind.get("vwap") or 0
        ema_9 = ind.get("ema_9") or 0
        ema_21 = ind.get("ema_21") or 0
        ema_50 = ind.get("ema_50") or 0
        adx = ind.get("adx") or 0
        volume_ratio = ind.get("volume_ratio") or 1.0
        supertrend_dir = ind.get("supertrend_dir")

        # === TREND ===
        if trend == "BULLISH":
            buy_score += 2
            reasons["buy"].append("Bullish trend confirmed")
        elif trend == "BEARISH":
            sell_score += 2
            reasons["sell"].append("Bearish trend confirmed")

        # === RSI ===
        if 40 <= rsi <= 60:
            pass  # Neutral
        elif rsi < 35:
            buy_score += 2
            reasons["buy"].append(f"RSI oversold ({rsi:.1f})")
        elif rsi < 50:
            buy_score += 1
            reasons["buy"].append(f"RSI below 50 ({rsi:.1f})")
        elif rsi > 65:
            sell_score += 2
            reasons["sell"].append(f"RSI overbought ({rsi:.1f})")
        elif rsi > 50:
            sell_score += 1

        # === MACD crossover ===
        macd_cross_up = prev_macd < prev_macd_sig and macd > macd_signal
        macd_cross_down = prev_macd > prev_macd_sig and macd < macd_signal
        if macd_cross_up:
            buy_score += 2
            reasons["buy"].append("MACD bullish crossover")
        elif macd > macd_signal:
            buy_score += 1
        if macd_cross_down:
            sell_score += 2
            reasons["sell"].append("MACD bearish crossover")
        elif macd < macd_signal:
            sell_score += 1

        # === EMA alignment ===
        if close and ema_9 and ema_21 and ema_50:
            if close > ema_9 > ema_21:
                buy_score += 2
                reasons["buy"].append("Price above EMA 9 > EMA 21")
            elif ema_9 > ema_21 > ema_50:
                buy_score += 1
                reasons["buy"].append("Bullish EMA alignment")
            if close < ema_9 < ema_21:
                sell_score += 2
                reasons["sell"].append("Price below EMA 9 < EMA 21")
            elif ema_9 < ema_21 < ema_50:
                sell_score += 1

        # === VWAP ===
        if close and vwap:
            if close > vwap:
                buy_score += 1
                reasons["buy"].append(f"Price above VWAP ({vwap:.2f})")
            else:
                sell_score += 1
                reasons["sell"].append(f"Price below VWAP ({vwap:.2f})")

        # === Supertrend ===
        if supertrend_dir == 1:
            buy_score += 1
            reasons["buy"].append("Supertrend bullish")
        elif supertrend_dir == -1:
            sell_score += 1
            reasons["sell"].append("Supertrend bearish")

        # === ADX (trend strength) ===
        if adx > 25:
            di_plus = ind.get("di_plus") or 0
            di_minus = ind.get("di_minus") or 0
            if di_plus > di_minus:
                buy_score += 1
                reasons["buy"].append(f"Strong uptrend (ADX={adx:.1f})")
            else:
                sell_score += 1
                reasons["sell"].append(f"Strong downtrend (ADX={adx:.1f})")

        # === Volume ===
        if volume_ratio > 2.0:
            reasons["buy" if buy_score >= sell_score else "sell"].append(f"Volume spike {volume_ratio:.1f}x")
            if buy_score >= sell_score:
                buy_score += 1
            else:
                sell_score += 1

        # === Patterns ===
        bullish_patterns = {"BREAKOUT", "BULLISH_ENGULFING", "HAMMER_BULLISH", "BULLISH_MARUBOZU",
                            "CONSECUTIVE_HIGHER_CLOSES", "VWAP_BOUNCE_UP", "INVERTED_HAMMER"}
        bearish_patterns = {"BREAKDOWN", "BEARISH_ENGULFING", "SHOOTING_STAR", "BEARISH_MARUBOZU",
                            "CONSECUTIVE_LOWER_CLOSES", "VWAP_BREAKDOWN"}

        detected = set(patterns.get("patterns", []))
        bull_hits = detected & bullish_patterns
        bear_hits = detected & bearish_patterns

        if bull_hits:
            buy_score += len(bull_hits)
            reasons["buy"].append(f"Patterns: {', '.join(bull_hits)}")
        if bear_hits:
            sell_score += len(bear_hits)
            reasons["sell"].append(f"Patterns: {', '.join(bear_hits)}")

        # === Institutional activity ===
        if inst_activity:
            if inst_activity.signal == "ACCUMULATION":
                buy_score += 2
                reasons["buy"].append(f"Institutional accumulation (delivery: {inst_activity.delivery_percent:.1f}%)")
            elif inst_activity.signal == "DISTRIBUTION":
                sell_score += 2
                reasons["sell"].append("Institutional distribution detected")

        return buy_score, sell_score, reasons

    def _determine_signal_type(self, buy_score: int, sell_score: int) -> tuple:
        """Determine final signal type. Requires significant edge."""
        MIN_SCORE = 5  # At least 5 points to generate a signal
        DOMINANCE = 2  # Must beat other side by at least 2

        if buy_score >= MIN_SCORE and buy_score - sell_score >= DOMINANCE:
            return "BUY", buy_score
        elif sell_score >= MIN_SCORE and sell_score - buy_score >= DOMINANCE:
            return "SELL", sell_score
        return None, 0

    def _calculate_levels(
        self, signal_type: str, price: float, atr: float,
        support: list, resistance: list, indicators: dict
    ) -> tuple:
        """Calculate entry, SL, T1, T2, T3 using ATR and S/R levels."""
        if signal_type == "BUY":
            entry = price  # Enter at current market price / LTP

            # Stop loss: just below nearest support or 1.5x ATR
            if support and abs(price - support[0]) < 2 * atr:
                sl = support[0] - atr * 0.3
            else:
                sl = price - 1.5 * atr

            # Targets based on ATR multiples
            t1 = price + 2.0 * atr
            t2 = price + 3.5 * atr
            t3 = price + 5.0 * atr

            # Adjust t1 to nearest resistance if closer
            if resistance and price < resistance[0] < t1:
                t1 = resistance[0] * 0.998  # Just below resistance

        else:  # SELL
            entry = price
            if resistance and abs(resistance[0] - price) < 2 * atr:
                sl = resistance[0] + atr * 0.3
            else:
                sl = price + 1.5 * atr

            t1 = price - 2.0 * atr
            t2 = price - 3.5 * atr
            t3 = price - 5.0 * atr

            if support and t1 < support[0] < price:
                t1 = support[0] * 1.002

        return entry, sl, t1, t2, t3

    def _get_strength(self, confidence: float) -> str:
        if confidence >= 0.80:
            return "STRONG"
        elif confidence >= 0.70:
            return "MODERATE"
        return "WEAK"

    async def scan_market(
        self, candles_by_symbol: Dict[str, list],
        exchange: str = "NSE"
    ) -> List[dict]:
        """
        Scan multiple symbols and return all valid signals.
        Used for market-wide signal generation.
        """
        tasks = [
            self.generate_signal(symbol, candles, exchange)
            for symbol, candles in candles_by_symbol.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        signals = []
        for r in results:
            if isinstance(r, dict) and r:
                signals.append(r)

        # Sort by confidence descending
        signals.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return signals

    async def get_market_sentiment(self, nifty_candles: list, bank_nifty_candles: list) -> dict:
        """Determine overall market sentiment."""
        nifty_signal = await self.generate_signal("NIFTY50", nifty_candles, include_institutional=False)
        bn_signal = await self.generate_signal("BANKNIFTY", bank_nifty_candles, include_institutional=False)

        nifty_trend = nifty_signal.get("trend", "SIDEWAYS") if nifty_signal else "SIDEWAYS"
        bn_trend = bn_signal.get("trend", "SIDEWAYS") if bn_signal else "SIDEWAYS"

        bullish_count = sum(1 for t in [nifty_trend, bn_trend] if t == "BULLISH")
        bearish_count = sum(1 for t in [nifty_trend, bn_trend] if t == "BEARISH")

        if bullish_count >= 2:
            sentiment = "BULLISH"
        elif bearish_count >= 2:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"

        return {
            "market_sentiment": sentiment,
            "nifty_trend": nifty_trend,
            "bank_nifty_trend": bn_trend,
        }
