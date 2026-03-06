"""
Pattern detection engine for price action patterns:
Breakouts, Breakdowns, Gap Up/Down, Support/Resistance, Volume Spikes, etc.
"""
import logging
from typing import Optional, List, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PatternDetector:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.patterns: List[str] = []
        self.support_levels: List[float] = []
        self.resistance_levels: List[float] = []

    def detect_all(self) -> dict:
        """Run all pattern detection algorithms."""
        if self.df is None or len(self.df) < 20:
            return {"patterns": [], "support": [], "resistance": []}

        self._find_support_resistance()
        self._detect_breakout()
        self._detect_breakdown()
        self._detect_gap()
        self._detect_volume_spike()
        self._detect_momentum_patterns()
        self._detect_candle_patterns()

        return {
            "patterns": self.patterns,
            "support": self.support_levels[:3],
            "resistance": self.resistance_levels[:3],
            "primary_pattern": self.patterns[0] if self.patterns else None,
        }

    def _find_support_resistance(self, window: int = 10, strength: int = 3):
        """Identify support and resistance using pivot points."""
        highs = self.df["High"].values
        lows = self.df["Low"].values
        n = len(highs)

        pivot_highs = []
        pivot_lows = []

        for i in range(window, n - window):
            if all(highs[i] >= highs[i - j] for j in range(1, window + 1)) and \
               all(highs[i] >= highs[i + j] for j in range(1, window + 1)):
                pivot_highs.append(highs[i])
            if all(lows[i] <= lows[i - j] for j in range(1, window + 1)) and \
               all(lows[i] <= lows[i + j] for j in range(1, window + 1)):
                pivot_lows.append(lows[i])

        # Cluster nearby levels
        current_price = float(self.df["Close"].iloc[-1])
        self.resistance_levels = sorted([r for r in pivot_highs if r > current_price])[:5]
        self.support_levels = sorted([s for s in pivot_lows if s < current_price], reverse=True)[:5]

    def _detect_breakout(self):
        """Detect price breakout above resistance with volume confirmation."""
        if not self.resistance_levels:
            return
        last_close = float(self.df["Close"].iloc[-1])
        volume_ratio = self.df["Volume_Ratio"].iloc[-1] if "Volume_Ratio" in self.df.columns else 1.0

        nearest_resistance = self.resistance_levels[0] if self.resistance_levels else None
        if nearest_resistance and last_close > nearest_resistance and (volume_ratio or 0) > 1.5:
            self.patterns.append("BREAKOUT")
            self.patterns.append(f"BREAKOUT_ABOVE_{nearest_resistance:.2f}")

    def _detect_breakdown(self):
        """Detect price breakdown below support with volume confirmation."""
        if not self.support_levels:
            return
        last_close = float(self.df["Close"].iloc[-1])
        volume_ratio = self.df["Volume_Ratio"].iloc[-1] if "Volume_Ratio" in self.df.columns else 1.0

        nearest_support = self.support_levels[0] if self.support_levels else None
        if nearest_support and last_close < nearest_support and (volume_ratio or 0) > 1.5:
            self.patterns.append("BREAKDOWN")
            self.patterns.append(f"BREAKDOWN_BELOW_{nearest_support:.2f}")

    def _detect_gap(self):
        """Detect gap up / gap down on open vs previous close."""
        if len(self.df) < 2:
            return
        today_open = float(self.df["Open"].iloc[-1])
        prev_close = float(self.df["Close"].iloc[-2])
        if prev_close == 0:
            return

        gap_pct = ((today_open - prev_close) / prev_close) * 100
        if gap_pct >= 1.0:
            self.patterns.append(f"GAP_UP_{gap_pct:.1f}%")
        elif gap_pct <= -1.0:
            self.patterns.append(f"GAP_DOWN_{abs(gap_pct):.1f}%")

    def _detect_volume_spike(self):
        """Detect unusual volume activity (2x+ average)."""
        if "Volume_Ratio" not in self.df.columns:
            return
        vol_ratio = self.df["Volume_Ratio"].iloc[-1]
        if pd.isna(vol_ratio):
            return
        if vol_ratio >= 3.0:
            self.patterns.append("EXTREME_VOLUME_SPIKE")
        elif vol_ratio >= 2.0:
            self.patterns.append("VOLUME_SPIKE")

    def _detect_momentum_patterns(self):
        """Detect momentum-based patterns."""
        if len(self.df) < 3:
            return

        closes = self.df["Close"].values
        last = closes[-1]
        prev = closes[-2]
        prev2 = closes[-3]

        # Consecutive higher closes (momentum building)
        if last > prev > prev2:
            self.patterns.append("CONSECUTIVE_HIGHER_CLOSES")

        # Consecutive lower closes
        if last < prev < prev2:
            self.patterns.append("CONSECUTIVE_LOWER_CLOSES")

        # VWAP bounce
        if "VWAP" in self.df.columns:
            vwap = self.df["VWAP"].iloc[-1]
            if not pd.isna(vwap):
                if prev < vwap and last > vwap:
                    self.patterns.append("VWAP_BOUNCE_UP")
                elif prev > vwap and last < vwap:
                    self.patterns.append("VWAP_BREAKDOWN")

    def _detect_candle_patterns(self):
        """Detect Japanese candlestick patterns."""
        if len(self.df) < 3:
            return
        last = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        body = abs(last["Close"] - last["Open"])
        range_ = last["High"] - last["Low"]
        upper_wick = last["High"] - max(last["Open"], last["Close"])
        lower_wick = min(last["Open"], last["Close"]) - last["Low"]

        if range_ == 0:
            return

        body_ratio = body / range_

        # Doji
        if body_ratio < 0.1:
            self.patterns.append("DOJI")

        # Hammer / Hanging Man
        if lower_wick > 2 * body and upper_wick < 0.1 * range_:
            if last["Close"] > last["Open"]:
                self.patterns.append("HAMMER_BULLISH")
            else:
                self.patterns.append("HANGING_MAN")

        # Shooting Star / Inverted Hammer
        if upper_wick > 2 * body and lower_wick < 0.1 * range_:
            if last["Close"] < last["Open"]:
                self.patterns.append("SHOOTING_STAR")
            else:
                self.patterns.append("INVERTED_HAMMER")

        # Engulfing patterns
        prev_body = abs(prev["Close"] - prev["Open"])
        if body > prev_body:
            if last["Close"] > last["Open"] and prev["Close"] < prev["Open"]:
                self.patterns.append("BULLISH_ENGULFING")
            elif last["Close"] < last["Open"] and prev["Close"] > prev["Open"]:
                self.patterns.append("BEARISH_ENGULFING")

        # Marubozu (strong candle, no wicks)
        if body_ratio > 0.9:
            if last["Close"] > last["Open"]:
                self.patterns.append("BULLISH_MARUBOZU")
            else:
                self.patterns.append("BEARISH_MARUBOZU")


def get_support_resistance(df: pd.DataFrame) -> Tuple[List[float], List[float]]:
    """Quick helper to get S/R levels."""
    detector = PatternDetector(df)
    detector._find_support_resistance()
    return detector.support_levels, detector.resistance_levels
