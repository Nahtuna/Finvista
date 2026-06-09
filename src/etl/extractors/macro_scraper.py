# -*- coding: utf-8 -*-
"""
📡 FINVISTA: MACRO DATA SCRAPER
==============================
Fetches real-time macro-economic indicators (Interbank rates, CPI, etc.)
using vnstock3 to keep the credit distress model updated.
"""

from vnstock import Vnstock
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from src.common.utils import logger
from src.common import config

def fetch_macro_indicators():
    """Fetches latest interbank rates and other macro data."""
    logger.info("📡 Fetching latest macro indicators from market sources (vnstock)...")

    try:
        # Initialize vnstock (v4.x standard)
        v = Vnstock()

        # 1. Fetch Interbank Rates (Money Market)
        start_date = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')

        # Fetch interbank rate data
        # Based on vnstock v4.x documentation/standard
        df_interbank = v.macro.money_market.interbank_rate(start_date=start_date)
        
        if df_interbank.empty:
            logger.warning("⚠️ No interbank rate data found. Using fallback values.")
            return None
            
        # Get latest Overnight (ON) rate
        on_rates = df_interbank[df_interbank['term'] == 'ON']
        if not on_rates.empty:
            latest_on = on_rates.iloc[-1]
            interbank_on_rate = float(latest_on['rate']) / 100.0 # 5.2 -> 0.052
            report_date = latest_on['date']
        else:
            interbank_on_rate = 0.045 # Fallback 4.5%
            report_date = datetime.now().strftime('%Y-%m-%d')

        # 2. Structure the data
        macro_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_date": str(report_date),
            "indicators": {
                "interbank_rate": interbank_on_rate,
                "inflation_rate": 0.041,      # Fallback/Manual for now (CPI changes monthly)
                "unemployment_rate": 0.023,
                "gdp_growth_rate": 0.065
            },
            "source": "vnstock / SBV"
        }
        
        # 3. Save to config directory
        output_path = os.path.join(config.DATA_DIR, "config", "macro_indicators.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(macro_data, f, indent=4, ensure_ascii=False)
            
        logger.info(f"✅ Macro indicators updated: Interbank Rate = {interbank_on_rate:.2%} (Date: {report_date})")
        return macro_data

    except Exception as e:
        logger.error(f"❌ Failed to fetch macro indicators: {e}")
        return None

if __name__ == "__main__":
    fetch_macro_indicators()
