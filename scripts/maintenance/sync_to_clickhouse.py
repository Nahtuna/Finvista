# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: CLICKHOUSE OLAP SYNCHRONIZER
========================================
Exports time-series price data (cw_history, stock_history) from the transactional database
to a ClickHouse instance for high-speed quantitative backtesting and analytical aggregates.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.core.database import CWHistoricalPrice, StockHistoricalPrice

# Load environment variables
load_dotenv()

# ClickHouse settings from env with fallbacks
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))  # HTTP port
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "finvista")

def sync_to_clickhouse():
    # 1. Connect to Main SQL Database (Source)
    postgres_url = os.getenv("DATABASE_URL")
    # Safe fallback to SQLite if PostgreSQL not configured yet
    if not postgres_url or "user:password@host:port" in postgres_url:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        postgres_url = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'finvista.db')}"
        
    print(f"🔌 Connecting to source database: {postgres_url}")
    engine = create_engine(postgres_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 2. Try to connect to ClickHouse
    print("🔌 Connecting to ClickHouse OLAP server...")
    try:
        import clickhouse_connect
    except ImportError:
        print("❌ 'clickhouse-connect' library not installed in your Python environment.")
        print("   To install it, run: pip install clickhouse-connect")
        print("   Skipping actual sync execution, but showing ClickHouse SQL structures below:\n")
        print_clickhouse_ddl()
        return

    try:
        ch_client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD
        )
        print("   ✅ ClickHouse connection established successfully!")
    except Exception as ch_err:
        print(f"   ❌ ClickHouse connection failed: {ch_err}")
        print("   Ensure ClickHouse is running locally or check env variables.")
        return

    try:
        # 3. Create target Database & Tables in ClickHouse
        print(f"🏗️ Setting up database and tables in ClickHouse (Database: {CLICKHOUSE_DATABASE})...")
        ch_client.command(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DATABASE}")
        
        # ClickHouse DDLs using MergeTree engines optimized for range query filters
        ch_client.command(f"""
            CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DATABASE}.cw_history (
                symbol LowCardinality(String),
                date Date,
                open Float32,
                high Float32,
                low Float32,
                close Float32,
                volume Float64,
                ref_price Float32
            ) ENGINE = MergeTree()
            ORDER BY (symbol, date);
        """)
        
        ch_client.command(f"""
            CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DATABASE}.stock_history (
                symbol LowCardinality(String),
                date Date,
                open Float32,
                high Float32,
                low Float32,
                close Float32,
                volume Float64,
                ref_price Float32
            ) ENGINE = MergeTree()
            ORDER BY (symbol, date);
        """)
        print("   ✅ ClickHouse OLAP tables verified!")

        # 4. Sync Covered Warrant History
        print("📦 Syncing Covered Warrant history (cw_history) to ClickHouse...")
        cw_records = session.query(CWHistoricalPrice).all()
        total_cw = len(cw_records)
        print(f"   - Found {total_cw:,} records in source SQL database.")
        
        if total_cw > 0:
            # Prepare data matrix for ClickHouse bulk insert
            data = []
            for r in cw_records:
                # Convert string date to Date string if stored as string in source
                date_val = str(r.date)[:10]
                data.append([
                    r.symbol, date_val, r.open or 0.0, r.high or 0.0, 
                    r.low or 0.0, r.close or 0.0, r.volume or 0.0, r.ref_price or 0.0
                ])
                
            ch_client.insert(
                f"{CLICKHOUSE_DATABASE}.cw_history",
                data,
                column_names=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'ref_price']
            )
            print(f"   ✅ Synced {total_cw:,} cw_history rows.")

        # 5. Sync Stock History
        print("📦 Syncing Underlying Stock history (stock_history) to ClickHouse...")
        stock_records = session.query(StockHistoricalPrice).all()
        total_stock = len(stock_records)
        print(f"   - Found {total_stock:,} records in source SQL database.")
        
        if total_stock > 0:
            data = []
            for r in stock_records:
                date_val = str(r.date)[:10]
                data.append([
                    r.symbol, date_val, r.open or 0.0, r.high or 0.0, 
                    r.low or 0.0, r.close or 0.0, r.volume or 0.0, r.ref_price or 0.0
                ])
                
            ch_client.insert(
                f"{CLICKHOUSE_DATABASE}.stock_history",
                data,
                column_names=['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'ref_price']
            )
            print(f"   ✅ Synced {total_stock:,} stock_history rows.")
            
        print("\n🎉 DATA SYNCHRONIZATION COMPLETED SUCCESSFULLY!")

    except Exception as e:
        print(f"\n❌ Error executing ClickHouse synchronization: {e}")
    finally:
        session.close()

def print_clickhouse_ddl():
    print("--- CLICKHOUSE RECOMMENDED DDL STATEMENTS ---")
    print(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DATABASE};")
    print(f"""
CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DATABASE}.cw_history (
    symbol LowCardinality(String),
    date Date,
    open Float32,
    high Float32,
    low Float32,
    close Float32,
    volume Float64,
    ref_price Float32
) ENGINE = MergeTree()
ORDER BY (symbol, date);
    """)
    print(f"""
CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DATABASE}.stock_history (
    symbol LowCardinality(String),
    date Date,
    open Float32,
    high Float32,
    low Float32,
    close Float32,
    volume Float64,
    ref_price Float32
) ENGINE = MergeTree()
ORDER BY (symbol, date);
    """)

if __name__ == "__main__":
    sync_to_clickhouse()
