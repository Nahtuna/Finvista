# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HISTORICAL MARKET INDICES BACKFILL PIPELINE
======================================================
Downloads full historical daily data (OHLCV) for market indices (VNINDEX, VN30)
from 2016-01-01 to today in chunks of 90 days (due to vnstock API pagination limit of 100 rows).
For UPCOM and HNXINDEX, uses VPS datafeed (histdatafeed.vps.com.vn) which supports all VN indices.
Merges and cleans data, then populates the stock_history SQLite table.
"""

import os
import sys
import time
from datetime import datetime, timedelta
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.core.database import SessionLocal, StockHistoricalPrice
from sqlalchemy import text

# Suppress vnstock banners
import contextlib
with contextlib.redirect_stdout(open(os.devnull, 'w')), \
     contextlib.redirect_stderr(open(os.devnull, 'w')):
    from vnstock import Market


def get_date_chunks(start_date: datetime, end_date: datetime, chunk_days: int = 90):
    chunks = []
    curr = start_date
    while curr < end_date:
        next_date = min(curr + timedelta(days=chunk_days), end_date)
        chunks.append((curr.strftime("%Y-%m-%d"), next_date.strftime("%Y-%m-%d")))
        curr = next_date + timedelta(days=1)
    return chunks


def backfill_index(symbol: str, start_year: int = 2016):
    print(f"Starting backfill for index: {symbol}...")
    
    start_date = datetime(start_year, 1, 1)
    # Check if the date chunk is within range (vnstock / CafeF limit is 100 days)
    end_date = datetime.now()
    chunks = get_date_chunks(start_date, end_date, chunk_days=80)
    
    market = Market()
    
    # Try to fetch index data
    try:
        idx = market.index(symbol=symbol)
    except Exception as e:
        print(f"⚠️ Could not fetch index {symbol} from vnstock: {e}")
        return
    
    all_dfs = []
    
    for i, (s_str, e_str) in enumerate(chunks):
        print(f"  [{i+1}/{len(chunks)}] Fetching {symbol} from {s_str} to {e_str}...")
        try:
            df = idx.ohlcv(start=s_str, end=e_str, resolution='1D')
            if df is not None and not df.empty:
                # Reset index to get time column if it's in index
                if df.index.name == 'time' or df.index.name == 'date':
                    df = df.reset_index()
                all_dfs.append(df)
            time.sleep(0.5)  # Cooldown to respect rate limit
        except Exception as e:
            print(f"  Error fetching chunk {s_str} -> {e_str}: {e}")
            time.sleep(2.0)
            
    if not all_dfs:
        print(f"Error: Failed to fetch any data for {symbol}.")
        return
        
    master_df = pd.concat(all_dfs, ignore_index=True)
    
    # Standardize columns
    time_col = 'time' if 'time' in master_df.columns else ('date' if 'date' in master_df.columns else master_df.columns[0])
    master_df = master_df.rename(columns={
        time_col: 'date',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    })
    
    # Format date
    master_df['date'] = pd.to_datetime(master_df['date']).dt.strftime('%Y-%m-%d')
    master_df = master_df.drop_duplicates(subset=['date']).sort_values('date')
    
    print(f"Downloaded {len(master_df)} rows for {symbol} ({master_df['date'].min()} to {master_df['date'].max()})")
    
    # Insert to DB
    db = SessionLocal()
    try:
        # Delete existing data to avoid primary key/unique constraint conflicts
        deleted = db.query(StockHistoricalPrice).filter(StockHistoricalPrice.symbol == symbol).delete()
        print(f"  Deleted {deleted} pre-existing rows for {symbol} in stock_history")
        db.commit()
        
        db.bulk_save_objects([
            StockHistoricalPrice(
                symbol=symbol,
                date=row['date'],
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume']) if pd.notna(row['volume']) else 0.0,
                ref_price=float(row['open'])
            )
            for _, row in master_df.iterrows()
        ])
        db.commit()
        print(f"Successfully inserted {len(master_df)} rows for {symbol} into stock_history!")
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def backfill_index_vps(symbol: str, start_year: int = 2020):
    """Fetch index OHLCV from VPS datafeed. Works for UPCOM, HNXINDEX, VNINDEX, VN30.
    VPS symbol mapping: UPCOM -> UPCOMINDEX, others same.
    """
    import requests
    from datetime import timezone

    VPS_SYMBOL_MAP = {"UPCOM": "UPCOMINDEX"}
    vps_sym = VPS_SYMBOL_MAP.get(symbol, symbol)

    start_ts = int(datetime(start_year, 1, 1, tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime.now(tz=timezone.utc).timestamp())

    print(f"Starting VPS backfill for {symbol} (vps: {vps_sym})...")
    try:
        url = f"https://histdatafeed.vps.com.vn/tradingview/history?symbol={vps_sym}&resolution=D&from={start_ts}&to={end_ts}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("s") != "ok" or not data.get("t"):
            print(f"⚠️ VPS returned no data for {symbol}: {data.get('s')}")
            return
    except Exception as e:
        print(f"⚠️ VPS fetch failed for {symbol}: {e}")
        return

    # Build DataFrame from VPS response arrays
    df = pd.DataFrame({
        "date": pd.to_datetime(data["t"], unit="s").strftime("%Y-%m-%d"),
        "open": [float(x) for x in data.get("o", data["c"])],
        "high": [float(x) for x in data.get("h", data["c"])],
        "low": [float(x) for x in data.get("l", data["c"])],
        "close": [float(x) for x in data["c"]],
        "volume": [float(x) for x in data.get("v", [0] * len(data["c"]))],
    })
    df = df.drop_duplicates(subset=["date"]).sort_values("date")
    print(f"  Downloaded {len(df)} rows ({df['date'].min()} → {df['date'].max()})")

    db = SessionLocal()
    try:
        deleted = db.query(StockHistoricalPrice).filter(StockHistoricalPrice.symbol == symbol).delete()
        print(f"  Deleted {deleted} existing rows for {symbol}")
        db.bulk_save_objects([
            StockHistoricalPrice(
                symbol=symbol, date=row["date"],
                open=row["open"], high=row["high"], low=row["low"],
                close=row["close"], volume=row["volume"], ref_price=row["open"]
            )
            for _, row in df.iterrows()
        ])
        db.commit()
        print(f"  ✅ Inserted {len(df)} rows for {symbol}")
    except Exception as e:
        db.rollback()
        print(f"  ❌ DB error: {e}")
    finally:
        db.close()


def backfill_spx_index(start_year: int = 2020):
    """Fetch S&P 500 index data from Yahoo Finance using yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("⚠️ yfinance not installed. Install with: pip install yfinance")
        return

    print(f"Starting SPX backfill from {start_year}...")
    try:
        ticker = yf.Ticker("^GSPC")  # S&P 500 ticker on Yahoo Finance
        start_date = f"{start_year}-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            print(f"⚠️ No data returned for SPX")
            return
            
        # Standardize columns
        df = df.reset_index()
        df = df.rename(columns={
            'Date': 'date',
            'Open': 'open', 
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # Format date
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        df = df.drop_duplicates(subset=['date']).sort_values('date')
        
        print(f"Downloaded {len(df)} rows for SPX ({df['date'].min()} to {df['date'].max()})")
        
        # Insert to DB
        db = SessionLocal()
        try:
            deleted = db.query(StockHistoricalPrice).filter(StockHistoricalPrice.symbol == "SPX").delete()
            print(f"  Deleted {deleted} existing rows for SPX")
            
            for _, row in df.iterrows():
                db.execute(
                    text("""
                        INSERT INTO stock_history (symbol, date, open, high, low, close, volume, ref_price)
                        VALUES (:symbol, :date, :open, :high, :low, :close, :volume, :ref_price)
                    """),
                    {
                        "symbol": "SPX",
                        "date": row['date'],
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": float(row['volume']) if pd.notna(row['volume']) else 0.0,
                        "ref_price": float(row['open'])
                    }
                )
            
            db.commit()
            print(f"✅ Successfully inserted {len(df)} rows for SPX")
        except Exception as e:
            db.rollback()
            print(f"❌ Database error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ SPX fetch error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=== BACKFILL ALL VIETNAM INDICES ===")
    backfill_index_vps("VNINDEX")
    backfill_index_vps("VN30")
    backfill_index_vps("HNXINDEX")
    backfill_index_vps("UPCOM")
    
    print("\n=== BACKFILL INTERNATIONAL INDICES ===")
    backfill_spx_index(start_year=2020)
    
    print("\n✅ All indices backfill completed!")
