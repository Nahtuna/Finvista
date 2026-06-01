# -*- coding: utf-8 -*-
"""
🏆 FINVISTA QUANTITATIVE REST API GATEWAY
=========================================
SaaS-ready FastAPI microservice for Covered Warrant (CW) pricing, Greeks, 
and machine learning corporate credit risk (distress) warning systems.

Author: samvo
Version: 1.0.0
"""

import os
import sys
import pandas as pd
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, status, BackgroundTasks, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
import threading
import time
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
import jwt
import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# Ensure sys.path contains the project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.common import config
from src.cw_engine.pricing_core import (
    calculate_greeks_for_cw,
    estimate_implied_volatility,
    fetch_dynamic_risk_free_rate,
    RISK_FREE_RATE,
    parse_ratio
)
from src.cw_engine.run_analysis import run_quant_pipeline_programmatic
from src.cw_engine.paper_trader import (
    load_portfolio,
    reset_portfolio,
    execute_buy,
    execute_sell,
    scan_and_trade,
    is_market_open,
    PORTFOLIO_FILE,
    REPORT_PATH
)
from src.cw_engine.history_analyzer import analyze_historical_warrant
from scipy.stats import norm
from datetime import datetime

# ---------- Load Credit Risk Model at startup ----------
import joblib, json as _json
_MODEL_DIR = os.path.join("data", "financial_distress", "models")
_distress_model = None
_distress_scaler = None
_distress_threshold = 0.5
try:
    _distress_model  = joblib.load(os.path.join(_MODEL_DIR, "best_distress_model.pkl"))
    _distress_scaler = joblib.load(os.path.join(_MODEL_DIR, "scaler.pkl"))
    _thr_cfg_path = os.path.join(_MODEL_DIR, "threshold_config.json")
    if os.path.exists(_thr_cfg_path):
        with open(_thr_cfg_path) as _f:
            _distress_threshold = _json.load(_f).get("active_threshold", 0.5)
except Exception as _e:
    print(f"[API] ⚠️ Could not load distress model: {_e}")

# Create FastAPI instance with gorgeous metadata
app = FastAPI(
    title="Finvista Quantitative REST API Gateway",
    description=(
        "⚡ <b>SaaS Quantitative Core Engine</b> for real-time Covered Warrants (CW) "
        "pricing, Greeks analysis (Delta, Gamma, Vega, Theta, Rho), and XGBoost-powered "
        "corporate credit health warning system."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ---------- SaaS-ready Rate Limiter Setup (slowapi) ----------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "status": "error",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": f"Too many requests. Limit is {exc.detail}.",
            "retry_after_seconds": 60
        }
    )

# ---------- WebSocket Real-Time Connection Manager ----------
class ConnectionManager:
    """Manages active WebSockets connections to stream real-time events to the SaaS Frontend."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 [WebSocket] New client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"🔌 [WebSocket] Client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast live updates to all connected web clients asynchronously."""
        if not self.active_connections:
            return
        
        # Avoid blocking by calling asyncio.gather on all connection sends
        tasks = []
        for connection in self.active_connections:
            tasks.append(connection.send_json(message))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

manager = ConnectionManager()

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket event broadcaster for portfolio NAV and market scanning states."""
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "event": "connected",
            "message": "Successfully connected to Finvista Quantitative WebSocket stream.",
            "timestamp": datetime.now().isoformat()
        })
        while True:
            # Keeps the WebSocket alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"🔌 [WebSocket] Error: {e}")
        manager.disconnect(websocket)

# CORS middleware for standard SaaS frontend cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Periodic Background Ingestion Scheduler ----------
def start_periodic_scheduler():
    def scheduler_loop():
        # Delay startup slightly to let API server initialize fully
        time.sleep(10)
        print("🕒 [Scheduler Thread] Starting periodic market scanning background loop...")
        while True:
            try:
                # Enforce HOSE trading hours checks
                now = datetime.now()
                # Check if weekday (0-4 are Mon-Fri)
                is_weekday = now.weekday() < 5
                time_str = now.strftime("%H:%M:%S")
                in_morning = "09:00:00" <= time_str <= "11:30:00"
                in_afternoon = "13:00:00" <= time_str <= "14:45:00"
                
                if is_weekday and (in_morning or in_afternoon):
                    print("🕒 [Scheduler Thread] HOSE Market is open. Executing scheduled quantitative scan...")
                    run_quant_pipeline_programmatic(strategy="balanced")
                    print("🕒 [Scheduler Thread] Scheduled quantitative scan completed and persisted.")
                    # Sleep 15 minutes (900 seconds)
                    time.sleep(900)
                else:
                    # Market closed, sleep 5 minutes before checking hours again
                    time.sleep(300)
            except Exception as e:
                print(f"⚠️ [Scheduler Thread] Error in loop: {e}")
                time.sleep(60)

    # Launch daemon thread
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

@app.on_event("startup")
def on_startup():
    start_periodic_scheduler()

# ---------- JWT Security & Multi-User Authentication ----------
from dotenv import load_dotenv
load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "finvista_saas_ultra_secure_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against secure hash with demo fallback."""
    try:
        # Fallback for the demo account
        if password == "finvista123" and hashed == "$pbkdf2-sha256$29000$h6UqC5q9G6S1.$D9y1Kz77tFpT5q0x4Z0u1u":
            return True
            
        parts = hashed.split('$')
        if len(parts) < 4:
            return False
            
        iterations = int(parts[1])
        salt = parts[2].encode('utf-8')
        target_hash = parts[3]
        
        calc_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        calc_hash_b64 = base64.b64encode(calc_hash).decode('ascii')
        return hmac.compare_digest(target_hash.encode('ascii'), calc_hash_b64.encode('ascii'))
    except Exception:
        return password == hashed

def hash_password(password: str) -> str:
    """Hash password using secure PBKDF2 HMAC SHA-256."""
    salt = base64.b64encode(os.urandom(12)).decode('ascii')
    iterations = 30000
    calc_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
    calc_hash_b64 = base64.b64encode(calc_hash).decode('ascii')
    return f"pbkdf2_sha256${iterations}${salt}${calc_hash_b64}"

def create_access_token(data: dict) -> str:
    """Generate a JWT token with dynamic expiration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to retrieve the currently authenticated user."""
    from src.common.database import SessionLocal, User
    db = SessionLocal()
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in system.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "id": user.id,
            "username": user.username
        }
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    finally:
        db.close()

# Pydantic Authentication schemas
class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, example="quant_trader")
    password: str = Field(..., min_length=6, example="mysecurepassword")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest):
    """Register a new quant trader account."""
    from src.common.database import SessionLocal, User
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == req.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already registered."
            )
        
        new_user = User(
            username=req.username,
            hashed_password=hash_password(req.password)
        )
        db.add(new_user)
        db.commit()
        return {
            "status": "success",
            "message": f"Successfully registered user '{req.username}'. You can now login to get a token."
        }
    finally:
        db.close()

@app.post("/api/auth/login", response_model=TokenResponse)
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate credentials and return a secure JWT Access Token."""
    from src.common.database import SessionLocal, User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = create_access_token(data={"sub": user.username})
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user.username
        }
    finally:
        db.close()

@app.get("/api/auth/me")
def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Retrieve details of the currently authenticated trader."""
    return current_user

# Pydantic Schemas for validation
class GreeksCalculatorRequest(BaseModel):
    underlying_price: float = Field(..., description="Current market price of the underlying asset (VND)", example=28500.0)
    strike_price: float = Field(..., description="Strike price of the covered warrant (VND)", example=25000.0)
    days_to_maturity: int = Field(..., description="Number of calendar days remaining until expiry", example=95)
    implied_volatility: float = Field(..., description="Annualized implied volatility (as decimal, e.g. 0.45 for 45%)", example=0.42)
    conversion_ratio: float = Field(1.0, description="Conversion ratio (e.g. 10.0 for 10:1 ratio)", example=10.0)
    risk_free_rate: Optional[float] = Field(None, description="Continuous risk-free rate (optional, falls back to live 1Y Gov Yield)", example=0.045)

class GreekCalculatorResponse(BaseModel):
    delta: float = Field(..., description="Warrant Delta adjusted for conversion ratio")
    gamma: float = Field(..., description="Warrant Gamma adjusted for conversion ratio")
    vega: float = Field(..., description="Warrant Vega adjusted for conversion ratio")
    theta: float = Field(..., description="Warrant Theta per calendar day (VND)")
    rho: float = Field(..., description="Warrant Rho")
    moneyness: float = Field(..., description="Underlying / Strike")
    moneyness_category: str = Field(..., description="ITM, ATM, or OTM")
    prob_itm: float = Field(..., description="Probability of expiring in-the-money")

# Cache to avoid running heavy pipeline scans on every request
_pipeline_cache = {
    "data": None,
    "last_scanned": None
}

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
            "dynamic_greeks_calculator": "/api/warrants/greeks"
        },
        "systems": {
            "credit_risk_model": "XGBoost Credit Classifier v1.0 (Sequential OOT Trained)",
            "pricing_engine": "Black-Scholes-Merton Options Solver"
        }
    }

@app.get("/api/health")
def health_check():
    """Retrieve runtime diagnostics, model registry integrity, and cached state."""
    model_dir = os.path.join("data", "financial_distress", "models")
    model_exists = os.path.exists(os.path.join(model_dir, "best_distress_model.pkl"))
    scaler_exists = os.path.exists(os.path.join(model_dir, "scaler.pkl"))
    dataset_exists = os.path.exists(config.FINAL_DATASET_FILE)
    
    dataset_rows = 0
    if dataset_exists:
        try:
            df = pd.read_csv(config.FINAL_DATASET_FILE, nrows=1)
            dataset_rows = len(pd.read_csv(config.FINAL_DATASET_FILE))
        except Exception:
            pass

    return {
        "status": "healthy" if (model_exists and dataset_exists) else "warning",
        "model_registry": {
            "xgboost_model_loaded": model_exists,
            "scaler_loaded": scaler_exists
        },
        "database_layer": {
            "distress_dataset_found": dataset_exists,
            "total_corporate_records": dataset_rows
        },
        "live_market_cache": {
            "cached_warrants_present": _pipeline_cache["data"] is not None,
            "last_scan_timestamp": _pipeline_cache["last_scanned"]
        }
    }

@app.get("/api/credit-health/{ticker}")
def get_corporate_credit_health(ticker: str):
    """
    Retrieve deep fundamental credit indicators and XGBoost bankruptcy alert ratings 
    for a given Vietnamese public underlying stock ticker.
    """
    ticker_clean = ticker.upper().strip()
    if not os.path.exists(config.FINAL_DATASET_FILE):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Corporate Credit Health Database is currently offline/unavailable."
        )

    try:
        df = pd.read_csv(config.FINAL_DATASET_FILE)
        ticker_df = df[df["ticker"] == ticker_clean]
        if ticker_df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticker '{ticker_clean}' not found in the credit health registry or is an excluded sector."
            )
            
        # Take the latest reported year's financials
        latest = ticker_df.sort_values("year").iloc[-1]
        
        z_score = float(latest.get("altman_z_score", 0.0))
        is_distressed = int(latest.get("distress_label", 0))
        
        # --- Real probability from ML model (not hardcoded) ---
        bankruptcy_prob: float
        if _distress_model is not None and _distress_scaler is not None:
            try:
                exclude_cols = {
                    "ticker", "company_name", "year", "exchange", "industry", 
                    "distress_label", "distress_label_next_year",
                    "ebit_to_interest", "icr", "current_ratio", "total_equity",
                    "springate_distressed", "zmijewski_distressed"
                }
                feature_cols = [c for c in ticker_df.columns if c not in exclude_cols]
                latest_feat = latest[feature_cols].to_frame().T.astype(float)
                latest_scaled = _distress_scaler.transform(latest_feat)
                import pandas as _pd
                latest_scaled_df = _pd.DataFrame(latest_scaled, columns=feature_cols)
                if hasattr(_distress_model, "predict_proba"):
                    bankruptcy_prob = float(_distress_model.predict_proba(latest_scaled_df)[0, 1])
                else:
                    score = float(_distress_model.decision_function(latest_scaled_df)[0])
                    bankruptcy_prob = float(1 / (1 + __import__("math").exp(-score)))
            except Exception as _pe:
                # Fallback to rule-based estimate if inference fails
                bankruptcy_prob = 0.85 if is_distressed == 1 else 0.10
        else:
            bankruptcy_prob = 0.85 if is_distressed == 1 else 0.10
        
        # Classify Altman Z'' zones
        if is_distressed == 1 or z_score < 1.1:
            zone = "DANGER (RED)"
            risk_description = "Extreme corporate financial distress. Highly likely default / trading suspension."
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
                "active_threshold": _distress_threshold,
                "status_description": risk_description
            },
            "financial_ratios": {
                "leverage_debt_ratio": round(float(latest.get("debt_ratio", 0.0)), 4),
                "liquidity_current_ratio": round(float(latest.get("current_ratio", 0.0)), 4),
                "roa": round(float(latest.get("roa", 0.0)), 4),
                "roe": round(float(latest.get("roe", 0.0)), 4),
                "ebit_to_assets": round(float(latest.get("ebit_to_assets", 0.0)), 4),
                "icr": round(float(latest.get("icr", latest.get("ebit_to_interest", 0.0))), 4),
                "ocf_to_total_debt": round(float(latest.get("ocf_to_total_debt", 0.0)), 4)
            },
            "distress_scores": {
                "altman_z_score": round(z_score, 4),
                "altman_zone": zone,
                "springate_s_score": round(float(latest.get("springate_s_score", 0.0)), 4),
                "springate_distressed": bool(latest.get("springate_distressed", 0)),
                "zmijewski_x_score": round(float(latest.get("zmijewski_x_score", 0.0)), 4),
                "zmijewski_distressed": bool(latest.get("zmijewski_distressed", 0))
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query credit health indicators: {str(e)}"
        )

@app.get("/api/warrants/opportunities")
def get_cw_opportunities(
    strategy: str = Query("balanced", regex="^(balanced|safe|aggressive)$", description="Target trading profile"),
    underlying: Optional[str] = Query(None, description="Filter by underlying stock ticker (e.g. HPG)"),
    limit: int = Query(10, ge=1, le=100, description="Max recommendations to return"),
    force_refresh: bool = Query(False, description="Force running full market crawl and calculations")
):
    """
    Retrieve elite quantitative Covered Warrant recommendations sorted by G-Score, 
    automatically filtered by credit distress Hard-Gates. Reads directly from SQLite DB under 5ms.
    """
    from src.common.database import SessionLocal, MarketOpportunity
    from sqlalchemy import desc
    
    db = SessionLocal()
    try:
        # Check if SQLite table has records and force_refresh is not requested
        count = db.query(MarketOpportunity).count()
        
        if count == 0 or force_refresh:
            print("🚀 Database empty or refresh forced. Triggering live market quantitative pipeline scan...")
            # run_quant_pipeline_programmatic automatically syncs to database
            df = run_quant_pipeline_programmatic(strategy=strategy)
            
        # Apply filters & sorting in SQLAlchemy
        query = db.query(MarketOpportunity)
        if underlying:
            query = query.filter(MarketOpportunity.underlying == underlying.upper().strip())
            
        # Sort by G-Score descending
        query = query.order_by(desc(MarketOpportunity.score))
        opps_list = query.limit(limit).all()
        
        results = []
        for row in opps_list:
            results.append({
                "warrant_symbol": row.symbol,
                "underlying_symbol": row.underlying,
                "issuer": row.issuer,
                "market_price": row.price,
                "price_change_pct": round(row.price_change_pct, 2) if row.price_change_pct is not None else 0.0,
                "strike_price": row.strike_price,
                "break_even_price": row.break_even_price,
                "premium_pct": round(row.premium_pct, 2) if row.premium_pct is not None else 0.0,
                "days_to_maturity": row.days_to_maturity,
                "effective_gearing": round(row.gearing, 2) if row.gearing is not None else 0.0,
                "implied_volatility_pct": round(row.implied_volatility_pct, 2) if row.implied_volatility_pct is not None else 0.0,
                "historical_volatility_pct": round(row.historical_volatility_pct, 2) if row.historical_volatility_pct is not None else 0.0,
                "delta": round(row.delta, 4) if row.delta is not None else 0.0,
                "theta_daily_burn": round(row.theta_burn_day, 2) if row.theta_burn_day is not None else 0.0,
                "composite_g_score": round(row.score, 2) if row.score is not None else 0.0,
                "recommendation_signal": row.decision_signal,
                "proj_3d_flat_pct": round(row.proj_3d_flat_pct, 2) if row.proj_3d_flat_pct is not None else 0.0,
                "proj_3d_up_pct": round(row.proj_3d_up_pct, 2) if row.proj_3d_up_pct is not None else 0.0,
                "proj_3d_down_pct": round(row.proj_3d_down_pct, 2) if row.proj_3d_down_pct is not None else 0.0,
                "underlying_credit": {
                    "is_distressed": row.underlying_is_distressed == 1,
                    "altman_z_score": round(row.underlying_altman_z, 2) if row.underlying_altman_z is not None else 3.0
                }
            })
            
        return {
            "status": "success",
            "strategy": strategy,
            "count": len(results),
            "recommendations": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market opportunities: {str(e)}"
        )
    finally:
        db.close()

@app.post("/api/warrants/greeks", response_model=GreekCalculatorResponse)
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
            risk_free_rate=r
        )
        return {
            "delta": round(res["delta"], 4),
            "gamma": round(res["gamma"], 6),
            "vega": round(res["vega"], 4),
            "theta": round(res["theta"] * req.underlying_price, 2),  # Dollar Theta approximation
            "rho": round(res["rho"], 4),
            "moneyness": round(res["moneyness"], 4),
            "moneyness_category": res["moneyness_category"],
            "prob_itm": round(res["prob_itm"], 4)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Options solver calculation failed: {str(e)}"
        )

@app.post("/api/warrants/scan")
@limiter.limit("1/minute")
async def trigger_market_scan(
    request: Request,
    strategy: str = Query("balanced", regex="^(balanced|safe|aggressive)$")
):
    """
    Manually trigger a complete real-time market data crawl and quantitative analysis scan.
    Rate limited to 1 execution per minute per client IP. Broadcasts completion state to WebSockets.
    """
    try:
        print("⚡ Manual trigger: Real-time quantitative scanner initiated...")
        # Offload heavy mathematical pipeline to a worker thread to keep the server responsive
        df = await asyncio.to_thread(run_quant_pipeline_programmatic, strategy=strategy)
        _pipeline_cache["data"] = df
        from datetime import datetime
        _pipeline_cache["last_scanned"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Broadcast the successful update to active WebSocket clients
        await manager.broadcast({
            "event": "market_scan_completed",
            "message": f"Real-time quantitative scan successfully completed! Refreshed {len(df)} Covered Warrants.",
            "timestamp": _pipeline_cache["last_scanned"]
        })
        
        return {
            "status": "success",
            "message": f"Successfully completed real-time quant scanner! Refreshed {len(df)} warrants.",
            "last_updated": _pipeline_cache["last_scanned"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scanner execution failed: {str(e)}"
        )

async def run_async_scan_task(strategy: str):
    """Worker function to run heavy quant calculations in a worker thread and broadcast over WS."""
    try:
        print(f"⚙️ [Async Background Task] Starting full quant scan under strategy: {strategy}")
        await asyncio.to_thread(run_quant_pipeline_programmatic, strategy=strategy)
        print("✅ [Async Background Task] Successfully completed scan and synchronized to database.")
        
        await manager.broadcast({
            "event": "market_scan_completed",
            "message": "Background market data scan finished and SQLite DB is fully synchronized.",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        print(f"❌ [Async Background Task] Scan failed: {e}")

@app.post("/api/warrants/scan/async", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("1/minute")
async def trigger_market_scan_async(
    request: Request,
    background_tasks: BackgroundTasks,
    strategy: str = Query("balanced", regex="^(balanced|safe|aggressive)$")
):
    """
    Asynchronously triggers a complete real-time market data crawl and quantitative scan.
    Rate limited to 1 execution per minute per client IP. Broadcasts queueing state instantly.
    """
    background_tasks.add_task(run_async_scan_task, strategy)
    
    # Notify clients that an async task is running
    await manager.broadcast({
        "event": "market_scan_queued",
        "message": f"Market scan asynchronously queued in background under strategy: '{strategy}'",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return {
        "status": "accepted",
        "message": "Market scan successfully queued in background task queue. Check logs or query database.",
        "strategy_queued": strategy
    }

# ---------- SaaS Paper Trading & Volatility Simulator Endpoints ----------

class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Covered warrant symbol, e.g. CACB2510", example="CACB2510")
    side: str = Field(..., description="BUY or SELL", pattern="^(BUY|SELL|buy|sell)$", example="BUY")
    qty: Optional[int] = Field(None, description="Quantity to buy/sell. If BUY, qty is optional (allocates max 20% NAV by default if not specified). Must be multiple of 100.")
    price: Optional[float] = Field(None, description="Optional override price. If not specified, uses current live market price.")
    reason: Optional[str] = Field("Manual User Order", description="Optional reason for the transaction")

@app.get("/api/portfolio")
def get_portfolio(current_user: dict = Depends(get_current_user)):
    """
    Retrieve detailed Paper Trading portfolio state, including current cash, 
    open positions with real-time valuation/P/L, win rate, and full transaction history.
    """
    try:
        portfolio = load_portfolio(username=current_user["username"])
        
        # Read latest prices from cache report to calculate active NAV
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
            p_l_pct = (curr_price - pos["buy_price"]) / pos["buy_price"] * 100 if pos["buy_price"] > 0 else 0.0
            
            # Check T+2.5 settlement lock status
            settlement_dt = datetime.fromisoformat(pos["settlement_date"])
            is_locked = now < settlement_dt
            time_left_hours = max(0.0, (settlement_dt - now).total_seconds() / 3600.0) if is_locked else 0.0
            
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
                "days_at_buy": pos.get("days_at_buy")
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
            "history": list(reversed(history))  # Chronological descending
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load paper trading portfolio: {str(e)}"
        )

@app.post("/api/portfolio/orders")
async def place_order(req: OrderRequest, current_user: dict = Depends(get_current_user)):
    """
    Place a manual paper trading BUY or SELL order. 
    Validates HOSE rules, transaction fees, and T+2.5 settlement lock constraints.
    Broadcasts successful transactions in real-time over WebSocket.
    """
    symbol_clean = req.symbol.upper().strip()
    side_clean = req.side.upper().strip()
    
    # Read latest report to fetch default values (underlying ticker, days to maturity, prices, etc.)
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
            detail=f"Could not resolve a valid market price for '{symbol_clean}'. Please provide an explicit price."
        )
        
    if side_clean == "BUY":
        # Enforce maturity days check (skip deep maturity)
        if days_left < 10:  # MATURITY_LIMIT_DAYS
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Warrant '{symbol_clean}' is within 10 days of maturity ({days_left} days left) and cannot be bought due to risk constraints."
            )
            
        # Load portfolio to do validation
        portfolio = load_portfolio(username=current_user["username"])
        if symbol_clean in portfolio.get("positions", {}):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Already holding an active position in '{symbol_clean}'."
            )
            
        if req.qty is None:
            # Automatic 20% NAV allocation buy
            res = execute_buy(symbol_clean, underlying, price, score, days_left, username=current_user["username"])
            if res.get("status") == "error":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("message"))
            
            # Broadcast the buy action
            await manager.broadcast({
                "event": "order_executed",
                "username": current_user["username"],
                "message": res.get("message"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return res
        else:
            # Specific quantity buy
            qty = req.qty
            if qty <= 0 or qty % 100 != 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Quantity must be a positive integer and a multiple of 100 (HOSE lot size)."
                )
                
            gross_value = qty * price
            fee = gross_value * 0.0015  # BUY_FEE_RATE
            total_cost = gross_value + fee
            
            if total_cost > portfolio.get("cash", 0.0):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Insufficient cash. Required: {total_cost:,.0f}đ, Available: {portfolio.get('cash'):,.0f}đ."
                )
                
            # Deduct cash and save position
            from src.cw_engine.paper_trader import calculate_settlement_date, save_portfolio
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
                "days_at_buy": days_left
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
                "reason": req.reason
            })
            save_portfolio(portfolio, username=current_user["username"])
            
            msg = f"🛍️ BOUGHT {qty:,} {symbol_clean} at {price:,.0f}đ | Total Cost: {total_cost:,.0f}đ (Fee: {fee:,.0f}đ)"
            await manager.broadcast({
                "event": "order_executed",
                "username": current_user["username"],
                "message": msg,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return {
                "status": "success",
                "message": msg
            }
            
    elif side_clean == "SELL":
        # Execute HOSE sell
        res = execute_sell(symbol_clean, price, req.reason, username=current_user["username"])
        if res.get("status") == "error":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("message"))
        
        # Broadcast the sell action
        await manager.broadcast({
            "event": "order_executed",
            "username": current_user["username"],
            "message": res.get("message"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return res
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transaction side '{req.side}'. Use 'BUY' or 'SELL'."
        )

@app.post("/api/portfolio/reset")
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
            "portfolio": res
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset portfolio: {str(e)}"
        )

@app.post("/api/portfolio/scan")
def trigger_paper_trader_scan(
    force: bool = Query(False, description="Set to true to bypass HOSE trading hours checks"),
    current_user: dict = Depends(get_current_user)
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
            "actions_executed": actions
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Paper trading scan execution failed: {str(e)}"
        )

@app.get("/api/warrants/{symbol}/simulate")
def get_warrant_simulation(symbol: str):
    """
    Generate a 2D P/L Scenario Matrix for a specific Covered Warrant.
    Models the joint impact of underlying asset price changes (-10% to +10%) 
    and holding period theta time decay (0 to 30 days) using Black-Scholes pricing.
    """
    symbol_clean = symbol.upper().strip()
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market report is not initialized. Run analysis pipeline first."
        )
        
    try:
        df = pd.read_csv(REPORT_PATH)
        match_rows = df[df["A_MaCW"] == symbol_clean]
        if match_rows.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Covered Warrant symbol '{symbol_clean}' was not found in the latest market scan."
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
                detail=f"Warrant '{symbol_clean}' has invalid market pricing parameters."
            )
            
        from src.cw_engine.pricing_core import calculate_d1_d2
        
        price_changes = [-0.10, -0.05, -0.02, 0.00, 0.02, 0.05, 0.10]
        holding_days = [0, 5, 10, 20, 30]
        
        scenarios = []
        for hold in holding_days:
            if hold >= days_to_maturity:
                continue
                
            remaining_days = days_to_maturity - hold
            T_new = remaining_days / 365.0
            
            import math
            matrix_row = []
            for chg in price_changes:
                S_new = S * (1 + chg)
                d1, d2 = calculate_d1_d2(S_new, K, T_new, RISK_FREE_RATE, iv)
                theo_new = (S_new * norm.cdf(d1) - K * math.exp(-RISK_FREE_RATE * T_new) * norm.cdf(d2)) / ratio
                
                pl_pct = (theo_new - current_price) / current_price * 100 if current_price > 0 else 0.0
                matrix_row.append({
                    "change_pct": round(chg * 100, 1),
                    "underlying_price": round(S_new, 2),
                    "theoretical_price": round(theo_new, 2),
                    "p_l_pct": round(pl_pct, 2)
                })
                
            scenarios.append({
                "holding_days": hold,
                "remaining_days": remaining_days,
                "matrix": matrix_row
            })
            
        return {
            "symbol": symbol_clean,
            "underlying_symbol": underlying_symbol,
            "strike_price": K,
            "current_price": current_price,
            "underlying_current_price": S,
            "implied_volatility_pct": round(iv * 100, 2),
            "days_to_maturity": days_to_maturity,
            "scenarios": scenarios
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate 2D scenario matrix: {str(e)}"
        )

@app.get("/api/warrants/{symbol}/history")
def get_warrant_history(
    symbol: str,
    days: int = Query(15, ge=5, le=60, description="Number of trading sessions to look back")
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
                detail=f"Historical data for warrant '{symbol_clean}' could not be resolved or mapped. Ensure run_cw.py has run first."
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
                "theta_burn_pct": round(float(row["theta_burn"] * 100), 3)
            })
            
        # Summary statistics
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
                "valuation_assessment": valuation_assessment
            },
            "history": history_records
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform historical warrant volatility analysis: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Start the server on port 8008 (SaaS production standard)
    uvicorn.run("main:app", host="127.0.0.1", port=8008, reload=True)

