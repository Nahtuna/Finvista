# -*- coding: utf-8 -*-
"""
🚀 FINVISTA: MASTER ORCHESTRATOR
================================
The "Brain" that coordinates all scheduled tasks:
- Ingestion (Price & News)
- Quant Analysis
- Credit Evaluation
- AI Committee Reviews
- Alert Dispatching (Telegram)
"""

import os
import sys
import time
from datetime import datetime
from src.common.utils import logger
from src.etl.extractors.vietstock_scraper import VietstockScraper
from src.etl.extractors.macro_scraper import fetch_macro_indicators
from src.quant.engines.run_analysis import run_quant_pipeline_programmatic
from src.common.news_alerts import dispatch_news_alerts, dispatch_event_alerts
from src.common.telegram_alerts import send_telegram_alert_batch, send_credit_distress_alert_batch

class FinvistaOrchestrator:
    def __init__(self):
        self.last_full_run = None
        self.last_news_crawl = None

    def run_morning_prep(self):
        """Pre-market preparation (08:30 - 09:00)."""
        logger.info("🌅 [Orchestrator] Running Morning Preparation...")
        
        # 1. Fetch Macro Data
        fetch_macro_indicators()
        
        # 2. Deep News Crawl
        scraper = VietstockScraper()
        scraper.run(limit=10) # Process top 10 underlyings deeply
        
        # 3. Dispatch Alerts
        dispatch_news_alerts(limit=5)
        dispatch_event_alerts(limit=3)
        
        logger.info("✅ [Orchestrator] Morning Prep Complete.")

    def run_market_loop(self):
        """Intra-day market monitoring loop."""
        now = datetime.now()
        is_weekday = now.weekday() < 5
        time_str = now.strftime("%H:%M:%S")
        
        in_morning = "09:15:00" <= time_str <= "11:30:00"
        in_afternoon = "13:00:00" <= time_str <= "14:45:00"
        
        if not is_weekday:
            return

        if in_morning or in_afternoon:
            logger.info(f"📈 [Orchestrator] Market Open ({time_str}). Running live analysis...")
            
            # 1. Run Quant Pipeline
            df = run_quant_pipeline_programmatic(strategy="balanced")
            
            # 2. Identify signals for Telegram
            if df is not None and not df.empty:
                # Filter for signals to alert
                buy_signals = df[df['U_Signal'].isin(['STRONG BUY', 'BUY'])].to_dict('records')
                # (You might want more logic here to only alert NEW signals)
                # send_telegram_alert_batch(buy_signals, []) 
                pass

            # 3. Quick News Refresh (every 30 mins)
            if self.last_news_crawl is None or (now - self.last_news_crawl).total_seconds() > 1800:
                scraper = VietstockScraper()
                scraper.run(limit=5)
                dispatch_news_alerts(limit=3)
                self.last_news_crawl = now

    def start(self):
        """Start the continuous orchestration service."""
        logger.info("🚀 Finvista Master Orchestrator Started.")
        
        # Initial run
        self.run_morning_prep()
        
        try:
            while True:
                self.run_market_loop()
                time.sleep(300) # Check every 5 minutes
        except KeyboardInterrupt:
            logger.info("🛑 Orchestrator stopped.")

if __name__ == "__main__":
    orchestrator = FinvistaOrchestrator()
    orchestrator.start()
