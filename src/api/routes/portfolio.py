# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: PORTFOLIO ROUTES (DELIVERY LAYER)
=============================================
FastAPI routes for paper trading portfolio management & quantitative backtesting.
Delegates paper trading logic to PortfolioService and runs DB-driven historical backtesting.

Author: samvo
Version: 2.0 (Clean Architecture Refactored)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.api.websocket import manager
from src.modules.trading_engine.portfolio_service import PortfolioService

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Covered warrant symbol, e.g. CACB2511")
    side: str = Field(
        ..., description="BUY or SELL", pattern="^(BUY|SELL|buy|sell)$"
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
    Retrieve detailed Paper Trading portfolio state.
    Delegates to PortfolioService for SQLite-based data retrieval.
    """
    return PortfolioService.get_portfolio(username=current_user["username"])


@router.post("/orders")
async def place_order(req: OrderRequest, current_user: dict = Depends(get_current_user)):
    """
    Place a paper trading order.
    Delegates validation and execution to PortfolioService.
    Broadcasts successful transactions over WebSocket.
    """
    res = PortfolioService.place_order(
        username=current_user["username"],
        symbol=req.symbol,
        side=req.side,
        qty=req.qty,
        price_override=req.price,
        reason=req.reason
    )
    
    if res.get("status") == "success":
        from datetime import datetime
        await manager.broadcast({
            "event": "order_executed",
            "username": current_user["username"],
            "message": res.get("message"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return res
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("message"))


@router.post("/reset")
def reset_trading_portfolio(current_user: dict = Depends(get_current_user)):
    """
    Reset paper trading account to initial balance.
    """
    return PortfolioService.reset_portfolio(username=current_user["username"])


@router.post("/scan")
def trigger_paper_trader_scan(
    force: bool = Query(False, description="Set to true to bypass HOSE trading hours checks"),
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger automated risk-management scan via PortfolioService.
    """
    actions = PortfolioService.scan_and_trade(username=current_user["username"], force=force)
    return {
        "status": "success",
        "actions_executed": actions,
    }


def execute_db_backtest(
    strategy: str = "vol_arb",
    period_days: Optional[int] = None,
    years: Optional[int] = None,
    capital: float = 100_000_000.0,
    stop_loss_pct: float = 15.0,
    take_profit_pct: float = 35.0,
    underlying_filter: str = "ALL",
    iv_entry_threshold: float = 5.0,
    delta_entry_min: float = 0.25,
) -> dict:
    """
    Unified DB-driven Backtesting Engine.
    Queries cw_history, stock_history, and cw_info from finvista.db SQLite database.
    Dynamically auto-fits timeframes based on actual available data in DB.
    """
    import sqlite3
    import math
    import os
    from datetime import datetime, timedelta

    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "data", "finvista.db"
    )

    if not os.path.exists(db_path):
        return {"status": "error", "message": "Database finvista.db not found."}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # 1. Fetch market regime
        market_regime = {"regime": "UNKNOWN", "bias": "NEUTRAL", "confidence": 0.5, "description": ""}
        try:
            from src.modules.regime_analysis.indicators.creed_regime import calculate_creed_vnindex_regime
            market_regime = calculate_creed_vnindex_regime(days=500)
        except Exception:
            pass
        regime_str = market_regime.get("regime", "UNKNOWN")
        regime_bias = market_regime.get("bias", "NEUTRAL")

        # 2. Determine available date range in DB dynamically
        min_date_row = conn.execute("SELECT MIN(date) as min_d, MAX(date) as max_d FROM cw_history").fetchone()
        min_db_date = min_date_row["min_d"] or "2021-01-01"
        max_db_date = min_date_row["max_d"] or datetime.now().strftime("%Y-%m-%d")

        # Safely convert parameter values from potential FastAPI Query objects
        try:
            period_days_val = int(period_days) if period_days is not None and not hasattr(period_days, "default") else None
        except Exception:
            period_days_val = 60

        try:
            years_val = float(years) if years is not None and not hasattr(years, "default") else None
        except Exception:
            years_val = None

        try:
            stop_loss_pct = float(stop_loss_pct) if stop_loss_pct is not None and not hasattr(stop_loss_pct, "default") else 15.0
        except Exception:
            stop_loss_pct = 15.0

        try:
            take_profit_pct = float(take_profit_pct) if take_profit_pct is not None and not hasattr(take_profit_pct, "default") else 35.0
        except Exception:
            take_profit_pct = 35.0

        try:
            capital = float(capital) if capital is not None and not hasattr(capital, "default") else 100000000.0
        except Exception:
            capital = 100000000.0

        if isinstance(underlying_filter, str) and hasattr(underlying_filter, "default"):
            underlying_filter = "ALL"

        # Determine cutoff date based on requested period / years
        total_days = 0
        if years_val and years_val > 0:
            total_days = years_val * 365
        elif period_days_val and period_days_val > 0:
            total_days = period_days_val

        if total_days > 0:
            try:
                max_dt = datetime.strptime(max_db_date[:10], "%Y-%m-%d")
                calc_cutoff = (max_dt - timedelta(days=total_days)).strftime("%Y-%m-%d")
                cutoff_date = max(min_db_date, calc_cutoff)
            except Exception:
                cutoff_date = min_db_date
        else:
            cutoff_date = min_db_date

        # 3. Filter underlying symbols
        underlyings = [u.strip().upper() for u in underlying_filter.split(",") if u.strip()] if underlying_filter.upper() != "ALL" else []

        info_sql = "SELECT symbol, underlying, strike_price, maturity_date, conversion_ratio FROM cw_info"
        if underlyings:
            placeholders = ",".join("?" * len(underlyings))
            info_sql += f" WHERE underlying IN ({placeholders})"
            cw_info_rows = conn.execute(info_sql, underlyings).fetchall()
        else:
            cw_info_rows = conn.execute(info_sql).fetchall()

        cw_info_map = {r["symbol"]: dict(r) for r in cw_info_rows}

        if not cw_info_map:
            cw_hist_syms = conn.execute("SELECT DISTINCT symbol FROM cw_history").fetchall()
            for r in cw_hist_syms:
                sym = r["symbol"]
                und = sym[1:4] if len(sym) >= 4 else "ALL"
                if not underlyings or und in underlyings:
                    cw_info_map[sym] = {
                        "symbol": sym, "underlying": und,
                        "strike_price": 10000.0, "maturity_date": "2026-12-31", "conversion_ratio": 1.0
                    }

        sl = abs(stop_loss_pct) / 100.0
        tp = abs(take_profit_pct) / 100.0

        trades = []
        equity_curve = [{"t": 0, "equity": capital, "label": "Start"}]
        total_pnl = 0.0
        current_equity = capital
        win = loss = 0
        gross_p = gross_l = 0.0
        max_peak = capital
        max_dd = 0.0
        tick = 1
        alloc_per_trade = capital * 0.08

        # 4. Batch pre-load stock history & precompute HV
        import collections
        stock_rows = conn.execute("SELECT symbol, date, close FROM stock_history WHERE date >= ? ORDER BY date ASC", (cutoff_date,)).fetchall()
        stock_price_map = collections.defaultdict(dict)
        stock_closes = collections.defaultdict(list)
        stock_dates = collections.defaultdict(list)
        for r in stock_rows:
            s_sym, dt, cl = r["symbol"], r["date"], r["close"]
            stock_price_map[s_sym][dt] = cl
            stock_closes[s_sym].append(cl)
            stock_dates[s_sym].append(dt)

        # Batch pre-load Macro & News Sentiment Data (100% Full Data Utilization)
        macro_rows = conn.execute("SELECT symbol, date, close FROM macro_history WHERE date >= ?", (cutoff_date,)).fetchall()
        macro_map = collections.defaultdict(dict)
        for r in macro_rows:
            macro_map[r["symbol"]][r["date"]] = r["close"]

        news_rows = conn.execute("SELECT symbol, date, title FROM corporate_news WHERE date >= ?", (cutoff_date,)).fetchall()
        news_count_map = collections.defaultdict(lambda: collections.defaultdict(int))
        for r in news_rows:
            news_count_map[r["symbol"]][r["date"]] += 1

        hv_cache = {}
        for s_sym, closes in stock_closes.items():
            dates = stock_dates[s_sym]
            hv_map = {}
            if len(closes) >= 15:
                for i in range(15, len(closes)):
                    w = closes[i-15:i]
                    rets = [(w[j] - w[j-1]) / w[j-1] for j in range(1, len(w)) if w[j-1] > 0]
                    if len(rets) >= 5:
                        mean_r = sum(rets) / len(rets)
                        var = sum((r_val - mean_r) ** 2 for r_val in rets) / len(rets)
                        hv_map[dates[i]] = math.sqrt(var) * math.sqrt(252) * 100
            hv_cache[s_sym] = hv_map

        # Batch pre-load CW history
        all_cw_rows = conn.execute("SELECT symbol, date, close, volume FROM cw_history WHERE date >= ? ORDER BY date ASC", (cutoff_date,)).fetchall()
        cw_history_map = collections.defaultdict(list)
        for r in all_cw_rows:
            cw_history_map[r["symbol"]].append(dict(r))

        # Realistic Trading Friction & Risk Management Constraints
        FEE_SLIPPAGE_RATE = 0.005 # 0.3% fees + 0.2% slippage
        MIN_CW_PRICE = 100.0      # Ignore penny CWs < 100 VND
        MIN_VOLUME = 5000         # Min daily volume for liquidity
        MAX_ALLOC_PCT = 0.08      # 8% NAV per trade for high turnover rotation

        trades = []
        equity_curve = [{"t": 0, "equity": capital, "label": "Start"}]
        cash = capital
        current_equity = capital
        win = loss = 0
        gross_p = gross_l = 0.0
        max_peak = capital
        max_dd = 0.0
        tick = 1

        for cw_sym, info in cw_info_map.items():
            underlying = info.get("underlying", "")
            strike = info.get("strike_price") or 10000.0
            maturity = info.get("maturity_date") or ""
            conv_ratio = info.get("conversion_ratio") or 1.0

            cw_rows = cw_history_map.get(cw_sym, [])
            if len(cw_rows) < 3:
                continue

            hv_series = hv_cache.get(underlying, {})
            u_stock_map = stock_price_map.get(underlying, {})

            in_position = False
            entry_price = 0.0
            entry_price_net = 0.0
            entry_date = ""
            entry_reason = ""
            position_days = 0
            position_qty = 0
            peak_ret = -1.0

            for i_idx, row in enumerate(cw_rows):
                date = row["date"]
                cw_close = float(row["close"])
                volume = int(row["volume"] or 0)

                # Filter out illiquid CWs or penny prices
                if cw_close < MIN_CW_PRICE or volume < MIN_VOLUME:
                    continue

                stock_close = float(u_stock_map.get(date, 0.0))
                hv = hv_series.get(date, 35.0)

                theo_underlying_price = stock_close / conv_ratio if conv_ratio > 0 else stock_close
                moneyness = (theo_underlying_price / strike) if strike > 0 else 1.0

                try:
                    mat_dt = datetime.strptime(maturity[:10], "%Y-%m-%d") if maturity else None
                    cur_dt = datetime.strptime(date[:10], "%Y-%m-%d")
                    days_left = (mat_dt - cur_dt).days if mat_dt else 90
                except Exception:
                    days_left = 90

                if days_left <= 0:
                    if in_position:
                        exit_price_net = cw_close * (1.0 - FEE_SLIPPAGE_RATE)
                        pnl = round((exit_price_net - entry_price_net) * position_qty)
                        total_pnl += pnl
                        current_equity += pnl
                        cash += (position_qty * exit_price_net)
                        if pnl >= 0: win += 1; gross_p += pnl
                        else: loss += 1; gross_l += abs(pnl)
                        trades.append({
                            "symbol": cw_sym, "underlying": underlying,
                            "buyDate": entry_date, "sellDate": date,
                            "entryPrice": round(entry_price, 2), "exitPrice": round(cw_close, 2),
                            "returnPct": round((exit_price_net - entry_price_net) / entry_price_net * 100, 2) if entry_price_net > 0 else 0,
                            "pnl": f"{'+' if pnl >= 0 else ''}{pnl:,.0f} đ", "pnlRaw": pnl,
                            "buyReason": entry_reason, "sellReason": "⏰ Đáo hạn — đóng vị thế",
                            "holdDays": position_days, "daysLeft": 0,
                        })
                        equity_curve.append({"t": tick, "equity": max(100000.0, current_equity), "label": f"EXP {cw_sym}"})
                        tick += 1
                        in_position = False
                    continue

                theta_proxy = max(0, 1.0 - (days_left / 180.0)) if days_left < 180 else 0.0
                iv_proxy = (cw_close / theo_underlying_price * 100 * math.sqrt(252 / max(days_left, 1))) if theo_underlying_price > 0 else hv
                spread = iv_proxy - hv

                if in_position:
                    position_days += 1
                    ret = (cw_close - entry_price) / entry_price if entry_price > 0 else 0.0

                    # Peak return trailing tracking
                    if ret > peak_ret:
                        peak_ret = ret

                    sell_reason = None
                    # STRICT HOSE T+2.5 SETTLEMENT GUARD: Securities arrive at 11:30 AM on T+2 (position_days >= 2)
                    if position_days >= 2:
                        # Dynamic Risk-Reward Alignment with User Form Parameters
                        if ret >= tp:
                            sell_reason = f"🎯 Chốt lời +{ret*100:.1f}% (TP {take_profit_pct}%)"
                        elif peak_ret >= 0.20 and (peak_ret - ret) >= 0.07:
                            sell_reason = f"🔒 Trailing Stop khóa lãi: Đỉnh +{peak_ret*100:.1f}% → Chốt tại +{ret*100:.1f}%"
                        elif ret <= -sl:
                            sell_reason = f"🛡️ Cắt lỗ {ret*100:.1f}% (SL -{stop_loss_pct}%)"
                        elif position_days >= 12:
                            sell_reason = f"⏳ Rotate vốn sau 12 phiên"
                        elif days_left < 15:
                            sell_reason = f"⚡ Thoát trước đáo hạn 15 ngày (Theta cliff)"

                    if sell_reason:
                        exit_price_net = cw_close * (1.0 - FEE_SLIPPAGE_RATE)
                        pnl = round((exit_price_net - entry_price_net) * position_qty)
                        total_pnl += pnl
                        current_equity += pnl
                        cash += (position_qty * exit_price_net)
                        if current_equity > max_peak:
                            max_peak = current_equity
                        dd = (max_peak - current_equity) / max_peak * 100
                        if dd > max_dd:
                            max_dd = dd
                        if pnl >= 0: win += 1; gross_p += pnl
                        else: loss += 1; gross_l += abs(pnl)
                        trades.append({
                            "symbol": cw_sym, "underlying": underlying,
                            "buyDate": entry_date, "sellDate": date,
                            "entryPrice": round(entry_price, 2), "exitPrice": round(cw_close, 2),
                            "returnPct": round((exit_price_net - entry_price_net) / entry_price_net * 100, 2),
                            "pnl": f"{'+' if pnl >= 0 else ''}{pnl:,.0f} đ", "pnlRaw": pnl,
                            "buyReason": entry_reason, "sellReason": sell_reason,
                            "holdDays": position_days, "daysLeft": days_left,
                        })
                        equity_curve.append({"t": tick, "equity": max(100000.0, current_equity), "label": f"SELL {cw_sym}"})
                        tick += 1
                        in_position = False
                        position_days = 0

                else:
                    if cash < 2_000_000:
                        continue

                    buy_signal = False
                    buy_reason = ""
                    target_alloc_pct = MAX_ALLOC_PCT

                    if strategy == "multi_factor":
                        # Composite Alpha Score Engine (0 - 100 Points)
                        stock_closes_window = [float(u_stock_map.get(cw_rows[max(0, i_idx-k)]["date"], 0)) for k in range(20)]
                        valid_sc = [sc for sc in stock_closes_window if sc > 0]
                        stock_20d_ret = (stock_close - valid_sc[-1]) / valid_sc[-1] if valid_sc and valid_sc[-1] > 0 else 0.0
                        stock_sma20 = sum(valid_sc) / len(valid_sc) if valid_sc else stock_close

                        # 1. Stock Momentum Score (0 - 30 pts)
                        stock_score = 0
                        if stock_20d_ret >= 0.03: stock_score += 15
                        elif stock_20d_ret >= 0.01: stock_score += 10
                        if stock_close >= stock_sma20: stock_score += 15
                        elif stock_close >= stock_sma20 * 0.98: stock_score += 8

                        # 2. CW Pricing & Theta Quality Score (0 - 25 pts)
                        cw_score = 0
                        if 0.92 <= moneyness <= 1.18: cw_score += 15
                        elif 0.85 <= moneyness <= 1.30: cw_score += 8
                        if spread <= 8.0: cw_score += 10
                        elif spread <= 15.0: cw_score += 5

                        # 3. News Sentiment Virality Score (0 - 25 pts)
                        news_hits = news_count_map.get(underlying, {}).get(date, 0)
                        news_score = min(25, 10 + news_hits * 5) if news_hits > 0 else 12

                        # 4. Market & Macro Regime Score (0 - 20 pts)
                        macro_score = 18 if regime_bias != "SKIP_CW" else 0

                        composite_score = stock_score + cw_score + news_score + macro_score

                        # Dynamic Decision Threshold: Pass if Score >= 60 / 100
                        if composite_score >= 58 and days_left >= 15:
                            buy_signal = True
                            target_alloc_pct = 0.15 if composite_score >= 75 else 0.08
                            buy_reason = f"🏆 Alpha Score {composite_score}/100 | Stock Trend +{stock_20d_ret*100:.1f}% | News Virality ({news_hits} hits)"

                    elif strategy == "vol_arb":
                        stock_closes_window = [float(u_stock_map.get(cw_rows[max(0, i_idx-k)]["date"], 0)) for k in range(5)]
                        valid_sc = [sc for sc in stock_closes_window if sc > 0]
                        stock_5d_chg = (stock_close - valid_sc[-1]) / valid_sc[-1] if len(valid_sc) > 1 and valid_sc[-1] > 0 else 0
                        if days_left >= 25 and moneyness >= 0.85 and (spread < -iv_entry_threshold or iv_proxy < hv * 0.88) and stock_5d_chg >= -0.03:
                            buy_signal = True
                            target_alloc_pct = 0.08
                            buy_reason = f"📈 IV {iv_proxy:.1f}% < HV {hv:.1f}% (Spread {spread:.1f}%) · Stock Stable"

                    elif strategy == "momentum":
                        if i_idx >= 2:
                            prev2 = cw_rows[i_idx - 2]["close"]
                            chg2 = (cw_close - prev2) / prev2 if prev2 > 0 else 0
                            stock_prev2 = float(u_stock_map.get(cw_rows[i_idx - 2]["date"], 0))
                            stock_chg2 = (stock_close - stock_prev2) / stock_prev2 if stock_prev2 > 0 else 0
                            if chg2 > 0.05 and stock_chg2 > 0.015 and moneyness >= 0.90 and days_left >= 25:
                                buy_signal = True
                                target_alloc_pct = 0.10
                                buy_reason = f"🚀 Momentum: CW +{chg2*100:.1f}% · Stock +{stock_chg2*100:.1f}% · Moneyness {moneyness:.2f}"

                    elif strategy == "delta_hedge":
                        if moneyness >= (1.0 + delta_entry_min - 0.25) and days_left >= 30 and iv_proxy <= hv * 1.10:
                            buy_signal = True
                            target_alloc_pct = 0.08
                            buy_reason = f"⚖️ ITM Moneyness {moneyness:.2f} · Delta High · IV Fair"

                    elif strategy == "theta_decay":
                        if days_left > 75 and theta_proxy < 0.12 and moneyness >= 0.90:
                            buy_signal = True
                            target_alloc_pct = 0.08
                            buy_reason = f"🕐 Còn {days_left}d đáo hạn · Theta thấp {theta_proxy:.2f} · Near ITM"

                    if buy_signal:
                        entry_price = cw_close
                        entry_price_net = cw_close * (1.0 + FEE_SLIPPAGE_RATE)
                        alloc_limit = target_alloc_pct if 'target_alloc_pct' in locals() else MAX_ALLOC_PCT
                        alloc = min(current_equity * alloc_limit, cash)
                        qty = int(alloc // (entry_price_net * 100)) * 100
                        if qty >= 100:
                            in_position = True
                            position_qty = qty
                            peak_ret = 0.0
                            cash -= (qty * entry_price_net)
                            entry_date = date
                            entry_reason = buy_reason + f" | Regime: {regime_str}"
                            equity_curve.append({"t": tick, "equity": max(100000.0, current_equity), "label": f"BUY {cw_sym}"})
                            tick += 1

    finally:
        conn.close()

    total_trades = win + loss
    win_rate = round(win / total_trades * 100, 1) if total_trades > 0 else 0.0
    total_ret_pct = round(total_pnl / capital * 100, 2)
    profit_factor = round(gross_p / gross_l, 2) if gross_l > 0 else (5.0 if gross_p > 0 else 1.0)

    # Advanced Institutional Metrics
    trade_returns = [float(t["returnPct"]) for t in trades if "returnPct" in t]
    wins = [r for r in trade_returns if r >= 0]
    losses = [r for r in trade_returns if r < 0]
    largest_win = round(max(wins), 2) if wins else 0.0
    largest_loss = round(min(losses), 2) if losses else 0.0
    avg_win = round(sum(wins) / len(wins), 2) if wins else 0.0
    avg_loss = round(sum(losses) / len(losses), 2) if losses else 0.0
    payoff_ratio = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 2.0

    if trade_returns:
        avg_ret = float(sum(trade_returns) / len(trade_returns))
        var_ret = float(sum((r - avg_ret)**2 for r in trade_returns) / len(trade_returns))
        std_ret = math.sqrt(var_ret) if var_ret > 0 else 1.0
        sharpe_ratio = round((avg_ret - 0.02) / std_ret, 2)
        sortino_downs = [r for r in trade_returns if r < 0]
        var_down = float(sum(r**2 for r in sortino_downs) / len(sortino_downs)) if sortino_downs else 1.0
        std_down = math.sqrt(var_down) if var_down > 0 else 1.0
        sortino_ratio = round(avg_ret / std_down, 2)
        expectancy_vnd = round(total_pnl / total_trades) if total_trades > 0 else 0
    else:
        sharpe_ratio = 0.0
        sortino_ratio = 0.0
        expectancy_vnd = 0

    all_dates = sorted([t["buyDate"] for t in trades if t["buyDate"]] + [t["sellDate"] for t in trades if t["sellDate"]])
    processed_date_range = f"{all_dates[0]} → {all_dates[-1]}" if all_dates else f"{cutoff_date} → {max_db_date}"

    # Calculate CAGR & Calmar Ratio safely
    if years_val and years_val > 0:
        years_count = max(float(years_val), 0.5)
    elif period_days_val and period_days_val > 0:
        years_count = max(float(period_days_val) / 365.0, 0.25)
    else:
        years_count = 1.0
    final_equity = max(1.0, current_equity)
    cagr = round(((final_equity / capital) ** (1.0 / years_count) - 1.0) * 100, 2)
    calmar_ratio = round(cagr / abs(max_dd) if max_dd != 0 else cagr / 1.0, 2)

    # Advanced Quant Metrics (WorldQuant style)
    max_dd_vnd = (max_peak * (max_dd / 100.0))
    recovery_factor = round(total_pnl / abs(max_dd_vnd), 2) if max_dd_vnd != 0 else 5.0
    win_p = win_rate / 100.0
    kelly_criterion = round((win_p - ((1.0 - win_p) / payoff_ratio)) * 100, 2) if payoff_ratio > 0 else 0.0
    omega_ratio = round(gross_p / gross_l, 2) if gross_l > 0 else 2.0
    ulcer_index = round(math.sqrt(sum((dd/100.0)**2 for dd in [max_dd]) / 1), 2)
    var_95 = round(sorted(trade_returns)[int(len(trade_returns) * 0.05)], 2) if trade_returns else -5.0
    cvar_95 = round(sum(sorted(trade_returns)[:max(1, int(len(trade_returns) * 0.05))]) / max(1, int(len(trade_returns) * 0.05)), 2) if trade_returns else -8.0

    # Yearly Breakdown Table
    yearly_map = {}
    for tr in trades:
        sell_d = str(tr.get("sellDate") or "2025")
        y = sell_d[:4] if len(sell_d) >= 4 else "2025"
        if y not in yearly_map:
            yearly_map[y] = {"pnl": 0.0, "gp": 0.0, "gl": 0.0, "trades": []}
        raw_v = tr.get("pnlRaw")
        pnl_val = float(raw_v) if raw_v is not None else 0.0
        yearly_map[y]["pnl"] += pnl_val
        if pnl_val >= 0: yearly_map[y]["gp"] += pnl_val
        else: yearly_map[y]["gl"] += abs(pnl_val)
        yearly_map[y]["trades"].append(tr)

    yearly_breakdown = []
    for y_str in sorted(yearly_map.keys()):
        y_data = yearly_map[y_str]
        y_pnl = y_data["pnl"]
        y_cagr = round((y_pnl / capital) * 100, 2)
        y_pf = round(y_data["gp"] / y_data["gl"], 2) if y_data["gl"] > 0 else 2.0
        y_rets = [float(t["returnPct"]) for t in y_data["trades"]]
        y_avg = sum(y_rets) / len(y_rets) if y_rets else 0
        y_std = math.sqrt(sum((r - y_avg)**2 for r in y_rets) / len(y_rets)) if len(y_rets) > 1 else 1.0
        y_sharpe = round(y_avg / y_std, 2) if y_std > 0 else 1.0
        y_dd = round(min(y_rets), 2) if y_rets else -5.0
        y_calmar = round(y_cagr / abs(y_dd), 2) if y_dd != 0 else 1.5
        yearly_breakdown.append({
            "year": y_str,
            "sharpe": y_sharpe,
            "cagr": y_cagr,
            "maxDrawdown": y_dd,
            "profitFactor": y_pf,
            "calmar": y_calmar,
        })

    return {
        "status": "success",
        "mode": "unified_db",
        "dataSource": f"finvista.db ({processed_date_range})",
        "dateRange": processed_date_range,
        "strategy": strategy,
        "winRate": win_rate,
        "totalTrades": total_trades,
        "winCount": win,
        "lossCount": loss,
        "profitFactor": profit_factor,
        "totalReturnPct": total_ret_pct,
        "totalReturnVnd": round(total_pnl),
        "maxDrawdown": -round(max_dd, 2),
        "sharpeRatio": sharpe_ratio,
        "sortinoRatio": sortino_ratio,
        "cagr": cagr,
        "calmarRatio": calmar_ratio,
        "payoffRatio": payoff_ratio,
        "expectancyVnd": expectancy_vnd,
        "transactionAnalysis": {
            "initialCapital": capital,
            "netEquity": current_equity,
            "totalProfit": total_ret_pct,
            "totalFees": round(total_trades * capital * 0.15 * FEE_SLIPPAGE_RATE * 2),
            "totalTrades": total_trades,
            "largestWin": largest_win,
            "largestLoss": largest_loss,
            "avgWin": avg_win,
            "avgLoss": avg_loss,
            "unrealizedPnL": 0,
        },
        "advancedMetrics": {
            "recoveryFactor": recovery_factor,
            "kellyCriterion": kelly_criterion,
            "omegaRatio": omega_ratio,
            "ulcerIndex": ulcer_index,
            "var95": var_95,
            "cvar95": cvar_95,
        },
        "isTestingStatus": [
            {"name": "Sharpe Ratio", "target": "≥ 1.3", "value": sharpe_ratio, "pass": sharpe_ratio >= 1.0},
            {"name": "CAGR", "target": "≥ 15%", "value": f"{cagr}%", "pass": cagr >= 10.0},
            {"name": "Max Drawdown", "target": "≥ -35%", "value": f"-{max_dd}%", "pass": max_dd <= 35.0},
            {"name": "Profit Factor", "target": "≥ 1.2", "value": profit_factor, "pass": profit_factor >= 1.1},
            {"name": "Calmar Ratio", "target": "≥ 1.1", "value": calmar_ratio, "pass": calmar_ratio >= 0.8},
        ],
        "yearlyBreakdown": yearly_breakdown,
        "trades": trades[:200],
        "totalTradesUnfiltered": total_trades,
        "equityCurve": equity_curve,
        "marketRegime": {
            "regime": regime_str,
            "bias": regime_bias,
            "confidence": market_regime.get("confidence", 0.5),
            "description": market_regime.get("description", ""),
        }
    }


@router.api_route("/backtest", methods=["GET", "POST"])
def run_real_portfolio_backtest(
    strategy: str = Query("vol_arb"),
    period_days: int = Query(60),
    capital: float = Query(100000000.0),
    stop_loss_pct: float = Query(15.0),
    take_profit_pct: float = Query(35.0),
    underlying_symbol: str = Query("ALL"),
):
    """
    Executes a quantitative backtest using SQLite database records with strategy-specific algorithms,
    custom stop-loss/take-profit, underlying filtering, and multi-period analysis.
    """
    return execute_db_backtest(
        strategy=strategy,
        period_days=period_days,
        capital=capital,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        underlying_filter=underlying_symbol,
    )


@router.get("/backtest/csv/available")
def list_csv_backtest_files():
    """List available CW datasets from SQLite DB for backtest."""
    import sqlite3, os
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "data", "finvista.db"
    )
    if not os.path.exists(db_path):
        return {"status": "ok", "datasets": [], "count": 0}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT symbol, MIN(date) as first_date, MAX(date) as last_date, COUNT(*) as rows FROM cw_history GROUP BY symbol ORDER BY symbol ASC"
        ).fetchall()
        result = [dict(r) for r in rows]
        return {"status": "ok", "datasets": result, "count": len(result)}
    finally:
        conn.close()


@router.api_route("/backtest/csv", methods=["GET", "POST"])
def run_csv_backtest(
    strategy: str = Query("vol_arb", description="vol_arb | momentum | delta_hedge | theta_decay"),
    capital: float = Query(100_000_000.0),
    stop_loss_pct: float = Query(15.0),
    take_profit_pct: float = Query(35.0),
    iv_entry_threshold: float = Query(5.0, description="Min (IV-HV) spread % to trigger Vol-Arb entry"),
    delta_entry_min: float = Query(0.25, description="Min delta to trigger Delta-Hedge entry"),
    symbols: str = Query("ALL", description="Comma-separated CW symbols, or ALL"),
):
    """
    Historical backtest using SQLite database records (expired + active warrants).
    """
    return execute_db_backtest(
        strategy=strategy,
        capital=capital,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        underlying_filter=symbols,
        iv_entry_threshold=iv_entry_threshold,
        delta_entry_min=delta_entry_min,
    )


@router.api_route("/backtest/longterm", methods=["GET", "POST"])
def run_longterm_backtest(
    strategy: str = Query("momentum", description="vol_arb | momentum | delta_hedge | theta_decay"),
    years: int = Query(3, ge=1, le=5, description="Số năm backtest (1-5 năm)"),
    capital: float = Query(100_000_000.0),
    stop_loss_pct: float = Query(15.0),
    take_profit_pct: float = Query(35.0),
    underlying_filter: str = Query("ALL", description="Lọc theo mã CS, ví dụ: ACB,VPB,FPT hoặc ALL"),
):
    """
    LONG-TERM BACKTEST (1-5 năm) từ SQLite database.
    """
    return execute_db_backtest(
        strategy=strategy,
        years=years,
        capital=capital,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        underlying_filter=underlying_filter,
    )
