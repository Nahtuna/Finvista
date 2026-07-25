# -*- coding: utf-8 -*-
"""
🏆 FINVISTA QUANTITATIVE REST API GATEWAY
=========================================
SaaS-ready FastAPI microservice — app factory, CORS, startup hooks, and router wiring.

Author: samvo
Version: 1.1.7
"""

import hashlib
import json
import os
import sys

import pandas as pd
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi.errors import RateLimitExceeded

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.api import state
from src.api.dependencies import limiter
from src.api.routes import auth, chat, credit, market, news_impact, portfolio, regime, warrants, analyst, reports, admin, fireant, udf
from src.api.scheduler import start_periodic_scheduler
from src.api.websocket import websocket_endpoint
from src.core import config

# ── GZip Compression: giảm ~70% kích thước JSON payload ─────────────────────
# (phải add TRƯỚC CORSMiddleware để không bị conflict)

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

app.add_middleware(GZipMiddleware, minimum_size=512)

app.state.limiter = limiter
state.load_distress_models()



# CORS: allow_credentials=True is incompatible with wildcard origin.
# The frontend uses JWT in Authorization header (not cookies), so credentials=False is safe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ETag Cache Routes: các endpoint ít thay đổi sẽ trả 304 khi unchanged ────
_ETAG_ROUTES = {
    "/api/warrants/opportunities",
    "/api/credit",
    "/api/credit-health",
    "/api/regime/market",
    "/api/health",
}

@app.middleware("http")
async def smart_cache_and_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Remove deprecated headers
    for h in ["x-xss-protection", "X-XSS-Protection", "x-frame-options", "X-Frame-Options", "expires", "Expires"]:
        if h in response.headers:
            del response.headers[h]

    # Security headers
    response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Smart cache: ETag cho static-ish endpoints, no-store cho dynamic endpoints
    path = request.url.path
    is_etag_route = any(path.startswith(r) for r in _ETAG_ROUTES)

    if is_etag_route and response.status_code == 200:
        # Đọc body để tính ETag
        body = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body += chunk
        etag = '"' + hashlib.md5(body).hexdigest() + '"'
        client_etag = request.headers.get("if-none-match", "")
        if client_etag == etag:
            return Response(status_code=304, headers={
                "ETag": etag,
                "Cache-Control": "private, max-age=60",
            })
        # Trả về response với ETag
        c_type = response.headers.get("content-type", "application/json")
        if "charset" not in c_type and "application/json" in c_type:
            c_type = f"{c_type}; charset=utf-8"
        return Response(
            content=body,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                "ETag": etag,
                "Cache-Control": "private, max-age=60",
                "content-type": c_type,
            },
        )
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        c_type = response.headers.get("content-type", "")
        if "application/json" in c_type and "charset" not in c_type:
            response.headers["content-type"] = f"{c_type}; charset=utf-8"
        return response

app.include_router(auth.router)
app.include_router(warrants.router)
app.include_router(portfolio.router)
app.include_router(credit.router)
app.include_router(chat.router)
app.include_router(news_impact.router)
app.include_router(regime.router)
app.include_router(market.router)
app.include_router(analyst.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(fireant.router)
app.include_router(udf.router)


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
            "news_impact": "/api/news-impact/{ticker}",
            "news_ml_signal": "/api/news-impact/{ticker}/ml-signal",
            "market_regime": "/api/regime/market",
            "ticker_regime": "/api/regime/{ticker}",
        },
        "systems": {
            "credit_risk_model": "XGBoost Credit Classifier v1.0 (Sequential OOT Trained)",
            "pricing_engine": "Black-Scholes-Merton Options Solver",
        },
    }


@app.get("/api/health")
def health_check():
    """Retrieve runtime diagnostics, model registry integrity, and cached state."""
    model_exists = os.path.exists(config.BEST_DISTRESS_MODEL)
    scaler_exists = os.path.exists(config.SCALER_ARTIFACT)
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
