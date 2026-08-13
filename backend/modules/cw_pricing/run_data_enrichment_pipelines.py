# -*- coding: utf-8 -*-
"""
🚀 FINVISTA: DATA ENRICHMENT PIPELINES
======================================
Master script to run all data enrichment pipelines for market_opportunities table.
1. Banking Indicators (NIM, CASA, CAR, NPL)
2. Regime Probabilities (bull_prob, base_prob, bear_prob)
3. Leland Model (leland_theoretical_price, leland_upside_pct)

Author: samvo
"""

import logging
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data_enrichment_pipelines.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def run_banking_indicators_pipeline():
    """Run banking indicators pipeline."""
    logger.info("=" * 80)
    logger.info("RUNNING BANKING INDICATORS PIPELINE")
    logger.info("=" * 80)
    
    try:
        from backend.modules.cw_pricing.banking_indicators_pipeline import update_market_opportunities_with_bank_indicators
        update_market_opportunities_with_bank_indicators()
        logger.info("Banking indicators pipeline completed successfully")
        return True
    except Exception as e:
        logger.error(f"Banking indicators pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_regime_probabilities_pipeline():
    """Run regime probabilities pipeline."""
    logger.info("=" * 80)
    logger.info("RUNNING REGIME PROBABILITIES PIPELINE")
    logger.info("=" * 80)
    
    try:
        from backend.modules.cw_pricing.regime_probabilities_pipeline import update_market_opportunities_with_regime_probabilities
        update_market_opportunities_with_regime_probabilities()
        logger.info("Regime probabilities pipeline completed successfully")
        return True
    except Exception as e:
        logger.error(f"Regime probabilities pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_leland_model_pipeline():
    """Run Leland model pipeline."""
    logger.info("=" * 80)
    logger.info("RUNNING LELAND MODEL PIPELINE")
    logger.info("=" * 80)
    
    try:
        from backend.modules.cw_pricing.leland_model_pipeline import update_market_opportunities_with_leland_prices
        update_market_opportunities_with_leland_prices()
        logger.info("Leland model pipeline completed successfully")
        return True
    except Exception as e:
        logger.error(f"Leland model pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all data enrichment pipelines."""
    logger.info("=" * 80)
    logger.info("STARTING DATA ENRICHMENT PIPELINES")
    logger.info(f"Start time: {datetime.now()}")
    logger.info("=" * 80)
    
    results = {}
    
    # Run pipelines
    results['banking_indicators'] = run_banking_indicators_pipeline()
    results['regime_probabilities'] = run_regime_probabilities_pipeline()
    results['leland_model'] = run_leland_model_pipeline()
    
    # Summary
    logger.info("=" * 80)
    logger.info("PIPELINE EXECUTION SUMMARY")
    logger.info("=" * 80)
    
    for pipeline, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"{pipeline.replace('_', ' ').title()}: {status}")
    
    all_success = all(results.values())
    
    logger.info("=" * 80)
    if all_success:
        logger.info("ALL PIPELINES COMPLETED SUCCESSFULLY")
    else:
        logger.warning("SOME PIPELINES FAILED - CHECK LOGS")
    logger.info(f"End time: {datetime.now()}")
    logger.info("=" * 80)
    
    return 0 if all_success else 1

if __name__ == "__main__":
    exit(main())
