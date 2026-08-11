# -*- coding: utf-8 -*-
"""
🚀 FINVISTA: UNDERLYING MOMENTUM ENRICHER
==========================================
Computes momentum signals for underlying stocks and injects them into the CW DataFrame.
Also provides HMM-based auto strategy selection.

Author: Antigravity / samvo
Version: 1.0
"""

from __future__ import annotations

import os
import warnings
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# 1. MOMENTUM COMPUTATION
# ──────────────────────────────────────────────────────────────────────────────

def _compute_rsi(prices: pd.Series, period: int = 14) -> float:
    """Exponential-smoothed RSI (Wilder method)."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss
    return float((100 - 100 / (1 + rs)).iloc[-1])


def compute_underlying_momentum_map(
    underlyings: list[str], as_of_date: str | datetime | None = None
) -> dict[str, dict]:
    """
    For each underlying symbol, load price history from DB up to as_of_date and compute:
    - r5, r20, r60, r120  (log returns in %)
    - rsi14               (Wilder RSI)
    - vol_ratio_5v20      (Volume ratio last 5 vs prior 20 sessions)
    - ma_align_score      (0/33/67/100 – how many of MA20/50/120 are below price)
    - momentum_score      (weighted composite: 35%×r20 + 45%×r60 + 20%×r5, normalised to 0-100)
    - distance_from_hi52  (% below 52-week high – lower = more stretched)

    Returns: dict mapping symbol → metrics dict
    """
    try:
        import sqlite3
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir and not os.path.exists(os.path.join(current_dir, "data")):
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent
        db_path = os.path.join(current_dir, "data", "finvista.db")
    except Exception:
        db_path = os.path.join("data", "finvista.db")

    if not os.path.exists(db_path):
        return {}

    conn = sqlite3.connect(db_path)
    try:
        placeholders = ",".join("?" * len(underlyings))
        if as_of_date:
            date_str = as_of_date.strftime('%Y-%m-%d') if hasattr(as_of_date, 'strftime') else str(as_of_date)
            df = pd.read_sql(
                f"SELECT date, symbol, close, volume FROM stock_history "
                f"WHERE symbol IN ({placeholders}) AND date <= ? ORDER BY date ASC",
                conn,
                params=underlyings + [date_str],
            )
        else:
            df = pd.read_sql(
                f"SELECT date, symbol, close, volume FROM stock_history "
                f"WHERE symbol IN ({placeholders}) ORDER BY date ASC",
                conn,
                params=underlyings,
            )
    except Exception:
        conn.close()
        return {}
    conn.close()

    df["date"] = pd.to_datetime(df["date"])
    result: dict[str, dict] = {}

    for symbol, grp in df.groupby("symbol"):
        grp = grp.sort_values("date").reset_index(drop=True)
        n = len(grp)
        if n < 61:
            continue  # need at least 60 sessions

        prices = grp["close"]
        vols = grp["volume"]
        latest = float(prices.iloc[-1])

        # ── Returns ──────────────────────────────────────────────────
        r5  = (latest / float(prices.iloc[-6])  - 1) * 100 if n >= 6  else 0.0
        r20 = (latest / float(prices.iloc[-21]) - 1) * 100 if n >= 21 else 0.0
        r60 = (latest / float(prices.iloc[-61]) - 1) * 100 if n >= 61 else 0.0
        r120 = (latest / float(prices.iloc[-121]) - 1) * 100 if n >= 121 else r60

        # ── RSI ───────────────────────────────────────────────────────
        rsi = _compute_rsi(prices) if n >= 20 else 50.0

        # ── Volume Ratio (5-day vs prior 20) ─────────────────────────
        vol5  = float(vols.iloc[-5:].mean()) if n >= 5 else 1.0
        vol20 = float(vols.iloc[-25:-5].mean()) if n >= 25 else vol5
        vol_ratio = vol5 / vol20 if vol20 > 0 else 1.0

        # ── MA Alignment ──────────────────────────────────────────────
        ma20  = float(prices.tail(20).mean())
        ma50  = float(prices.tail(50).mean()) if n >= 50 else ma20
        ma120 = float(prices.tail(120).mean()) if n >= 120 else ma50
        ma_count = sum([latest > ma20, latest > ma50, latest > ma120])
        ma_align_score = ma_count / 3 * 100  # 0 / 33 / 67 / 100

        # ── Distance to Support (MA20) ────────────────────────────────
        dist_ma20 = (latest / ma20 - 1) * 100 if ma20 > 0 else 0.0

        # ── 52-week high distance ─────────────────────────────────────
        hi52 = float(prices.tail(252).max())
        dist_from_hi = (latest / hi52 - 1) * 100  # negative → below high

        # ── Composite Momentum Score (0 – 100) ────────────────────────
        # Anchored: r60D drives the trend thesis most
        raw_mom = 0.20 * r5 + 0.35 * r20 + 0.45 * r60
        # Normalize: treat [-10, +30] as [0, 100] range
        mom_score = (raw_mom + 10) / 40 * 100
        mom_score = float(np.clip(mom_score, 0, 100))

        result[symbol] = {
            "r5": round(r5, 3),
            "r20": round(r20, 3),
            "r60": round(r60, 3),
            "r120": round(r120, 3),
            "rsi": round(rsi, 1),
            "vol_ratio": round(vol_ratio, 3),
            "ma_align_score": round(ma_align_score, 1),
            "mom_score": round(mom_score, 1),
            "dist_from_hi52": round(dist_from_hi, 2),
            "dist_ma20": round(dist_ma20, 2),
        }

    return result


def enrich_with_underlying_momentum(df: pd.DataFrame, include_chart_patterns: bool = True) -> pd.DataFrame:
    """
    Adds momentum columns to the CW DataFrame.
    Looks up underlying symbol from column 'B_MaCPCS'.
    New columns added:
      und_r5, und_r20, und_r60, und_r120,
      und_rsi, und_vol_ratio, und_ma_align,
      und_mom_score, und_dist_from_hi52,
      und_dist_ma20, und_chart_pattern_score (if include_chart_patterns)
    """
    if df.empty:
        return df

    underlying_col = "B_MaCPCS" if "B_MaCPCS" in df.columns else "underlying"
    if underlying_col not in df.columns:
        return df

    # Check for date column
    date_col = None
    for c in ["date", "Date", "A_Ngay", "date_dt"]:
        if c in df.columns:
            date_col = c
            break

    fields = ["r5", "r20", "r60", "r120", "rsi", "vol_ratio", "ma_align_score", "mom_score", "dist_from_hi52", "dist_ma20"]
    defaults = [0.0, 0.0, 0.0, 0.0, 50.0, 1.0, 0.0, 50.0, -5.0, 0.0]

    # If df has multiple unique dates, process day by day to prevent lookahead bias
    if date_col and df[date_col].nunique() > 1:
        res_dfs = []
        for date_val, grp_date in df.groupby(date_col):
            underlyings = grp_date[underlying_col].dropna().unique().tolist()
            mom_map = compute_underlying_momentum_map(underlyings, as_of_date=date_val)
            
            grp_res = grp_date.copy()
            for field, default in zip(fields, defaults):
                grp_res[f"und_{field}"] = grp_res[underlying_col].map(
                    lambda s, f=field, d=default: mom_map.get(s, {}).get(f, d)
                )
            res_dfs.append(grp_res)
        return pd.concat(res_dfs, ignore_index=True)
    else:
        single_date = df[date_col].iloc[0] if date_col and not df[date_col].empty else None
        underlyings = df[underlying_col].dropna().unique().tolist()
        mom_map = compute_underlying_momentum_map(underlyings, as_of_date=single_date)

        res = df.copy()
        for field, default in zip(fields, defaults):
            res[f"und_{field}"] = res[underlying_col].map(
                lambda s, f=field, d=default: mom_map.get(s, {}).get(f, d)
            )
        
        # Add chart pattern score if requested
        if include_chart_patterns:
            try:
                # Use enhanced advanced support detection for better accuracy
                from backend.modules.cw_pricing.analysis import get_advanced_support_analysis
                chart_pattern_map = {}
                
                for underlying in underlyings:
                    try:
                        # Get advanced support analysis with K-means clustering
                        support_analysis = get_advanced_support_analysis(underlying, days=60)
                        score = support_analysis["score"]
                        chart_pattern_map[underlying] = score
                    except Exception as e:
                        chart_pattern_map[underlying] = 50.0  # default neutral
                
                res["und_chart_pattern_score"] = res[underlying_col].map(
                    lambda s: chart_pattern_map.get(s, 50.0)
                )
            except Exception as e:
                # Fallback: set all to neutral if enhanced analysis fails
                res["und_chart_pattern_score"] = 50.0
            except Exception as e:
                # Fallback to neutral if chart pattern analysis fails
                res["und_chart_pattern_score"] = 50.0
        
        return res


# ──────────────────────────────────────────────────────────────────────────────
# 2. HMM AUTO-REGIME → STRATEGY SELECTOR
# ──────────────────────────────────────────────────────────────────────────────

_STRATEGY_OVERRIDE_CACHE: dict = {}


def auto_select_strategy(requested_strategy: str = "balanced") -> str:
    """
    Reads the latest HMM regime from stock_history VNINDEX data and overrides the
    requested strategy if the market is clearly in a different regime.

    Regime → Strategy mapping:
        Bullish Low Vol  (state 0, Sharpe > 3) → 'aggressive'  (momentum mode)
        Bullish High Vol (state 1)              → 'balanced'    (vol is high, stay balanced)
        Bearish Low Vol  (state 2)              → 'safe'        (reduce exposure)
        Bearish Crisis   (state 3)              → 'safe'        (capital preservation)

    If HMM detection fails, returns the requested_strategy unchanged.
    """
    global _STRATEGY_OVERRIDE_CACHE

    try:
        import sqlite3
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir and not os.path.exists(os.path.join(current_dir, "data")):
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent
        db_path = os.path.join(current_dir, "data", "finvista.db")
    except Exception:
        db_path = os.path.join("data", "finvista.db")

    # ── Load VNINDEX history ───────────────────────────────────────────────────
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql(
            "SELECT date, close, volume FROM stock_history "
            "WHERE symbol='VNINDEX' ORDER BY date ASC",
            conn,
        )
        conn.close()
    except Exception:
        return requested_strategy

    if df.empty or len(df) < 60:
        return requested_strategy

    # ── Compute features for HMM ─────────────────────────────────────────────
    try:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["log_ret"] = np.log(df["close"] / df["close"].shift(1)).fillna(0)
        df["rolling_vol"] = df["log_ret"].rolling(20, min_periods=5).std() * np.sqrt(252)
        df["vol_ma50"] = df["close"].rolling(50, min_periods=10).mean()
        df["trend"] = (df["close"] > df["vol_ma50"]).astype(int)
        df = df.dropna(subset=["log_ret", "rolling_vol", "trend"])

        from backend.modules.regime_analysis.portfolio.regime_model import fit_vnindex_hmm, prepare_vnindex_features

        features_df = prepare_vnindex_features(df)
        hybrid_model, _ = fit_vnindex_hmm(features_df)
        last_state = int(hybrid_model.predict(features_df)[-1])
        last_prob = float(hybrid_model.predict_proba(features_df)[-1][last_state])
    except Exception:
        return requested_strategy

    # ── Map state → strategy ─────────────────────────────────────────────────
    STATE_STRATEGY = {
        0: "aggressive",  # Bullish Low Vol
        1: "balanced",    # Bullish High Vol (volatile)
        2: "safe",        # Bearish Low Vol
        3: "safe",        # Bearish Crisis
    }
    STATE_LABEL = {
        0: "Bullish (Low Vol)",
        1: "Bullish (High Vol)",
        2: "Bearish (Low Vol)",
        3: "Bearish Crisis",
    }

    # Only override if probability is high enough (> 0.60) to avoid noise
    hmm_strategy = STATE_STRATEGY.get(last_state, requested_strategy)
    label = STATE_LABEL.get(last_state, "Unknown")

    if last_prob >= 0.60:
        print(
            f"🔮 [HMM Auto-Strategy] Detected regime: {label} (State {last_state}, "
            f"P={last_prob:.1%}) → Strategy override: '{requested_strategy}' → '{hmm_strategy}'"
        )
        return hmm_strategy
    else:
        print(
            f"🔮 [HMM Auto-Strategy] Regime uncertain (State {last_state}, P={last_prob:.1%}). "
            f"Keeping requested strategy: '{requested_strategy}'"
        )
        return requested_strategy
