# -*- coding: utf-8 -*-
"""
Evaluate pricing model performance against market data
"""
from src.common.database import engine
import pandas as pd

# Check database tables and row counts
tables = pd.read_sql('SELECT name FROM sqlite_master WHERE type="table"', engine)
print("Database Tables:")
print(tables.to_string())
print("\n" + "="*50 + "\n")

# Check row counts
cw_count = pd.read_sql('SELECT COUNT(*) as count FROM cw_history', engine)
stock_count = pd.read_sql('SELECT COUNT(*) as count FROM stock_history', engine)
opp_count = pd.read_sql('SELECT COUNT(*) as count FROM market_opportunities', engine)

print(f'CW History: {cw_count.iloc[0]["count"]} rows')
print(f'Stock History: {stock_count.iloc[0]["count"]} rows')
print(f'Market Opportunities: {opp_count.iloc[0]["count"]} rows')

# Sample CW history data
if cw_count.iloc[0]["count"] > 0:
    print("\n" + "="*50 + "\n")
    print("Sample CW History Data:")
    sample_cw = pd.read_sql('SELECT * FROM cw_history LIMIT 5', engine)
    print(sample_cw.to_string())

# Sample market opportunities
if opp_count.iloc[0]["count"] > 0:
    print("\n" + "="*50 + "\n")
    print("Sample Market Opportunities:")
    sample_opp = pd.read_sql('SELECT symbol, underlying, price, theoretical_price, upside_pct, implied_volatility_pct, delta, prob_itm FROM market_opportunities LIMIT 5', engine)
    print(sample_opp.to_string())
