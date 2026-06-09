# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: PORTFOLIO & TRADING SERVICE
========================================
Handles all simulated trading logic, HOSE rule enforcement, 
and portfolio management using SQLite persistence.

Author: samvo
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import desc

from src.common.database import SessionLocal, User, Portfolio, Position, TransactionHistory, MarketOpportunity
from src.trading.paper_trader import (
    INITIAL_CASH, BUY_FEE_RATE, SELL_FEE_RATE, HOSE_LOT_SIZE, 
    MAX_ALLOCATION_PCT, MATURITY_LIMIT_DAYS,
    calculate_settlement_date, is_market_open, REPORT_PATH
)

class PortfolioService:
    @staticmethod
    def get_portfolio(username: str) -> Dict[str, Any]:
        """Retrieve detailed portfolio state for a user from SQLite."""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            port = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
            if not port:
                # Initialize portfolio if missing
                port = Portfolio(user_id=user.id, cash=INITIAL_CASH, initial_cash=INITIAL_CASH)
                db.add(port)
                db.commit()
                db.refresh(port)

            # Get live prices from market opportunities cache in DB
            opportunities = db.query(MarketOpportunity).all()
            live_prices = {opp.symbol: opp.price for opp in opportunities}

            db_positions = db.query(Position).filter(Position.user_id == user.id).all()
            
            cash = port.cash
            initial = port.initial_cash
            pos_val = 0.0
            active_positions = []
            now = datetime.now()

            for pos in db_positions:
                curr_price = live_prices.get(pos.symbol, pos.buy_price)
                val = pos.qty * curr_price
                pos_val += val

                p_l_vnd = val - pos.total_cost
                p_l_pct = ((curr_price - pos.buy_price) / pos.buy_price * 100) if pos.buy_price > 0 else 0.0

                settlement_dt = datetime.fromisoformat(pos.settlement_date)
                is_locked = now < settlement_dt
                time_left_hours = max(0.0, (settlement_dt - now).total_seconds() / 3600.0) if is_locked else 0.0

                active_positions.append({
                    "symbol": pos.symbol,
                    "underlying": pos.underlying,
                    "qty": pos.qty,
                    "buy_price": pos.buy_price,
                    "current_price": curr_price,
                    "buy_date": pos.buy_date,
                    "settlement_date": pos.settlement_date,
                    "total_cost": pos.total_cost,
                    "current_value": val,
                    "p_l_vnd": p_l_vnd,
                    "p_l_pct": p_l_pct,
                    "is_locked": is_locked,
                    "lock_hours_remaining": round(time_left_hours, 1),
                    "score_at_buy": pos.score_at_buy,
                    "days_at_buy": pos.days_at_buy,
                })

            total_nav = cash + pos_val
            cum_p_l = total_nav - initial
            cum_p_l_pct = (total_nav - initial) / initial * 100 if initial > 0 else 0.0

            db_history = db.query(TransactionHistory).filter(TransactionHistory.user_id == user.id).order_by(TransactionHistory.date.desc()).all()
            
            history = []
            completed_trades = 0
            win_trades = 0
            
            for tx in db_history:
                tx_data = {
                    "symbol": tx.symbol,
                    "underlying": tx.underlying,
                    "type": tx.type,
                    "qty": tx.qty,
                    "price": tx.price,
                    "value": tx.value,
                    "fee": tx.fee,
                    "date": tx.date,
                    "reason": tx.reason
                }
                history.append(tx_data)
                
                if tx.type == "SELL":
                    completed_trades += 1
                    # Logic to check P/L from history would need buy_price in history, 
                    # for now we rely on the logic used in the original paper_trader history appending
                    # but since we are standardizing, let's assume we might want to extend the model later.
            
            # Simple win rate calculation from existing history
            win_rate = 0.0 # Needs better tracking in history model for accurate calculation
            
            return {
                "cash": cash,
                "initial_cash": initial,
                "positions_value": pos_val,
                "total_nav": total_nav,
                "cumulative_p_l_vnd": cum_p_l,
                "cumulative_p_l_pct": cum_p_l_pct,
                "win_rate_pct": round(win_rate, 2),
                "total_completed_trades": completed_trades,
                "active_positions": active_positions,
                "history": history,
            }
        finally:
            db.close()

    @staticmethod
    def place_order(username: str, symbol: str, side: str, qty: Optional[int] = None, price_override: Optional[float] = None, reason: str = "Manual Order") -> Dict[str, Any]:
        """Place a BUY or SELL order enforcing HOSE rules."""
        from src.trading.paper_trader import execute_buy, execute_sell
        
        symbol_clean = symbol.upper().strip()
        side_clean = side.upper().strip()

        db = SessionLocal()
        try:
            # Get current market data for the symbol
            opp = db.query(MarketOpportunity).filter(MarketOpportunity.symbol == symbol_clean).first()
            
            live_price = opp.price if opp else 0.0
            underlying = opp.underlying if opp else "UNKNOWN"
            score = opp.score if opp else 50.0
            days_left = opp.days_to_maturity if opp else 90

            price = price_override if price_override is not None else live_price
            if price <= 0:
                raise HTTPException(status_code=422, detail=f"Invalid market price for {symbol_clean}")

            if side_clean == "BUY":
                if days_left < 10:
                    raise HTTPException(status_code=422, detail=f"Warrant {symbol_clean} is near maturity.")

                # Check existing position
                user = db.query(User).filter(User.username == username).first()
                existing = db.query(Position).filter(Position.user_id == user.id, Position.symbol == symbol_clean).first()
                if existing:
                    raise HTTPException(status_code=422, detail=f"Already holding {symbol_clean}")

                if qty is None:
                    # Use automated execute_buy logic
                    res = execute_buy(symbol_clean, underlying, price, score, days_left, username=username)
                else:
                    # Manual quantity BUY logic
                    if qty <= 0 or qty % HOSE_LOT_SIZE != 0:
                        raise HTTPException(status_code=422, detail=f"Qty must be multiple of {HOSE_LOT_SIZE}")

                    gross_value = qty * price
                    fee = gross_value * BUY_FEE_RATE
                    total_cost = gross_value + fee

                    port = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
                    if total_cost > port.cash:
                        raise HTTPException(status_code=422, detail="Insufficient cash")

                    # Execute purchase
                    port.cash -= total_cost
                    now_str = datetime.now().isoformat()
                    new_pos = Position(
                        user_id=user.id,
                        symbol=symbol_clean,
                        underlying=underlying,
                        qty=qty,
                        buy_price=price,
                        buy_date=now_str,
                        settlement_date=calculate_settlement_date(now_str),
                        total_cost=total_cost,
                        score_at_buy=score,
                        days_at_buy=days_left
                    )
                    db.add(new_pos)
                    
                    new_tx = TransactionHistory(
                        user_id=user.id,
                        symbol=symbol_clean,
                        underlying=underlying,
                        type="BUY",
                        qty=qty,
                        price=price,
                        value=gross_value,
                        fee=fee,
                        date=now_str,
                        reason=reason
                    )
                    db.add(new_tx)
                    db.commit()
                    res = {"status": "success", "message": f"BOUGHT {qty} {symbol_clean}"}
                
                return res

            elif side_clean == "SELL":
                return execute_sell(symbol_clean, price, reason, username=username)

            raise HTTPException(status_code=400, detail="Invalid order side")
        finally:
            db.close()

    @staticmethod
    def reset_portfolio(username: str) -> Dict[str, Any]:
        """Reset portfolio using database transactions."""
        from src.trading.paper_trader import reset_portfolio as legacy_reset
        return legacy_reset(username=username)

    @staticmethod
    def scan_and_trade(username: str, force: bool = False) -> List[str]:
        """Execute automated trading scan."""
        from src.trading.paper_trader import scan_and_trade as legacy_scan
        return legacy_scan(force=force, username=username)
