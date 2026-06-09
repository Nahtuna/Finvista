# -*- coding: utf-8 -*-
"""
🏆 FINVISTA QUANTITATIVE REST API GATEWAY
=========================================
SaaS-ready FastAPI microservice — app factory, CORS, startup hooks, and router wiring.

Author: samvo
Version: 1.0.0
"""

import os
import sys

import pandas as pd
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.api import state
from src.api.dependencies import limiter
from src.api.routes import auth, chat, credit, portfolio, warrants
from src.api.scheduler import start_periodic_scheduler
from src.api.websocket import websocket_endpoint
from src.common import config

app = FastAPI(
    title="Finvista Quantitative REST API Gateway",
    description=(
        "⚡ <b>SaaS Quantitative Core Engine</b> for real-time Covered Warrants (CW) "
        "pricing, Greeks analysis (Delta, Gamma, Vega, Theta, Rho), and XGBoost-powered "
        "corporate credit health warning system."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
state.load_distress_models()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(warrants.router)
app.include_router(portfolio.router)
app.include_router(credit.router)
app.include_router(chat.router)


@app.exception_handler(RateLimitExceeded)
def custom_rate_limit_exceeded_handler(request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "status": "error",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": f"Too many requests. Limit is {exc.detail}.",
            "retry_after_seconds": 60,
        },
    )


@app.websocket("/api/ws")
async def ws_route(websocket):
    await websocket_endpoint(websocket)


@app.on_event("startup")
def on_startup():
    start_periodic_scheduler()


@app.get("/", status_code=status.HTTP_200_OK)
def read_root():
    """Welcome page with overview and swagger links."""
    return {
        "gateway": "Finvista Quantitative Core REST API",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "interactive_docs": "/docs",
            "health_status": "/api/health",
            "corporate_credit_health": "/api/credit-health/{ticker}",
            "cw_opportunities": "/api/warrants/opportunities",
            "dynamic_greeks_calculator": "/api/warrants/greeks",
        },
        "systems": {
            "credit_risk_model": "XGBoost Credit Classifier v1.0 (Sequential OOT Trained)",
            "pricing_engine": "Black-Scholes-Merton Options Solver",
        },
    }


@app.get("/api/health")
def health_check():
    """Retrieve runtime diagnostics, model registry integrity, and cached state."""
    model_dir = os.path.join(config.DATA_DIR, "models")
    model_exists = os.path.exists(os.path.join(model_dir, "best_distress_model.pkl"))
    scaler_exists = os.path.exists(os.path.join(model_dir, "scaler.pkl"))
    dataset_exists = os.path.exists(config.FINAL_DATASET_FILE)

    dataset_rows = 0
    if dataset_exists:
        try:
            dataset_rows = len(pd.read_csv(config.FINAL_DATASET_FILE))
        except Exception:
            pass

    return {
        "status": "healthy" if (model_exists and dataset_exists) else "warning",
        "model_registry": {
            "xgboost_model_loaded": model_exists,
            "scaler_loaded": scaler_exists,
        },
        "database_layer": {
            "distress_dataset_found": dataset_exists,
            "total_corporate_records": dataset_rows,
        },
        "live_market_cache": {
            "cached_warrants_present": state.pipeline_cache["data"] is not None,
            "last_scan_timestamp": state.pipeline_cache["last_scanned"],
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8008, reload=True)
