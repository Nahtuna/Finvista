import numpy as np
import pandas as pd
from backend.modules.regime_analysis.portfolio.regime_model import calculate_kama

class RegimeFeatureEngineer:
    """Engineers features from stock/index price and volume data for Regime Forecasting."""
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs.fillna(0)))

    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        fast_ema = series.ewm(span=fast, adjust=False).mean()
        slow_ema = series.ewm(span=slow, adjust=False).mean()
        macd = fast_ema - slow_ema
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        return macd, macd_signal, macd - macd_signal

    @staticmethod
    def calculate_bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> tuple:
        sma = series.rolling(window=window).mean()
        rolling_std = series.rolling(window=window).std()
        upper = sma + (rolling_std * num_std)
        lower = sma - (rolling_std * num_std)
        bb_width = (upper - lower) / sma
        return upper, lower, bb_width

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        if 'high' not in df.columns or 'low' not in df.columns:
            return pd.Series(np.nan, index=df.index)
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff() * -1
        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)

        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift(1)).abs()
        tr3 = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()  # Wilder's smoothing
        plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(period).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(period).mean() / atr.replace(0, np.nan))
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
        return dx.rolling(period).mean()

    @staticmethod
    def generate_features(df: pd.DataFrame) -> pd.DataFrame:
        """Calculates all ML features. Expects DataFrame with 'close', 'high', 'low', 'volume' columns."""
        df = df.copy().sort_index()
        
        # Trend & Momentum
        df['return_1d'] = df['close'].pct_change(1)
        df['return_5d'] = df['close'].pct_change(5)
        df['return_20d'] = df['close'].pct_change(20)
        df['rsi_14'] = RegimeFeatureEngineer.calculate_rsi(df['close'], 14)
        
        macd, macd_signal, macd_hist = RegimeFeatureEngineer.calculate_macd(df['close'])
        df['macd_hist'] = macd_hist
        df['macd_slope'] = macd_hist.diff(2)
        
        df['kama_21'] = calculate_kama(df['close'], er_period=21, fast=5, slow=100)
        df['kama_slope'] = df['kama_21'].diff()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        df['dist_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']
        df['dist_sma200'] = (df['close'] - df['sma_200']) / df['sma_200']
        df['adx_14'] = RegimeFeatureEngineer.calculate_adx(df, 14)
        
        # Volatility
        df['volatility_10d'] = df['return_1d'].rolling(10).std() * np.sqrt(252)
        df['volatility_30d'] = df['return_1d'].rolling(30).std() * np.sqrt(252)
        df['bb_width'] = RegimeFeatureEngineer.calculate_bollinger_bands(df['close'], 20)[2]
        
        # True Range & ATR (if high/low available)
        if 'high' in df.columns and 'low' in df.columns:
            df['true_range'] = df[['high', 'low', 'close']].apply(
                lambda row: max(row['high'] - row['low'], abs(row['high'] - row['close']), abs(row['low'] - row['close'])), axis=1
            )
            df['atr_14'] = df['true_range'].rolling(14).mean() / df['close']
        
        # Volume
        df['vol_ma5'] = df['volume'].rolling(5).mean()
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['vol_trend_5_20'] = df['vol_ma5'] / df['vol_ma20'].replace(0, np.nan)
        df['log_volume_ratio'] = np.log(df['volume'] / df['vol_ma20'].replace(0, np.nan))
        
        # Feature selection
        features = ['return_1d', 'return_5d', 'return_20d', 'rsi_14', 'macd_hist', 'macd_slope', 'kama_slope', 
                    'dist_sma50', 'dist_sma200', 'adx_14', 'volatility_10d', 'volatility_30d', 'bb_width', 
                    'vol_trend_5_20', 'log_volume_ratio']
        if 'atr_14' in df.columns:
            features.append('atr_14')
        
        return df[features].dropna()
