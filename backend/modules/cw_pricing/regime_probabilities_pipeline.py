# -*- coding: utf-8 -*-
"""
FINVISTA: REGIME PROBABILITIES PIPELINE
=========================================
Populates regime probabilities (bull_prob, base_prob, bear_prob) into market_opportunities table.
Uses ML model predictions from regime analysis module.

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

def get_regime_probabilities_for_underlying(ticker: str) -> Dict[str, float]:
    """Get regime probabilities for a specific underlying ticker."""
    try:
        from backend.modules.regime_analysis.indicators.ensemble_regime_engine import EnsembleRegimeEngine
        
        # Initialize ensemble engine
        engine_regime = EnsembleRegimeEngine(
            use_ml_forecast=True,
            ml_horizon=1,
            instrument_type="STOCK",
            performance_mode="FULL"
        )
        
        # Fetch historical data for the ticker
        import vnstock as vn
        quote = vn.Quote(symbol=ticker, source='VCI')
        df = quote.history(start='2024-01-01', end='2025-12-31')
        
        if df is None or df.empty:
            logger.warning(f"No historical data found for {ticker}")
            return {}
        
        # Get regime prediction using the correct method
        prediction = engine_regime.analyze_regime(df, ticker)
        
        # Extract probabilities from prediction
        probabilities = {
            'bull_prob': prediction.get('bull_prob', 0.33),
            'base_prob': prediction.get('base_prob', 0.34),
            'bear_prob': prediction.get('bear_prob', 0.33)
        }
        
        return probabilities
        
    except Exception as e:
        logger.error(f"Error fetching regime probabilities for {ticker}: {e}")
        return {}

def update_market_opportunities_with_regime_probabilities():
    """Update market_opportunities table with regime probabilities for all underlyings."""
    with SessionLocal() as session:
        # Get distinct underlyings
        result = session.execute(text("SELECT DISTINCT underlying FROM market_opportunities"))
        underlyings = [row[0] for row in result.fetchall()]
    
    logger.info(f"Found {len(underlyings)} underlyings to update regime probabilities")
    
    updated_count = 0
    for ticker in underlyings:
        try:
            # Fetch regime probabilities
            probabilities = get_regime_probabilities_for_underlying(ticker)
            
            if not probabilities:
                logger.warning(f"No regime probabilities found for {ticker}, using defaults")
                probabilities = {'bull_prob': 0.33, 'base_prob': 0.34, 'bear_prob': 0.33}
            
            # Update database
            with SessionLocal() as session:
                update_query = text("""
                    UPDATE market_opportunities 
                    SET 
                        bull_prob = :bull_prob,
                        base_prob = :base_prob,
                        bear_prob = :bear_prob
                    WHERE underlying = :ticker
                """)
                
                session.execute(update_query, {
                    'bull_prob': probabilities['bull_prob'],
                    'base_prob': probabilities['base_prob'],
                    'bear_prob': probabilities['bear_prob'],
                    'ticker': ticker
                })
                session.commit()
                
                updated_count += session.execute(text("SELECT changes()")).scalar()
                logger.info(f"Updated {ticker}: Bull={probabilities['bull_prob']:.2f}, Base={probabilities['base_prob']:.2f}, Bear={probabilities['bear_prob']:.2f}")
                
        except Exception as e:
            logger.error(f"Error updating regime probabilities for {ticker}: {e}")
            continue
    
    logger.info(f"Regime probabilities pipeline complete. Updated {updated_count} records.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_market_opportunities_with_regime_probabilities()
