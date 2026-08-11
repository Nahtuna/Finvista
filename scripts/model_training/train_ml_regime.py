import sqlite3
import pandas as pd
import argparse
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

def main():
    parser = argparse.ArgumentParser(description="Train ML Forecaster for Market Regimes")
    parser.add_argument('--symbol', type=str, default='SPY', help='Stock symbol to train on (default: SPY for reliable data availability)')
    parser.add_argument('--horizon', type=int, default=5, help='Prediction horizon (e.g., 5 days ahead)')
    args = parser.parse_args()

    print(f"🚀 Starting ML Training Pipeline for {args.symbol} (Horizon: T+{args.horizon})")
    
    # 1. Load Data
    try:
        # Use yfinance with SPY as default for reliable data
        print(f"📊 Fetching data via yfinance...")
        import yfinance as yf
        ticker = args.symbol
        
        # Get 5 years of data for training
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5*365)  # 5 years
        
        df = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
        df = df.reset_index()
        df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        if df.empty:
            print(f"❌ Failed to fetch data for {args.symbol} from yfinance.")
            sys.exit(1)
            
        print(f"✅ Loaded {len(df)} rows from yfinance")
                
    except Exception as e:
        print(f"❌ Data loading error: {e}")
        sys.exit(1)

    df['date'] = pd.to_datetime(df['date'])
    
    # 2. Create Dataset
    print("\n⚙️ Generating Features and HMM Labels...")
    X, y = RegimeDataset.create_dataset(df, horizon=args.horizon)
    
    print(f"✅ Dataset ready: {len(X)} samples, {len(X.columns)} features.")
    
    # 3. Train Model
    trainer = XGBoostRegimeTrainer(horizon=args.horizon)
    trainer.train_and_evaluate(X, y, n_splits=5)
    
    # 4. Save Model
    model_name = f"xgboost_regime_{args.symbol}_T{args.horizon}.pkl"
    trainer.save_model(model_name)

if __name__ == "__main__":
    main()
