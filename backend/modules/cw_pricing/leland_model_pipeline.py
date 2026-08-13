# -*- coding: utf-8 -*-
"""
FINVISTA: LELAND MODEL PIPELINE
=================================
Implements Leland's model for option pricing with transaction costs.
Populates leland_theoretical_price and leland_upside_pct into market_opportunities table.

Leland Model:
- Adjusts volatility for transaction costs
- σ_leland = σ * sqrt(1 + (2k / (σ * sqrt(2π * T))))
- Where k is transaction cost per unit

Author: samvo
"""

import logging
import sys
import os
import math
from typing import Dict, Tuple
import pandas as pd
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.core.database import SessionLocal, engine

logger = logging.getLogger(__name__)

def calculate_leland_adjusted_volatility(sigma: float, T: float, k: float = 0.002) -> float:
    """
    Calculate Leland-adjusted volatility with transaction costs.
    
    Args:
        sigma: Original volatility (annualized)
        T: Time to maturity (years)
        k: Transaction cost per unit (default 0.2%)
    
    Returns:
        Adjusted volatility
    """
    if sigma <= 0 or T <= 0:
        return sigma
    
    # Leland adjustment factor
    adjustment_factor = math.sqrt(1 + (2 * k) / (sigma * math.sqrt(2 * math.pi * T)))
    
    return sigma * adjustment_factor

def calculate_black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, 
                                  option_type: str = 'call', q: float = 0.0) -> float:
    """
    Calculate Black-Scholes option price.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to maturity (years)
        r: Risk-free rate
        sigma: Volatility
        option_type: 'call' or 'put'
        q: Dividend yield
    
    Returns:
        Option price
    """
    if T <= 0:
        return max(S - K, 0) if option_type == 'call' else max(K - S, 0)
    
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    from scipy.stats import norm
    
    if option_type == 'call':
        price = S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)
    
    return price

def calculate_leland_price(row: Dict, transaction_cost: float = 0.002) -> Tuple[float, float]:
    """
    Calculate Leland theoretical price and upside for a CW.
    
    Args:
        row: Dictionary containing CW parameters
        transaction_cost: Transaction cost per unit
    
    Returns:
        Tuple of (leland_price, leland_upside_pct)
    """
    try:
        # Extract parameters
        S = float(row.get('underlying_price', 0))
        K = float(row.get('strike_price', 0))
        T = float(row.get('days_to_maturity', 0)) / 365.0  # Convert days to years
        r = 0.05  # Risk-free rate (5%)
        sigma = float(row.get('implied_volatility_pct', 0)) / 100.0  # Convert to decimal
        q = 0.0  # No dividends for most Vietnamese stocks
        
        if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
            return 0.0, 0.0
        
        # Calculate Leland-adjusted volatility
        sigma_leland = calculate_leland_adjusted_volatility(sigma, T, transaction_cost)
        
        # Calculate Leland price
        leland_price = calculate_black_scholes_price(S, K, T, r, sigma_leland, 'call', q)
        
        # Calculate upside
        current_price = float(row.get('price', 0))
        if current_price > 0:
            leland_upside_pct = (leland_price - current_price) / current_price
        else:
            leland_upside_pct = 0.0
        
        return leland_price, leland_upside_pct
        
    except Exception as e:
        logger.error(f"Error calculating Leland price: {e}")
        return 0.0, 0.0

def update_market_opportunities_with_leland_prices():
    """Update market_opportunities table with Leland theoretical prices."""
    with SessionLocal() as session:
        # Get all CWs with required parameters
        result = session.execute(text("""
            SELECT 
                symbol, underlying_price, strike_price, days_to_maturity, 
                implied_volatility_pct, price
            FROM market_opportunities 
            WHERE underlying_price > 0 AND strike_price > 0 
              AND days_to_maturity > 0 AND implied_volatility_pct > 0
        """))
        
        cw_list = result.fetchall()
    
    logger.info(f"Found {len(cw_list)} CWs to calculate Leland prices")
    
    updated_count = 0
    for row in cw_list:
        try:
            row_dict = {
                'symbol': row[0],
                'underlying_price': row[1],
                'strike_price': row[2],
                'days_to_maturity': row[3],
                'implied_volatility_pct': row[4],
                'price': row[5]
            }
            
            # Calculate Leland price
            leland_price, leland_upside = calculate_leland_price(row_dict)
            
            # Update database
            with SessionLocal() as session:
                update_query = text("""
                    UPDATE market_opportunities 
                    SET 
                        leland_theoretical_price = :leland_price,
                        leland_upside_pct = :leland_upside
                    WHERE symbol = :symbol
                """)
                
                session.execute(update_query, {
                    'leland_price': leland_price,
                    'leland_upside': leland_upside,
                    'symbol': row_dict['symbol']
                })
                session.commit()
                
                updated_count += 1
                logger.info(f"Updated {row_dict['symbol']}: Leland Price={leland_price:.2f}, Upside={leland_upside*100:.1f}%")
                
        except Exception as e:
            logger.error(f"Error updating Leland price for {row[0]}: {e}")
            continue
    
    logger.info(f"Leland model pipeline complete. Updated {updated_count} records.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_market_opportunities_with_leland_prices()
