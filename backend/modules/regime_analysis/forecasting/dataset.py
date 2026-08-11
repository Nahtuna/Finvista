import pandas as pd
import numpy as np
from typing import Tuple
from backend.modules.regime_analysis.forecasting.features import RegimeFeatureEngineer

class RegimeDataset:
    """Combines feature engineering with rule-based labeling to create ML dataset."""
    
    @staticmethod
    def create_dataset(df_raw: pd.DataFrame, horizon: int = 5) -> Tuple[pd.DataFrame, pd.Series]:
        """Creates X (features) and y (target regime at t+horizon) using rule-based labeling."""
        df = df_raw.copy()
        
        # Date handling
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
        elif hasattr(df.index, 'to_datetime'):
            df.index = pd.to_datetime(df.index)
            df = df.sort_index().reset_index()
        
        if len(df) < 200:
            raise ValueError(f"Insufficient data: {len(df)} rows. Need at least 200 rows.")
        
        # Rule-based regime classification (4 states)
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        df['volatility_20d'] = df['log_return'].rolling(20).std() * np.sqrt(252)
        df['momentum_20d'] = df['close'].pct_change(20)
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        df['price_vs_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']
        df['price_vs_sma200'] = (df['close'] - df['sma_200']) / df['sma_200']
        
        # Rule-based regime & trading signal classification (4 states)
        df['future_return'] = df['close'].pct_change(horizon).shift(-horizon)
        
        # Conditions for Entry (Bullish), Exit (Bearish), Low/High Volatility
        is_bull_trend = (df['price_vs_sma50'] > 0) & (df['momentum_20d'] > 0)
        is_bear_trend = (df['price_vs_sma50'] < 0) & (df['momentum_20d'] < 0)
        
        conditions = [
            is_bull_trend & (df['volatility_20d'] <= 0.22),  # 0: Bullish Low Vol (Signal MUA/GIỮ TỐT)
            is_bull_trend & (df['volatility_20d'] > 0.22),   # 1: Bullish High Vol (Signal XU HƯỚNG MẠNH / DAO ĐỘNG HIGH)
            is_bear_trend & (df['volatility_20d'] <= 0.22),  # 2: Bearish Low Vol (Signal ĐỨNG NGOÀI/HẠ TỶ TRỌNG)
            is_bear_trend & (df['volatility_20d'] > 0.22)    # 3: Bearish High Vol (Signal THOÁT HẲN / RISK CAO)
        ]
        df['regime_label'] = np.select(conditions, [0, 1, 2, 3], default=0)
        
        # Create target (shift by horizon)
        df['target'] = df['regime_label'].shift(-horizon)
        
        # Generate features
        try:
            features_df = RegimeFeatureEngineer.generate_features(df)
        except Exception as e:
            print(f"[WARNING] Feature generation failed: {e}. Using basic features.")
            df['return_1d'] = df['close'].pct_change(1)
            df['return_5d'] = df['close'].pct_change(5)
            df['return_20d'] = df['close'].pct_change(20)
            df['volatility_10d'] = df['return_1d'].rolling(10).std() * np.sqrt(252)
            df['volatility_30d'] = df['return_1d'].rolling(30).std() * np.sqrt(252)
            df['sma_50'] = df['close'].rolling(50).mean()
            df['dist_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']
            features_df = df[['return_1d', 'return_5d', 'return_20d', 'volatility_10d', 'volatility_30d', 'dist_sma50']].copy()
        
        # Merge target and clean
        dataset = features_df.join(df[['target']])
        dataset = dataset.dropna(subset=['target'])
        
        if len(dataset) == 0:
            raise ValueError("Dataset is empty after preprocessing.")
        
        X = dataset.drop(columns=['target'])
        y = dataset['target'].astype(int)
        
        print(f"[OK] Dataset created: {len(X)} samples, {len(X.columns)} features")
        print(f"   Target distribution: {y.value_counts().to_dict()}")
        print(f"   [INFO] Using rule-based labeling to avoid look-ahead bias")
        
        return X, y
