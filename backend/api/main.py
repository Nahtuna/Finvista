# -*- coding: utf-8 -*-
# Force reload: 2026-08-10T14:51:00
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

# Apply vnstock rate limit protection immediately
_original_exit = sys.exit
def _safe_exit(code=0):
    import multiprocessing, logging
    # Allow clean exits (code=0) and child process shutdowns to proceed normally
    if code == 0 or multiprocessing.current_process().name != 'MainProcess':
        _original_exit(code)
    try:
        logging.warning(f"Prevented sys.exit({code}) crash from vnstock")
    except (ValueError, IOError):
        pass
    raise RuntimeError(f"Rate limit exceeded: {code}")
sys.exit = _safe_exit

# Prevent vnstock update check from hanging by mocking the upgrade module
from unittest.mock import MagicMock
mock_upgrade = MagicMock()
mock_upgrade.update_notice = lambda *args, **kwargs: None
sys.modules['vnstock.core.utils.upgrade'] = mock_upgrade

import pandas as pd
from fastapi import FastAPI, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.api import state
from backend.api.dependencies import limiter, validate_environment_variables
from backend.api.routes import auth, chat, credit, market, news_impact, portfolio, regime, warrants, analyst, reports, admin, fireant, udf, atc, smc, flow
from backend.api.scheduler import start_periodic_scheduler, get_scheduler_status
from backend.api.websocket import websocket_endpoint
from backend.core import config

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
# We specify the exact frontend origins and allow credentials (cookies, auth headers, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8008",
        "http://localhost:8008"
    ],
    allow_credentials=True,
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

    # CORS origin resolving helper for middleware generated responses
    allowed_origins = {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8008",
        "http://localhost:8008"
    }
    origin = request.headers.get("origin", "")
    cors_origin = origin if origin in allowed_origins else "http://127.0.0.1:5173"

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
            headers = {
                "ETag": etag,
                "Cache-Control": "private, max-age=60",
            }
            if "Access-Control-Allow-Origin" not in response.headers:
                headers["Access-Control-Allow-Origin"] = cors_origin
                headers["Access-Control-Allow-Methods"] = "*"
                headers["Access-Control-Allow-Headers"] = "*"
                headers["Access-Control-Allow-Credentials"] = "true"
            return Response(status_code=304, headers=headers)
        # Trả về response với ETag
        c_type = response.headers.get("content-type", "application/json")
        if "charset" not in c_type and "application/json" in c_type:
            c_type = f"{c_type}; charset=utf-8"
        headers = {
            **dict(response.headers),
            "ETag": etag,
            "Cache-Control": "private, max-age=60",
            "content-type": c_type,
        }
        if "Access-Control-Allow-Origin" not in response.headers:
            headers["Access-Control-Allow-Origin"] = cors_origin
            headers["Access-Control-Allow-Methods"] = "*"
            headers["Access-Control-Allow-Headers"] = "*"
            headers["Access-Control-Allow-Credentials"] = "true"
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
        )
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        c_type = response.headers.get("content-type", "")
        if "application/json" in c_type and "charset" not in c_type:
            response.headers["content-type"] = f"{c_type}; charset=utf-8"
        # Ensure CORS headers are present only if not already set
        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
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
app.include_router(atc.router)
app.include_router(smc.router)
app.include_router(flow.router)


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


def run_background_startup_tasks():
    # 1. Run ATC check and sync (blocking=True inside the thread to run it sequentially)
    try:
        from backend.modules.atc_manager.service import run_startup_atc_check_and_sync
        run_startup_atc_check_and_sync(blocking=True)
    except Exception as e:
        print(f"⚠️ [Startup Sync] ATC sync failed in background: {e}")
        
    # 2. Run Indices and Regime check and sync
    try:
        from backend.api.scheduler import run_startup_indices_and_regime_check_and_sync
        run_startup_indices_and_regime_check_and_sync()
    except Exception as e:
        print(f"⚠️ [Startup Sync] Indices/Regime sync failed in background: {e}")


@app.on_event("startup")
async def on_startup():
    import asyncio as _asyncio
    import os as _os
    
    # === 0. Validate required environment variables ===
    try:
        validate_environment_variables()
    except ValueError as e:
        print(f"❌ [Startup] Environment validation failed: {e}")
        raise

    # === 0.5. Ensure FireAnt table exists ===
    try:
        from backend.infra.fireant_scraper import _ensure_table
        _ensure_table()
    except Exception as e:
        print(f"⚠️ [Startup] Failed to ensure FireAnt table: {e}")
    
    # === 1. Register the running event loop so scheduler threads can broadcast via WebSocket ===
    from backend.api.scheduler import set_event_loop as _set_loop
    _set_loop(_asyncio.get_event_loop())

    # === 2. Run Startup Freshness Checks Sequentially ===
    _skip_sync = _os.environ.get("FINVISTA_SKIP_STARTUP_SYNC", "false").lower() == "true"
    
    if _skip_sync:
        print("🔍 [Startup] Skipping startup data sync checks (FINVISTA_SKIP_STARTUP_SYNC=true)...")
        startup_check_result = {"status": "skipped", "reason": "Bypassed via environment variable"}
    else:
        _blocking = _os.environ.get("FINVISTA_ATC_STARTUP_BLOCKING", "false").lower() == "true"
        if _blocking:
            print("🔍 [Startup] Running startup data checks sequentially (blocking=True)...")
            from backend.modules.atc_manager.service import run_startup_atc_check_and_sync
            startup_check_result = run_startup_atc_check_and_sync(blocking=True)
            try:
                from backend.api.scheduler import run_startup_indices_and_regime_check_and_sync
                run_startup_indices_and_regime_check_and_sync()
            except Exception as startup_sync_err:
                print(f"⚠️ [Startup Sync] Indices/Regime sync failed on startup: {startup_sync_err}")
        else:
            print("🔍 [Startup] Running startup data checks sequentially in background (blocking=False)...")
            import threading
            t = threading.Thread(
                target=run_background_startup_tasks,
                daemon=True,
                name="FinvistaBackgroundStartup"
            )
            t.start()
            startup_check_result = {"status": "background_sync_started", "reason": "Startup check running sequentially in background"}

    # === 3. Bắt đầu Background Scheduler (sau khi đảm bảo data tươi) ===
    start_periodic_scheduler()

    # === 4. Optional: Lưu kết quả startup check vào app.state để API truy cập nhanh ===
    try:
        app.state.atc_startup_result = startup_check_result
    except NameError:
        app.state.atc_startup_result = {"status": "skipped", "reason": "Startup check was non-blocking"}


@app.get("/api/info", status_code=status.HTTP_200_OK)
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
def health_check(response: Response):
    """Retrieve runtime diagnostics, model registry integrity, and cached state."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    model_exists = os.path.exists(config.BEST_DISTRESS_MODEL)
    scaler_exists = os.path.exists(config.SCALER_ARTIFACT)
    # Check database for distress data instead of CSV file
    dataset_rows = 0
    dataset_exists = False
    try:
        from backend.core.database import SessionLocal, CompanyFinancial
        db = SessionLocal()
        try:
            dataset_rows = db.query(CompanyFinancial).count()
            dataset_exists = dataset_rows > 0
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"Health check database query failed: {e}")

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


@app.get("/api/scheduler/health")
def scheduler_health_check():
    """Retrieve scheduler status, job information, and next run times."""
    from backend.infra.redis_cache import cache
    
    scheduler_status = get_scheduler_status()
    cache_stats = cache.get_stats()
    
    return {
        "status": "healthy" if scheduler_status["engine"]["apscheduler"]["running"] or scheduler_status["engine"]["fallback_thread_loop"]["running"] else "warning",
        "scheduler": scheduler_status,
        "cache": cache_stats,
    }




# ── Reports & Frontend Static Asset Mounting ────────────────────────────────
reports_dir = os.path.join(BASE_DIR, "data", "reports")
os.makedirs(reports_dir, exist_ok=True)
app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")

frontend_dist = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path == "api" or full_path.startswith("docs") or full_path.startswith("redoc") or full_path == "openapi.json":
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target_file = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8008, reload=True)
# Forced reload comment to trigger uvicorn to pick up service.py changes.

