# -*- coding: utf-8 -*-
import os
import sys
import time
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.core.database import SessionLocal, CWHistoricalPrice
from backend.infra.scraper_engine import ScraperEngine
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        # Fetch all listed Covered Warrant symbols from Vietcap API
        cw_symbols = []
        try:
            import requests
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get("https://trading.vietcap.com.vn/api/price/symbols/getByGroup?group=CW", headers=headers, timeout=10)
            if resp.status_code == 200:
                cw_symbols = [item['symbol'] for item in resp.json() if item.get('symbol')]
        except Exception as e:
            print(f"Failed to fetch symbols from Vietcap API: {e}. Falling back to DB distinct symbols.")
            
        if not cw_symbols:
            cw_symbols = [r[0] for r in db.execute(text("SELECT DISTINCT symbol FROM cw_history")).fetchall()]
            
        print(f"Starting FULL history crawl for {len(cw_symbols)} CW symbols from 2025-01-01...")
        
        engine = ScraperEngine()
        start_date = "2025-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        for idx, ticker in enumerate(cw_symbols):
            print(f"[{idx+1}/{len(cw_symbols)}] Crawling full history for {ticker}...")
            try:
                # Fetch full history from vnstock using the engine helper
                records = engine._fetch_ohlcv_vnstock(ticker, start_date, end_date, is_cw=True)
                if not records:
                    print(f"  No records found for {ticker}")
                    # Sleep slightly even if no records to respect rate limits
                    time.sleep(2.0)
                    continue
                
                # Insert / Update records in database
                inserted = 0
                updated = 0
                for rec in records:
                    # Calculate ref_price fallback
                    ref_val = rec.get("ref_price")
                    if not ref_val:
                        prev_row = db.query(CWHistoricalPrice).filter(
                            CWHistoricalPrice.symbol == ticker,
                            CWHistoricalPrice.date < rec["date"]
                        ).order_by(CWHistoricalPrice.date.desc()).first()
                        ref_val = prev_row.close if prev_row else rec.get("close")
                        
                    existing = db.query(CWHistoricalPrice).filter(
                        CWHistoricalPrice.symbol == ticker,
                        CWHistoricalPrice.date == rec["date"]
                    ).first()
                    
                    if existing:
                        existing.close = rec.get("close")
                        existing.volume = rec.get("volume")
                        existing.high = rec.get("high")
                        existing.low = rec.get("low")
                        existing.open = rec.get("open")
                        existing.ref_price = ref_val
                        updated += 1
                    else:
                        new_rec = CWHistoricalPrice(
                            symbol=ticker,
                            date=rec["date"],
                            open=rec.get("open"),
                            high=rec.get("high"),
                            low=rec.get("low"),
                            close=rec.get("close"),
                            volume=rec.get("volume"),
                            ref_price=ref_val,
                        )
                        db.add(new_rec)
                        inserted += 1
                
                db.commit()
                print(f"  Success: {inserted} inserted, {updated} updated")
                
            except Exception as e:
                print(f"  Error crawling {ticker}: {e}")
                db.rollback()
                
            # Safe delay between requests to completely avoid rate limiting
            # 5.0 seconds delay keeps us well under the 60 requests/minute limit
            time.sleep(5.0)
            
        print("FULL history crawl completed successfully!")
    finally:
        db.close()

if __name__ == '__main__':
    main()
