# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HISTORICAL DATA ETL (Extract, Transform, Load)
===========================================================
Loads the compiled historical CSV files (CW and Underlying Stocks) 
into the high-performance SQLite database (finvista.db).
This eliminates the need for the API and Backtester to read flat CSVs,
drastically improving query speeds.

Usage:
  python scripts/run_etl_history.py

Author: Antigravity
"""
import os
import sys
import pandas as pd
from sqlalchemy import text

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.common.database import engine, CWHistoricalPrice, StockHistoricalPrice, Base

# Force stdout encoding to UTF-8 to handle emojis on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    print("=" * 80)
    print(" 🚀 FINVISTA DATABASE ETL (HISTORICAL TIME-SERIES)")
    print("=" * 80)

    # 1. Ensure schemas exist
    Base.metadata.create_all(bind=engine)
    print("✅ Verified database schemas.")

    # Paths to the compiled CSVs
    cw_csv_path = os.path.join("data", "all_cw_historical_prices.csv")
    stock_csv_path = os.path.join("data", "all_stock_historical_prices.csv")

    with engine.begin() as conn:
        # 2. Ingest Covered Warrants
        if os.path.exists(cw_csv_path):
            print(f"📥 Loading CW historical data from {cw_csv_path}...")
            cw_df = pd.read_csv(cw_csv_path)
            if not cw_df.empty:
                # Clear existing table to perform a fresh sync
                conn.execute(text("DELETE FROM cw_history"))
                
                # Bulk insert using pandas
                # Ensure columns match the SQL model
                # model: id, symbol, date, open, high, low, close, volume, ref_price
                columns_to_keep = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
                if 'ref_price' in cw_df.columns:
                    columns_to_keep.append('ref_price')
                
                cw_df = cw_df[[col for col in columns_to_keep if col in cw_df.columns]]
                
                cw_df.to_sql("cw_history", con=conn, if_exists="append", index=False, chunksize=5000)
                print(f"   ✅ Successfully ingested {len(cw_df):,} CW records into SQLite database.")
        else:
            print(f"⚠️  Missing {cw_csv_path}")

        # 3. Ingest Underlying Stocks
        if os.path.exists(stock_csv_path):
            print(f"📥 Loading Stock historical data from {stock_csv_path}...")
            stock_df = pd.read_csv(stock_csv_path)
            if not stock_df.empty:
                # Clear existing table
                conn.execute(text("DELETE FROM stock_history"))
                
                columns_to_keep = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
                if 'ref_price' in stock_df.columns:
                    columns_to_keep.append('ref_price')
                
                stock_df = stock_df[[col for col in columns_to_keep if col in stock_df.columns]]
                
                stock_df.to_sql("stock_history", con=conn, if_exists="append", index=False, chunksize=1000)
                print(f"   ✅ Successfully ingested {len(stock_df):,} Stock records into SQLite database.")
        else:
            print(f"⚠️  Missing {stock_csv_path}")

    print("=" * 80)
    print("🎉 ETL pipeline completed successfully!")

if __name__ == "__main__":
    main()
