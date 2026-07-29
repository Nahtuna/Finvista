from src.core.database import SessionLocal, StockHistoricalPrice, CWHistoricalPrice
from datetime import datetime

db = SessionLocal()

print("=== STOCK HISTORICAL PRICE (Indices) ===")
indices = ['VNINDEX', 'VN30', 'HNXINDEX', 'UPCOM', 'SPX', 'NDX']
for idx in indices:
    latest = db.query(StockHistoricalPrice).filter(
        StockHistoricalPrice.symbol == idx
    ).order_by(StockHistoricalPrice.date.desc()).first()
    if latest:
        print(f"{idx}: {latest.date} (close: {latest.close})")
    else:
        print(f"{idx}: No data")

print("\n=== CW HISTORICAL PRICE (CACB2511) ===")
cw_symbols = ['CACB2511']
for cw in cw_symbols:
    latest = db.query(CWHistoricalPrice).filter(
        CWHistoricalPrice.symbol == cw
    ).order_by(CWHistoricalPrice.date.desc()).first()
    if latest:
        print(f"{cw}: {latest.date} (close: {latest.close})")
        total = db.query(CWHistoricalPrice).filter(CWHistoricalPrice.symbol == cw).count()
        print(f"Total records: {total}")
    else:
        print(f"{cw}: No data")

print(f"\nToday: {datetime.now().strftime('%Y-%m-%d')}")

db.close()
