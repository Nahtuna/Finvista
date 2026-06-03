# -*- coding: utf-8 -*-
"""Corporate credit health and distress scoring routes."""

import os

import pandas as pd
from fastapi import APIRouter, HTTPException, status

from src.api import state
from src.common import config

router = APIRouter(tags=["credit"])


@router.get("/api/credit-health/{ticker}")
def get_corporate_credit_health(ticker: str):
    """
    Retrieve deep fundamental credit indicators and XGBoost bankruptcy alert ratings
    for a given Vietnamese public underlying stock ticker.
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

        z_score = float(latest.get("altman_z_score", 0.0))
        is_distressed = int(latest.get("distress_label", 0))

        bankruptcy_prob: float
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
                latest_scaled = state.distress_scaler.transform(latest_feat)
                latest_scaled_df = pd.DataFrame(latest_scaled, columns=feature_cols)
                if hasattr(state.distress_model, "predict_proba"):
                    bankruptcy_prob = float(
                        state.distress_model.predict_proba(latest_scaled_df)[0, 1]
                    )
                else:
                    score = float(state.distress_model.decision_function(latest_scaled_df)[0])
                    bankruptcy_prob = float(1 / (1 + __import__("math").exp(-score)))
            except Exception:
                bankruptcy_prob = 0.85 if is_distressed == 1 else 0.10
        else:
            bankruptcy_prob = 0.85 if is_distressed == 1 else 0.10

        if is_distressed == 1 or z_score < 1.1:
            zone = "DANGER (RED)"
            risk_description = (
                "Extreme corporate financial distress. Highly likely default / trading suspension."
            )
        elif z_score <= 2.6:
            zone = "WARNING (GREY)"
            risk_description = "Unstable financial position. Requires defensive investment strategy."
        else:
            zone = "SAFE (GREEN)"
            risk_description = "Excellent corporate credit score. Stable financial standing."

        return {
            "ticker": ticker_clean,
            "reported_year": int(latest.get("year")),
            "credit_metrics": {
                "altman_z_score": round(z_score, 4),
                "risk_zone": zone,
                "is_ml_distressed": is_distressed == 1,
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query credit health indicators: {str(e)}",
        )
