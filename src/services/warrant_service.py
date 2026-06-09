# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: WARRANT BUSINESS LOGIC SERVICE
===========================================
Decouples quantitative calculations, database access, and simulations
from the FastAPI delivery layer.

Author: samvo
"""

import math
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
from fastapi import HTTPException, status
from scipy.stats import norm
from sqlalchemy import desc

from src.common.database import MarketOpportunity, SessionLocal, CorporateNews, CorporateEvent
from src.quant.pricing.pricing_core import (
    RISK_FREE_RATE,
    calculate_d1_d2,
    calculate_greeks_for_cw,
    fetch_dynamic_risk_free_rate,
    parse_ratio,
)
from src.quant.engines.history_analyzer import analyze_historical_warrant
from src.quant.engines.run_analysis import run_quant_pipeline_programmatic
from src.trading.paper_trader import REPORT_PATH

class WarrantService:
    @staticmethod
    def get_news(symbol: Optional[str] = None, category: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """Retrieve latest corporate news from the database."""
        db = SessionLocal()
        try:
            query = db.query(CorporateNews)
            if symbol:
                query = query.filter(CorporateNews.symbol == symbol.upper().strip())
            if category:
                query = query.filter(CorporateNews.category == category)
            
            query = query.order_by(desc(CorporateNews.date))
            news_list = query.limit(limit).all()
            
            results = []
            for item in news_list:
                results.append({
                    "symbol": item.symbol,
                    "title": item.title,
                    "link": item.link,
                    "date": item.date,
                    "source": item.source,
                    "category": item.category,
                    "summary": item.summary
                })
            
            return {
                "status": "success",
                "count": len(results),
                "news": results
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Warrant Service: Failed to fetch news: {str(e)}",
            )
        finally:
            db.close()

    @staticmethod
    def get_events(ticker: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """Retrieve upcoming corporate events from the database."""
        db = SessionLocal()
        try:
            query = db.query(CorporateEvent)
            if ticker:
                query = query.filter(CorporateEvent.ticker == ticker.upper().strip())
            
            # Filter for future events or recent past if desired
            # For now, just return latest updated events
            query = query.order_by(desc(CorporateEvent.event_date))
            events_list = query.limit(limit).all()
            
            results = []
            for item in events_list:
                results.append({
                    "ticker": item.ticker,
                    "event_date": item.event_date,
                    "event_type": item.event_type,
                    "description": item.description
                })
            
            return {
                "status": "success",
                "count": len(results),
                "events": results
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Warrant Service: Failed to fetch events: {str(e)}",
            )
        finally:
            db.close()

    @staticmethod
    def get_opportunities(
        strategy: str = "balanced",
        underlying: Optional[str] = None,
        limit: int = 10,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Retrieve quantitative Covered Warrant recommendations."""
        db = SessionLocal()
        try:
            count = db.query(MarketOpportunity).count()

            if count == 0 or force_refresh:
                # Note: In a production environment, you might want to run this as a background task
                # or prevent multiple simultaneous scans.
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
                    "garch_theoretical_price": (
                        round(row.garch_theoretical_price, 2) if row.garch_theoretical_price is not None else 0.0
                    ),
                    "garch_upside_pct": (
                        round(row.garch_upside_pct, 2) if row.garch_upside_pct is not None else 0.0
                    ),
                    "merton_theoretical_price": (
                        round(row.merton_theoretical_price, 2) if row.merton_theoretical_price is not None else 0.0
                    ),
                    "merton_upside_pct": (
                        round(row.merton_upside_pct, 2) if row.merton_upside_pct is not None else 0.0
                    ),
                    "underlying_credit": {
                        "is_distressed": row.underlying_is_distressed == 1,
                        "altman_z_score": (
                            round(row.underlying_altman_z, 2)
                            if row.underlying_altman_z is not None
                            else 3.0
                        ),
                    },
                    "banking_metrics": {
                        "nim": round(row.underlying_nim, 4) if row.underlying_nim is not None else None,
                        "npl": round(row.underlying_npl, 4) if row.underlying_npl is not None else None,
                        "casa": round(row.underlying_casa, 4) if row.underlying_casa is not None else None,
                        "car": round(row.underlying_car, 4) if row.underlying_car is not None else None,
                    } if row.underlying_nim is not None else None,
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
                detail=f"Warrant Service: Failed to fetch market opportunities: {str(e)}",
            )
        finally:
            db.close()

    @staticmethod
    def calculate_greeks(
        underlying_price: float,
        strike_price: float,
        days_to_maturity: int,
        implied_volatility: float,
        conversion_ratio: float,
        risk_free_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """Solve for Option Greeks and probabilities."""
        try:
            r = risk_free_rate
            if r is None:
                r = fetch_dynamic_risk_free_rate()

            res = calculate_greeks_for_cw(
                underlying_price=underlying_price,
                strike_price=strike_price,
                days_to_maturity=days_to_maturity,
                implied_volatility=implied_volatility,
                conversion_ratio=conversion_ratio,
                risk_free_rate=r,
            )
            return {
                "delta": round(res["delta"], 4),
                "gamma": round(res["gamma"], 6),
                "vega": round(res["vega"], 4),
                "theta": round(res["theta"] * underlying_price, 2),
                "rho": round(res["rho"], 4),
                "moneyness": round(res["moneyness"], 4),
                "moneyness_category": res["moneyness_category"],
                "prob_itm": round(res["prob_itm"], 4),
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Warrant Service: Options solver calculation failed: {str(e)}",
            )

    @staticmethod
    def simulate_scenarios(symbol: str) -> Dict[str, Any]:
        """Generate a 2D P/L Scenario Matrix for a specific Covered Warrant."""
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
                detail=f"Warrant Service: Failed to calculate 2D scenario matrix: {str(e)}",
            )

    @staticmethod
    def get_history(symbol: str, days: int = 15) -> Dict[str, Any]:
        """Retrieve historical volatility and Greeks for a warrant."""
        symbol_clean = symbol.upper().strip()
        try:
            df = analyze_historical_warrant(symbol_clean, lookback_days=days)
            if df.empty:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Historical data for warrant '{symbol_clean}' could not be resolved or mapped."
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
                detail=f"Warrant Service: Failed to perform historical analysis: {str(e)}",
            )
