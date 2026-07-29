# -*- coding: utf-8 -*-
"""
🟢 FINVISTA: CREED MASTER GRID REGIME DETECTOR
=============================================
Native Python implementation of the Creed Master Grid trend & phase detection logic.
Replaces the external HMM model with a robust, zero-lag Master Trend & Volatility Grid.

Parameters:
  - trend_period: 240 (Master Trend EMA)
  - fast_period: 10
  - slow_period: 20
  - atr_period: 14

Author: samvo
"""
import pandas as pd
import numpy as np
from typing import Dict, Any


def calculate_creed_regime_from_df(df: pd.DataFrame, trend_period: int = 200) -> Dict[str, Any]:
    """
    Calculates Master Trend Grid Phase (BULL / BEAR / SIDEWAYS) from OHLCV dataframe.
    """
    if df is None or df.empty or len(df) < 20:
        return {
            "status": "ok",
            "source": "Creed Master Grid Engine (Fallback)",
            "regime": "SIDEWAYS",
            "bias": "NEUTRAL",
            "confidence": 0.5,
            "description": "Dữ liệu chưa đủ để tính toán Creed Grid",
        }

    df = df.copy()
    if 'close' not in df.columns and 'Close' in df.columns:
        df['close'] = df['Close']
    if 'high' not in df.columns and 'High' in df.columns:
        df['high'] = df['High']
    if 'low' not in df.columns and 'Low' in df.columns:
        df['low'] = df['Low']

    closes = df['close'].values
    highs = df['high'].values if 'high' in df.columns else closes
    lows = df['low'].values if 'low' in df.columns else closes

    n = len(closes)
    effective_trend_period = min(trend_period, max(20, n // 2))

    # 1. Master Trend Line (EMA)
    ema_trend = pd.Series(closes).ewm(span=effective_trend_period, adjust=False).mean().values
    ema10 = pd.Series(closes).ewm(span=10, adjust=False).mean().values
    ema20 = pd.Series(closes).ewm(span=20, adjust=False).mean().values

    # 2. Average True Range (ATR 14)
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    closes = np.asarray(closes, dtype=float)

    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1]))
    )
    tr = np.insert(tr, 0, highs[0] - lows[0])
    atr14 = pd.Series(tr, dtype=float).rolling(window=14, min_periods=1).mean().values

    latest_close = closes[-1]
    latest_trend = ema_trend[-1]
    latest_ema10 = ema10[-1]
    latest_ema20 = ema20[-1]
    latest_atr = atr14[-1]

    # Calculate Trend Slope & Distance
    dist_pct = (latest_close - latest_trend) / latest_trend
    momentum_bull = (latest_close > latest_trend) and (latest_ema10 > latest_ema20)
    momentum_bear = (latest_close < latest_trend) and (latest_ema10 < latest_ema20)

    # Determine Phase
    if momentum_bull and dist_pct > 0.005:
        regime = "BULLISH_VOL_EXPANSION"
        bias = "LONG_CW"
        confidence = min(0.98, 0.6 + abs(dist_pct) * 5)
        description = f"Creed Master Grid: PHASE BULL (Tăng giá - Giá {latest_close:,.0f} nằm trên Master Trend {latest_trend:,.0f})"
    elif momentum_bear or dist_pct < -0.005:
        regime = "BEARISH_HIGH_VOL"
        bias = "SKIP_CW"
        confidence = min(0.98, 0.6 + abs(dist_pct) * 5)
        description = f"Creed Master Grid: PHASE BEAR (Giảm giá / Rủi ro - Giá {latest_close:,.0f} nằm dưới Master Trend {latest_trend:,.0f})"
    else:
        regime = "SIDEWAYS"
        bias = "NEUTRAL"
        confidence = 0.70
        description = f"Creed Master Grid: PHASE SIDEWAYS (Đi ngang xung quanh dải Master Trend {latest_trend:,.0f})"

    phase = "BULL" if "BULL" in regime else ("BEAR" if "BEAR" in regime else "SIDEWAYS")
    layer = "ACTIVATE" if bias == "LONG_CW" else ("PAUSE" if bias == "SKIP_CW" else "NEUTRAL")

    latest_date_val = df['date'].iloc[-1] if 'date' in df.columns and len(df) > 0 else None
    latest_date_str = "23/07/2026"
    if latest_date_val is not None:
        try:
            parts = str(latest_date_val).split(" ")[0].split("-")
            if len(parts) == 3:
                latest_date_str = f"{parts[2]}/{parts[1]}/{parts[0]}"
            else:
                latest_date_str = str(latest_date_val)
        except Exception:
            latest_date_str = str(latest_date_val)

    return {
        "status": "ok",
        "source": "Creed Master Grid Engine (Native)",
        "regime": regime,
        "phase": phase,
        "layer": layer,
        "bias": bias,
        "confidence": round(float(confidence), 2),
        "description": description,
        "master_trend": round(float(latest_trend), 2),
        "dist_from_trend_pct": round(float(dist_pct * 100), 2),
        "atr14": round(float(latest_atr), 2),
        "latest_close": round(float(latest_close), 2),
        "updated_at": latest_date_str,
    }


def calculate_creed_vnindex_regime(days: int = 500) -> Dict[str, Any]:
    """
    Fetches VNINDEX OHLCV history from database and computes native Creed Master Grid regime.
    """
    from src.core.database import engine
    query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol IN ('VNINDEX', 'VN-INDEX', 'VNINDEX.VN') ORDER BY date DESC LIMIT {days}"
    try:
        df = pd.read_sql(query, engine)
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        # Fallback to fetching any available market symbol or stock index
        query_fallback = f"SELECT date, open, high, low, close, volume FROM stock_history ORDER BY date DESC LIMIT {days}"
        try:
            df = pd.read_sql(query_fallback, engine)
            if not df.empty:
                df = df.iloc[::-1].reset_index(drop=True)
        except Exception:
            df = pd.DataFrame()

    return calculate_creed_regime_from_df(df, trend_period=200)
