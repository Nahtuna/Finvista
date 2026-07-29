#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check CW historical data gaps in database
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"🔗 Connecting to database...")

try:
    engine = create_engine(DATABASE_URL)
    session = sessionmaker(bind=engine)()
    
    # Check a sample CW symbol for gaps
    symbol = "CACB2511"
    
    print(f"\n🔍 Checking CW historical data gaps for: {symbol}")
    print("=" * 60)
    
    # Get all data for this symbol
    rows = session.execute(text(
        "SELECT date, open, high, low, close, volume FROM cw_history WHERE symbol = :symbol ORDER BY date"
    ), {"symbol": symbol}).fetchall()
    
    if len(rows) == 0:
        print(f"❌ No data found for {symbol}")
    else:
        print(f"✅ Found {len(rows)} rows for {symbol}")
        print(f"   First date: {rows[0][0]}")
        print(f"   Last date: {rows[-1][0]}")
        
        # Find gaps
        gaps = []
        prev_date = rows[0][0]
        for row in rows[1:]:
            curr_date = row[0]
            if isinstance(curr_date, str):
                curr_date = datetime.strptime(curr_date, "%Y-%m-%d").date()
            if isinstance(prev_date, str):
                prev_date = datetime.strptime(prev_date, "%Y-%m-%d").date()
            
            days_diff = (curr_date - prev_date).days
            if days_diff > 1:
                gaps.append((prev_date, curr_date, days_diff))
            prev_date = curr_date
        
        print(f"\n📊 Gaps found: {len(gaps)}")
        if gaps:
            for gap in gaps[:10]:  # Show first 10 gaps
                print(f"   {gap[0]} to {gap[1]} ({gap[2]} days)")
        else:
            print("   No gaps found - data is continuous")
    
    # Check overall CW data coverage
    print(f"\n📋 Overall CW data statistics:")
    total_symbols = session.execute(text("SELECT COUNT(DISTINCT symbol) FROM cw_history")).scalar()
    total_records = session.execute(text("SELECT COUNT(*) FROM cw_history")).scalar()
    
    print(f"   Total symbols: {total_symbols}")
    print(f"   Total records: {total_records}")
    
    # Get date range
    date_range = session.execute(text(
        "SELECT MIN(date), MAX(date) FROM cw_history"
    )).fetchone()
    
    if date_range[0]:
        print(f"   Date range: {date_range[0]} to {date_range[1]}")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
