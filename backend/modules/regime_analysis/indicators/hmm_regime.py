# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: HMM REGIME DETECTOR
=================================
Calculates the dynamic market regime for VNINDEX using a 4-state Hybrid HMM.
"""

import os
import sqlite3
import warnings
import logging
warnings.filterwarnings('ignore')  # Silence hmmlearn warnings
logging.getLogger("hmmlearn").setLevel(logging.ERROR)
logging.getLogger("hmmlearn.base").setLevel(logging.ERROR)

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from backend.modules.regime_analysis.portfolio.regime_model import prepare_vnindex_features, fit_vnindex_hmm

def calculate_vnindex_regime(days: int = 1250, force_refresh: bool = False) -> dict:
    """
    Dynamically calculates the market regime based on recent VNINDEX history.
    
    Args:
        days: Number of days to look back for regime calculation
        force_refresh: Force refresh VNINDEX data before calculation
    """
    # Force refresh regime cache if requested
    if force_refresh:
        try:
            from backend.infra.redis_cache import invalidate_regime_cache
            invalidate_regime_cache()
            print("🔄 [Regime] Cache invalidated due to force_refresh=True")
        except Exception:
            pass
    
    # 1. Fetch VNINDEX data from PostgreSQL
    df = pd.DataFrame()
    try:
        from backend.core.database import SessionLocal, StockHistoricalPrice
        from sqlalchemy import desc
        
        db = SessionLocal()
        try:
            rows = db.query(
                StockHistoricalPrice.date, StockHistoricalPrice.open,
                StockHistoricalPrice.high, StockHistoricalPrice.low,
                StockHistoricalPrice.close, StockHistoricalPrice.volume
            ).filter(StockHistoricalPrice.symbol == 'VNINDEX').order_by(StockHistoricalPrice.date.asc()).all()
            
            if rows:
                df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ [HMM] PostgreSQL fetch error: {e}")

    if df.empty or len(df) < 100:
        try:
            # Fallback to vnstock first
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            from vnstock import Market
            market = Market()
            idx = market.index(symbol='VNINDEX')
            df_vn = idx.ohlcv(start=start_date, end=end_date, resolution='1D')
            if df_vn is not None and not df_vn.empty:
                df = df_vn.reset_index()
                time_col = 'time' if 'time' in df.columns else ('date' if 'date' in df.columns else df.columns[0])
                df = df.rename(columns={
                    time_col: 'date',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume'
                })
        except Exception:
            pass

        if df.empty or len(df) < 100:
            try:
                # Fallback to yfinance
                df = yf.download("^VNINDEX", start=start_date, end=end_date, progress=False)
                df = df.reset_index()
                df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
            except Exception:
                pass

    # Safe fallback if absolutely no data is found
    if df.empty or len(df) < 50:
        print(f"⚠️ [Regime] Insufficient data: {len(df)} rows")
        return {
            "regime": "UNKNOWN",
            "confidence": 0.0,
            "bias": "NEUTRAL",
            "state": -1,
            "description": "Insufficient data for regime calculation."
        }

    # 2. Process features and run HMM
    try:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df_feats = prepare_vnindex_features(df)
        
        hybrid_model, _ = fit_vnindex_hmm(df_feats)
        states = hybrid_model.predict(df_feats)
        probs = hybrid_model.predict_proba(df_feats)
        
        latest_state = int(states[-1])
        latest_prob = float(probs[-1, latest_state])
        
        # Get all probabilities for the latest observation
        latest_probs_dict = {
            "BULLISH_VOL_CONTRACTION": float(probs[-1, 0]),
            "BULLISH_VOL_EXPANSION": float(probs[-1, 1]),
            "BEARISH_VOL_CONTRACTION": float(probs[-1, 2]),
            "BEARISH_VOL_EXPANSION": float(probs[-1, 3])
        }
        
        # Mapping to regimes and biases
        # State 0: Bullish Low Vol
        # State 1: Bullish High Vol
        # State 2: Bearish Low Vol
        # State 3: Bearish High Vol (Crisis)
        regime_map = {
            0: "BULLISH_VOL_CONTRACTION",
            1: "BULLISH_VOL_EXPANSION",
            2: "BEARISH_VOL_CONTRACTION",
            3: "BEARISH_VOL_EXPANSION"
        }
        
        bias_map = {
            0: "LONG_CW",
            1: "LONG_CW",
            2: "CASH_ONLY",
            3: "CASH_ONLY"
        }
        
        desc_map = {
            0: "Thị trường tăng trưởng ổn định, biến động thấp.",
            1: "Thị trường tăng trưởng mạnh mẽ, biến động cao (Môi trường thuận lợi cho CW).",
            2: "Thị trường giảm điểm trong biên độ hẹp, biến động thấp.",
            3: "Thị trường giảm điểm mạnh, biến động cực đoan (Rủi ro đuôi béo)."
        }
        
        return {
            "regime": regime_map.get(latest_state, "SIDEWAYS"),
            "confidence": latest_prob,
            "bias": bias_map.get(latest_state, "NEUTRAL"),
            "state": latest_state,
            "hmm_probabilities": latest_probs_dict,
            "description": desc_map.get(latest_state, "Chế độ thị trường xác định bởi HMM.")
        }
        
    except Exception as e:
        print(f"⚠️ [HMM Error] {e}")
        return {
            "regime": "SIDEWAYS",
            "confidence": 0.50,
            "bias": "NEUTRAL",
            "state": 0,
            "description": f"Fallback regime due to error: {str(e)}"
        }
