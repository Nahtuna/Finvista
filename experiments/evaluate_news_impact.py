# -*- coding: utf-8 -*-
"""
📊 FINVISTA: NEWS & EVENT IMPACT EVALUATOR
==========================================
Statistical backtesting of how corporate news/events affect warrant prices.
Cross-references database news with historical CSV price data.
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import desc

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.common.database import SessionLocal, CorporateNews, CorporateEvent
from src.common import config

def evaluate_news_impact(lookback_days: int = 5):
    """Analyze the average price impact after specific news types."""
    db = SessionLocal()
    
    try:
        # 1. Load historical prices
        cw_prices = pd.read_csv(os.path.join("data", "processed", "all_cw_historical_prices.csv"))
        cw_prices['date'] = pd.to_datetime(cw_prices['date'])
        
        # 2. Fetch all news
        all_news = db.query(CorporateNews).all()
        
        results = []
        for news in all_news:
            try:
                # Handle potential date string issues
                news_date_str = news.date.split(" ")[0]
                news_date = pd.to_datetime(news_date_str, errors='coerce')
                if pd.isna(news_date): continue
                
                target_symbol = news.symbol
                
                # Ensure timezone naive for comparison
                if news_date.tzinfo is not None:
                    news_date = news_date.replace(tzinfo=None)
                
                # Find price movement for this symbol after news_date
                post_news_prices = cw_prices[
                    (cw_prices['symbol'] == target_symbol) & 
                    (cw_prices['date'] >= news_date) & 
                    (cw_prices['date'] <= news_date + timedelta(days=lookback_days))
                ].sort_values('date')
            
                if len(post_news_prices) >= 2:
                    start_p = post_news_prices.iloc[0]['close']
                    end_p = post_news_prices.iloc[-1]['close']
                    change_pct = (end_p - start_p) / start_p * 100
                    
                    results.append({
                        "symbol": target_symbol,
                        "category": news.category,
                        "change_pct": change_pct,
                        "title": news.title
                    })
            except Exception:
                continue
        
        if not results:
            print("⚠️ No enough price data to match news events.")
            return

        df_results = pd.DataFrame(results)
        
        print("\n" + "="*60)
        print("📊 HISTORICAL NEWS IMPACT STATISTICS")
        print("="*60)
        
        summary = df_results.groupby('category')['change_pct'].agg(['mean', 'count', 'std']).reset_index()
        summary = summary.sort_values('mean', ascending=False)
        
        for _, row in summary.iterrows():
            print(f"🔹 {row['category']:<20} | Count: {int(row['count']):>3} | Avg Impact: {row['mean']:>6.2f}%")
            
        print("="*60)
        
    except Exception as e:
        print(f"❌ Impact evaluation failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    evaluate_news_impact()
