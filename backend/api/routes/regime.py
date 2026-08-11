# -*- coding: utf-8 -*-
"""
🌊 FINVISTA: REGIME ANALYSIS ROUTES
=====================================
FastAPI delivery layer cho Market Regime Analysis.
Exposes HMM market regime state và RegimeDetector signals.

Endpoints:
    GET /api/regime/market              → HMM market regime hiện tại (VNINDEX)
    GET /api/regime/{ticker}            → Regime analysis cho một mã cụ thể
    GET /api/regime/{ticker}/indicators → Technical indicators đầy đủ
    GET /api/regime/evaluation          → Đánh giá hiệu suất regime model với bộ chỉ số toàn diện

Author: samvo
Version: 1.1
"""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import io
import matplotlib.pyplot as plt
import pandas as pd
from backend.core.utils import logger
from backend.core.database import engine


from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import numpy as np

def get_latest_index_date() -> str:
    try:
        from backend.core.database import engine
        import pandas as pd
        query = "SELECT MAX(date) as max_date FROM stock_history"
        df = pd.read_sql(query, engine)
        if not df.empty and df['max_date'].iloc[0]:
            # Convert YYYY-MM-DD to DD/MM/YYYY
            date_str = str(df['max_date'].iloc[0]).split(" ")[0]
            parts = date_str.split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
            return date_str
    except Exception:
        pass
    return "31/07/2026"

def ensure_stock_data(symbol: str) -> bool:
    """
    Checks if stock_history table has enough data (>= 30 rows) for the symbol.
    If not, fetches data from Entrade's TradingView API and populates it.
    Returns True if data is available (already existed or successfully synced).
    """
    sym = symbol.upper().strip()
    try:
        from backend.core.database import engine
        import pandas as pd
        
        # Check if table exists and has rows
        check_query = f"SELECT COUNT(*) as count FROM stock_history WHERE symbol = '{sym}'"
        df_check = pd.read_sql(check_query, engine)
        row_count = df_check['count'].iloc[0] if not df_check.empty else 0
        
        if row_count >= 30:
            return True
            
        # Not enough data, let's sync from Entrade
        logger.info(f"🔄 Auto-syncing stock data from Entrade for {sym}...")
        import requests
        import time
        from datetime import datetime
        
        to_time = int(time.time())
        from_time = to_time - 1825 * 86400  # 5 years
        
        entrade_symbol = sym
        is_entrade_index = entrade_symbol in ["VNINDEX", "VN30", "HNXINDEX", "HNX", "VN30INDEX", "CWINDEX", "UPINDEX", "HNX30", "SPX", "DJI", "NASDAQ", "NIKKEI", "HSI"]
        
        # Map indices names to Entrade symbols
        if sym in ["HNXINDEX", "HNX"]:
            entrade_symbol = "HNX"
        elif sym in ["VNINDEX", "VN30INDEX"]:
            entrade_symbol = "VNINDEX"
            
        path_type = "index" if is_entrade_index else "stock"
        url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/{path_type}?resolution=1D&symbol={entrade_symbol}&from={from_time}&to={to_time}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        res = requests.get(url, headers=headers, timeout=5.0).json()
        if res and res.get("t") and len(res["t"]) > 0:
            # Clear old rows to avoid duplicates
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM stock_history WHERE symbol = '{sym}'"))
                conn.commit()
                
            rows_to_insert = []
            scale = 1000.0 if not is_entrade_index else 1.0
            
            for i in range(len(res["t"])):
                dt_str = datetime.fromtimestamp(res["t"][i]).strftime('%Y-%m-%d')
                rows_to_insert.append({
                    "symbol": sym,
                    "date": dt_str,
                    "open": float(res["o"][i]) * scale,
                    "high": float(res["h"][i]) * scale,
                    "low": float(res["l"][i]) * scale,
                    "close": float(res["c"][i]) * scale,
                    "volume": float(res["v"][i])
                })
                
            if rows_to_insert:
                temp_df = pd.DataFrame(rows_to_insert)
                temp_df.to_sql('stock_history', engine, if_exists='append', index=False)
                logger.info(f"✅ Successfully synced {len(rows_to_insert)} bars for {sym}")
                return True
    except Exception as e:
        logger.error(f"❌ Failed to auto-sync {sym}: {e}")
    return False


router = APIRouter(tags=["regime-analysis"])

# In-memory store for real-time TradingView Webhook signals
_TRADINGVIEW_REGIME_CACHE: dict = {}


class TradingViewWebhookPayload(BaseModel):
    ticker: Optional[str] = "VNINDEX"
    regime: str  # BULL, BEAR, BULLISH, BEARISH, SIDEWAY, NEUTRAL
    bias: Optional[str] = None  # LONG_CW, SHORT_CW, SKIP_CW, NEUTRAL
    confidence: Optional[float] = 0.95
    source: Optional[str] = "TradingView Webhook"
    secret: Optional[str] = None


@router.post("/api/regime/webhook/tradingview")
def receive_tradingview_webhook(payload: TradingViewWebhookPayload):
    """
    Nhận tín hiệu Regime thời gian thực từ TradingView Alerts qua Webhook.

    Payload ví dụ từ TradingView Alert Message:
    {
      "ticker": "VNINDEX",
      "regime": "BEAR",
      "bias": "SKIP_CW",
      "source": "TradingView Creed Master Grid"
    }
    """
    global _TRADINGVIEW_REGIME_CACHE

    regime_raw = payload.regime.upper().strip()
    
    # Chuẩn hóa trạng thái Regime
    if "BEAR" in regime_raw or "CRISIS" in regime_raw:
        regime_norm = "BEARISH_HIGH_VOL"
        bias_norm = payload.bias.upper() if payload.bias else "SKIP_CW"
        desc = "TradingView xác nhận pha GIẢM giá (Risk-Off) - Tạm dừng mua mới"
    elif "BULL" in regime_raw:
        regime_norm = "BULLISH_VOL_EXPANSION"
        bias_norm = payload.bias.upper() if payload.bias else "LONG_CW"
        desc = "TradingView xác nhận pha TĂNG giá (Risk-On) - Phù hợp giao dịch"
    else:
        regime_norm = "SIDEWAYS"
        bias_norm = payload.bias.upper() if payload.bias else "NEUTRAL"
        desc = "TradingView xác nhận thị trường ĐI NGANG - Thận trọng"

    _TRADINGVIEW_REGIME_CACHE = {
        "status": "ok",
        "source": payload.source or "TradingView Webhook Alert",
        "regime": regime_norm,
        "raw_regime": payload.regime,
        "confidence": payload.confidence or 0.95,
        "bias": bias_norm,
        "description": desc,
        "ticker": (payload.ticker or "VNINDEX").upper(),
        "updated_at": datetime.now().isoformat(),
    }

    logger.info(f"🌐 [TradingView Webhook] Market Regime updated: {regime_norm} ({bias_norm}) from {payload.source}")

    return {
        "status": "success",
        "message": "Market regime updated successfully from TradingView",
        "active_regime": _TRADINGVIEW_REGIME_CACHE,
    }


@router.get("/api/regime/market")
def get_market_regime(
    mode: str = Query(default="ensemble", description="Regime calculation mode: 'ensemble', 'creed', 'hmm', 'kairos'"),
    performance_mode: str = Query(default=None, description="Performance mode for ensemble: 'fast', 'hybrid', 'full'")
):
    res = _get_market_regime_internal(mode, performance_mode)
    if isinstance(res, dict) and "updated_at" not in res:
        res["updated_at"] = get_latest_index_date()
    return res

def _get_market_regime_internal(mode: str, performance_mode: str):
    """
    Lấy Market Regime hiện tại với Ensemble Engine (mặc định).
    
    Ưu tiên 1: Tín hiệu từ TradingView Webhook (nếu có)
    Ưu tiên 2: Ensemble Regime Engine (Creed + HMM + Kairos + XGBoost)
    Ưu tiên 3: Single model fallback (tùy theo mode parameter)
    
    Performance modes:
    - fast: Chỉ Creed + HMM (tốc độ cao, độ chính xác trung bình)
    - hybrid: Creed + HMM + Kairos (cân bằng tốc độ và độ chính xác) 
    - full: Tất cả models + XGBoost (độ chính xác cao nhất, tốc độ thấp hơn)
    """
    if _TRADINGVIEW_REGIME_CACHE:
        return _TRADINGVIEW_REGIME_CACHE

    # Use ensemble mode by default
    if mode == "ensemble":
        try:
            from backend.modules.regime_analysis.indicators.ensemble_regime_engine import EnsembleRegimeEngine
            from backend.core import config
            
            # Get VNINDEX data
            query = "SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = 'VNINDEX' ORDER BY date DESC LIMIT 500"
            df = pd.read_sql(query, engine)
            
            if not df.empty and len(df) >= 50:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                
                # Initialize ensemble engine with specified performance mode
                perf_mode = performance_mode or config.REGIME_PERFORMANCE_MODE
                ensemble = EnsembleRegimeEngine(
                    use_ml_forecast=True,
                    ml_horizon=1,
                    instrument_type="CW",
                    performance_mode=perf_mode
                )
                
                regime_result = ensemble.calculate_ensemble_regime(df, "VNINDEX")
                
                return {
                    "status": "ok",
                    "source": f"Ensemble Regime Engine ({perf_mode.upper()} mode)",
                    **regime_result,
                }
        except Exception as e_ensemble:
            logger.warning(f"⚠️ [RegimeRoute] Ensemble regime failed: {e_ensemble}. Falling back to single model.")
    
    # Fallback to single model based on mode
    if mode in ["ensemble", "creed"]:
        try:
            from backend.modules.regime_analysis.indicators.creed_regime import calculate_creed_vnindex_regime
            return calculate_creed_vnindex_regime(days=500)
        except Exception as e_creed:
            logger.debug(f"⚠️ [RegimeRoute] Creed Grid fallback: {e_creed}")
    
    if mode in ["ensemble", "creed", "hmm"]:
        try:
            from backend.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
            regime = calculate_vnindex_regime(days=1250)
            return {
                "status": "ok",
                "source": "HMM 4-state Gaussian Model (VNINDEX 5yr)",
                **regime,
            }
        except Exception as e:
            logger.warning(f"⚠️ [RegimeRoute] HMM failed: {e}.")
    
    if mode in ["ensemble", "kairos"]:
        try:
            from backend.modules.regime_analysis.indicators.regime_detection import RegimeDetector
            query = "SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = 'VNINDEX' ORDER BY date DESC LIMIT 500"
            df = pd.read_sql(query, engine)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                kairos_result = RegimeDetector.calculate_kairos_regimes(df)
                latest_regime = kairos_result['regime'].iloc[-1]
                return {
                    "status": "ok",
                    "source": "Kairos 8-state Regime Detector",
                    "regime": latest_regime,
                    "bias": "NEUTRAL",  # Would need proper mapping
                    "confidence": 0.7,
                    "description": f"Kairos regime: {latest_regime}"
                }
        except Exception as e:
            logger.warning(f"⚠️ [RegimeRoute] Kairos failed: {e}.")
    
    # Final fallback
    logger.warning(f"⚠️ [RegimeRoute] All regime detectors failed. Using fallback.")
    return {
        "status": "fallback",
        "regime": "UNKNOWN",
        "confidence": 0.0,
        "bias": "NEUTRAL",
        "description": "Không thể tính toán regime - tất cả models thất bại",
    }


_EVALUATION_CACHE: dict = {}


@router.get("/api/regime/evaluation")
def get_regime_evaluation(
    ticker: str = Query(default="VNINDEX", description="Mã chứng khoán hoặc chỉ số để đánh giá"),
    days: int = Query(default=500, ge=60, le=1250, description="Số ngày dữ liệu để đánh giá"),
    regime_type: str = Query(default="creed", description="Loại regime detector: 'creed', 'hmm', 'kairos'"),
):
    """
    Đánh giá hiệu suất của mô hình nhận diện regime với bộ chỉ số toàn diện.
    """
    cache_key = f"{ticker.upper()}_{days}_{regime_type.lower()}"
    if cache_key in _EVALUATION_CACHE:
        cached_entry = _EVALUATION_CACHE[cache_key]
        if (datetime.now() - cached_entry['timestamp']).total_seconds() < 86400:
            return cached_entry['data']

    try:
        # Fetch price data
        from backend.core.database import engine
        query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = '{ticker.upper()}' ORDER BY date DESC LIMIT {days}"
        df = pd.read_sql(query, engine)
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)
        
        if df.empty:
            return {
                "status": "error",
                "message": f"No data found for ticker {ticker}",
                "ticker": ticker.upper()
            }
        
        # Calculate regimes based on selected detector
        if regime_type.lower() == "creed":
            from backend.modules.regime_analysis.indicators.creed_regime import calculate_creed_regime_from_df
            regime_result = calculate_creed_regime_from_df(df, trend_period=200)
            # Vectorize: apply the same EMA logic row-by-row to produce historical labels
            df['close'] = df['close'].astype(float)
            ema_trend = df['close'].ewm(span=min(200, max(20, len(df)//2)), adjust=False).mean()
            ema10 = df['close'].ewm(span=10, adjust=False).mean()
            ema20 = df['close'].ewm(span=20, adjust=False).mean()
            dist_pct = (df['close'] - ema_trend) / ema_trend
            bull = (df['close'] > ema_trend) & (ema10 > ema20) & (dist_pct > 0.005)
            bear = ((df['close'] < ema_trend) & (ema10 < ema20)) | (dist_pct < -0.005)
            df['regime'] = 'SIDEWAYS'
            df.loc[bull, 'regime'] = 'BULLISH_VOL_EXPANSION'
            df.loc[bear, 'regime'] = 'BEARISH_HIGH_VOL'
            
        elif regime_type.lower() == "hmm":
            from backend.modules.regime_analysis.portfolio.regime_model import prepare_vnindex_features, fit_vnindex_hmm
            df_feats = prepare_vnindex_features(df)
            hybrid_model, _ = fit_vnindex_hmm(df_feats)
            states = hybrid_model.predict(df_feats)
            
            # Map states to regime names
            regime_map = {
                0: "BULLISH_VOL_CONTRACTION",
                1: "BULLISH_VOL_EXPANSION", 
                2: "BEARISH_VOL_CONTRACTION",
                3: "BEARISH_VOL_EXPANSION"
            }
            df['regime'] = [regime_map.get(s, "UNKNOWN") for s in states]
            
        elif regime_type.lower() == "kairos":
            from backend.modules.regime_analysis.indicators.regime_detection import RegimeDetector
            regime_df = RegimeDetector.calculate_kairos_regimes(df)
            df['regime'] = regime_df['regime'].values
        else:
            return {
                "status": "error",
                "message": f"Unknown regime type: {regime_type}. Use 'creed', 'hmm', or 'kairos'",
                "ticker": ticker.upper()
            }
        
        # Run evaluation
        from backend.modules.regime_analysis.evaluation import evaluate_regime_performance
        evaluation_results = evaluate_regime_performance(df, regime_column='regime')
        
        # Add metadata
        evaluation_results['metadata'] = {
            'ticker': ticker.upper(),
            'regime_type': regime_type,
            'evaluation_period_days': days,
            'regime_detector_used': regime_type.upper()
        }
        
        return {
            "status": "ok",
            **evaluation_results
        }
        
    except Exception as e:
        logger.error(f"❌ [RegimeEval] Evaluation failed for {ticker}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "ticker": ticker.upper(),
            "regime_type": regime_type
        }


@router.get("/api/regime/{ticker}")
def get_ticker_regime(
    ticker: str,
    days: int = Query(default=252, ge=60, le=1250, description="Số ngày dữ liệu để phân tích"),
):
    """
    Phân tích Market Regime cho một mã cổ phiếu cụ thể.

    Trả về:
    - current_regime: trạng thái HMM hiện tại
    - garch_volatility: dự báo biến động GARCH 1 bước
    - momentum_signals: multi-timeframe EMA signals
    - regime_recommendation: khuyến nghị giao dịch dựa trên regime
    """
    ticker_clean = ticker.upper().strip()
    ensure_stock_data(ticker_clean)

    result: dict = {
        "ticker": ticker_clean,
        "period_days": days,
    }

    # 1. GARCH Volatility Forecast
    try:
        from backend.modules.regime_analysis.indicators.volatility_forecasting import (
            fetch_stock_returns, fit_garch_model,
        )
        df_ret = fetch_stock_returns(ticker_clean)
        if df_ret is not None and len(df_ret) >= days:
            df_ret = df_ret.tail(days)
        garch_result = fit_garch_model(df_ret, ticker_clean) if df_ret is not None else {"error": "No data"}
        result["garch_volatility"] = garch_result or {"error": "GARCH did not converge"}
    except Exception as e:
        logger.debug(f"[RegimeRoute] GARCH forecast failed for {ticker_clean}: {e}")
        result["garch_volatility"] = {"error": str(e)}

    # 2. Multi-TF EMA Momentum
    try:
        from backend.modules.regime_analysis.indicators.multi_tf_ema import get_multi_tf_status
        ema_result = get_multi_tf_status(ticker_clean)
        result["momentum_signals"] = ema_result
    except Exception as e:
        logger.debug(f"[RegimeRoute] EMA momentum failed for {ticker_clean}: {e}")
        result["momentum_signals"] = {"error": str(e)}

    # 3. Regime Recommendation
    try:
        from backend.modules.regime_analysis.indicators.regime_detection import RegimeDetector
        import pandas as pd
        from backend.core.database import engine
        query = f"SELECT date, close FROM stock_history WHERE symbol = '{ticker_clean}' ORDER BY date ASC LIMIT {days}"
        df_regime = pd.read_sql(query, engine)
        if df_regime.empty:
            raise ValueError("No stock data found")
        regime_df = RegimeDetector.calculate_kairos_regimes(df_regime)
        latest_regime = regime_df['regime'].iloc[-1]
        regime_data = {
            "regime": latest_regime,
            "momentum": float(regime_df['momentum'].iloc[-1]),
            "vol_30": float(regime_df['vol_30'].iloc[-1]),
            "p_turbulent": float(regime_df['p_turbulent'].iloc[-1]),
        }
        result["regime_detector"] = regime_data

        # Build recommendation
        if "Xu_Hướng" in latest_regime or "Đầu_Xu" in latest_regime:
            recommendation = "LONG — Xu hướng tăng, phù hợp mua CW CALL"
        elif "Cao_Trào" in latest_regime or "Quét" in latest_regime:
            recommendation = "AVOID / SHORT — Thị trường đang giảm mạnh"
        else:
            recommendation = "NEUTRAL — Sideways, chờ tín hiệu rõ hơn"

        result["regime_recommendation"] = recommendation
    except Exception as e:
        logger.debug(f"[RegimeRoute] RegimeDetector failed for {ticker_clean}: {e}")
        result["regime_detector"] = {"error": str(e)}
        result["regime_recommendation"] = "UNKNOWN"

    return result


@router.get("/api/regime/{ticker}/indicators")
def get_ticker_indicators(
    ticker: str,
    days: int = Query(default=252, ge=60, le=1250, description="Số ngày dữ liệu"),
):
    """
    Lấy toàn bộ technical indicators cho một mã.

    Bao gồm: GARCH, HMM state probabilities, Kalman Filter trend, EMA multi-TF.
    """
    ticker_clean = ticker.upper().strip()
    ensure_stock_data(ticker_clean)
    result: dict = {"ticker": ticker_clean, "period_days": days, "indicators": {}}

    # GARCH EVT VaR
    try:
        from backend.modules.regime_analysis.indicators.volatility_forecasting import get_underlying_garch_evt_var
        result["indicators"]["garch_evt_var"] = get_underlying_garch_evt_var(
            underlying_symbol=ticker_clean
        )
    except Exception as e:
        result["indicators"]["garch_evt_var"] = {"error": str(e)}

    # Kalman Filter
    try:
        from backend.modules.regime_analysis.indicators.kalman_filter import KalmanFilter
        kf = KalmanFilter()
        result["indicators"]["kalman_trend"] = kf.estimate(ticker=ticker_clean, days=days)
    except Exception as e:
        result["indicators"]["kalman_trend"] = {"error": str(e)}

    # Volatility Models
    try:
        from backend.modules.regime_analysis.indicators.volatility_models import (
            calculate_realized_volatility,
        )
        result["indicators"]["realized_volatility"] = calculate_realized_volatility(
            ticker=ticker_clean, days=days
        )
    except Exception as e:
        result["indicators"]["realized_volatility"] = {"error": str(e)}

    return result


@router.get("/api/regime/{ticker}/plot")
def plot_regime(
    ticker: str,
    days: int = Query(default=252, ge=60, le=1250, description="Số ngày dữ liệu để plot"),
):
    """
    Plot price, volatility and momentum signals for a ticker.
    Returns a PNG image.
    """
    ticker_clean = ticker.upper().strip()
    # Fetch price data
    query = f"SELECT date, close FROM stock_history WHERE symbol = '{ticker_clean}' ORDER BY date ASC LIMIT {days}"
    df_price = pd.read_sql(query, engine)
    if df_price.empty:
        raise ValueError("No price data for ticker")
    # GARCH volatility (using returns)
    from backend.modules.regime_analysis.indicators.garch_volatility_forecaster import fetch_stock_returns, fit_garch_model
    df_ret = fetch_stock_returns(ticker_clean)
    if df_ret is not None and len(df_ret) >= days:
        df_ret = df_ret.tail(days)
    garch_res = fit_garch_model(df_ret, ticker_clean) if df_ret is not None else {"vol": None}
    # Momentum signals
    from backend.modules.regime_analysis.indicators.multi_tf_ema import get_multi_tf_status
    momentum = get_multi_tf_status(ticker_clean)
    # Plot
    plt.switch_backend('agg')
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(pd.to_datetime(df_price['date']), df_price['close'], label='Close Price', color='tab:blue')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price', color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    # Secondary axis for volatility if available
    if isinstance(garch_res, dict) and garch_res.get('vol') is not None:
        ax2 = ax1.twinx()
        ax2.plot(pd.to_datetime(df_price['date'])[-len(garch_res['vol']):], garch_res['vol'], label='GARCH Vol', color='tab:red', alpha=0.6)
        ax2.set_ylabel('Volatility', color='tab:red')
        ax2.tick_params(axis='y', labelcolor='tab:red')
    # Add momentum annotation
    if isinstance(momentum, dict):
        txt = f"Momentum: {momentum.get('signal','N/A')}"
        plt.title(f"{ticker_clean} Regime Plot – {txt}")
    else:
        plt.title(f"{ticker_clean} Regime Plot")
    plt.legend(loc='upper left')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type='image/png')


@router.get("/api/regime/ensemble/{ticker}")
def get_ensemble_regime(ticker: str):
    """
    Lấy ensemble regime decision từ hệ thống voting đa model.
    
    Kết hợp 3 models:
    - Creed Master Grid (Technical analysis)
    - HMM 4-state (Statistical)  
    - Kairos 8-state (Complex multi-factor)
    - XGBoost Forecast (ML predictive)
    
    Returns:
        Ensemble decision với confidence scoring và model breakdown
    """
    try:
        from backend.core.database import engine
        query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = '{ticker.upper()}' ORDER BY date DESC LIMIT 500"
        df = pd.read_sql(query, engine)
        
        if df.empty:
            return {
                "status": "error",
                "message": f"No data found for ticker {ticker}",
                "ticker": ticker.upper()
            }
        
        df = df.iloc[::-1].reset_index(drop=True)
        
        # Use ensemble engine
        from backend.modules.regime_analysis.indicators.ensemble_regime_engine import ensemble_engine
        ensemble_result = ensemble_engine.calculate_ensemble_regime(df, ticker.upper())
        
        return {
            "status": "ok",
            "ticker": ticker.upper(),
            "ensemble_decision": ensemble_result
        }
        
    except Exception as e:
        logger.error(f"❌ [RegimeRoute] Ensemble regime error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "ticker": ticker.upper()
        }


@router.get("/api/regime/forecast/{ticker}")
def get_regime_forecast(ticker: str):
    """
    Lấy regime forecast với transition probabilities.
    
    Args:
        ticker: Mã chứng khoán hoặc chỉ số
        horizon: Số ngày dự báo (1-20 ngày)
    
    Returns:
        Forecast với transition probabilities và risk assessment
    """
    try:
        from backend.core.database import engine
        query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = '{ticker.upper()}' ORDER BY date DESC LIMIT 500"
        df = pd.read_sql(query, engine)
        
        if df.empty:
            return {
                "status": "error",
                "message": f"No data found for ticker {ticker}",
                "ticker": ticker.upper()
            }
        
        df = df.iloc[::-1].reset_index(drop=True)
        
        # Use ensemble engine for forecasting
        from backend.modules.regime_analysis.indicators.ensemble_regime_engine import ensemble_engine
        forecast = ensemble_engine.forecast_regime_transition(df, ticker.upper(), 5)
        
        return {
            "status": "ok",
            "ticker": ticker.upper(),
            "forecast": forecast
        }
        
    except Exception as e:
        logger.error(f"❌ [RegimeRoute] Regime forecast error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "ticker": ticker.upper()
        }


@router.post("/api/regime/alert/check")
def check_regime_alert(payload: dict):
    """
    Kiểm tra và log regime change alert nếu cần.
    
    Payload:
    {
        "ticker": "VNINDEX",
        "current_regime": {...},
        "previous_regime": {...}
    }
    
    Returns:
        Alert check result
    """
    try:
        ticker = payload.get('ticker', 'VNINDEX')
        current_regime = payload.get('current_regime')
        previous_regime = payload.get('previous_regime')
        
        if not current_regime:
            return {
                "status": "error",
                "message": "current_regime is required"
            }
        
        # Use regime change detector
        from backend.modules.regime_analysis.indicators.regime_change_detector import regime_change_detector
        result = regime_change_detector.process_regime_update(
            current_regime, previous_regime, ticker
        )
        
        return {
            "status": "ok",
            "ticker": ticker.upper(),
            "alert_result": result
        }
        
    except Exception as e:
        logger.error(f"❌ [RegimeRoute] Regime alert check error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/api/regime/{symbol}/support-resistance")
def get_support_resistance(
    symbol: str,
    lookback_days: int = Query(default=250, description="Số ngày nhìn lại để tính S/R (mặc định 250)"),
    top_n: int = Query(default=8, description="Số vùng S/R trả về"),
):
    """
    Tính vùng Hỗ trợ / Kháng cự cho một mã chứng khoán hoặc chỉ số.

    Thuật toán:
    - Williams Fractal Pivots: đỉnh/đáy cục bộ có ít nhất 5 nến mỗi bên
    - Volume Profile (POC/VAL/VAH): vùng giá giao dịch volume nhiều nhất
    - Mức tâm lý (round numbers): bội số 50/100 điểm gần giá hiện tại

    Returns:
        current_price, support_zones[], resistance_zones[], poc
    """
    try:
        sym = symbol.upper().strip()
        ensure_stock_data(sym)
        query = f"""
            SELECT date, open, high, low, close, volume
            FROM stock_history
            WHERE symbol = '{sym}'
            ORDER BY date DESC
            LIMIT {lookback_days + 20}
        """
        df = pd.read_sql(query, engine)

        if df.empty or len(df) < 30:
            return {"status": "error", "message": f"Không đủ dữ liệu cho {sym}"}

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        from backend.modules.regime_analysis.indicators.support_resistance import calculate_support_resistance
        result = calculate_support_resistance(df, lookback_days=lookback_days, top_n=top_n)

        return {
            "status": "ok",
            "symbol": sym,
            **result,
        }

    except Exception as e:
        logger.error(f"❌ [S/R] Error for {symbol}: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/api/regime/{symbol}/confluence")
def get_confluence_score(
    symbol: str,
    lookback_days: int = Query(default=120, description="Số ngày lookback để tính chỉ báo"),
):
    """
    Workflow #3: Tính Confluence Score (0-100) gộp Regime + EMA + RSI + S/R.
    Dùng để đánh giá mức độ đồng thuận của nhiều chỉ báo trước khi vào lệnh.
    """
    try:
        sym = symbol.upper().strip()
        ensure_stock_data(sym)

        query = f"""
            SELECT date, open, high, low, close, volume
            FROM stock_history
            WHERE symbol = '{sym}'
            ORDER BY date DESC
            LIMIT {lookback_days + 20}
        """
        df = pd.read_sql(query, engine)
        if df.empty or len(df) < 20:
            return {"status": "error", "message": f"Không đủ dữ liệu cho {sym}"}

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df['symbol'] = sym

        # Compute regime so confluence can read it
        from backend.modules.regime_analysis.indicators.regime_detection import (
            RegimeDetector, calculate_confluence_score
        )
        regime_df = RegimeDetector.calculate_kairos_regimes(df)
        df['regime'] = regime_df['regime']

        # Optionally fetch S/R for position scoring
        sr_data = None
        try:
            from backend.modules.regime_analysis.indicators.support_resistance import calculate_support_resistance
            sr_data = calculate_support_resistance(df, lookback_days=min(lookback_days, 250), top_n=6)
        except Exception:
            pass

        result = calculate_confluence_score(df, sr_data=sr_data)

        return {
            "status": "ok",
            "symbol": sym,
            **result,
        }

    except Exception as e:
        logger.error(f"❌ [Confluence] Error for {symbol}: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/api/regime/{symbol}/mtf-bias")
def get_mtf_bias(
    symbol: str,
    lookback_days: int = Query(default=200, description="Số ngày lookback (cần ít nhất 100)"),
):
    """
    Workflow #4: Multi-Timeframe Bias — Phân tích 3 khung thời gian (dài/trung/ngắn hạn)
    từ dữ liệu Daily. Trả về Entry Grade A/B/C/D và điểm bias_score 0-100.
    """
    try:
        sym = symbol.upper().strip()
        ensure_stock_data(sym)

        query = f"""
            SELECT date, open, high, low, close, volume
            FROM stock_history
            WHERE symbol = '{sym}'
            ORDER BY date DESC
            LIMIT {lookback_days + 10}
        """
        df = pd.read_sql(query, engine)
        if df.empty or len(df) < 50:
            return {"status": "error", "message": f"Không đủ dữ liệu cho {sym}"}

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        from backend.modules.regime_analysis.indicators.multi_timeframe_bias import calculate_mtf_bias
        result = calculate_mtf_bias(df)

        return {
            "status": "ok",
            "symbol": sym,
            **result,
        }

    except Exception as e:
        logger.error(f"❌ [MTF] Error for {symbol}: {e}")
        return {"status": "error", "message": str(e)}
