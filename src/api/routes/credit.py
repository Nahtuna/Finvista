# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: CORPORATE CREDIT HEALTH ROUTES
===========================================
FastAPI delivery layer for bankruptcy prediction and financial health assessment.
Delegates all ML inference and scoring logic to CreditRiskService.

Author: samvo
Version: 2.0 (Clean Architecture Refactored)
"""

from fastapi import APIRouter
from src.services.credit_risk_service import CreditRiskService

router = APIRouter(tags=["credit"])


@router.get("/api/credit-health/{ticker}")
def get_corporate_credit_health(ticker: str):
    """
    Retrieve deep fundamental credit indicators and XGBoost bankruptcy alert ratings.
    Delegates all heavy lifting to CreditRiskService.
    """
    return CreditRiskService.get_credit_health(ticker)
