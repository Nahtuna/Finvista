# -*- coding: utf-8 -*-
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.services.portfolio_service import PortfolioService
from src.common.database import SessionLocal, Portfolio, Position, MarketOpportunity

def test_buy_order():
    username = "demo"
    db = SessionLocal()
    
    # 1. Find a warrant for HPG
    opp = db.query(MarketOpportunity).filter(MarketOpportunity.underlying == 'HPG').first()
    if not opp:
        print("❌ No HPG warrant found in database.")
        return
    
    symbol = opp.symbol
    price = opp.price
    print(f"🔍 Found warrant: {symbol} (Underlying: HPG, Price: {price:,.0f}đ)")
    
    # 2. Check initial state
    port = db.query(Portfolio).first() # Demo user should be first
    initial_cash = port.cash
    print(f"💰 Initial Cash: {initial_cash:,.0f}đ")
    
    # 3. Execute Order via Service
    print(f"🚀 Placing order: BUY 1,000 {symbol}...")
    res = PortfolioService.place_order(
        username=username,
        symbol=symbol,
        side="BUY",
        qty=1000,
        price_override=None,
        reason="Manual Test Order"
    )
    print(f"📝 Result: {res['message']}")
    
    # 4. Verify Final State
    db.expire_all()
    port = db.query(Portfolio).filter(Portfolio.user_id == port.user_id).first()
    pos = db.query(Position).filter(Position.user_id == port.user_id, Position.symbol == symbol).first()
    
    print("\n" + "="*40)
    print("📊 VERIFICATION IN SQLITE")
    print("="*40)
    print(f"💵 Final Cash Balance: {port.cash:,.0f}đ (Reduced by {initial_cash - port.cash:,.0f}đ)")
    if pos:
        print(f"📦 Active Position: {pos.symbol}")
        print(f"   - Quantity: {pos.qty:,}")
        print(f"   - Buy Price: {pos.buy_price:,.0f}đ")
        print(f"   - Total Cost: {pos.total_cost:,.0f}đ")
    else:
        print("❌ Position not found in database!")
    print("="*40)

if __name__ == "__main__":
    test_buy_order()
