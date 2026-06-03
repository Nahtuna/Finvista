# -*- coding: utf-8 -*-
"""Covered warrant pricing, scan, simulation, and history routes."""

import asyncio
import math
import os
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from scipy.stats import norm

from src.api import state
from src.api.dependencies import limiter
from src.api.websocket import manager
from src.common import config
from src.cw_engine.history_analyzer import analyze_historical_warrant
from src.cw_engine.pricing_core import (
    RISK_FREE_RATE,
    calculate_d1_d2,
    calculate_greeks_for_cw,
    fetch_dynamic_risk_free_rate,
    parse_ratio,
)
from src.cw_engine.run_analysis import run_quant_pipeline_programmatic

router = APIRouter(tags=["warrants"])


class GreeksCalculatorRequest(BaseModel):
    underlying_price: float = Field(
        ..., description="Current market price of the underlying asset (VND)", example=28500.0
    )
    strike_price: float = Field(
        ..., description="Strike price of the covered warrant (VND)", example=25000.0
    )
    days_to_maturity: int = Field(
        ..., description="Number of calendar days remaining until expiry", example=95
    )
    implied_volatility: float = Field(
        ...,
        description="Annualized implied volatility (as decimal, e.g. 0.45 for 45%)",
        example=0.42,
    )
    conversion_ratio: float = Field(
        1.0, description="Conversion ratio (e.g. 10.0 for 10:1 ratio)", example=10.0
    )
    risk_free_rate: Optional[float] = Field(
        None,
        description="Continuous risk-free rate (optional, falls back to live 1Y Gov Yield)",
        example=0.045,
    )


class GreekCalculatorResponse(BaseModel):
    delta: float = Field(..., description="Warrant Delta adjusted for conversion ratio")
    gamma: float = Field(..., description="Warrant Gamma adjusted for conversion ratio")
    vega: float = Field(..., description="Warrant Vega adjusted for conversion ratio")
    theta: float = Field(..., description="Warrant Theta per calendar day (VND)")
    rho: float = Field(..., description="Warrant Rho")
    moneyness: float = Field(..., description="Underlying / Strike")
    moneyness_category: str = Field(..., description="ITM, ATM, or OTM")
    prob_itm: float = Field(..., description="Probability of expiring in-the-money")


@router.get("/api/warrants/opportunities")
def get_cw_opportunities(
    strategy: str = Query(
        "balanced", regex="^(balanced|safe|aggressive)$", description="Target trading profile"
    ),
    underlying: Optional[str] = Query(
        None, description="Filter by underlying stock ticker (e.g. HPG)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Max recommendations to return"),
    force_refresh: bool = Query(
        False, description="Force running full market crawl and calculations"
    ),
):
    """
    Retrieve elite quantitative Covered Warrant recommendations sorted by G-Score,
    automatically filtered by credit distress Hard-Gates. Reads directly from SQLite DB under 5ms.
    """
    from sqlalchemy import desc
    from src.common.database import MarketOpportunity, SessionLocal

    db = SessionLocal()
    try:
        count = db.query(MarketOpportunity).count()

        if count == 0 or force_refresh:
            print(
                "🚀 Database empty or refresh forced. "
                "Triggering live market quantitative pipeline scan..."
            )
            run_quant_pipeline_programmatic(strategy=strategy)

        query = db.query(MarketOpportunity)
        if underlying:
            query = query.filter(MarketOpportunity.underlying == underlying.upper().strip())

        query = query.order_by(desc(MarketOpportunity.score))
        opps_list = query.limit(limit).all()

        results = []
        for row in opps_list:
            results.append({
                "warrant_symbol": row.symbol,
                "underlying_symbol": row.underlying,
                "issuer": row.issuer,
                "market_price": row.price,
                "price_change_pct": (
                    round(row.price_change_pct, 2) if row.price_change_pct is not None else 0.0
                ),
                "strike_price": row.strike_price,
                "break_even_price": row.break_even_price,
                "premium_pct": round(row.premium_pct, 2) if row.premium_pct is not None else 0.0,
                "days_to_maturity": row.days_to_maturity,
                "effective_gearing": round(row.gearing, 2) if row.gearing is not None else 0.0,
                "implied_volatility_pct": (
                    round(row.implied_volatility_pct, 2)
                    if row.implied_volatility_pct is not None
                    else 0.0
                ),
                "historical_volatility_pct": (
                    round(row.historical_volatility_pct, 2)
                    if row.historical_volatility_pct is not None
                    else 0.0
                ),
                "delta": round(row.delta, 4) if row.delta is not None else 0.0,
                "theta_daily_burn": (
                    round(row.theta_burn_day, 2) if row.theta_burn_day is not None else 0.0
                ),
                "composite_g_score": round(row.score, 2) if row.score is not None else 0.0,
                "recommendation_signal": row.decision_signal,
                "proj_3d_flat_pct": (
                    round(row.proj_3d_flat_pct, 2) if row.proj_3d_flat_pct is not None else 0.0
                ),
                "proj_3d_up_pct": (
                    round(row.proj_3d_up_pct, 2) if row.proj_3d_up_pct is not None else 0.0
                ),
                "proj_3d_down_pct": (
                    round(row.proj_3d_down_pct, 2) if row.proj_3d_down_pct is not None else 0.0
                ),
                "underlying_credit": {
                    "is_distressed": row.underlying_is_distressed == 1,
                    "altman_z_score": (
                        round(row.underlying_altman_z, 2)
                        if row.underlying_altman_z is not None
                        else 3.0
                    ),
                },
            })

        return {
            "status": "success",
            "strategy": strategy,
            "count": len(results),
            "recommendations": results,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market opportunities: {str(e)}",
        )
    finally:
        db.close()


@router.post("/api/warrants/greeks", response_model=GreekCalculatorResponse)
def calculate_greeks(req: GreeksCalculatorRequest):
    """
    Dynamic BSM Options Solver Calculator. Accepts price, strike, volatility
    and returns full Greeks and ITM probabilities.
    """
    try:
        r = req.risk_free_rate
        if r is None:
            r = fetch_dynamic_risk_free_rate()

        res = calculate_greeks_for_cw(
            underlying_price=req.underlying_price,
            strike_price=req.strike_price,
            days_to_maturity=req.days_to_maturity,
            implied_volatility=req.implied_volatility,
            conversion_ratio=req.conversion_ratio,
            risk_free_rate=r,
        )
        return {
            "delta": round(res["delta"], 4),
            "gamma": round(res["gamma"], 6),
            "vega": round(res["vega"], 4),
            "theta": round(res["theta"] * req.underlying_price, 2),
            "rho": round(res["rho"], 4),
            "moneyness": round(res["moneyness"], 4),
            "moneyness_category": res["moneyness_category"],
            "prob_itm": round(res["prob_itm"], 4),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Options solver calculation failed: {str(e)}",
        )


@router.post("/api/warrants/scan")
@limiter.limit("1/minute")
async def trigger_market_scan(
    request: Request,
    strategy: str = Query("balanced", regex="^(balanced|safe|aggressive)$"),
):
    """
    Manually trigger a complete real-time market data crawl and quantitative analysis scan.
    Rate limited to 1 execution per minute per client IP. Broadcasts completion state to WebSockets.
    """
    try:
        print("⚡ Manual trigger: Real-time quantitative scanner initiated...")
        df = await asyncio.to_thread(run_quant_pipeline_programmatic, strategy=strategy)
        state.pipeline_cache["data"] = df
        state.pipeline_cache["last_scanned"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        await manager.broadcast({
            "event": "market_scan_completed",
            "message": (
                f"Real-time quantitative scan successfully completed! "
                f"Refreshed {len(df)} Covered Warrants."
            ),
            "timestamp": state.pipeline_cache["last_scanned"],
        })

        return {
            "status": "success",
            "message": (
                f"Successfully completed real-time quant scanner! Refreshed {len(df)} warrants."
            ),
            "last_updated": state.pipeline_cache["last_scanned"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scanner execution failed: {str(e)}",
        )


async def run_async_scan_task(strategy: str):
    """Worker function to run heavy quant calculations in a worker thread and broadcast over WS."""
    try:
        print(f"⚙️ [Async Background Task] Starting full quant scan under strategy: {strategy}")
        await asyncio.to_thread(run_quant_pipeline_programmatic, strategy=strategy)
        print("✅ [Async Background Task] Successfully completed scan and synchronized to database.")

        await manager.broadcast({
            "event": "market_scan_completed",
            "message": (
                "Background market data scan finished and SQLite DB is fully synchronized."
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception as e:
        print(f"❌ [Async Background Task] Scan failed: {e}")


@router.post("/api/warrants/scan/async", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("1/minute")
async def trigger_market_scan_async(
    request: Request,
    background_tasks: BackgroundTasks,
    strategy: str = Query("balanced", regex="^(balanced|safe|aggressive)$"),
):
    """
    Asynchronously triggers a complete real-time market data crawl and quantitative scan.
    Rate limited to 1 execution per minute per client IP. Broadcasts queueing state instantly.
    """
    background_tasks.add_task(run_async_scan_task, strategy)

    await manager.broadcast({
        "event": "market_scan_queued",
        "message": (
            f"Market scan asynchronously queued in background under strategy: '{strategy}'"
        ),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    return {
        "status": "accepted",
        "message": (
            "Market scan successfully queued in background task queue. "
            "Check logs or query database."
        ),
        "strategy_queued": strategy,
    }


@router.get("/api/warrants/{symbol}/simulate")
def get_warrant_simulation(symbol: str):
    """
    Generate a 2D P/L Scenario Matrix for a specific Covered Warrant.
    Models the joint impact of underlying asset price changes (-10% to +10%)
    and holding period theta time decay (0 to 30 days) using Black-Scholes pricing.
    """
    from src.cw_engine.paper_trader import REPORT_PATH

    symbol_clean = symbol.upper().strip()
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market report is not initialized. Run analysis pipeline first.",
        )

    try:
        df = pd.read_csv(REPORT_PATH)
        match_rows = df[df["A_MaCW"] == symbol_clean]
        if match_rows.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Covered Warrant symbol '{symbol_clean}' was not found in the latest market scan."
                ),
            )

        row = match_rows.iloc[0]
        S = float(row.get("hidden_underlying_price", 0.0))
        K = float(row.get("R_Strike", 0.0))
        days_to_maturity = int(row.get("L_Ngay", 0))
        iv = float(row.get("S_IV_Pct", 45.0)) / 100.0
        ratio = parse_ratio(row.get("hidden_ratio", "1:1"))
        current_price = float(row.get("C_GiaCW", 0.0))
        underlying_symbol = row.get("B_MaCPCS", "UNKNOWN")

        if S <= 0 or current_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Warrant '{symbol_clean}' has invalid market pricing parameters.",
            )

        price_changes = [-0.10, -0.05, -0.02, 0.00, 0.02, 0.05, 0.10]
        holding_days = [0, 5, 10, 20, 30]

        scenarios = []
        for hold in holding_days:
            if hold >= days_to_maturity:
                continue

            remaining_days = days_to_maturity - hold
            T_new = remaining_days / 365.0

            matrix_row = []
            for chg in price_changes:
                S_new = S * (1 + chg)
                d1, d2 = calculate_d1_d2(S_new, K, T_new, RISK_FREE_RATE, iv)
                theo_new = (
                    S_new * norm.cdf(d1) - K * math.exp(-RISK_FREE_RATE * T_new) * norm.cdf(d2)
                ) / ratio

                pl_pct = (theo_new - current_price) / current_price * 100 if current_price > 0 else 0.0
                matrix_row.append({
                    "change_pct": round(chg * 100, 1),
                    "underlying_price": round(S_new, 2),
                    "theoretical_price": round(theo_new, 2),
                    "p_l_pct": round(pl_pct, 2),
                })

            scenarios.append({
                "holding_days": hold,
                "remaining_days": remaining_days,
                "matrix": matrix_row,
            })

        return {
            "symbol": symbol_clean,
            "underlying_symbol": underlying_symbol,
            "strike_price": K,
            "current_price": current_price,
            "underlying_current_price": S,
            "implied_volatility_pct": round(iv * 100, 2),
            "days_to_maturity": days_to_maturity,
            "scenarios": scenarios,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate 2D scenario matrix: {str(e)}",
        )


@router.get("/api/warrants/{symbol}/history")
def get_warrant_history(
    symbol: str,
    days: int = Query(15, ge=5, le=60, description="Number of trading sessions to look back"),
):
    """
    Retrieve session-by-session historical volatility structures, back-solved IVs,
    rolling HVs, spreads, daily price changes, and historical Greeks for a specific Covered Warrant.
    """
    symbol_clean = symbol.upper().strip()
    try:
        df = analyze_historical_warrant(symbol_clean, lookback_days=days)
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Historical data for warrant '{symbol_clean}' could not be resolved or mapped. "
                    "Ensure run_cw.py has run first."
                ),
            )

        history_records = []
        for _, row in df.iterrows():
            history_records.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "warrant_price": float(row["close_cw"]),
                "warrant_change_pct": round(float(row["chg_cw"]), 2),
                "underlying_price": float(row["close_stock"]),
                "underlying_change_pct": round(float(row["chg_stock"]), 2),
                "implied_volatility_pct": round(float(row["iv"] * 100), 2),
                "historical_volatility_pct": round(float(row["hv"] * 100), 2),
                "vol_spread_pct": round(float((row["iv"] - row["hv"]) * 100), 2),
                "delta": round(float(row["delta"]), 4),
                "gearing": round(float(row["gearing"]), 2),
                "theta_burn_pct": round(float(row["theta_burn"] * 100), 3),
            })

        avg_iv = float(df["iv"].mean() * 100)
        avg_hv = float(df["hv"].mean() * 100)
        avg_spread = avg_iv - avg_hv
        avg_gearing = float(df["gearing"].mean())

        valuation_assessment = "FAIR"
        if avg_spread < -5.0:
            valuation_assessment = "CHEAP"
        elif avg_spread > 10.0:
            valuation_assessment = "EXPENSIVE"

        return {
            "symbol": symbol_clean,
            "lookback_sessions": len(df),
            "averages": {
                "average_iv_pct": round(avg_iv, 2),
                "average_hv_pct": round(avg_hv, 2),
                "average_spread_pct": round(avg_spread, 2),
                "average_gearing": round(avg_gearing, 2),
                "valuation_assessment": valuation_assessment,
            },
            "history": history_records,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform historical warrant volatility analysis: {str(e)}",
        )
