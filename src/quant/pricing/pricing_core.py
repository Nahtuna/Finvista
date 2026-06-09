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
try:
    from src.common.utils import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

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

# Standard Risk-Free Rate for Vietnamese Market (Dynamically fetched)
RISK_FREE_RATE = fetch_dynamic_risk_free_rate()
logger.info(f"🎯 Dynamic Risk-Free Rate initialized at: {RISK_FREE_RATE:.2%}")

# ==========================================================
# 1. CORE BLACK-SCHOLES FORMULAS & GREEKS
# ==========================================

def calculate_d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
    """Calculate d1 and d2 parameters for Black-Scholes formula."""
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return 0.0, 0.0
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2

def calculate_merton_jump_diffusion_price(S: float, K: float, T: float, r: float, sigma: float, 
                                          lamb: float, mu_J: float, sigma_J: float, 
                                          option_type: str = 'call', max_n: int = 12) -> float:
    """
    Merton's Jump-Diffusion Option Pricing Model.
    Accounts for asset price jumps (fat tails) by adding a Poisson jump component.
    """
    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return max(S - K, 0.0) if option_type.lower() == 'call' else max(K - S, 0.0)
        
    kappa = np.exp(mu_J + 0.5 * sigma_J**2) - 1
    lamb_prime = lamb * (1 + kappa)
    
    price = 0.0
    fact = 1.0
    for n in range(max_n):
        if n > 0:
            fact *= n
        term_coef = np.exp(-lamb_prime * T) * ((lamb_prime * T)**n) / fact
        
        r_n = r - lamb * kappa + (n * np.log(1 + kappa)) / T
        sigma_n = np.sqrt(sigma**2 + (n * sigma_J**2) / T)
        
        # Calculate BS price
        d1, d2 = calculate_d1_d2(S, K, T, r_n, sigma_n)
        if option_type.lower() == 'call':
            bs_price = S * norm.cdf(d1) - K * np.exp(-r_n * T) * norm.cdf(d2)
        else:
            bs_price = K * np.exp(-r_n * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            
        price += term_coef * bs_price
        
    return float(price)

def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """Calculate Option Delta (Sensitivity to underlying asset price)."""
    if T <= 0:
        if option_type.lower() == 'call':
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    if option_type.lower() == 'call':
        return float(norm.cdf(d1))
    return float(norm.cdf(d1) - 1.0)

def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate Option Gamma (Rate of change of Delta)."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))

def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call', per_day: bool = True) -> float:
    """Calculate Option Theta (Time decay per day)."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)
    sqrt_T = np.sqrt(T)
    term1 = -(S * norm.pdf(d1) * sigma) / (2.0 * sqrt_T)
    if option_type.lower() == 'call':
        theta = term1 - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        theta = term1 + r * K * np.exp(-r * T) * norm.cdf(-d2)
    if per_day:
        return theta / 365.0
    return theta

def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate Option Vega (Sensitivity to a 1% absolute change in volatility)."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return S * norm.pdf(d1) * np.sqrt(T) * 0.01

def calculate_rho(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """Calculate Option Rho (Sensitivity to a 1% absolute change in risk-free interest rate)."""
    if T <= 0 or S <= 0 or sigma <= 0:
        return 0.0
    _, d2 = calculate_d1_d2(S, K, T, r, sigma)
    if option_type.lower() == 'call':
        return K * T * np.exp(-r * T) * norm.cdf(d2) * 0.01
    return -K * T * np.exp(-r * T) * norm.cdf(-d2) * 0.01

def calculate_all_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> Dict[str, float]:
    """Calculate all standard Greeks at once."""
    return {
        'delta': calculate_delta(S, K, T, r, sigma, option_type),
        'gamma': calculate_gamma(S, K, T, r, sigma),
        'theta': calculate_theta(S, K, T, r, sigma, option_type, per_day=True),
        'vega': calculate_vega(S, K, T, r, sigma),
        'rho': calculate_rho(S, K, T, r, sigma, option_type)
    }

def calculate_greeks_for_cw(
    underlying_price: float,
    strike_price: float,
    days_to_maturity: int,
    implied_volatility: float,
    conversion_ratio: float = 1.0,
    risk_free_rate: float = RISK_FREE_RATE,
    option_type: str = 'call'
) -> Dict[str, Any]:
    """Calculate Greeks specifically for Vietnamese Covered Warrants, adjusting for conversion ratio."""
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
    _, d2 = calculate_d1_d2(underlying_price, strike_price, T, risk_free_rate, implied_volatility)
    prob_itm = float(norm.cdf(d2)) if option_type.lower() == 'call' else float(norm.cdf(-d2))
    
    raw_greeks = calculate_all_greeks(underlying_price, strike_price, T, risk_free_rate, implied_volatility, option_type)
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

def estimate_implied_volatility(
    market_price: float,
    underlying_price: float,
    strike_price: float,
    days_to_maturity: int,
    risk_free_rate: float = RISK_FREE_RATE,
    option_type: str = 'call',
    max_iterations: int = 100,
    tolerance: float = 1e-5
) -> float:
    """Solve for Implied Volatility (IV) using Newton-Raphson method."""
    T = days_to_maturity / 365.0
    if T <= 0 or market_price <= 0:
        return 0.3
    
    sigma = 0.3 # Initial volatility guess
    
    for _ in range(max_iterations):
        d1, d2 = calculate_d1_d2(underlying_price, strike_price, T, risk_free_rate, sigma)
        if option_type.lower() == 'call':
            price = (underlying_price * norm.cdf(d1) - 
                     strike_price * np.exp(-risk_free_rate * T) * norm.cdf(d2))
        else:
            price = (strike_price * np.exp(-risk_free_rate * T) * norm.cdf(-d2) - 
                     underlying_price * norm.cdf(-d1))
                     
        diff = market_price - price
        if abs(diff) < tolerance:
            return sigma
            
        vega = underlying_price * norm.pdf(d1) * np.sqrt(T)
        if vega < 1e-10:
            break
            
        sigma = sigma + diff / vega
        sigma = max(0.01, min(sigma, 5.0)) # Bound checks
        
    return sigma

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
HARD_GATES = {
    'min_days_to_expiry':     15,     # < 15 ngày: Cấm chơi. Tránh bị Theta decay ăn mòn quá nhanh sát ngày đáo hạn.
    'min_gtgd_trieu':        150.0,   # Tăng thanh khoản tối thiểu lên 150 triệu/ngày để dễ dàng cắt lỗ không bị trượt giá.
    'max_premium_pct':        18.0,   # > 18% premium: Bị loại. Tiêu chí QUAN TRỌNG NHẤT, Premium quá cao là bị nhà cái úp sọt.
    'max_iv_pct':            100.0,   # > 100% IV: Bị loại. IV > 100% chứng tỏ giá CW đang bị đầu cơ vống lên trên trời.
    'min_delta':               0.15,  # < 0.15 Delta: Cấm Deep OTM. Không mua "vé số" vô vọng, xác suất về bờ gần bằng 0.
    'max_delta':               0.80,  # > 0.80 Delta: Quá ITM, đòn bẩy thấp như mua cổ phiếu thường.
    'max_theta_burn_rate':     0.05,  # Tối đa hao mòn 5%/ngày.
}

def passes_hard_gates(row: Any, use_derivatives_filter: bool = False) -> tuple:
    """
    Kiểm tra tất cả bộ lọc cứng. Trả về (True, '') nếu qua hết.
    Trả về (False, lý_do) nếu bị loại.
    """
    # ── LỚP 0: Corporate Credit Health Check (XGBoost ML) ────────────────
    is_dist = int(row.get('underlying_is_distressed', 0) or 0)
    altman_z = float(row.get('underlying_altman_z', 3.0) or 3.0)
    if is_dist == 1 or altman_z < 1.1:
        return False, "DISTRESSED ASSET"

    # ── LỚP 0.5: Systemic Contagion Gate (DebtRank Network Risk) ─────────
    sys_prob = float(row.get('underlying_systemic_prob', 0.10) or 0.10)
    sys_delta = float(row.get('underlying_systemic_delta', 0.0) or 0.0)
    if sys_prob >= 0.50:
        return False, f"SYSTEMIC RISK ({sys_prob:.0%})"
    if sys_delta >= 0.15:   # contagion risk jumped > 15% from base
        return False, f"CONTAGION SPIKE (+{sys_delta:.0%})"

    # ── LỚP 0.5: Derivatives Sentiment Adaptive Controls ────────────
    sentiment = str(row.get('market_sentiment', 'NEUTRAL')).upper()
    max_premium_gate = HARD_GATES['max_premium_pct']
    min_days_gate = HARD_GATES['min_days_to_expiry']
    
    if use_derivatives_filter and sentiment == 'BEARISH':
        max_premium_gate = 12.0  # Tighten premium threshold to protect against high-premium CWs
        min_days_gate = 30       # Tighten expiry threshold to avoid rapid theta decay in panic

    days       = float(row.get('L_Ngay', 0) or 0)
    gtgd       = float(row.get('E_GTGD', 0) or 0)          # đơn vị: triệu VND
    premium    = float(row.get('Premium_Pct', 999) or 999)
    iv         = float(row.get('S_IV_Pct', 999) or 999)
    delta      = float(row.get('T_Delta', 0) or 0)
    cw_price   = float(row.get('C_GiaCW', 0) or 0)
    theta      = abs(float(row.get('T_Theta', 0) or 0))
    theta_burn = theta / cw_price if cw_price > 0 else 0
    bid        = float(row.get('bid', 0) or 0)
    ask        = float(row.get('ask', 0) or 0)

    if days < min_days_gate:
        reason = "ĐÁO HẠN NHANH" if sentiment != 'BEARISH' else "BÃO PHÁI SINH (ĐÁO HẠN < 30N)"
        return False, f"{reason} ({int(days)}N)"
        
    # Xử lý Thanh khoản thông minh:
    # Buổi sáng (trước 10h) KLGD tự nhiên sẽ rất thấp. Ta đánh giá qua thanh khoản sổ lệnh (Bid/Ask).
    # Sau 10h, mới ép điều kiện KLGD (GTGD) tối thiểu.
    from datetime import datetime
    now = datetime.now()
    if now.hour == 9:
        if bid == 0 or ask == 0:
            return False, "TRỐNG MUA/BÁN"
        spread_pct = (ask - bid) / bid if bid > 0 else 999
        if spread_pct > 0.15: # Spread > 15% là quá rủi ro
            return False, f"SPREAD RỘNG ({spread_pct*100:.0f}%)"
    else:
        if gtgd < HARD_GATES['min_gtgd_trieu']:
            return False, "THANH KHOẢN THẤP"
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

def score_cw(df: pd.DataFrame, strategy: str = 'balanced') -> pd.DataFrame:
    """
    Score Covered Warrants based on strategy (Safe, Balanced, Aggressive)
    using robust financial scaling (handling outliers in volume, gearing and upside).
    """
    res = df.copy()
    if res.empty:
        return res
        
    def normalize(series, reverse=False):
        if series.max() == series.min():
            return series * 0 + 50
        norm = (series - series.min()) / (series.max() - series.min()) * 100
        return 100 - norm if reverse else norm

    # Robust scaling for volume: use log1p transformation to handle log-normal distribution
    res['norm_vol'] = normalize(np.log1p(res['D_Volume']))
    
    # Robust scaling for days to maturity: clip at 150 days (longer is great, no need to over-reward 300 days vs 150 days)
    res['norm_days'] = normalize(res['L_Ngay'].clip(0, 150))
    
    res['norm_prob'] = normalize(res['prob_itm'])
    
    # Robust scaling for gearing: clip at 15x (very high gearing is often too risky, 10x-15x is sweet)
    res['norm_gear'] = normalize(res['F_DonBay'].clip(0, 15))
    
    res['norm_iv'] = normalize(res['S_IV_Pct'], reverse=True)
    
    # Delta Sweet Spot (ATM optimization near 0.5)
    res['delta_score'] = res['T_Delta'].apply(lambda x: 100 - abs(x - 0.5) * 200).clip(0, 100)
    
    # Robust scaling for theoretical upside: clip between -100% and +200% to remove deep OTM price outliers
    clipped_upside = res['I_Upside'].clip(-1.0, 2.0)
    norm_upside = normalize(clipped_upside)
    
    sentiment = 'NEUTRAL'
    if not res.empty and 'market_sentiment' in res.columns:
        sentiment = str(res['market_sentiment'].iloc[0]).upper()

    if strategy == 'safe':
        if sentiment == 'BEARISH':
            # Ultra-safe profile in a bear market: emphasize ITM probability (35%), expiry (30%), low IV (20%), reduce volume (10%), Delta (5%)
            res['G_Score'] = (res['norm_prob'] * 0.35 + res['norm_days'] * 0.30 + 
                              res['norm_iv'] * 0.20 + res['norm_vol'] * 0.10 + res['delta_score'] * 0.05)
        elif sentiment == 'BULLISH':
            # Slightly more opportunistic: ITM probability (25%), expiry (20%), low IV (10%), volume (15%), Gearing (20%), Delta (10%)
            res['G_Score'] = (res['norm_prob'] * 0.25 + res['norm_days'] * 0.20 + 
                              res['norm_iv'] * 0.10 + res['norm_vol'] * 0.15 + res['norm_gear'] * 0.20 + res['delta_score'] * 0.10)
        else:
            # Probability ITM (30%) + Days to expiry (25%) + Liquidity (20%) + Low IV (15%) + Delta Sweet (10%)
            res['G_Score'] = (res['norm_prob'] * 0.3 + res['norm_days'] * 0.25 + 
                              res['norm_vol'] * 0.2 + res['norm_iv'] * 0.15 + res['delta_score'] * 0.1)
    elif strategy == 'aggressive':
        if sentiment == 'BEARISH':
            # Defensive aggressive: Gearing (20%), Upside (25%), ITM probability (20%), Expiry (15%), Liquidity (10%), Delta (10%)
            res['G_Score'] = (res['norm_gear'] * 0.20 + norm_upside * 0.25 + 
                              res['norm_prob'] * 0.20 + res['norm_days'] * 0.15 + res['norm_vol'] * 0.10 + res['delta_score'] * 0.10)
        elif sentiment == 'BULLISH':
            # Aggressive bull mode: Gearing (40%), Upside (35%), Delta (15%), Liquidity (10%)
            res['G_Score'] = (res['norm_gear'] * 0.40 + norm_upside * 0.35 + 
                              normalize(res['T_Delta']) * 0.15 + res['norm_vol'] * 0.10)
        else:
            # Leverage Gearing (35%) + Fair Value Upside (30%) + Target Delta (20%) + Liquidity (15%)
            res['G_Score'] = (res['norm_gear'] * 0.35 + norm_upside * 0.3 + 
                              normalize(res['T_Delta']) * 0.2 + res['norm_vol'] * 0.15)
    else: # balanced
        if sentiment == 'BEARISH':
            # Balanced-safe in bear market: Delta Sweet (25%), Probability ITM (25%), Expiry (20%), Liquidity (15%), Upside (15%)
            res['G_Score'] = (res['delta_score'] * 0.25 + res['norm_prob'] * 0.25 + 
                              res['norm_days'] * 0.20 + res['norm_vol'] * 0.15 + norm_upside * 0.15)
        elif sentiment == 'BULLISH':
            # Balanced-aggressive in bull market: Delta Sweet (20%), Gearing (20%), Upside (25%), Liquidity (20%), Probability ITM (15%)
            res['G_Score'] = (res['delta_score'] * 0.20 + res['norm_gear'] * 0.20 + 
                              norm_upside * 0.25 + res['norm_vol'] * 0.20 + res['norm_prob'] * 0.15)
        else:
            # Delta Sweet (30%) + Liquidity (20%) + Probability ITM (20%) + Upside (20%) + Expiry (10%)
            res['G_Score'] = (res['delta_score'] * 0.3 + res['norm_vol'] * 0.2 + 
                              res['norm_prob'] * 0.2 + norm_upside * 0.2 + res['norm_days'] * 0.1)
        
    # Health score incorporates Fundamental FA score and Sentiment AI scores
    res['P_Health'] = (res['O_Stock_FA'] * 0.7 + (res.get('N_Sentiment', 0) * 50 + 50) * 0.3).clip(0, 100)
    return res

def make_decision(row: Any, use_derivatives_filter: bool = False) -> str:
    """
    Multi-layer decision engine cho giao dịch thực chiến.

    Lớp 1 — Hard Gates:     Loại ngay bất kể điểm số (an toàn tuyệt đối)
    Lớp 2 — Theta Bomb:     Cảnh báo hao mòn thời gian quá nhanh
    Lớp 3 — IV Signal:      Ưu tiên CW được định giá rẻ (IV < HV)
    Lớp 4 — Score Tiering:  Phân hạng khuyến nghị theo G_Score
    """
    # ── LỚP 1: Hard Gates — loại tức thì ────────────────────────────────────
    passed, reason = passes_hard_gates(row, use_derivatives_filter=use_derivatives_filter)
    if not passed:
        return f"SKIP ({reason})"

    # ── LỚP 2: Theta Bomb — hao mòn/ngày quá lớn ────────────────────────────
    cw_price = float(row.get('C_GiaCW', 0) or 0)
    theta    = abs(float(row.get('T_Theta', 0) or 0))
    theta_burn = theta / cw_price if cw_price > 0 else 0
    if theta_burn > 0.04:  # Nhắc nhở nhẹ hơn Hard Gate: 4-6% → cảnh báo, > 6% đã bị chặn ở Lớp 1
        return f"CAUTION (Θ={theta_burn*100:.1f}%/ngày)"

    # ── LỚP 3: IV Signal — ưu tiên nếu CW đang rẻ ──────────────────────────
    iv_signal = str(row.get('IV_vs_HV_Signal', ''))
    score = float(row.get('G_Score', 0) or 0)

    # ── LỚP 4: Score Tiering ─────────────────────────────────────────────────
    cheap_bonus = 'CHEAP' in iv_signal  # Ưu tiên CW rẻ hơn HV

    if score >= 75 or (score >= 68 and cheap_bonus):
        return "STRONG BUY"
    if score >= 65 or (score >= 60 and cheap_bonus):
        return "BUY"
    if score >= 55:
        return "WATCH"
    return "SKIP"
