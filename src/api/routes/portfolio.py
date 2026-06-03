# -*- coding: utf-8 -*-
"""Paper trading portfolio routes."""

import os
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.api.websocket import manager
from src.trading.paper_trader import (
    REPORT_PATH,
    execute_buy,
    execute_sell,
    is_market_open,
    load_portfolio,
    reset_portfolio,
    scan_and_trade,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Covered warrant symbol, e.g. CACB2510", example="CACB2510")
    side: str = Field(
        ..., description="BUY or SELL", pattern="^(BUY|SELL|buy|sell)$", example="BUY"
    )
    qty: Optional[int] = Field(
        None,
        description=(
            "Quantity to buy/sell. If BUY, qty is optional (allocates max 20% NAV by default "
            "if not specified). Must be multiple of 100."
        ),
    )
    price: Optional[float] = Field(
        None, description="Optional override price. If not specified, uses current live market price."
    )
    reason: Optional[str] = Field("Manual User Order", description="Optional reason for the transaction")


@router.get("")
def get_portfolio(current_user: dict = Depends(get_current_user)):
    """
    Retrieve detailed Paper Trading portfolio state, including current cash,
    open positions with real-time valuation/P/L, win rate, and full transaction history.
    """
    try:
        portfolio = load_portfolio(username=current_user["username"])

        live_prices = {}
        if os.path.exists(REPORT_PATH):
            try:
                df = pd.read_csv(REPORT_PATH)
                live_prices = dict(zip(df["A_MaCW"], df["C_GiaCW"]))
            except Exception:
                pass

        cash = portfolio.get("cash", 100_000_000.0)
        initial = portfolio.get("initial_cash", 100_000_000.0)
        pos_val = 0.0
        active_positions = []

        now = datetime.now()

        for sym, pos in portfolio.get("positions", {}).items():
            curr_price = live_prices.get(sym, pos["buy_price"])
            val = pos["qty"] * curr_price
            pos_val += val

            p_l_vnd = val - pos["total_cost"]
            p_l_pct = (
                (curr_price - pos["buy_price"]) / pos["buy_price"] * 100
                if pos["buy_price"] > 0
                else 0.0
            )

            settlement_dt = datetime.fromisoformat(pos["settlement_date"])
            is_locked = now < settlement_dt
            time_left_hours = (
                max(0.0, (settlement_dt - now).total_seconds() / 3600.0) if is_locked else 0.0
            )

            active_positions.append({
                "symbol": sym,
                "underlying": pos.get("underlying"),
                "qty": pos["qty"],
                "buy_price": pos["buy_price"],
                "current_price": curr_price,
                "buy_date": pos["buy_date"],
                "settlement_date": pos["settlement_date"],
                "total_cost": pos["total_cost"],
                "current_value": val,
                "p_l_vnd": p_l_vnd,
                "p_l_pct": p_l_pct,
                "is_locked": is_locked,
                "lock_hours_remaining": round(time_left_hours, 1),
                "score_at_buy": pos.get("score_at_buy"),
                "days_at_buy": pos.get("days_at_buy"),
            })

        total_nav = cash + pos_val
        cum_p_l = total_nav - initial
        cum_p_l_pct = (total_nav - initial) / initial * 100 if initial > 0 else 0.0

        history = portfolio.get("history", [])
        completed_trades = [t for t in history if t.get("type") == "SELL"]
        win_trades = [t for t in completed_trades if t.get("p_l_vnd", 0.0) > 0]
        win_rate = (len(win_trades) / len(completed_trades) * 100) if completed_trades else 0.0

        return {
            "cash": cash,
            "initial_cash": initial,
            "positions_value": pos_val,
            "total_nav": total_nav,
            "cumulative_p_l_vnd": cum_p_l,
            "cumulative_p_l_pct": cum_p_l_pct,
            "win_rate_pct": round(win_rate, 2),
            "total_completed_trades": len(completed_trades),
            "total_won_trades": len(win_trades),
            "active_positions": active_positions,
            "history": list(reversed(history)),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load paper trading portfolio: {str(e)}",
        )


@router.post("/orders")
async def place_order(req: OrderRequest, current_user: dict = Depends(get_current_user)):
    """
    Place a manual paper trading BUY or SELL order.
    Validates HOSE rules, transaction fees, and T+2.5 settlement lock constraints.
    Broadcasts successful transactions in real-time over WebSocket.
    """
    symbol_clean = req.symbol.upper().strip()
    side_clean = req.side.upper().strip()

    underlying = "UNKNOWN"
    live_price = 0.0
    score = 50.0
    days_left = 90

    if os.path.exists(REPORT_PATH):
        try:
            df = pd.read_csv(REPORT_PATH)
            row = df[df["A_MaCW"] == symbol_clean]
            if not row.empty:
                underlying = row.iloc[0].get("B_MaCPCS", "UNKNOWN")
                live_price = float(row.iloc[0].get("C_GiaCW", 0.0))
                score = float(row.iloc[0].get("G_Score", 50.0))
                days_left = int(row.iloc[0].get("L_Ngay", 90))
        except Exception:
            pass

    price = req.price if req.price is not None else live_price
    if price <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Could not resolve a valid market price for '{symbol_clean}'. "
                "Please provide an explicit price."
            ),
        )

    if side_clean == "BUY":
        if days_left < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Warrant '{symbol_clean}' is within 10 days of maturity "
                    f"({days_left} days left) and cannot be bought due to risk constraints."
                ),
            )

        portfolio = load_portfolio(username=current_user["username"])
        if symbol_clean in portfolio.get("positions", {}):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Already holding an active position in '{symbol_clean}'.",
            )

        if req.qty is None:
            res = execute_buy(
                symbol_clean, underlying, price, score, days_left, username=current_user["username"]
            )
            if res.get("status") == "error":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("message"))

            await manager.broadcast({
                "event": "order_executed",
                "username": current_user["username"],
                "message": res.get("message"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            return res

        qty = req.qty
        if qty <= 0 or qty % 100 != 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Quantity must be a positive integer and a multiple of 100 (HOSE lot size).",
            )

        gross_value = qty * price
        fee = gross_value * 0.0015
        total_cost = gross_value + fee

        if total_cost > portfolio.get("cash", 0.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Insufficient cash. Required: {total_cost:,.0f}đ, "
                    f"Available: {portfolio.get('cash'):,.0f}đ."
                ),
            )

        from src.trading.paper_trader import calculate_settlement_date, save_portfolio

        portfolio["cash"] -= total_cost
        now_str = datetime.now().isoformat()
        portfolio["positions"][symbol_clean] = {
            "symbol": symbol_clean,
            "underlying": underlying,
            "qty": qty,
            "buy_price": price,
            "buy_date": now_str,
            "settlement_date": calculate_settlement_date(now_str),
            "total_cost": total_cost,
            "score_at_buy": score,
            "days_at_buy": days_left,
        }
        portfolio["history"].append({
            "symbol": symbol_clean,
            "underlying": underlying,
            "type": "BUY",
            "qty": qty,
            "price": price,
            "value": gross_value,
            "fee": fee,
            "date": now_str,
            "reason": req.reason,
        })
        save_portfolio(portfolio, username=current_user["username"])

        msg = (
            f"🛍️ BOUGHT {qty:,} {symbol_clean} at {price:,.0f}đ | "
            f"Total Cost: {total_cost:,.0f}đ (Fee: {fee:,.0f}đ)"
        )
        await manager.broadcast({
            "event": "order_executed",
            "username": current_user["username"],
            "message": msg,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return {"status": "success", "message": msg}

    elif side_clean == "SELL":
        res = execute_sell(symbol_clean, price, req.reason, username=current_user["username"])
        if res.get("status") == "error":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("message"))

        await manager.broadcast({
            "event": "order_executed",
            "username": current_user["username"],
            "message": res.get("message"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return res

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid transaction side '{req.side}'. Use 'BUY' or 'SELL'.",
    )


@router.post("/reset")
def reset_trading_portfolio(current_user: dict = Depends(get_current_user)):
    """
    Reset the paper trading account portfolio back to 100,000,000 VND initial balance,
    clearing all open positions and transaction logs.
    """
    try:
        res = reset_portfolio(username=current_user["username"])
        return {
            "status": "success",
            "message": "Demo paper trading account cash successfully reset to 100,000,000đ.",
            "portfolio": res,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset portfolio: {str(e)}",
        )


@router.post("/scan")
def trigger_paper_trader_scan(
    force: bool = Query(False, description="Set to true to bypass HOSE trading hours checks"),
    current_user: dict = Depends(get_current_user),
):
    """
    Scan the latest market prices against active positions to trigger risk-management
    exits (cắt lỗ -15%, chốt lời +20%, Theta decay) and execute entry signals.
    """
    try:
        actions = scan_and_trade(force=force, username=current_user["username"])
        return {
            "status": "success",
            "market_status": "open" if is_market_open() or force else "closed",
            "actions_executed": actions,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paper trading scan execution failed: {str(e)}",
        )
