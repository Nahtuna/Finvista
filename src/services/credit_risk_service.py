# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: CORPORATE CREDIT RISK SERVICE
==========================================
Orchestrates feature engineering, ML distress prediction (XGBoost),
and financial health assessment.

Author: samvo
"""

import os
import math
import pandas as pd
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

from src.api import state
from src.common import config
from src.common.ai_client import get_ai_client

class CreditRiskService:
    @staticmethod
    def get_credit_health(ticker: str) -> Dict[str, Any]:
        """
        Retrieve deep fundamental credit indicators and XGBoost bankruptcy alert ratings.
        """
        ticker_clean = ticker.upper().strip()
        
        if not os.path.exists(config.FINAL_DATASET_FILE):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Corporate Credit Health Database is currently offline/unavailable.",
            )

        try:
            df = pd.read_csv(config.FINAL_DATASET_FILE)
            ticker_df = df[df["ticker"] == ticker_clean]
            
            if ticker_df.empty:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Ticker '{ticker_clean}' not found in the credit health registry "
                        "or is an excluded sector."
                    ),
                )

            latest = ticker_df.sort_values("year").iloc[-1]
            
            # 1. Basic Metrics
            z_score = float(latest.get("altman_z_score", 0.0))
            is_distressed_label = int(latest.get("distress_label", 0))

            # 2. ML Prediction (XGBoost)
            bankruptcy_prob = CreditRiskService._predict_bankruptcy_probability(latest, ticker_df)
            
            # 3. Determine Risk Zone
            zone, risk_description = CreditRiskService._determine_risk_zone(z_score, is_distressed_label)

            # 4. Generate AI Commentary
            ai_commentary = CreditRiskService._get_ai_commentary(ticker_clean, latest, z_score)

            # 5. Build Response
            response = {
                "ticker": ticker_clean,
                "reported_year": int(latest.get("year")),
                "credit_metrics": {
                    "altman_z_score": round(z_score, 4),
                    "risk_zone": zone,
                    "is_ml_distressed": is_distressed_label == 1,
                    "bankruptcy_probability": round(bankruptcy_prob, 4),
                    "active_threshold": state.distress_threshold,
                    "status_description": risk_description,
                },
                "financial_ratios": {
                    "leverage_debt_ratio": round(float(latest.get("debt_ratio", 0.0)), 4),
                    "liquidity_current_ratio": round(float(latest.get("current_ratio", 0.0)), 4),
                    "roa": round(float(latest.get("roa", 0.0)), 4),
                    "roe": round(float(latest.get("roe", 0.0)), 4),
                    "ebit_to_assets": round(float(latest.get("ebit_to_assets", 0.0)), 4),
                    "icr": round(
                        float(latest.get("icr", latest.get("ebit_to_interest", 0.0))), 4
                    ),
                    "ocf_to_total_debt": round(float(latest.get("ocf_to_total_debt", 0.0)), 4),
                },
                "distress_scores": {
                    "altman_z_score": round(z_score, 4),
                    "altman_zone": zone,
                    "springate_s_score": round(float(latest.get("springate_s_score", 0.0)), 4),
                    "springate_distressed": bool(latest.get("springate_distressed", 0)),
                    "zmijewski_x_score": round(float(latest.get("zmijewski_x_score", 0.0)), 4),
                    "zmijewski_distressed": bool(latest.get("zmijewski_distressed", 0)),
                },
            }

            if ai_commentary:
                response["ai_commentary"] = ai_commentary

            return response

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Credit Risk Service: Failed to query credit health: {str(e)}",
            )

    @staticmethod
    def _predict_bankruptcy_probability(latest: pd.Series, ticker_df: pd.DataFrame) -> float:
        """Internal helper to run XGBoost inference."""
        if state.distress_model is not None and state.distress_scaler is not None:
            try:
                exclude_cols = {
                    "ticker", "company_name", "year", "exchange", "industry",
                    "distress_label", "distress_label_next_year",
                    "ebit_to_interest", "icr", "current_ratio", "total_equity",
                    "springate_distressed", "zmijewski_distressed",
                }
                feature_cols = [c for c in ticker_df.columns if c not in exclude_cols]
                latest_feat = latest[feature_cols].to_frame().T.astype(float)
                
                # Apply scaling
                latest_scaled = state.distress_scaler.transform(latest_feat)
                latest_scaled_df = pd.DataFrame(latest_scaled, columns=feature_cols)
                
                if hasattr(state.distress_model, "predict_proba"):
                    return float(state.distress_model.predict_proba(latest_scaled_df)[0, 1])
                else:
                    score = float(state.distress_model.decision_function(latest_scaled_df)[0])
                    return float(1 / (1 + math.exp(-score)))
            except Exception as e:
                print(f"⚠️ ML Prediction failed, falling back to label: {e}")
        
        return 0.85 if int(latest.get("distress_label", 0)) == 1 else 0.10

    @staticmethod
    def _determine_risk_zone(z_score: float, is_distressed: int) -> tuple:
        """Categorize credit risk into zones."""
        if is_distressed == 1 or z_score < 1.1:
            return "DANGER (RED)", "Extreme corporate financial distress. Highly likely default / trading suspension."
        elif z_score <= 2.6:
            return "WARNING (GREY)", "Unstable financial position. Requires defensive investment strategy."
        else:
            return "SAFE (GREEN)", "Excellent corporate credit score. Stable financial standing."

    @staticmethod
    def _get_ai_commentary(ticker: str, latest: pd.Series, z_score: float) -> Optional[str]:
        """Generate AI commentary using the AI client."""
        try:
            ai_client = get_ai_client()
            return ai_client.generate_financial_commentary(
                ticker=ticker,
                current_ratio=float(latest.get("current_ratio", 1.0)),
                debt_ratio=float(latest.get("debt_ratio", 0.0)),
                altman_z_score=z_score,
                profit_after_tax=float(latest.get("profit_after_tax", 0.0)),
                operating_cash_flow=float(latest.get("operating_cash_flow", 0.0)),
                ebit_to_interest=float(latest.get("ebit_to_interest", 9999.0))
            )
        except Exception as e:
            print(f"⚠️ AI commentary generation failed: {e}")
            return None
