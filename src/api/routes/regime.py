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

Author: samvo
Version: 1.0
"""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import io
import matplotlib.pyplot as plt
import pandas as pd
from src.core.utils import logger
from src.core.database import engine


from datetime import datetime
from typing import Optional
from pydantic import BaseModel

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
def get_market_regime():
    """
    Lấy Market Regime hiện tại.
    Ưu tiên 1: Tín hiệu từ TradingView Webhook (nếu có)
    Ưu tiên 2: Mô hình Native Creed Master Grid Engine (EMA 200 + ATR Volatility)
    Ưu tiên 3: Fallback HMM
    """
    if _TRADINGVIEW_REGIME_CACHE:
        return _TRADINGVIEW_REGIME_CACHE

    try:
        from src.modules.regime_analysis.indicators.creed_regime import calculate_creed_vnindex_regime
        return calculate_creed_vnindex_regime(days=500)
    except Exception as e_creed:
        logger.debug(f"⚠️ [RegimeRoute] Creed Grid fallback: {e_creed}")
        try:
            from src.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
            regime = calculate_vnindex_regime(days=1250)
            return {
                "status": "ok",
                "source": "HMM 4-state Gaussian Model (VNINDEX 5yr)",
                **regime,
            }
        except Exception as e:
            logger.warning(f"⚠️ [RegimeRoute] All regime detectors failed: {e}. Using fallback.")
            return {
                "status": "fallback",
                "regime": "UNKNOWN",
                "confidence": 0.0,
                "bias": "NEUTRAL",
                "description": f"Không thể tính toán regime: {e}",
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

    result: dict = {
        "ticker": ticker_clean,
        "period_days": days,
    }

    # 1. GARCH Volatility Forecast
    try:
        from src.modules.regime_analysis.indicators.garch_volatility_forecaster import (
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
        from src.modules.regime_analysis.indicators.multi_tf_ema import get_multi_tf_status
        ema_result = get_multi_tf_status(ticker_clean)
        result["momentum_signals"] = ema_result
    except Exception as e:
        logger.debug(f"[RegimeRoute] EMA momentum failed for {ticker_clean}: {e}")
        result["momentum_signals"] = {"error": str(e)}

    # 3. Regime Recommendation
    try:
        from src.modules.regime_analysis.indicators.regime_detector import RegimeDetector
        import pandas as pd
        from src.core.database import engine
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
    result: dict = {"ticker": ticker_clean, "period_days": days, "indicators": {}}

    # GARCH EVT VaR
    try:
        from src.modules.regime_analysis.indicators.garch_evt_var import calculate_garch_evt_var
        result["indicators"]["garch_evt_var"] = calculate_garch_evt_var(
            ticker=ticker_clean, days=days
        )
    except Exception as e:
        result["indicators"]["garch_evt_var"] = {"error": str(e)}

    # Kalman Filter
    try:
        from src.modules.regime_analysis.indicators.kalman_filter import KalmanFilter
        kf = KalmanFilter()
        result["indicators"]["kalman_trend"] = kf.estimate(ticker=ticker_clean, days=days)
    except Exception as e:
        result["indicators"]["kalman_trend"] = {"error": str(e)}

    # Volatility Models
    try:
        from src.modules.regime_analysis.indicators.volatility_models import (
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
    from src.modules.regime_analysis.indicators.garch_volatility_forecaster import fetch_stock_returns, fit_garch_model
    df_ret = fetch_stock_returns(ticker_clean)
    if df_ret is not None and len(df_ret) >= days:
        df_ret = df_ret.tail(days)
    garch_res = fit_garch_model(df_ret, ticker_clean) if df_ret is not None else {"vol": None}
    # Momentum signals
    from src.modules.regime_analysis.indicators.multi_tf_ema import get_multi_tf_status
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
