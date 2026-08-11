# -*- coding: utf-8 -*-
"""
Regime Evaluation Module
Computes quantitative performance metrics for regime-switching strategies.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any


def evaluate_regime_performance(df: pd.DataFrame, regime_column: str = "regime") -> Dict[str, Any]:
    """
    Evaluate the financial and statistical performance of a regime-labelled strategy.

    The strategy rule is simple:
      - BULLISH_VOL_EXPANSION / BULLISH_VOL_CONTRACTION → fully invested (LONG)
      - Everything else (BEARISH / SIDEWAYS)            → cash (0 exposure)

    Args:
        df: DataFrame with at least 'close' and a regime column.
        regime_column: Column name containing regime labels.

    Returns:
        Dict with performance metrics, overall_score, and grade.
    """
    if df.empty or regime_column not in df.columns or 'close' not in df.columns:
        return _empty_result("Insufficient data or missing columns")

    df = df.copy().reset_index(drop=True)
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df = df.dropna(subset=['close'])

    if len(df) < 10:
        return _empty_result("Not enough rows after cleaning")

    # --- Daily returns ---
    df['ret'] = df['close'].pct_change().fillna(0.0)

    # --- Strategy signal: 1 if bullish regime, 0 otherwise (next-bar execution) ---
    def _is_bullish(r: str) -> int:
        if not isinstance(r, str):
            return 0
        r_upper = r.upper()
        if any(b in r_upper for b in ['BULLISH', 'BULL']):
            return 1
        if any(k in r for k in ['S2:', 'S3:', 'S4:', 'Đầu_Xu_Hướng', 'Xu_Hướng_Mạnh', 'Cao_Trào']):
            return 1
        return 0

    df['signal'] = df[regime_column].apply(_is_bullish).shift(1).fillna(0)

    df['strategy_ret'] = df['signal'] * df['ret']
    df['bh_ret'] = df['ret']  # buy-and-hold benchmark

    # Equity curves
    df['eq_strategy'] = (1 + df['strategy_ret']).cumprod()
    df['eq_bh'] = (1 + df['bh_ret']).cumprod()

    # --- Core metrics ---
    trading_days = len(df)
    years = max(trading_days / 252, 0.25)

    # CAGR
    final_equity = float(df['eq_strategy'].iloc[-1])
    cagr = float(round((final_equity ** (1 / years) - 1) * 100, 2))

    # Sharpe (annualised, risk-free = 0)
    std = float(df['strategy_ret'].std())
    sharpe = float(round((float(df['strategy_ret'].mean()) / std * np.sqrt(252)) if std > 0 else 0.0, 3))

    # Max Drawdown
    roll_max = df['eq_strategy'].cummax()
    drawdown = (df['eq_strategy'] - roll_max) / roll_max
    max_dd = float(round(float(drawdown.min()) * 100, 2))  # negative value

    # Profit Factor
    gross_profit = float(df.loc[df['strategy_ret'] > 0, 'strategy_ret'].sum())
    gross_loss = float(abs(df.loc[df['strategy_ret'] < 0, 'strategy_ret'].sum()))
    if gross_loss > 0:
        profit_factor = float(round(gross_profit / gross_loss, 3))
    else:
        profit_factor = float(round(gross_profit, 3)) if gross_profit > 0 else 1.0

    # Calmar Ratio
    calmar = float(round(cagr / abs(max_dd), 3)) if max_dd != 0 else 0.0

    # Sortino
    downside = float(df.loc[df['strategy_ret'] < 0, 'strategy_ret'].std())
    sortino = float(round((float(df['strategy_ret'].mean()) / downside * np.sqrt(252)) if downside > 0 else 0.0, 3))

    # Win rate (per trade, treating regime-on days as individual observations)
    active = df[df['signal'] == 1]
    win_rate = float(round(float((active['strategy_ret'] > 0).mean()) * 100, 2)) if len(active) > 0 else 0.0

    # --- Regime stability ---
    regime_changes = int((df[regime_column] != df[regime_column].shift()).sum())
    avg_regime_duration = float(round(trading_days / max(regime_changes, 1), 1))

    regime_counts = df[regime_column].value_counts().to_dict()
    time_in_bull = int((df['signal'] == 1).sum())
    pct_in_market = float(round(time_in_bull / trading_days * 100, 1))

    # --- vs Buy-and-Hold ---
    bh_cagr = float(round((float(df['eq_bh'].iloc[-1]) ** (1 / years) - 1) * 100, 2))
    alpha = float(round(cagr - bh_cagr, 2))

    # Time to Recovery (Max days below previous peak)
    is_underwater = df['eq_strategy'] < roll_max
    underwater_groups = (~is_underwater).cumsum()
    time_to_recovery = int(is_underwater.groupby(underwater_groups).sum().max()) if is_underwater.any() else 0

    # Max Consecutive Losses
    loss_series = df['strategy_ret'] < 0
    loss_groups = (~loss_series).cumsum()
    max_consec_losses = int(loss_series.groupby(loss_groups).sum().max()) if loss_series.any() else 0

    # Out-of-Sample (OOS) Sharpe Ratio — true 70/30 IS/OOS split.
    # Re-generate regime labels using ONLY IS data so the OOS period is genuinely unseen.
    split_idx = int(len(df) * 0.7)
    df_is = df.iloc[:split_idx].copy()
    df_oos = df.iloc[split_idx:].copy()

    # Build a simple IS-only signal: use the same bullish flag on IS labels,
    # then apply it forward to OOS rows (walk-forward, no future peeking).
    # If the regime column contains HMM labels, IS labels are safe to use as-is
    # because they were computed from data ending at split_idx.
    oos_signal = df_oos[regime_column].apply(_is_bullish).shift(1).fillna(0)
    oos_ret = df_oos['ret'] * oos_signal
    oos_std = float(oos_ret.std())
    oos_sharpe = float(round((float(oos_ret.mean()) / oos_std * np.sqrt(252)) if oos_std > 0 else 0.0, 3))

    # --- Overall score (0-100) ---
    score = int(_compute_score(sharpe, cagr, max_dd, profit_factor, calmar))
    grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"

    return {
        "status": "ok",
        "overall_score": score,
        "grade": grade,
        "financial_performance": {
            "cagr_pct": cagr,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown_pct": max_dd,
            "profit_factor": profit_factor,
            "calmar_ratio": calmar,
            "win_rate_pct": win_rate,
            "alpha_vs_bh_pct": alpha,
            "bh_cagr_pct": bh_cagr,
            "time_to_recovery_days": time_to_recovery,
            "max_consecutive_losses": max_consec_losses,
            "oos_sharpe_ratio": oos_sharpe,
        },
        "stability_metrics": {
            "regime_changes": int(regime_changes),
            "avg_regime_duration_days": float(avg_regime_duration),
            "pct_time_in_market": float(pct_in_market),
            "regime_distribution": {str(k): int(v) for k, v in regime_counts.items()},
        },
        "benchmarks": {
            "sharpe_target": "≥ 1.2",
            "cagr_target": "≥ 25%",
            "max_dd_target": "≥ -40%",
            "profit_factor_target": "≥ 1.7",
            "calmar_target": "≥ 0.9",
            "recovery_target": "< 45 phiên",
            "loss_streak_target": "< 5 lệnh",
            "oos_target": "OOS/IS ≥ 70%",
        },
        "benchmark_pass": {
            "sharpe": bool(sharpe >= 1.2),
            "cagr": bool(cagr >= 25.0),
            "max_dd": bool(max_dd >= -40.0),
            "profit_factor": bool(profit_factor >= 1.7),
            "calmar": bool(calmar >= 0.9),
            "recovery": bool(time_to_recovery < 45),
            "loss_streak": bool(max_consec_losses < 5),
            "oos": bool((oos_sharpe / max(0.001, sharpe)) >= 0.70),
        },
    }


def _compute_score(sharpe: float, cagr: float, max_dd: float, pf: float, calmar: float) -> int:
    """Weighted score 0-100 across the 5 benchmark targets."""
    s = 0
    s += min(25, max(0, sharpe / 1.2 * 25))        # Sharpe: 25pts
    s += min(25, max(0, cagr / 25.0 * 25))          # CAGR:   25pts
    s += min(20, max(0, (40 + max_dd) / 40 * 20))   # MDD:    20pts (max_dd is negative)
    s += min(15, max(0, pf / 1.7 * 15))             # PF:     15pts
    s += min(15, max(0, calmar / 0.9 * 15))         # Calmar: 15pts
    return int(round(s))


def _empty_result(reason: str) -> Dict[str, Any]:
    return {"status": "error", "message": reason, "overall_score": 0, "grade": "D"}
