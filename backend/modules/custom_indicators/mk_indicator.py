"""
MK Indicator - Volume-Weighted Momentum Indicator
Implements the MK (Market Key) indicator for momentum analysis.
"""

import pandas as pd
import numpy as np
from typing import Optional
from backend.core.utils import get_logger

indicator_logger = get_logger(__name__)


class MKIndicator:
    """
    MK Indicator - Volume-Weighted Momentum with Volatility Adjustment.
    
    Combines volume-weighted price momentum with ATR volatility adjustment,
    normalized using Z-score and bounded with tanh function.
    """
    
    def __init__(self, atr_period: int = 14, volume_period: int = 20):
        """
        Initialize MK Indicator.
        
        Args:
            atr_period: Period for ATR calculation
            volume_period: Period for volume moving average
        """
        self.atr_period = atr_period
        self.volume_period = volume_period
        indicator_logger.info(f"Initialized MKIndicator with atr_period={atr_period}, volume_period={volume_period}")
    
    def calculate_volume_weighted_momentum(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate volume-weighted momentum.
        
        Momentum is weighted by volume relative to its moving average,
        giving more importance to high-volume price movements.
        
        Args:
            df: DataFrame with 'close' and 'volume' columns
            
        Returns:
            Series of volume-weighted momentum values
        """
        if not all(col in df.columns for col in ['close', 'volume']):
            raise ValueError("DataFrame must contain 'close' and 'volume' columns")
        
        # Calculate price change
        price_change = df['close'].pct_change()
        
        # Calculate volume weight (volume relative to moving average)
        volume_ma = df['volume'].rolling(self.volume_period).mean()
        volume_weight = df['volume'] / volume_ma
        
        # Volume-weighted momentum
        momentum = price_change * volume_weight
        
        indicator_logger.info(f"Calculated volume-weighted momentum for {len(df)} bars")
        return momentum
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        ATR measures market volatility and is used to adjust momentum
        for different volatility regimes.
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            
        Returns:
            Series of ATR values
        """
        if not all(col in df.columns for col in ['high', 'low', 'close']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close' columns")
        
        # Calculate True Range
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Calculate ATR
        atr = tr.rolling(self.atr_period).mean()
        
        indicator_logger.info(f"Calculated ATR with period {self.atr_period}")
        return atr
    
    def apply_atr_adjustment(self, df: pd.DataFrame, momentum: pd.Series) -> pd.Series:
        """
        Adjust momentum by ATR volatility.
        
        Higher volatility requires stronger momentum to be significant.
        
        Args:
            df: DataFrame with OHLC data
            momentum: Series of momentum values
            
        Returns:
            Series of ATR-adjusted momentum
        """
        atr = self.calculate_atr(df)
        atr_normalized = atr / atr.rolling(self.volume_period).mean()
        
        # Adjust momentum by inverse of normalized ATR
        adjusted = momentum / atr_normalized
        
        indicator_logger.info("Applied ATR adjustment to momentum")
        return adjusted
    
    def z_score_normalization(self, series: pd.Series) -> pd.Series:
        """
        Normalize using Z-score.
        
        Standardizes the indicator to have mean 0 and standard deviation 1
        over the rolling window period.
        
        Args:
            series: Series to normalize
            
        Returns:
            Series of Z-score normalized values
        """
        mean = series.rolling(self.volume_period).mean()
        std = series.rolling(self.volume_period).std()
        
        # Avoid division by zero
        std = std.replace(0, 1)
        
        normalized = (series - mean) / std
        
        indicator_logger.info("Applied Z-score normalization")
        return normalized
    
    def tanh_scaling(self, series: pd.Series) -> pd.Series:
        """
        Apply tanh scaling to bound values between -1 and 1.
        
        Tanh function squashes extreme values while preserving the sign
        and relative magnitude.
        
        Args:
            series: Series to scale
            
        Returns:
            Series of tanh-scaled values
        """
        scaled = np.tanh(series)
        
        indicator_logger.info("Applied tanh scaling")
        return scaled
    
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute complete MK indicator.
        
        Combines all steps: volume-weighted momentum → ATR adjustment →
        Z-score normalization → tanh scaling.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Series of MK indicator values bounded between -1 and 1
        """
        # Step 1: Volume-weighted momentum
        momentum = self.calculate_volume_weighted_momentum(df)
        
        # Step 2: ATR adjustment
        adjusted = self.apply_atr_adjustment(df, momentum)
        
        # Step 3: Z-score normalization
        normalized = self.z_score_normalization(adjusted)
        
        # Step 4: Tanh scaling
        scaled = self.tanh_scaling(normalized)
        
        indicator_logger.info(f"Computed MK indicator for {len(df)} bars")
        return scaled
    
    def get_signals(self, mk_values: pd.Series, buy_threshold: float = 0.5, sell_threshold: float = -0.5) -> pd.Series:
        """
        Generate trading signals from MK indicator.
        
        Args:
            mk_values: Series of MK indicator values
            buy_threshold: Threshold for buy signal
            sell_threshold: Threshold for sell signal
            
        Returns:
            Series of signals (1=buy, -1=sell, 0=hold)
        """
        signals = pd.Series(0, index=mk_values.index)
        
        signals[mk_values > buy_threshold] = 1
        signals[mk_values < sell_threshold] = -1
        
        buy_count = (signals == 1).sum()
        sell_count = (signals == -1).sum()
        
        indicator_logger.info(f"Generated signals: {buy_count} buy, {sell_count} sell")
        return signals
    
    def optimize_parameters(self, df: pd.DataFrame) -> tuple:
        """
        Optimize ATR and volume period parameters.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (optimal_atr_period, optimal_volume_period)
        """
        best_atr_period = self.atr_period
        best_volume_period = self.volume_period
        best_score = 0
        
        for atr_period in [7, 14, 21, 28]:
            for volume_period in [10, 20, 30, 40]:
                indicator = MKIndicator(atr_period=atr_period, volume_period=volume_period)
                mk_values = indicator.compute(df)
                
                # Score based on signal distribution
                signals = indicator.get_signals(mk_values)
                signal_count = (signals != 0).sum()
                ideal_signals = len(df) // 20  # Roughly 5% signals
                score = 1 - abs(signal_count - ideal_signals) / ideal_signals
                
                if score > best_score:
                    best_score = score
                    best_atr_period = atr_period
                    best_volume_period = volume_period
        
        indicator_logger.info(f"Optimized parameters: atr_period={best_atr_period}, volume_period={best_volume_period} (score: {best_score:.3f})")
        return best_atr_period, best_volume_period
