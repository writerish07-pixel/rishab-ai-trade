"""
Real-time technical indicator calculation engine.
Uses pandas-ta for all indicators. Operates on OHLCV DataFrames.
"""
import logging
from typing import Optional
import pandas as pd
import numpy as np
import pandas_ta as ta

logger = logging.getLogger(__name__)


def build_dataframe(candles: list) -> Optional[pd.DataFrame]:
    """Convert list of OHLCData to a pandas DataFrame."""
    if not candles or len(candles) < 5:
        return None
    records = []
    for c in candles:
        if hasattr(c, "dict"):
            records.append(c.dict())
        else:
            records.append(c)
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
    df["Open"] = df["Open"].astype(float)
    df["High"] = df["High"].astype(float)
    df["Low"] = df["Low"].astype(float)
    df["Close"] = df["Close"].astype(float)
    df["Volume"] = df["Volume"].astype(float)
    return df


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators and append to DataFrame."""
    if df is None or len(df) < 14:
        return df

    try:
        # Moving averages
        df["EMA_9"] = ta.ema(df["Close"], length=9)
        df["EMA_21"] = ta.ema(df["Close"], length=21)
        df["EMA_50"] = ta.ema(df["Close"], length=50)
        df["EMA_200"] = ta.ema(df["Close"], length=200)
        df["SMA_20"] = ta.sma(df["Close"], length=20)

        # RSI
        df["RSI"] = ta.rsi(df["Close"], length=14)

        # MACD
        macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            df["MACD"] = macd["MACD_12_26_9"]
            df["MACD_Signal"] = macd["MACDs_12_26_9"]
            df["MACD_Hist"] = macd["MACDh_12_26_9"]

        # Bollinger Bands
        bb = ta.bbands(df["Close"], length=20, std=2)
        if bb is not None and not bb.empty:
            df["BB_Upper"] = bb["BBU_20_2.0"]
            df["BB_Middle"] = bb["BBM_20_2.0"]
            df["BB_Lower"] = bb["BBL_20_2.0"]
            df["BB_Width"] = bb["BBB_20_2.0"]

        # VWAP (volume-weighted average price)
        df["VWAP"] = _calculate_vwap(df)

        # ATR
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)

        # Stochastic
        stoch = ta.stoch(df["High"], df["Low"], df["Close"], k=14, d=3, smooth_k=3)
        if stoch is not None and not stoch.empty:
            df["Stoch_K"] = stoch.iloc[:, 0]
            df["Stoch_D"] = stoch.iloc[:, 1]

        # Supertrend
        st = ta.supertrend(df["High"], df["Low"], df["Close"], length=10, multiplier=3)
        if st is not None and not st.empty:
            df["Supertrend"] = st.iloc[:, 0]
            df["Supertrend_Dir"] = st.iloc[:, 1]  # 1 = bullish, -1 = bearish

        # ADX — trend strength
        adx = ta.adx(df["High"], df["Low"], df["Close"], length=14)
        if adx is not None and not adx.empty:
            df["ADX"] = adx["ADX_14"]
            df["DI_Plus"] = adx["DMP_14"]
            df["DI_Minus"] = adx["DMN_14"]

        # Volume indicators
        df["Volume_SMA_20"] = ta.sma(df["Volume"], length=20)
        df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA_20"].replace(0, np.nan)
        df["OBV"] = ta.obv(df["Close"], df["Volume"])

        # Momentum
        df["ROC"] = ta.roc(df["Close"], length=9)
        df["CCI"] = ta.cci(df["High"], df["Low"], df["Close"], length=14)

    except Exception as e:
        logger.error(f"Indicator calculation error: {e}")

    return df


def _calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Intraday VWAP reset each day."""
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cumulative_pv = (typical_price * df["Volume"]).cumsum()
    cumulative_v = df["Volume"].cumsum()
    return cumulative_pv / cumulative_v.replace(0, np.nan)


def get_latest_indicators(df: pd.DataFrame) -> dict:
    """Extract latest indicator values from the DataFrame."""
    if df is None or df.empty:
        return {}

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    def safe_float(val, decimals=2):
        try:
            return round(float(val), decimals) if not pd.isna(val) else None
        except Exception:
            return None

    return {
        "close": safe_float(last["Close"]),
        "open": safe_float(last["Open"]),
        "high": safe_float(last["High"]),
        "low": safe_float(last["Low"]),
        "volume": safe_float(last["Volume"], 0),
        "ema_9": safe_float(last.get("EMA_9")),
        "ema_21": safe_float(last.get("EMA_21")),
        "ema_50": safe_float(last.get("EMA_50")),
        "ema_200": safe_float(last.get("EMA_200")),
        "sma_20": safe_float(last.get("SMA_20")),
        "rsi": safe_float(last.get("RSI")),
        "macd": safe_float(last.get("MACD")),
        "macd_signal": safe_float(last.get("MACD_Signal")),
        "macd_hist": safe_float(last.get("MACD_Hist")),
        "bb_upper": safe_float(last.get("BB_Upper")),
        "bb_middle": safe_float(last.get("BB_Middle")),
        "bb_lower": safe_float(last.get("BB_Lower")),
        "bb_width": safe_float(last.get("BB_Width")),
        "vwap": safe_float(last.get("VWAP")),
        "atr": safe_float(last.get("ATR")),
        "adx": safe_float(last.get("ADX")),
        "di_plus": safe_float(last.get("DI_Plus")),
        "di_minus": safe_float(last.get("DI_Minus")),
        "supertrend_dir": safe_float(last.get("Supertrend_Dir")),
        "stoch_k": safe_float(last.get("Stoch_K")),
        "stoch_d": safe_float(last.get("Stoch_D")),
        "obv": safe_float(last.get("OBV"), 0),
        "roc": safe_float(last.get("ROC")),
        "cci": safe_float(last.get("CCI")),
        "volume_ratio": safe_float(last.get("Volume_Ratio")),
        # Prev values for crossover detection
        "prev_macd": safe_float(prev.get("MACD")),
        "prev_macd_signal": safe_float(prev.get("MACD_Signal")),
        "prev_ema_9": safe_float(prev.get("EMA_9")),
        "prev_ema_21": safe_float(prev.get("EMA_21")),
        "prev_rsi": safe_float(prev.get("RSI")),
    }


def detect_trend(df: pd.DataFrame) -> str:
    """Determine overall market trend: BULLISH / BEARISH / SIDEWAYS."""
    if df is None or len(df) < 50:
        return "SIDEWAYS"
    ind = get_latest_indicators(df)
    score = 0

    # EMA alignment
    if ind.get("ema_9") and ind.get("ema_21") and ind.get("ema_50"):
        if ind["ema_9"] > ind["ema_21"] > ind["ema_50"]:
            score += 2   # Strong bullish alignment
        elif ind["ema_9"] < ind["ema_21"] < ind["ema_50"]:
            score -= 2   # Strong bearish alignment

    # Price vs VWAP
    close = ind.get("close", 0)
    vwap = ind.get("vwap", 0)
    if close and vwap:
        if close > vwap:
            score += 1
        else:
            score -= 1

    # ADX + DI
    adx = ind.get("adx", 0)
    if adx and adx > 25:
        if (ind.get("di_plus") or 0) > (ind.get("di_minus") or 0):
            score += 1
        else:
            score -= 1

    # Supertrend
    st_dir = ind.get("supertrend_dir")
    if st_dir == 1:
        score += 1
    elif st_dir == -1:
        score -= 1

    # RSI momentum
    rsi = ind.get("rsi", 50)
    if rsi:
        if rsi > 60:
            score += 1
        elif rsi < 40:
            score -= 1

    if score >= 3:
        return "BULLISH"
    elif score <= -3:
        return "BEARISH"
    return "SIDEWAYS"
