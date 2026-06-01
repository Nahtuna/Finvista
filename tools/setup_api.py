# -*- coding: utf-8 -*-
"""
Setup and API test tool for the Financial Distress Prediction Pipeline.
Verifies dependencies like vnstock and tests basic data pulling.
"""

import sys
from src.common.utils import logger

def verify_environment():
    """Checks for necessary packages and logs status."""
    logger.info("🔍 Checking environment dependencies...")
    required_packages = {
        "pandas": "pandas",
        "numpy": "numpy",
        "requests": "requests",
        "tqdm": "tqdm",
        "vnstock": "vnstock"
    }
    
    missing_any = False
    for label, package in required_packages.items():
        try:
            __import__(package)
            logger.info(f"   ✅ {label} is installed.")
        except ImportError:
            logger.error(f"   ❌ {label} is missing! Install using: pip install {package}")
            missing_any = True
            
    if missing_any:
        logger.warning("⚠️ Some dependencies are missing. Pipeline may not run correctly.")
        return False
        
    logger.info("🎉 Environment check passed!")
    return True

def test_api_connection():
    """Tests basic connectivity to vnstock APIs."""
    logger.info("🌐 Testing connection to vnstock financial APIs...")
    try:
        from vnstock import listing_companies
        
        # Test pulling companies list
        df = listing_companies()
        if df is not None and not df.empty:
            logger.info(f"   ✅ API test successful! Fetched {len(df)} listed tickers from exchange.")
            logger.info(f"   💡 Sample tickers: {', '.join(df['ticker'].head().tolist())}")
            return True
        else:
            logger.warning("   ⚠️ API returned empty company list. Might be offline or blocked.")
            return False
    except Exception as e:
        logger.error(f"   ❌ API connection failed. Error: {e}")
        logger.info("   💡 Note: A simulated fallback data generator will be used if real APIs fail.")
        return False

def main():
    logger.info("=============================================")
    logger.info("🏁 INITIALIZING FINANCIAL DISTRESS PIPELINE SETUP")
    logger.info("=============================================")
    env_ok = verify_environment()
    api_ok = False
    if env_ok:
        api_ok = test_api_connection()
        
    if env_ok and api_ok:
        logger.info("✅ Everything is set up! You are ready to run: python run_pipeline.py")
    else:
        logger.warning("⚠️ Setup finished with warnings. The pipeline will run in hybrid/fallback mode.")
    logger.info("=============================================")

if __name__ == "__main__":
    main()
