import requests
import datetime
import sys
import os
sys.path.insert(0, os.getcwd())

now = int(datetime.datetime.now().timestamp())
ago = int((datetime.datetime.now() - datetime.timedelta(days=400)).timestamp())

sym = "CACB2511"

# 1. Check Entrade API
print("=== ENTRADE API ===")
url = f"https://api.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=1D&symbol={sym}&from={ago}&to={now}"
try:
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6).json()
    t = r.get("t", [])
    c = r.get("c", [])
    print(f"Entrade {sym}: {len(t)} candles")
    if t:
        print(f"  First: {datetime.datetime.fromtimestamp(t[0]).strftime('%Y-%m-%d')} close={c[0]}")
        print(f"  Last:  {datetime.datetime.fromtimestamp(t[-1]).strftime('%Y-%m-%d')} close={c[-1]}")
        print(f"  Price range: min={min(c):.2f} max={max(c):.2f}")
except Exception as e:
    print(f"Entrade error: {e}")

# 2. Check DB - CWHistoricalPrice
print("\n=== DB - CWHistoricalPrice ===")
try:
    from backend.core.database import SessionLocal, CWHistoricalPrice
    db = SessionLocal()
    rows = db.query(CWHistoricalPrice).filter(CWHistoricalPrice.symbol == sym).order_by(CWHistoricalPrice.date).all()
    print(f"CWHistoricalPrice {sym}: {len(rows)} rows")
    if rows:
        print(f"  First: {rows[0].date} close={rows[0].close}")
        print(f"  Last:  {rows[-1].date} close={rows[-1].close}")
    db.close()
except Exception as e:
    print(f"CWHistoricalPrice error: {e}")

# 3. Check StockHistoricalPrice for underlying ACB
print("\n=== DB - StockHistoricalPrice (ACB) ===")
try:
    from backend.core.database import SessionLocal, StockHistoricalPrice
    db = SessionLocal()
    rows = db.query(StockHistoricalPrice).filter(StockHistoricalPrice.symbol == "ACB").order_by(StockHistoricalPrice.date).all()
    print(f"StockHistoricalPrice ACB: {len(rows)} rows")
    if rows:
        print(f"  First: {rows[0].date} close={rows[0].close}")
        print(f"  Last:  {rows[-1].date} close={rows[-1].close}")
    db.close()
except Exception as e:
    print(f"StockHistoricalPrice error: {e}")
