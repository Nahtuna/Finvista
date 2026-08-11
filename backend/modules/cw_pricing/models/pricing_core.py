# -*- coding: utf-8 -*-
"""
🏆 VN-QUANT: QUANTITATIVE COVERED WARRANT PRICING ENGINE
======================================================
Consolidated Core Mathematical calculations for Covered Warrants (CW).
European Option Black-Scholes formula, Greeks, Newton-Raphson Implied Volatility.
Scoring strategies: Safe, Balanced, Aggressive.

Author: samvo
Version: 2.0 (Super Minimalist)
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Dict, Tuple, Any
import math
try:
    from numba import njit
except ImportError:
    # Fallback to a dummy decorator if numba is not installed
    def njit(f): return f

try:
    from backend.core.utils import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# ==========================================================
# 0. NUMBA-COMPATIBLE FAST MATH
# ==========================================

@njit
def n_pdf(x: float) -> float:
    """Fast Normal PDF."""
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

@njit
def n_cdf(x: float) -> float:
    """Fast Normal CDF using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

# Default Volatility for Fair Value comparison (SSC Benchmark approximation)
DEFAULT_VOLATILITY = 0.45

def fetch_dynamic_risk_free_rate() -> float:
    """
    Fetch the live Vietnam 1-Year Government Bond Yield from WorldGovernmentBonds.
    Returns the yield as a float (e.g. 0.0352 for 3.52%).
    Falls back to 0.045 if the request fails or is blocked.
    """
    url = "https://www.worldgovernmentbonds.com/wp-json/country/v1/main"
    body = {
        "GLOBALVAR": {
            "JS_VARIABLE": "jsGlobalVars",
            "FUNCTION": "Country",
            "DOMESTIC": True,
            "ENDPOINT": "http://www.worldgovernmentbonds.com/wp-json/country/v1/historical",
            "DATE_RIF": "2099-12-31",
            "OBJ": None,
            "COUNTRY1": {
                "SYMBOL": "58",
                "PAESE": "Vietnam",
                "PAESE_UPPERCASE": "VIETNAM",
                "BANDIERA": "vn",
                "URL_PAGE": "vietnam"
            },
            "COUNTRY2": None,
            "OBJ1": None,
            "OBJ2": None
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.worldgovernmentbonds.com",
        "Referer": "https://www.worldgovernmentbonds.com/country/vietnam/",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:
        import requests
        from bs4 import BeautifulSoup
        
        response = requests.post(url, json=body, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            table_html = data.get('mainTable', '')
            if table_html:
                soup = BeautifulSoup(table_html, 'html.parser')
                for tr in soup.find_all('tr'):
                    tds = tr.find_all(['td', 'th'])
                    if len(tds) >= 3:
                        maturity = tds[1].text.strip().lower()
                        if "1 year" in maturity or maturity == "1y":
                            yield_str = tds[2].text.strip()
                            yield_str = yield_str.replace('%', '').replace(',', '').strip()
                            val = float(yield_str) / 100.0
                            if 0.01 < val < 0.15:  # Sanity check
                                return val
    except Exception:
        pass
    return 0.045  # Safe default fallback

# Standard Risk-Free Rate for Vietnamese Market (Default 4.5%, updated dynamically by orchestrator/pipelines)
RISK_FREE_RATE = 0.045

# ==========================================================
# 1. CORE BLACK-SCHOLES FORMULAS & GREEKS
# ==========================================

@njit
def calculate_d1_d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> Tuple[float, float]:
    """Calculate d1 and d2 parameters for Black-Scholes formula with dividend yield q."""
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return 0.0, 0.0
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2

@njit
def calculate_merton_jump_diffusion_price(S: float, K: float, T: float, r: float, sigma: float, 
                                          lamb: float, mu_J: float, sigma_J: float, 
                                          option_type_is_call: bool = True, max_n: int = 12, q: float = 0.0) -> float:
    """
    Merton's Jump-Diffusion Option Pricing Model with dividend yield q.
    Accounts for asset price jumps (fat tails) by adding a Poisson jump component.
    """
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return max(S - K, 0.0) if option_type_is_call else max(K - S, 0.0)
        
    kappa = math.exp(mu_J + 0.5 * sigma_J**2) - 1
    lamb_prime = lamb * (1 + kappa)
    
    price = 0.0
    fact = 1.0
    for n in range(max_n):
        if n > 0:
            fact *= n
        term_coef = math.exp(-lamb_prime * T) * ((lamb_prime * T)**n) / fact
        
        # Adjust drift for risk-free rate r and Poisson jump component (without subtracting q)
        r_n = r - lamb * kappa + (n * math.log(1 + kappa)) / T
        sigma_n = math.sqrt(sigma**2 + (n * sigma_J**2) / T)
        
        # Calculate BS price with dividend yield q
        d1, d2 = calculate_d1_d2(S, K, T, r_n, sigma_n, q)
        if option_type_is_call:
            bs_price = S * math.exp(-q * T) * n_cdf(d1) - K * math.exp(-r_n * T) * n_cdf(d2)
        else:
            bs_price = K * math.exp(-r_n * T) * n_cdf(-d2) - S * math.exp(-q * T) * n_cdf(-d1)
            
        price += term_coef * bs_price
        
    return float(price)

@njit
def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type_is_call: bool = True, q: float = 0.0) -> float:
    """Calculate Option Delta (Sensitivity to underlying asset price) with dividend yield q."""
    if T <= 0:
        if option_type_is_call:
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma, q)
    df_q = math.exp(-q * T)
    if option_type_is_call:
        return df_q * n_cdf(d1)
    return df_q * (n_cdf(d1) - 1.0)

@njit
def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Calculate Option Gamma (Rate of change of Delta) with dividend yield q."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma, q)
    return math.exp(-q * T) * n_pdf(d1) / (S * sigma * math.sqrt(T))

@njit
def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type_is_call: bool = True, per_day: bool = True, q: float = 0.0) -> float:
    """Calculate Option Theta (Time decay per day) with dividend yield q."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
    sqrt_T = math.sqrt(T)
    df_q = math.exp(-q * T)
    df_r = math.exp(-r * T)
    term1 = -(S * df_q * n_pdf(d1) * sigma) / (2.0 * sqrt_T)
    if option_type_is_call:
        theta = term1 + q * S * df_q * n_cdf(d1) - r * K * df_r * n_cdf(d2)
    else:
        theta = term1 - q * S * df_q * n_cdf(-d1) + r * K * df_r * n_cdf(-d2)
    if per_day:
        return theta / 365.0
    return theta

@njit
def calculate_vega(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Calculate Option Vega (Sensitivity to a 1% absolute change in volatility) with dividend yield q."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma, q)
    return S * math.exp(-q * T) * n_pdf(d1) * math.sqrt(T) * 0.01

@njit
def calculate_rho(S: float, K: float, T: float, r: float, sigma: float, option_type_is_call: bool = True, q: float = 0.0) -> float:
    """Calculate Option Rho (Sensitivity to a 1% absolute change in risk-free interest rate) with dividend yield q."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    _, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
    df_r = math.exp(-r * T)
    if option_type_is_call:
        return K * T * df_r * n_cdf(d2) * 0.01
    return -K * T * df_r * n_cdf(-d2) * 0.01


def calculate_leland_volatility(sigma: float, spread_pct: float, k_transaction_cost: float = 0.0015, dt: float = 1.0/252.0, is_long: bool = True) -> float:
    """
    Calculate Leland's Liquidity-Adjusted Volatility to account for transaction costs and bid-ask spreads.
    spread_pct: Bid-Ask Spread in percentage (e.g. 2.5 for 2.5%)
    k_transaction_cost: Transaction cost rate (brokerage fee + taxes) (e.g. 0.0015 for 0.15%)
    dt: Hedging/rebalancing frequency in years (default: 1/252 for daily)
    is_long: True for option buyers (reduces volatility), False for writers/issuers.
    """
    if sigma <= 0 or dt <= 0:
        return sigma
    # Total transaction cost rate (one-way)
    k = k_transaction_cost + 0.5 * (spread_pct / 100.0)
    
    # Leland adjustment factor
    adjustment = np.sqrt(2.0 / np.pi) * k / (sigma * np.sqrt(dt))
    
    if is_long:
        # Long option buyers face higher transaction cost which dampens volatility
        variance_leland = sigma**2 * (1.0 - adjustment)
    else:
        variance_leland = sigma**2 * (1.0 + adjustment)
        
    if variance_leland <= 1e-4:
        return 0.01 # floor to prevent negative or zero volatility
    return float(np.sqrt(variance_leland))


def calculate_leland_price(S: float, K: float, T: float, r: float, sigma: float, spread_pct: float, 
                            option_type_is_call: bool = True, q: float = 0.0, k_transaction_cost: float = 0.0015, dt: float = 1.0/252.0) -> float:
    """
    Calculate Option Price using Leland's Liquidity-Adjusted BSM Model.
    """
    sigma_leland = calculate_leland_volatility(sigma, spread_pct, k_transaction_cost, dt, is_long=True)
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma_leland, q)
    if option_type_is_call:
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    return float(max(0.0, price))


def calculate_cbbc_bull_price(S: float, K: float, H: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """
    Down-and-out Call option pricing model (CBBC Bull contract)
    S: Spot Price
    K: Strike Price (usually K <= H)
    H: Call Price / Barrier (Knock-out level)
    """
    if S <= H:
        return 0.0 # Knocked out
    if T <= 0:
        return max(S - K, 0.0)
    
    # Standard BSM Call Price
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
    bs_call = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    # Down-and-In Call component
    sigma2 = sigma**2
    lam = (r - q + 0.5 * sigma2) / sigma2
    y = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + lam * sigma * np.sqrt(T)
    
    term_spot = S * np.exp(-q * T) * (H/S)**(2*lam) * norm.cdf(y)
    term_strike = K * np.exp(-r * T) * (H/S)**(2*lam - 2) * norm.cdf(y - sigma * np.sqrt(T))
    c_di = term_spot - term_strike
    
    price = bs_call - c_di
    return float(max(0.0, price))


def calculate_cbbc_bear_price(S: float, K: float, H: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """
    Up-and-out Put option pricing model (CBBC Bear contract)
    S: Spot Price
    K: Strike Price (usually K >= H)
    H: Call Price / Barrier (Knock-out level)
    """
    if S >= H:
        return 0.0 # Knocked out
    if T <= 0:
        return max(K - S, 0.0)
    
    # Standard BSM Put Price
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
    bs_put = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    
    # Up-and-In Put component
    sigma2 = sigma**2
    lam = (r - q + 0.5 * sigma2) / sigma2
    y = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + lam * sigma * np.sqrt(T)
    
    term_strike = K * np.exp(-r * T) * (H/S)**(2*lam - 2) * norm.cdf(-y + sigma * np.sqrt(T))
    term_spot = S * np.exp(-q * T) * (H/S)**(2*lam) * norm.cdf(-y)
    p_ui = term_strike - term_spot
    
    price = bs_put - p_ui
    return float(max(0.0, price))


def calculate_all_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call', q: float = 0.0) -> Dict[str, float]:
    """Calculate all standard Greeks at once with dividend yield q."""
    is_call = option_type.lower() == 'call'
    return {
        'delta': calculate_delta(S, K, T, r, sigma, is_call, q),
        'gamma': calculate_gamma(S, K, T, r, sigma, q),
        'theta': calculate_theta(S, K, T, r, sigma, is_call, per_day=True, q=q),
        'vega': calculate_vega(S, K, T, r, sigma, q),
        'rho': calculate_rho(S, K, T, r, sigma, is_call, q)
    }

def calculate_greeks_for_cw(
    underlying_price: float,
    strike_price: float,
    days_to_maturity: int,
    implied_volatility: float,
    conversion_ratio: float = 1.0,
    risk_free_rate: float = RISK_FREE_RATE,
    option_type: str = 'call',
    q: float = 0.0
) -> Dict[str, Any]:
    """Calculate Greeks specifically for Vietnamese Covered Warrants, adjusting for conversion ratio and dividend yield q."""
    T = days_to_maturity / 365.0
    
    # Calculate moneyness
    moneyness = underlying_price / strike_price if strike_price > 0 else 0
    if moneyness > 1.05:
        moneyness_category = 'ITM'
    elif moneyness < 0.95:
        moneyness_category = 'OTM'
    else:
        moneyness_category = 'ATM'
        
    if T <= 0:
        prob_itm = 1.0 if underlying_price > strike_price else 0.0
        return {
            'delta': 1.0 if underlying_price > strike_price else 0.0,
            'gamma': 0.0, 'theta': 0.0, 'vega': 0.0, 'rho': 0.0,
            'moneyness': moneyness, 'moneyness_category': moneyness_category, 'prob_itm': prob_itm
        }
        
    # Calculate d1, d2
    _, d2 = calculate_d1_d2(underlying_price, strike_price, T, risk_free_rate, implied_volatility, q)
    is_call = option_type.lower() == 'call'
    prob_itm = float(n_cdf(d2)) if is_call else float(n_cdf(-d2))
    
    raw_greeks = calculate_all_greeks(underlying_price, strike_price, T, risk_free_rate, implied_volatility, option_type, q)
    greeks: Dict[str, Any] = dict(raw_greeks)
    
    # Adjust Greeks affected by the conversion ratio (Delta, Gamma, Vega are per unit)
    greeks['delta'] = greeks['delta'] / conversion_ratio
    greeks['gamma'] = greeks['gamma'] / conversion_ratio
    greeks['vega'] = greeks['vega'] / conversion_ratio
    
    # Append custom metrics
    greeks['moneyness'] = moneyness
    greeks['moneyness_category'] = moneyness_category
    greeks['prob_itm'] = prob_itm
    return greeks

# ==========================================
# 2. IMPLIED VOLATILITY NEWTON-RAPHSON SOLVER
# ==========================================

@njit
def _fast_iv_solver(
    market_price: float,
    underlying_price: float,
    strike_price: float,
    T: float,
    risk_free_rate: float,
    is_call: bool,
    max_iterations: int,
    tolerance: float,
    q: float = 0.0
) -> float:
    """Internal fast solver for IV with dividend yield q."""
    sigma = 0.3 # Initial volatility guess
    
    for _ in range(max_iterations):
        d1, d2 = calculate_d1_d2(underlying_price, strike_price, T, risk_free_rate, sigma, q)
        df_q = math.exp(-q * T)
        df_r = math.exp(-risk_free_rate * T)
        if is_call:
            price = (underlying_price * df_q * n_cdf(d1) - 
                     strike_price * df_r * n_cdf(d2))
        else:
            price = (strike_price * df_r * n_cdf(-d2) - 
                     underlying_price * df_q * n_cdf(-d1))
                     
        diff = market_price - price
        if abs(diff) < tolerance:
            return sigma
            
        vega = underlying_price * df_q * n_pdf(d1) * math.sqrt(T)
        if vega < 1e-10:
            break
            
        sigma = sigma + diff / vega
        sigma = max(0.01, min(sigma, 5.0)) # Bound checks
        
    return sigma

def estimate_implied_volatility(
    market_price: float,
    underlying_price: float,
    strike_price: float,
    days_to_maturity: int,
    risk_free_rate: float = RISK_FREE_RATE,
    option_type: str = 'call',
    max_iterations: int = 100,
    tolerance: float = 1e-5,
    q: float = 0.0
) -> float:
    """Solve for Implied Volatility (IV) using Newton-Raphson method with dividend yield q."""
    T = days_to_maturity / 365.0
    if T <= 0 or market_price <= 0:
        return 0.3
    
    is_call = option_type.lower() == 'call'
    return _fast_iv_solver(
        market_price, underlying_price, strike_price, T, 
        risk_free_rate, is_call, max_iterations, tolerance, q
    )

def parse_ratio(ratio_str: Any) -> float:
    """Safely parse exercise ratio strings such as '10:1' or '5:1' to numeric values."""
    if isinstance(ratio_str, (int, float)):
        return float(ratio_str)
    if not ratio_str:
        return 1.0
    try:
        ratio_s = str(ratio_str).strip()
        if ':' in ratio_s:
            parts = ratio_s.split(':')
            return float(parts[0]) / float(parts[1]) if len(parts) > 1 else float(parts[0])
        return float(ratio_s)
    except:
        return 1.0

# ==========================================
# 3. HARD GATES — ABSOLUTE DISQUALIFIERS
# ==========================================

# Bộ lọc cứng: Loại mã ngay lập tức bất kể G_Score cao đến đâu
# Tất cả ngưỡng đều có cơ sở định lượng rõ ràng
# Bộ lọc cứng (Đã được chuẩn hóa theo kinh nghiệm thực chiến của Pro-traders Việt Nam):
# Các ngưỡng này được siết chặt để loại bỏ hoàn toàn các mã "cờ bạc" và rủi ro cao.
# BACKTEST MODE: Relaxed gates to generate more trade candidates for tuning analysis
HARD_GATES = {
    'min_days_to_expiry':     10,     # < 10 ngày: Cấm chơi. (Relaxed from 15 for backtest)
    'min_gtgd_trieu':         30.0,   # Hạ từ 50tr xuống 30tr để bắt được nhiều mã hơn cho backtest.
    'max_premium_pct':        25.0,   # Relaxed from 18% to allow more candidates for backtest analysis.
    'max_iv_pct':            120.0,   # Relaxed IV threshold for backtest
    'min_delta':               0.10,   # Relaxed from 0.15 to include more OTM candidates
    'max_delta':               0.85,   # Relaxed from 0.80 to include more ITM candidates
    'max_theta_burn_rate':     0.08,   # Relaxed from 5% to 8% for backtest
}

def passes_hard_gates(row: Any, use_derivatives_filter: bool = False) -> tuple:
    """
    Kiểm tra tất cả bộ lọc cứng. Đã tối ưu hóa cho thanh khoản thích ứng (Adaptive Liquidity).
    """
    # ... (Credit & Systemic checks remain the same)
    is_dist = int(row.get('underlying_is_distressed', 0) or 0)
    altman_z = float(row.get('underlying_altman_z', 3.0) or 3.0)
    if is_dist == 1 or altman_z < 1.1:
        return False, "DISTRESSED ASSET"

    sys_prob = float(row.get('underlying_systemic_prob', 0.10) or 0.10)
    if sys_prob >= 0.50:
        return False, f"SYSTEMIC RISK ({sys_prob:.0%})"

    # ── LỚP 0.1: Merton Structural Risk Gate (Real-time) ────────────────
    # Chặn các mã có rủi ro vỡ nợ cao dựa trên biến động giá & nợ
    underlying = str(row.get('S_CPCS', '') or '')
    current_stock_price = float(row.get('S_GiaCP', 0) or 0)
    
    if underlying and current_stock_price > 0:
        from backend.modules.credit_risk.models.merton_engine import calculate_merton_dd_realtime
        merton = calculate_merton_dd_realtime(underlying, current_stock_price)
        if merton.get('status') == 'DISTRESSED':
            dd = merton.get('merton_dd', 0)
            return False, f"MERTON RISK (DD={dd:.2f})"

    # ── LỚP 0.5: Adaptive Liquidity & Spread Logic ────────────────────
    bid = float(row.get('bid', 0) or 0)
    ask = float(row.get('ask', 0) or 0)
    
    # Nếu cả bid VÀ ask đều = 0 -> Ngoài giờ giao dịch hoặc chưa có lệnh
    # Không tính là SPREAD RỘNG, coi như chưa có dữ liệu thực tế
    from datetime import datetime
    now = datetime.now()
    is_trading_hours = (now.hour == 9 or 
                        (10 <= now.hour < 15) or 
                        (now.hour == 15 and now.minute == 0))
    
    if bid > 0 and ask > 0:
        spread_pct = (ask - bid) / bid  # Spread thực sự có dữ liệu
    elif is_trading_hours and (bid > 0 or ask > 0):
        spread_pct = 0.50  # Một chiều lệnh trong giờ giao dịch -> spread rộng
    else:
        spread_pct = 0.0   # Ngoài giờ / không có lệnh -> bỏ qua spread check
    
    gtgd = float(row.get('E_GTGD', 0) or 0)
    hist_avg_gtgd = float(row.get('hist_avg_gtgd', 0.0) or 0.0)
    
    # CHIẾN LƯỢC: Nếu Spread cực hẹp (< 2%) -> Có MM xịn, chấp nhận GTGD thấp hơn (25tr)
    # Nếu Spread rộng -> Ép GTGD cao (50tr)
    min_gtgd_required = HARD_GATES['min_gtgd_trieu']
    if spread_pct < 0.02: # 2%
        min_gtgd_required = 25.0 # Chỉ cần 25tr/ngày nếu có MM kê lệnh sát
    
    # Buổi sáng (trước 10h) giảm 50% yêu cầu thanh khoản để bắt sóng
    if now.hour == 9 or (now.hour == 10 and now.minute < 30):
        min_gtgd_required *= 0.5

    if gtgd < min_gtgd_required and hist_avg_gtgd < min_gtgd_required:
        return False, f"THANH KHOẢN THẤP (Nay: {gtgd:.1f}tr, TB 10N: {hist_avg_gtgd:.1f}tr)"

    if spread_pct > 0.12: # Spread > 12% là quá rủi ro cho mọi trường hợp
        return False, f"SPREAD RỘNG ({spread_pct*100:.1f}%)"

    # ── LỚP 1: Các bộ lọc kỹ thuật khác ────────────────────────────────────
    sentiment = str(row.get('market_sentiment', 'NEUTRAL')).upper()
    max_premium_gate = HARD_GATES['max_premium_pct']
    min_days_gate = HARD_GATES['min_days_to_expiry']
    
    if use_derivatives_filter and sentiment == 'BEARISH':
        max_premium_gate = 12.0
        min_days_gate = 30

    # Extract required technical fields
    days       = float(row.get('L_Ngay', 0) or 0)
    premium    = float(row.get('Premium_Pct', 999) or 999)
    iv         = float(row.get('S_IV_Pct', 999) or 999)
    delta      = float(row.get('T_Delta', 0) or 0)
    cw_price   = float(row.get('C_GiaCW', 0) or 0)
    theta      = abs(float(row.get('T_Theta', 0) or 0))
    theta_burn = theta / cw_price if cw_price > 0 else 0

    if days < min_days_gate:
        reason = "ĐÁO HẠN NHANH" if sentiment != 'BEARISH' else "BÃO PHÁI SINH (ĐÁO HẠN < 30N)"
        return False, f"{reason} ({int(days)}N)"

    if premium > max_premium_gate:
        reason = "PREMIUM CAO" if sentiment != 'BEARISH' else "BÃO PHÁI SINH (PREMIUM CAO)"
        return False, f"{reason} ({premium:.0f}%)"
    if iv > HARD_GATES['max_iv_pct']:
        return False, f"IV CỰC CAO ({iv:.0f}%)"
    if delta < HARD_GATES['min_delta']:
        return False, f"DEEP OTM (Δ={delta:.2f})"
    if delta > HARD_GATES['max_delta']:
        return False, f"DEEP ITM (Δ={delta:.2f})"
    if theta_burn > HARD_GATES['max_theta_burn_rate']:
        return False, f"THETA BOMB ({theta_burn*100:.1f}%/ngày)"
    return True, ''

# ==========================================
# 3. SCORING & DECISION TREE ENGINES
# ==========================================

def score_cw(df: pd.DataFrame, strategy: str = 'balanced', market_regime: str = 'NEUTRAL') -> pd.DataFrame:
    """
    Score Covered Warrants based on strategy (Safe, Balanced, Aggressive)
    using robust financial scaling (handling outliers in volume, gearing and upside).

    v2.0 Upgrade: Integrates Underlying Momentum Score (und_mom_score) as a
    first-class factor. The momentum of the underlying stock (r5/r20/r60 composite,
    RSI, MA alignment) is the single most important predictor for CW bull call P&L.
    Weights by strategy:
      aggressive/BULLISH : momentum 25%  (highest weight, pure momentum mode)
      balanced/BULLISH   : momentum 20%  (significant weight in bull trend)
      balanced/NEUTRAL   : momentum 15%  (tiebreaker between similar CWs)
      safe               : momentum 10%  (minimal — safety first)
    
    v2.1 Upgrade: Regime-aware filtering parameters
    Market regimes from HMM model adjust filtering criteria:
      BULLISH_VOL_CONTRACTION: Relaxed spread (20%), DTM (20), R:R (1.2)
      BULLISH_VOL_EXPANSION: Moderate spread (15%), DTM (25), R:R (1.3)
      BEARISH_VOL_CONTRACTION: Strict spread (10%), DTM (40), R:R (1.5)
      BEARISH_VOL_EXPANSION: Ultra-strict spread (8%), DTM (50), R:R (1.8)
      NEUTRAL: Standard spread (15%), DTM (30), R:R (1.5)
    """
    res = df.copy()
    if res.empty:
        return res
    
    # ===== REGIME-AWARE FILTERING PARAMETERS =====
    regime_params = {
        'BULLISH_VOL_CONTRACTION': {'max_spread': 20.0, 'min_dtm': 20, 'min_rr': 1.2, 'vol_multiplier': 1.2},
        'BULLISH_VOL_EXPANSION': {'max_spread': 15.0, 'min_dtm': 25, 'min_rr': 1.3, 'vol_multiplier': 1.1},
        'BEARISH_VOL_CONTRACTION': {'max_spread': 10.0, 'min_dtm': 40, 'min_rr': 1.5, 'vol_multiplier': 0.9},
        'BEARISH_VOL_EXPANSION': {'max_spread': 8.0, 'min_dtm': 50, 'min_rr': 1.8, 'vol_multiplier': 0.8},
        'NEUTRAL': {'max_spread': 15.0, 'min_dtm': 30, 'min_rr': 1.5, 'vol_multiplier': 1.0},
        'UNKNOWN': {'max_spread': 15.0, 'min_dtm': 30, 'min_rr': 1.5, 'vol_multiplier': 1.0}
    }
    
    params = regime_params.get(market_regime, regime_params['NEUTRAL'])
    max_spread = params['max_spread']
    min_dtm = params['min_dtm']
    min_rr = params['min_rr']
    vol_multiplier = params['vol_multiplier']
        
    def normalize(series, reverse=False):
        # Handle NaN values safely by filling with media/zero
        series = pd.Series(series).fillna(0.0)
        s_min = float(series.min())
        s_max = float(series.max())
        if s_max == s_min:
            return pd.Series(50.0, index=series.index)
        norm = (series - s_min) / (s_max - s_min) * 100.0
        return 100.0 - norm if reverse else norm

    # Fill NaN values for all core columns safely checking existence to prevent KeyErrors
    if 'D_Volume' in res.columns:
        res['D_Volume'] = res['D_Volume'].fillna(0.0)
    else:
        res['D_Volume'] = 0.0

    if 'outstanding_volume' in res.columns:
        res['outstanding_volume'] = res['outstanding_volume'].fillna(1000000.0)
    else:
        res['outstanding_volume'] = 1000000.0

    if 'Spread_Pct' in res.columns:
        res['Spread_Pct'] = res['Spread_Pct'].fillna(0.0)
    else:
        if 'bid' in res.columns and 'ask' in res.columns:
            b = res['bid'].astype(float).fillna(0.0)
            a = res['ask'].astype(float).fillna(0.0)
            res['Spread_Pct'] = np.where((b > 0) & (a > 0), (a - b) / b * 100.0, 0.0)
        else:
            res['Spread_Pct'] = 0.0

    if 'L_Ngay' in res.columns:
        res['L_Ngay'] = res['L_Ngay'].fillna(30.0)
    else:
        res['L_Ngay'] = 30.0

    if 'prob_itm' in res.columns:
        res['prob_itm'] = res['prob_itm'].fillna(0.1)
    else:
        res['prob_itm'] = 0.1

    if 'F_DonBay' in res.columns:
        res['F_DonBay'] = res['F_DonBay'].fillna(1.0)
    else:
        res['F_DonBay'] = 1.0

    if 'S_IV_Pct' in res.columns:
        res['S_IV_Pct'] = res['S_IV_Pct'].fillna(45.0)
    else:
        res['S_IV_Pct'] = 45.0

    if 'T_Delta' in res.columns:
        res['T_Delta'] = res['T_Delta'].fillna(0.0)
    else:
        res['T_Delta'] = 0.0

    # Robust scaling for volume: use log1p transformation to handle log-normal distribution
    res['norm_vol'] = normalize(np.log1p(res['D_Volume']))
    
    # ── MM Liquidity & Spread integration ─────────────────────────────────
    res['norm_outstanding'] = normalize(np.log1p(res['outstanding_volume']))
    # Regime-aware spread tolerance: clip at regime-specific max_spread
    res['norm_spread'] = normalize(res['Spread_Pct'].clip(0, max_spread), reverse=True)
    
    # Combine daily volume (50%), outstanding volume (30%), and bid-ask spread (20%)
    res['norm_vol'] = res['norm_vol'] * 0.5 + res['norm_outstanding'] * 0.3 + res['norm_spread'] * 0.2
    
    # Robust scaling for days to maturity: regime-aware minimum DTM
    res['norm_days'] = normalize(res['L_Ngay'].clip(min_dtm, 150))
    
    res['norm_prob'] = normalize(res['prob_itm'])
    
    # Robust scaling for gearing: clip at 15x (very high gearing is often too risky, 10x-15x is sweet)
    res['norm_gear'] = normalize(res['F_DonBay'].clip(0, 15))
    
    res['norm_iv'] = normalize(res['S_IV_Pct'], reverse=True)
    
    # Delta Sweet Spot (ATM optimization near 0.5)
    res['delta_score'] = res['T_Delta'].apply(lambda x: 100 - abs(x - 0.5) * 200 if not pd.isna(x) else 50.0).clip(0, 100)

    # ── v2.0: UNDERLYING MOMENTUM SCORE ──────────────────────────────────────
    # If momentum enrichment was run upstream, und_mom_score is already in the df.
    # Fallback to 50 (neutral) if column is missing (backward-compatible).
    if 'und_mom_score' in res.columns:
        res['norm_momentum'] = res['und_mom_score'].fillna(50.0).clip(0, 100)
    else:
        res['norm_momentum'] = 50.0  # neutral default — no momentum data available

    # RSI quality filter: reward 50-72 (healthy uptrend), penalise overbought (>80)
    def _rsi_quality(rsi_val):
        if 50 <= rsi_val <= 72: return 100
        if 72 < rsi_val <= 80:  return 70
        if rsi_val > 80:        return 30   # overbought — risk of reversal
        if 40 <= rsi_val < 50:  return 50
        return 10  # oversold or no data
    if 'und_rsi' in res.columns:
        res['norm_rsi_quality'] = res['und_rsi'].fillna(50.0).apply(_rsi_quality)
    else:
        res['norm_rsi_quality'] = 70.0  # default moderate quality

    # Combined momentum signal (80% composite momentum, 20% RSI quality check)
    res['norm_momentum'] = (res['norm_momentum'] * 0.80 + res['norm_rsi_quality'] * 0.20).clip(0, 100)
    
    # ── v2.2: CHART PATTERN SCORE ─────────────────────────────────────────
    # Chart pattern recognition for underlying stock (CPCS, support/resistance, trend)
    # Default to 50 (neutral) if chart pattern analysis not available
    if 'und_chart_pattern_score' in res.columns:
        res['norm_chart_pattern'] = res['und_chart_pattern_score'].fillna(50.0).clip(0, 100)
    else:
        res['norm_chart_pattern'] = 50.0  # neutral default — no chart pattern data available
    
    # 1. VALUATION DEPTH (LAV - Liquidity Adjusted Valuation)
    # The true upside must factor in the cost to cross the spread (Ask price)
    mkt_price = res['C_GiaCW'].astype(float)
    theo_price = res['theo_price'].astype(float)
    ask_col = res['ask'] if 'ask' in res.columns else mkt_price
    ask_price = ask_col.fillna(mkt_price).astype(float)
    
    # Use Leland theoretical price if available, otherwise fallback to BSM theo_price
    if 'theo_price_leland' in res.columns:
        theo_ref = np.where(res['theo_price_leland'] > 0, res['theo_price_leland'], theo_price)
    else:
        theo_ref = theo_price
        
    # Raw Upside (Mid-to-Theo) vs Real Upside (Ask-to-Theo) using Leland reference
    raw_upside = (theo_ref - mkt_price) / mkt_price.replace(0, np.nan)
    raw_upside = raw_upside.fillna(0)
    real_upside = (theo_ref - ask_price) / ask_price.replace(0, np.nan)
    real_upside = real_upside.fillna(0)
    
    # Penalize wide spreads in the valuation score
    bid_col = res['bid'] if 'bid' in res.columns else pd.Series(0.0, index=res.index)
    bid = bid_col.fillna(0).astype(float)
    spread_pct = (ask_price - bid) / bid.replace(0, np.nan)
    spread_pct = spread_pct.fillna(0.1)
    
    # Adjusted Upside Score (Institutional Grade)
    # We clip real_upside to remove outliers and normalize it
    clipped_upside = real_upside.clip(-0.5, 1.5)
    norm_upside = (clipped_upside + 0.5) / 2.0 * 100 # Map -50%..+150% to 0..100
    
    # 2. GREEK ALPHA & TIME DECAY
    # ... existing logic ...
    
    sentiment = 'NEUTRAL'
    if not res.empty and 'market_sentiment' in res.columns:
        sentiment = str(res['market_sentiment'].iloc[0]).upper()
 
    if strategy == 'safe':
        if sentiment == 'BEARISH':
            # Ultra-safe bear market: ITM prob (30%) + Expiry (25%) + low IV (20%) + Volume (10%) + Delta (10%) + Momentum (05%)
            res['G_Score'] = (res['norm_prob'] * 0.30 + res['norm_days'] * 0.25 +
                              res['norm_iv'] * 0.20 + res['norm_vol'] * 0.10 +
                              res['delta_score'] * 0.10 + res['norm_momentum'] * 0.05)
        elif sentiment == 'BULLISH':
            # Slightly opportunistic: ITM prob (22%) + Expiry (18%) + Gearing (18%) + Volume (14%) + Delta (10%) + low IV (08%) + Momentum (10%)
            res['G_Score'] = (res['norm_prob'] * 0.22 + res['norm_days'] * 0.18 +
                              res['norm_gear'] * 0.18 + res['norm_vol'] * 0.14 +
                              res['delta_score'] * 0.10 + res['norm_iv'] * 0.08 +
                              res['norm_momentum'] * 0.10)
        else:
            # Neutral safe: ITM prob (28%) + Expiry (22%) + Volume (18%) + low IV (14%) + Delta (08%) + Momentum (10%)
            res['G_Score'] = (res['norm_prob'] * 0.28 + res['norm_days'] * 0.22 +
                              res['norm_vol'] * 0.18 + res['norm_iv'] * 0.14 +
                              res['delta_score'] * 0.08 + res['norm_momentum'] * 0.10)
    elif strategy == 'aggressive':
        if sentiment == 'BEARISH':
            # Defensive aggressive: Upside (22%) + Gearing (18%) + ITM prob (18%) + Expiry (14%) + Volume (10%) + Delta (08%) + Momentum (10%)
            res['G_Score'] = (norm_upside * 0.22 + res['norm_gear'] * 0.18 +
                              res['norm_prob'] * 0.18 + res['norm_days'] * 0.14 +
                              res['norm_vol'] * 0.10 + res['delta_score'] * 0.08 +
                              res['norm_momentum'] * 0.10)
        elif sentiment == 'BULLISH':
            # Aggressive bull mode: Momentum (25%) + Gearing (30%) + Upside (25%) + Delta (10%) + Volume (10%)
            # v2.0: Momentum is now the primary qualifier — only buy CW on trending stocks
            base_score = (res['norm_momentum'] * 0.25 + res['norm_gear'] * 0.30 +
                          norm_upside * 0.25 + normalize(res['T_Delta']) * 0.10 +
                          res['norm_vol'] * 0.10)

            # 🛡️ ANTI-SIDEWAYS PROTECTION (ADX / MA alignment filter)
            def apply_trend_penalty(row):
                adx = row.get('underlying_adx', 25.0)  # assume trending if missing
                ma_align = row.get('und_ma_align_score', 67.0)  # use MA alignment if ADX missing
                # Zero MA alignment (below all 3 MAs) = sideways/bearish → halve score
                if ma_align < 34 and adx < 20: return 0.4
                if adx < 18: return 0.5
                if adx < 22: return 0.8
                return 1.0

            res['G_Score'] = base_score * res.apply(apply_trend_penalty, axis=1)
        else:
            # Neutral aggressive: Momentum (20%) + Gearing (30%) + Upside (28%) + Delta (12%) + Volume (10%)
            res['G_Score'] = (res['norm_momentum'] * 0.20 + res['norm_gear'] * 0.30 +
                              norm_upside * 0.28 + normalize(res['T_Delta']) * 0.12 +
                              res['norm_vol'] * 0.10)
    else:  # balanced
        if sentiment == 'BEARISH':
            # Balanced-safe in bear: Delta (22%) + ITM prob (22%) + Expiry (18%) + Volume (14%) + Upside (14%) + Momentum (10%)
            res['G_Score'] = (res['delta_score'] * 0.22 + res['norm_prob'] * 0.22 +
                              res['norm_days'] * 0.18 + res['norm_vol'] * 0.14 +
                              norm_upside * 0.14 + res['norm_momentum'] * 0.10)
        elif sentiment == 'BULLISH':
            # Balanced bull: Momentum (25%) + ITM prob (20%) + Delta (15%) + Gearing (15%) + Upside (15%) + Volume (10%)
            # BACKTEST MODE: Higher weight on probability and momentum for better win rate
            res['G_Score'] = (res['norm_momentum'] * 0.25 + res['norm_prob'] * 0.20 +
                              res['delta_score'] * 0.15 + res['norm_gear'] * 0.15 +
                              norm_upside * 0.15 + res['norm_vol'] * 0.10)
        else:
            # Neutral balanced: ITM prob (25%) + Momentum (20%) + Delta (15%) + Volume (15%) + Upside (15%) + Expiry (10%)
            # BACKTEST MODE: Prioritize probability and momentum for higher success rate
            res['G_Score'] = (res['norm_prob'] * 0.25 + res['norm_momentum'] * 0.20 +
                              res['delta_score'] * 0.15 + res['norm_vol'] * 0.15 +
                              norm_upside * 0.15 + res['norm_days'] * 0.10)
    
    # ── v2.2: ADD CHART PATTERN BONUS ───────────────────────────────────────
    # Add chart pattern score as bonus/penalty after base calculation
    if 'norm_chart_pattern' in res.columns:
        # Chart pattern bonus: up to ±5 points
        chart_pattern_bonus = (res['norm_chart_pattern'] - 50) * 0.1  # -5 to +5 points
        res['G_Score'] = res['G_Score'] + chart_pattern_bonus
        
    # ── ADVANCED SCORING OPTIMIZATIONS ──────────────────────────────────────
    # 1. Support Distance Penalty / Bonus
    if 'und_dist_ma20' in res.columns:
        def calc_support_adj(row):
            dist_val = row.get('und_dist_ma20')
            if pd.isna(dist_val) or dist_val is None:
                return 0.0
            dist = float(dist_val)
            if dist > 5.0:
                # Moderate penalty: 0.4 point per 1% above support, max 6 points
                return -min(6.0, (dist - 5.0) * 0.4)
            elif 0.0 <= dist <= 1.5:
                # Reward buying near support
                return 4.0
            return 0.0
        res['G_Score'] += res.apply(calc_support_adj, axis=1)

    # 2. Bid-Ask Spread Penalty
    if 'Spread_Pct' in res.columns:
        def calc_spread_penalty(row):
            spread_val = row.get('Spread_Pct')
            if pd.isna(spread_val) or spread_val is None:
                return 0.0
            spread = float(spread_val) * 100.0
            if spread > 5.0:
                # Moderate penalty: 0.2 point per 1% spread, max 5 points
                return -min(5.0, (spread - 5.0) * 0.2)
            return 0.0
        res['G_Score'] += res.apply(calc_spread_penalty, axis=1)

    # 3. Issuer Credit Risk Penalty (Fundamental FA stress)
    if 'O_Stock_FA' in res.columns:
        fa_score = res['O_Stock_FA'].fillna(50.0)
        # Max 5 points deduction if FA is extremely low
        res['G_Score'] -= ((50.0 - fa_score).clip(0, 50) * 0.1)

    # 4. Issuer Tiering Penalty / Bonus (Liquidity Provision Tiering)
    if 'issuer' in res.columns:
        def calc_issuer_adj(row):
            nph = str(row.get('issuer', '') or '').upper()
            if any(x in nph for x in ['SSI', 'HSC', 'VND', 'VCSC']):
                return 2.0  # +2 bonus for Tier 1
            if any(x in nph for x in ['VPBS', 'VPS', 'PHS', 'LPB', 'KAFI', 'SSV', 'MSVN']):
                return -3.0  # -3 penalty for Tier 3
            return 0.0
        res['G_Score'] += res.apply(calc_issuer_adj, axis=1)

    res['G_Score'] = res['G_Score'].fillna(35.0).clip(0, 100)

    # Health score incorporates Fundamental FA score and Sentiment AI scores
    res['P_Health'] = (res['O_Stock_FA'] * 0.7 + (res.get('N_Sentiment', 0) * 50 + 50) * 0.3).clip(0, 100)
    return res
 
def make_decision(row: Any, use_derivatives_filter: bool = False, market_regime: str = 'NEUTRAL') -> str:
    """
    Multi-layer decision engine cho giao dịch thực chiến.
 
    Lớp 1 — Hard Gates:     Loại ngay bất kể điểm số (an toàn tuyệt đối)
    Lớp 2 — Theta Bomb:     Cảnh báo hao mòn thời gian quá nhanh
    Lớp 3 — IV Signal:      Ưu tiên CW được định giá rẻ (IV < HV)
    Lớp 4 — Score Tiering:  Phân hạng khuyến nghị theo G_Score (Regime-aware)
    
    v2.1 Upgrade: Regime-aware signal thresholds
    BULLISH_VOL_CONTRACTION: More aggressive (lower thresholds)
    BULLISH_VOL_EXPANSION: Slightly aggressive
    BEARISH_VOL_CONTRACTION: More conservative (higher thresholds)
    BEARISH_VOL_EXPANSION: Very conservative (highest thresholds)
    NEUTRAL: Standard thresholds
    """
    # ── LỚP 1: Hard Gates — loại tức thì ────────────────────────────────────
    passed, reason = passes_hard_gates(row, use_derivatives_filter=use_derivatives_filter)
    if not passed:
        return f"SKIP ({reason})"
 
    # ── LỚP 1.2: CPCS Trend Gate — Chặn các mã có xu hướng giảm ────────────
    # BACKTEST MODE: Relaxed trend gate to allow more candidates
    ma_align = float(row.get('und_ma_align_score', 67.0) or 67.0)
    mom_score = float(row.get('und_mom_score', 50.0) or 50.0)
    if ma_align < 25 and mom_score < 35:  # Relaxed from 34/45 to 25/35
        return "SKIP (CPCS DOWNTREND)"

    # ── LỚP 2: Theta-Burn & Đáo hạn (Mô hình DVA thực chiến) ────────────────────────────
    cw_price = float(row.get('C_GiaCW', 0) or 0)
    theta    = abs(float(row.get('T_Theta', 0) or 0))
    theta_burn = theta / cw_price if cw_price > 0 else 0
    
    # Tính chi phí hao mòn 5 ngày (Theta Rent)
    theta_rent_5d = theta_burn * 5.0
    
    # Nếu chi phí hao mòn 5 ngày cắn quá 20% vốn, lập tức cảnh báo
    # BACKTEST MODE: Relaxed from 20% to 30% to allow more candidates
    if theta_rent_5d > 0.30:
        return f"CAUTION (5D Θ-Rent={theta_rent_5d*100:.1f}%)"
 
    # ── LỚP 3: Volatility Arbitrage (Săn lệch giá biến động) ──────────────────────────
    # Check if we have GARCH volatility vs Implied Volatility
    # Use S_GARCH_Vol_Pct from ranker.py
    garch_vol_pct = float(row.get('S_GARCH_Vol_Pct', 0) or 0)
    iv_pct = float(row.get('S_IV_Pct', 0) or 0)
    
    vol_arb_bonus = False
    if garch_vol_pct > 0 and iv_pct > 0:
        # Nếu biến động dự báo (GARCH) lớn hơn biến động nhà cái đang áp giá (IV) > 15% -> Mỏ vàng!
        if garch_vol_pct - iv_pct > 15.0:
            vol_arb_bonus = True
            
    # GARCH Fair Value Upside
    garch_upside = float(row.get('I_GARCH_Upside', 0) or 0)
 
    # ── LỚP 3.5: MM Hedging Pressure Bonus ──────────────────────────────────────────
    delta = float(row.get('T_Delta', 0) or 0)
    outstanding_vol = float(row.get('outstanding_volume', 0) or 0)
    mm_pressure_bonus = False
    if delta > 0.6 and outstanding_vol > 5000000:
        mm_pressure_bonus = True
 
    iv_signal = str(row.get('IV_vs_HV_Signal', ''))
    score = float(row.get('G_Score', 0) or 0)
 
    # ── REGIME-AWARE SIGNAL THRESHOLDS ───────────────────────────────────────
    # BACKTEST MODE: Optimized thresholds for high-quality signals only
    regime_thresholds = {
        'BULLISH_VOL_CONTRACTION': {
            'strong_buy': 65, 'strong_buy_bonus': 60, 'strong_buy_mm': 62,
            'buy': 55, 'buy_bonus': 50, 'buy_mm': 50, 'watch': 45
        },
        'BULLISH_VOL_EXPANSION': {
            'strong_buy': 68, 'strong_buy_bonus': 62, 'strong_buy_mm': 65,
            'buy': 58, 'buy_bonus': 52, 'buy_mm': 52, 'watch': 48
        },
        'BEARISH_VOL_CONTRACTION': {
            'strong_buy': 72, 'strong_buy_bonus': 66, 'strong_buy_mm': 70,
            'buy': 62, 'buy_bonus': 56, 'buy_mm': 56, 'watch': 52
        },
        'BEARISH_VOL_EXPANSION': {
            'strong_buy': 75, 'strong_buy_bonus': 68, 'strong_buy_mm': 72,
            'buy': 65, 'buy_bonus': 58, 'buy_mm': 58, 'watch': 55
        },
        'NEUTRAL': {
            'strong_buy': 70, 'strong_buy_bonus': 64, 'strong_buy_mm': 67,
            'buy': 60, 'buy_bonus': 54, 'buy_mm': 54, 'watch': 50
        },
        'UNKNOWN': {
            'strong_buy': 70, 'strong_buy_bonus': 64, 'strong_buy_mm': 67,
            'buy': 60, 'buy_bonus': 54, 'buy_mm': 54, 'watch': 50
        }
    }
    
    thresholds = regime_thresholds.get(market_regime, regime_thresholds['NEUTRAL'])
    
    # ── LỚP 4: Score Tiering ─────────────────────────────────────────────────
    cheap_bonus = 'CHEAP' in iv_signal  # Ưu tiên CW rẻ hơn HV
 
    if vol_arb_bonus and garch_upside > 0.2:
        return "VOL ARBITRAGE BUY" # Tín hiệu tấn công mạnh nhất
 
    if score >= thresholds['strong_buy'] or (score >= thresholds['strong_buy_bonus'] and (cheap_bonus or vol_arb_bonus)) or (score >= thresholds['strong_buy_mm'] and mm_pressure_bonus):
        return "STRONG BUY"
    if score >= thresholds['buy'] or (score >= thresholds['buy_bonus'] and (cheap_bonus or vol_arb_bonus)) or (score >= thresholds['buy_mm'] and mm_pressure_bonus):
        return "BUY"
    if score >= thresholds['watch']:
        return "WATCH"
    return "SKIP"

def get_latest_merton_credit(ticker: str) -> Tuple[float, float]:
    """Retrieve distance to default and default probability from SQLite database."""
    try:
        from backend.core.database import engine
        import pandas as pd
        query = f"SELECT distance_to_default, default_probability FROM corporate_merton_credit WHERE ticker = '{ticker}' ORDER BY date DESC LIMIT 1"
        res = pd.read_sql(query, engine)
        if not res.empty:
            return float(res['distance_to_default'].iloc[0]), float(res['default_probability'].iloc[0])
    except Exception:
        pass
    return None, None

def price_cw_with_credit_linkage(S: float, K: float, T: float, r: float, sigma: float, 
                                 underlying_symbol: str, option_type_is_call: bool = True, q: float = 0.0) -> Dict[str, Any]:
    """
    Prices a Covered Warrant by linking underlying Merton Structural Credit Risk.
    If the firm is distressed (PD > 1% or DD < 1.5), automatically switches to the
    Merton Jump-Diffusion model to account for sudden asset price drops.
    """
    dd, pd_val = get_latest_merton_credit(underlying_symbol)
    
    is_distressed = False
    model_used = 'BSM'
    price = 0.0
    
    if pd_val is not None and dd is not None:
        if pd_val > 0.01 or dd < 1.5:
            is_distressed = True
            model_used = 'Merton-Jump-Diffusion'
            
    if is_distressed:
        # Calibrate jump parameters based on distress severity
        severity = min(5.0, max(1.0, 1.5 / max(dd, 0.1)))
        lamb = 0.5 * severity      # jump frequency per year
        mu_J = -0.10 * severity     # average jump size (downward)
        sigma_J = 0.15 * severity   # jump volatility
        
        price = calculate_merton_jump_diffusion_price(
            S, K, T, r, sigma, lamb, mu_J, sigma_J, option_type_is_call, q=q
        )
    else:
        # Standard Black-Scholes
        d1, d2 = calculate_d1_d2(S, K, T, r, sigma, q)
        if option_type_is_call:
            price = S * math.exp(-q * T) * n_cdf(d1) - K * math.exp(-r * T) * n_cdf(d2)
        else:
            price = K * math.exp(-r * T) * n_cdf(-d2) - S * math.exp(-q * T) * n_cdf(-d1)
            
    return {
        'price': price,
        'model_used': model_used,
        'is_distressed': is_distressed,
        'distance_to_default': dd,
        'default_probability': pd_val
    }

