# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import numpy as np
import sys
import os
import warnings

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

from backend.modules.regime_analysis.forecasting.dataset import RegimeDataset
from backend.modules.regime_analysis.forecasting.xgboost_trainer import XGBoostRegimeTrainer
from datetime import datetime, timedelta

def get_vietnam_data(symbol: str, days: int = 1500) -> pd.DataFrame:
    """Load stock or index data from SQLite or fallback to vnstock."""
    db_path = os.path.join(BASE_DIR, "data", "finvista.db")
    df = pd.DataFrame()
    
    # Try SQLite
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = '{symbol}' ORDER BY date ASC"
            df = pd.read_sql(query, conn)
            conn.close()
            print(f"📊 Loaded {len(df)} rows for {symbol} from SQLite.")
        except Exception as e:
            print(f"⚠️ SQLite load error for {symbol}: {e}")
            
    # Fallback to vnstock
    if df.empty or len(df) < 200:
        print(f"🔄 Fetching {symbol} via vnstock...")
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            if symbol == 'VNINDEX':
                from vnstock import Market
                market = Market()
                idx = market.index(symbol='VNINDEX')
                df_vn = idx.ohlcv(start=start_date, end=end_date, resolution='1D', count=days)
            else:
                from vnstock import Quote
                q = Quote(symbol=symbol)
                df_vn = q.history(start=start_date, end=end_date)
                
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
                print(f"✅ Loaded {len(df)} rows for {symbol} from vnstock.")
        except Exception as e:
            print(f"❌ Failed to fetch {symbol} from vnstock: {e}")
            
    return df

def train_for_symbol(symbol: str):
    print(f"\n=======================================================")
    print(f"🚀 TRAINING REGIME FORECASTING MODELS FOR {symbol}")
    print(f"=======================================================")
    
    df = get_vietnam_data(symbol)
    if df.empty or len(df) < 200:
        print(f"❌ Insufficient data for {symbol}. Skipping.")
        return
        
    for horizon in [1, 5]:
        print(f"\n--- Training T+{horizon} Horizon ---")
        try:
            X, y = RegimeDataset.create_dataset(df, horizon=horizon)
            trainer = XGBoostRegimeTrainer(horizon=horizon)
            trainer.train_and_evaluate(X, y, n_splits=5)
            
            model_name = f"xgboost_regime_{symbol}_T{horizon}.pkl"
            trainer.save_model(model_name)
        except Exception as e:
            print(f"❌ Training failed for {symbol} (T+{horizon}): {e}")

if __name__ == "__main__":
    # Train for VNINDEX, FPT, HPG, MWG
    tickers = ["VNINDEX", "FPT", "HPG", "MWG"]
    for ticker in tickers:
        train_for_symbol(ticker)
