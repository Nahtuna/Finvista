# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from src.modules.regime_analysis.indicators.creed_regime import calculate_creed_regime_from_df


def test_creed_regime_bullish():
    # Generate synthetic bullish price trend
    dates = pd.date_range(start="2026-01-01", periods=100)
    prices = np.linspace(100, 200, 100)  # Strong uptrend
    df = pd.DataFrame({
        "date": dates,
        "open": prices - 1,
        "high": prices + 2,
        "low": prices - 2,
        "close": prices,
        "volume": 1000000
    })
    res = calculate_creed_regime_from_df(df, trend_period=50)
    assert res["status"] == "ok"
    assert res["regime"] == "BULLISH_VOL_EXPANSION"
    assert res["bias"] == "LONG_CW"
    assert res["confidence"] > 0.5


def test_creed_regime_bearish():
    # Generate synthetic bearish price trend
    dates = pd.date_range(start="2026-01-01", periods=100)
    prices = np.linspace(200, 100, 100)  # Strong downtrend
    df = pd.DataFrame({
        "date": dates,
        "open": prices + 1,
        "high": prices + 2,
        "low": prices - 2,
        "close": prices,
        "volume": 1000000
    })
    res = calculate_creed_regime_from_df(df, trend_period=50)
    assert res["status"] == "ok"
    assert res["regime"] == "BEARISH_HIGH_VOL"
    assert res["bias"] == "SKIP_CW"
