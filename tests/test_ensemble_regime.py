# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import pytest
from backend.modules.regime_analysis.indicators.ensemble_regime_engine import EnsembleRegimeEngine


def test_apply_trend_filter_aligned():
    engine = EnsembleRegimeEngine(ml_horizon=1)
    
    t1_decision = {
        'bias': 'LONG_CW',
        'confidence': 0.8,
        'recommendation': 'BUY'
    }
    t5_forecast = {
        'bias': 'LONG_CW',
        'confidence': 0.7
    }
    
    res = engine._apply_trend_filter(t1_decision, t5_forecast)
    assert res['trend_filter'] == 'ALIGNED'
    assert res['confidence'] == pytest.approx(0.88)  # 0.8 * 1.1


def test_apply_trend_filter_opposed():
    engine = EnsembleRegimeEngine(ml_horizon=1)
    
    t1_decision = {
        'bias': 'LONG_CW',
        'confidence': 0.8,
        'recommendation': 'BUY'
    }
    t5_forecast = {
        'bias': 'SHORT_CW',
        'confidence': 0.7
    }
    
    res = engine._apply_trend_filter(t1_decision, t5_forecast)
    assert res['trend_filter'] == 'OPPOSED'
    assert res['confidence'] == pytest.approx(0.4)  # 0.8 * 0.5
    assert "opposes" in res['recommendation']


def test_apply_vietnam_adjustments_stock():
    engine = EnsembleRegimeEngine(ml_horizon=1, instrument_type="STOCK")
    decision = {'confidence': 0.8}
    df = pd.DataFrame({'close': [100.0] * 20})  # stable price
    
    res = engine._apply_vietnam_adjustments(decision, df)
    assert "T+3.5 days" in res['effective_horizon']
    assert res['settlement_delay'] == 2.5
    assert res['confidence'] == 0.8  # No price limit warning triggered


def test_apply_vietnam_adjustments_price_limit():
    engine = EnsembleRegimeEngine(ml_horizon=1, instrument_type="STOCK")
    decision = {'confidence': 0.8}
    # 20 days: 19 days of 100.0, and latest day is 120.0 (large jump)
    close_prices = [100.0] * 19 + [120.0]
    df = pd.DataFrame({'close': close_prices})
    
    res = engine._apply_vietnam_adjustments(decision, df)
    assert res['confidence'] == pytest.approx(0.4)  # 0.8 * 0.5 (halved)
    assert 'price_band_warning' in res
