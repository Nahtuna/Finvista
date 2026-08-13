# -*- coding: utf-8 -*-
"""
FINVISTA: BANKING INDICATORS PIPELINE
=========================================
Populates banking indicators (NIM, CASA, CAR, NPL) into market_opportunities table.
Integrates with existing bank_scoring module to fetch data from vnstock.

Author: samvo
"""

import logging
import sys
import os
from typing import Dict, List
import pandas as pd
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.core.database import SessionLocal, engine

logger = logging.getLogger(__name__)

def get_banking_underlyings() -> List[str]:
    """Get list of banking sector underlying stocks from market_opportunities."""
    with SessionLocal() as session:
        result = session.execute(text("""
            SELECT DISTINCT underlying 
            FROM market_opportunities 
            WHERE underlying IN ('ACB', 'VCB', 'MBB', 'TCB', 'HDB', 'LPB', 'SSB', 'STB', 'TPB', 'VPB', 'VIB', 'SHB')
        """))
        return [row[0] for row in result.fetchall()]

def fetch_bank_indicators(ticker: str) -> Dict[str, float]:
    """Fetch banking indicators for a specific ticker using vnstock."""
    try:
        from vnstock import Company
        company = Company(symbol=ticker, source='VCI')
        df_ratios = company.ratio_df(period='year')
        
        if df_ratios is None or df_ratios.empty:
            logger.warning(f"No ratio data found for {ticker}")
            return {}
        
        # Use existing bank_scoring module
        from backend.modules.credit_risk.models.bank_scoring import get_bank_metrics_from_df
        metrics = get_bank_metrics_from_df(df_ratios, ticker)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error fetching bank indicators for {ticker}: {e}")
        return {}

def update_market_opportunities_with_bank_indicators():
    """Update market_opportunities table with banking indicators for all banking underlyings."""
    banking_underlyings = get_banking_underlyings()
    logger.info(f"Found {len(banking_underlyings)} banking underlyings: {banking_underlyings}")
    
    updated_count = 0
    for ticker in banking_underlyings:
        try:
            # Fetch indicators
            indicators = fetch_bank_indicators(ticker)
            
            if not indicators:
                logger.warning(f"No indicators found for {ticker}, skipping")
                continue
            
            # Update database
            with SessionLocal() as session:
                update_query = text("""
                    UPDATE market_opportunities 
                    SET 
                        underlying_nim = :nim,
                        underlying_npl = :npl,
                        underlying_casa = :casa,
                        underlying_car = :car
                    WHERE underlying = :ticker
                """)
                
                session.execute(update_query, {
                    'nim': indicators.get('nim'),
                    'npl': indicators.get('npl'),
                    'casa': indicators.get('casa'),
                    'car': indicators.get('car'),
                    'ticker': ticker
                })
                session.commit()
                
                updated_count += session.execute(text("SELECT changes()")).scalar()
                logger.info(f"Updated {ticker}: NIM={indicators.get('nim'):.3f}, NPL={indicators.get('npl'):.3f}, CASA={indicators.get('casa'):.3f}, CAR={indicators.get('car'):.3f}")
                
        except Exception as e:
            logger.error(f"Error updating indicators for {ticker}: {e}")
            continue
    
    logger.info(f"Banking indicators pipeline complete. Updated {updated_count} records.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_market_opportunities_with_bank_indicators()
