# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: PRICING CORE UNIT TESTS
====================================
Tests the Black-Scholes-Merton (BSM) option mathematical solver,
Greeks computations, and Newton-Raphson Implied Volatility solver.
"""

import pytest
import numpy as np
from src.cw_engine.pricing_core import (
    calculate_d1_d2,
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    calculate_rho,
    calculate_all_greeks,
    calculate_greeks_for_cw,
    estimate_implied_volatility,
    parse_ratio
)

def test_calculate_d1_d2():
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
    assert d1 == pytest.approx(0.35, abs=1e-5)
    assert d2 == pytest.approx(0.15, abs=1e-5)

    d1_err, d2_err = calculate_d1_d2(-10, 100, 1.0, 0.05, 0.2)
    assert d1_err == 0.0 and d2_err == 0.0

def test_calculate_delta():
    delta_call = calculate_delta(100.0, 100.0, 1.0, 0.05, 0.2, option_type='call')
    assert delta_call == pytest.approx(0.6368, abs=1e-4)

    delta_put = calculate_delta(100.0, 100.0, 1.0, 0.05, 0.2, option_type='put')
    assert delta_put == pytest.approx(-0.3632, abs=1e-4)

def test_calculate_gamma():
    gamma = calculate_gamma(100.0, 100.0, 1.0, 0.05, 0.2)
    assert gamma == pytest.approx(0.01876, abs=1e-4)

def test_calculate_theta():
    theta_call_daily = calculate_theta(100.0, 100.0, 1.0, 0.05, 0.2, option_type='call', per_day=True)
    assert theta_call_daily < 0

def test_calculate_vega():
    vega = calculate_vega(100.0, 100.0, 1.0, 0.05, 0.2)
    assert vega > 0

def test_calculate_rho():
    rho_call = calculate_rho(100.0, 100.0, 1.0, 0.05, 0.2, option_type='call')
    assert rho_call > 0

def test_calculate_greeks_for_cw():
    res = calculate_greeks_for_cw(
        underlying_price=28500.0,
        strike_price=25000.0,
        days_to_maturity=95,
        implied_volatility=0.42,
        conversion_ratio=10.0,
        risk_free_rate=0.045
    )
    assert 'delta' in res
    assert 'gamma' in res
    assert 'vega' in res
    assert 'theta' in res
    assert 'rho' in res
    assert res['moneyness'] > 1.0
    assert res['moneyness_category'] == 'ITM'

def test_estimate_implied_volatility():
    S, K, T_days, r = 100.0, 100.0, 365, 0.05
    market_price = 18.02
    
    iv = estimate_implied_volatility(
        market_price=market_price,
        underlying_price=S,
        strike_price=K,
        days_to_maturity=T_days,
        risk_free_rate=r,
        option_type='call'
    )
    assert iv == pytest.approx(0.40, abs=1e-2)

def test_parse_ratio():
    assert parse_ratio("10:1") == 10.0
    assert parse_ratio("5:1") == 5.0
    assert parse_ratio("2") == 2.0
    assert parse_ratio(10.0) == 10.0
    assert parse_ratio(None) == 1.0
