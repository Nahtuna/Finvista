"""
Multi-Timeframe Bias Module — Workflow #4
=========================================
VN market only has daily candles. We simulate MTF by:
  - "Monthly" = 100-day EMA macro trend filter
  - "Weekly"  = 5/20-day EMA cross (direction of trend over sessions)
  - "Daily"   = RSI14 + EMA slope (entry timing signal)

Three layers must align for a HIGH-quality entry (Entry Grade A/B/C/D).
"""
import pandas as pd
import numpy as np


def calculate_mtf_bias(df: pd.DataFrame) -> dict:
    """Compute Multi-Timeframe Bias from daily OHLCV data."""
    if df is None or df.empty or len(df) < 100:
        return {
            "bias_score": 50, "entry_grade": "D", "alignment": "INSUFFICIENT_DATA",
            "weekly_trend": "NEUTRAL", "daily_signal": "WAIT", "monthly_bias": "FLAT",
            "description": "Khong du du lieu de phan tich da khung thoi gian."
        }

    close = df["close"].copy()

    # MONTHLY (100-day EMA)
    ema100 = close.ewm(span=100, adjust=False).mean()
    monthly_slope = (ema100.iloc[-1] - ema100.iloc[-5]) / max(ema100.iloc[-5], 1) * 100
    if close.iloc[-1] > ema100.iloc[-1] and monthly_slope > 0:
        monthly_bias, monthly_score = "UP", 100
    elif close.iloc[-1] < ema100.iloc[-1] and monthly_slope < 0:
        monthly_bias, monthly_score = "DOWN", 0
    elif close.iloc[-1] > ema100.iloc[-1]:
        monthly_bias, monthly_score = "UP", 65
    elif close.iloc[-1] < ema100.iloc[-1]:
        monthly_bias, monthly_score = "DOWN", 35
    else:
        monthly_bias, monthly_score = "FLAT", 50

    # WEEKLY (5/20-day EMA)
    ema5  = close.ewm(span=5,  adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    w_price_above_20 = close.iloc[-1] > ema20.iloc[-1]
    w_5_above_20     = ema5.iloc[-1] > ema20.iloc[-1]
    cross_signal = 0
    for i in range(2, min(11, len(close))):
        if ema5.iloc[-i] <= ema20.iloc[-i] and ema5.iloc[-i+1] > ema20.iloc[-i+1]:
            cross_signal = 1; break
        if ema5.iloc[-i] >= ema20.iloc[-i] and ema5.iloc[-i+1] < ema20.iloc[-i+1]:
            cross_signal = -1; break

    if w_price_above_20 and w_5_above_20:
        weekly_trend = "BULLISH"
        weekly_score = min(100, 85 + (15 if cross_signal == 1 else 0))
    elif not w_price_above_20 and not w_5_above_20:
        weekly_trend = "BEARISH"
        weekly_score = max(0, 15 - (10 if cross_signal == -1 else 0))
    else:
        weekly_trend = "NEUTRAL"
        weekly_score = 50

    # DAILY (RSI14 + EMA slope + volume)
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rsi_s = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))
    rsi14 = float(rsi_s.iloc[-1]) if not rsi_s.isna().iloc[-1] else 50.0

    ema20_slope = (ema20.iloc[-1] - ema20.iloc[-5]) / max(ema20.iloc[-5], 1) * 100
    vol_ratio = 1.0
    if "volume" in df.columns:
        vm = df["volume"].rolling(20).mean()
        if not vm.isna().iloc[-1] and vm.iloc[-1] > 0:
            vol_ratio = df["volume"].iloc[-1] / vm.iloc[-1]

    if rsi14 < 30 and close.iloc[-1] > close.iloc[-2]:
        daily_signal, daily_score = "BUY", 85
    elif rsi14 > 70:
        daily_signal, daily_score = "SELL", 20
    elif 45 <= rsi14 <= 65 and ema20_slope > 0 and close.iloc[-1] > ema20.iloc[-1]:
        daily_signal, daily_score = "BUY", 80
    elif close.iloc[-1] < ema20.iloc[-1] and ema20_slope < 0:
        daily_signal, daily_score = "SELL", 25
    else:
        daily_signal, daily_score = "WAIT", 50

    if daily_signal == "BUY" and vol_ratio >= 1.5:
        daily_score = min(100, daily_score + 10)

    # TOTAL: monthly 30% + weekly 45% + daily 25%
    bias_score = round(monthly_score * 0.30 + weekly_score * 0.45 + daily_score * 0.25, 1)

    # ALIGNMENT & GRADE
    b_votes = sum([monthly_bias == "UP", weekly_trend == "BULLISH", daily_signal == "BUY"])
    s_votes = sum([monthly_bias == "DOWN", weekly_trend == "BEARISH", daily_signal == "SELL"])

    if b_votes == 3:   alignment, entry_grade = "ALIGNED_BULLISH",  "A"
    elif b_votes == 2 and s_votes == 0: alignment, entry_grade = "PARTIAL_BULLISH", "B"
    elif s_votes == 3: alignment, entry_grade = "ALIGNED_BEARISH",  "D"
    elif s_votes >= 2: alignment, entry_grade = "PARTIAL_BEARISH",  "D"
    elif b_votes == 1 and s_votes == 1: alignment, entry_grade = "CONFLICTING", "C"
    else:              alignment, entry_grade = "NEUTRAL", "C"

    advice = {
        "A": "? Entry Grade A — Ba khung dong thuan Tang. Vao lenh voi ty trong day du.",
        "B": "?? Entry Grade B — Hai khung dong thuan. Vao lenh 50-75% ty trong.",
        "C": "?? Entry Grade C — Xung dot khung thoi gian. Cho tin hieu ro hon.",
        "D": "?? Entry Grade D — KHONG VEN LENH. Xu huong khong thuan loi."
    }

    desc = (
        f"Dai han EMA100: {monthly_bias} | Trung han EMA5/20: {weekly_trend} | "
        f"Ngan han RSI{rsi14:.0f}: {daily_signal}. {advice[entry_grade]}"
    )

    return {
        "bias_score": bias_score,
        "entry_grade": entry_grade,
        "alignment": alignment,
        "monthly_bias": monthly_bias,
        "monthly_score": monthly_score,
        "weekly_trend": weekly_trend,
        "weekly_score": round(weekly_score, 1),
        "daily_signal": daily_signal,
        "daily_score": daily_score,
        "rsi14": round(rsi14, 1),
        "ema5":  round(float(ema5.iloc[-1]),  2),
        "ema20": round(float(ema20.iloc[-1]), 2),
        "ema50": round(float(ema50.iloc[-1]), 2),
        "ema100":round(float(ema100.iloc[-1]),2),
        "vol_ratio": round(vol_ratio, 2),
        "description": desc,
    }
