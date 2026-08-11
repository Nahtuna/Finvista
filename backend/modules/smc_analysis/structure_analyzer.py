"""
Structure Analyzer - CHoCH and BOS Detection
Implements Change of Character and Break of Structure detection for SMC analysis.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from backend.core.utils import get_logger

smc_logger = get_logger(__name__)


class StructureAnalyzer:
    """
    Detects market structure changes (CHoCH - Change of Character, BOS - Break of Structure).
    
    CHoCH: Significant structure change with high volume
    BOS: Simple break of previous structure
    """
    
    def __init__(self, volume_threshold: float = 1.5, min_price_change: float = 0.01):
        """
        Initialize StructureAnalyzer.
        
        Args:
            volume_threshold: Volume multiplier for CHoCH confirmation
            min_price_change: Minimum price change percentage for structure break
        """
        self.volume_threshold = volume_threshold
        self.min_price_change = min_price_change
        smc_logger.info(f"Initialized StructureAnalyzer with volume_threshold={volume_threshold}, min_price_change={min_price_change}")
    
    def detect_choch(self, df: pd.DataFrame, pivot_highs: pd.Series) -> pd.Series:
        """
        Detect Change of Character (bullish).
        
        CHoCH occurs when price breaks a pivot high with increased volume,
        indicating a potential trend change.
        
        Args:
            df: DataFrame with 'high', 'low', 'close', 'volume' columns
            pivot_highs: Series indicating pivot high locations
            
        Returns:
            Series of booleans indicating CHoCH locations
        """
        if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close', 'volume' columns")
        
        choch = pd.Series(False, index=df.index)
        volume_ma = df['volume'].rolling(20).mean()
        
        for i in range(len(df) - 1):
            if pivot_highs.iloc[i]:
                pivot_high = df['high'].iloc[i]
                
                # Check if next bar breaks pivot high
                if df['high'].iloc[i + 1] > pivot_high:
                    # Check for volume confirmation (handle NaN in volume_ma)
                    vol_ma_val = volume_ma.iloc[i + 1]
                    if pd.notna(vol_ma_val) and df['volume'].iloc[i + 1] > vol_ma_val * self.volume_threshold:
                        # Check for price change threshold
                        price_change = (df['high'].iloc[i + 1] - pivot_high) / pivot_high
                        if price_change >= self.min_price_change:
                            choch.iloc[i + 1] = True
        
        smc_logger.info(f"Detected {choch.sum()} bullish CHoCH events out of {len(df)} bars")
        return choch
    
    def detect_choch_bearish(self, df: pd.DataFrame, pivot_lows: pd.Series) -> pd.Series:
        """
        Detect Change of Character (bearish).
        
        Args:
            df: DataFrame with 'high', 'low', 'close', 'volume' columns
            pivot_lows: Series indicating pivot low locations
            
        Returns:
            Series of booleans indicating bearish CHoCH locations
        """
        if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close', 'volume' columns")
        
        choch = pd.Series(False, index=df.index)
        volume_ma = df['volume'].rolling(20).mean()
        
        for i in range(len(df) - 1):
            if pivot_lows.iloc[i]:
                pivot_low = df['low'].iloc[i]
                
                # Check if next bar breaks pivot low
                if df['low'].iloc[i + 1] < pivot_low:
                    # Check for volume confirmation (handle NaN in volume_ma)
                    vol_ma_val = volume_ma.iloc[i + 1]
                    if pd.notna(vol_ma_val) and df['volume'].iloc[i + 1] > vol_ma_val * self.volume_threshold:
                        # Check for price change threshold
                        price_change = (pivot_low - df['low'].iloc[i + 1]) / pivot_low
                        if price_change >= self.min_price_change:
                            choch.iloc[i + 1] = True
        
        smc_logger.info(f"Detected {choch.sum()} bearish CHoCH events out of {len(df)} bars")
        return choch
    
    def detect_bos(self, df: pd.DataFrame, pivot_highs: pd.Series) -> pd.Series:
        """
        Detect Break of Structure (bullish).
        
        BOS is a simple break of previous pivot high without strong volume confirmation.
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            pivot_highs: Series indicating pivot high locations
            
        Returns:
            Series of booleans indicating BOS locations
        """
        if not all(col in df.columns for col in ['high', 'low', 'close']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close' columns")
        
        bos = pd.Series(False, index=df.index)
        
        for i in range(len(df) - 1):
            if pivot_highs.iloc[i]:
                pivot_high = df['high'].iloc[i]
                
                # Simple break of structure
                if df['high'].iloc[i + 1] > pivot_high:
                    bos.iloc[i + 1] = True
        
        smc_logger.info(f"Detected {bos.sum()} bullish BOS events out of {len(df)} bars")
        return bos
    
    def detect_bos_bearish(self, df: pd.DataFrame, pivot_lows: pd.Series) -> pd.Series:
        """
        Detect Break of Structure (bearish).
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            pivot_lows: Series indicating pivot low locations
            
        Returns:
            Series of booleans indicating bearish BOS locations
        """
        if not all(col in df.columns for col in ['high', 'low', 'close']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close' columns")
        
        bos = pd.Series(False, index=df.index)
        
        for i in range(len(df) - 1):
            if pivot_lows.iloc[i]:
                pivot_low = df['low'].iloc[i]
                
                # Simple break of structure
                if df['low'].iloc[i + 1] < pivot_low:
                    bos.iloc[i + 1] = True
        
        smc_logger.info(f"Detected {bos.sum()} bearish BOS events out of {len(df)} bars")
        return bos
    
    def distinguish_choch_bos(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Distinguish between CHoCH and BOS for both bullish and bearish.
        
        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            Tuple of (choch_bullish, choch_bearish, bos_bullish, bos_bearish) Series
        """
        choch_bullish = self.detect_choch(df, pivot_highs)
        choch_bearish = self.detect_choch_bearish(df, pivot_lows)
        bos_bullish = self.detect_bos(df, pivot_highs)
        bos_bearish = self.detect_bos_bearish(df, pivot_lows)
        
        # Remove CHoCH from BOS (CHoCH takes precedence)
        bos_bullish = bos_bullish & ~choch_bullish
        bos_bearish = bos_bearish & ~choch_bearish
        
        smc_logger.info(f"Distinguished: {choch_bullish.sum()} CHoCH bull, {choch_bearish.sum()} CHoCH bear, {bos_bullish.sum()} BOS bull, {bos_bearish.sum()} BOS bear")
        
        return choch_bullish, choch_bearish, bos_bullish, bos_bearish
    
    def analyze_trend_context(self, df: pd.DataFrame, choch_bullish: pd.Series, choch_bearish: pd.Series) -> pd.Series:
        """
        Analyze trend context based on CHoCH events.
        
        Args:
            df: DataFrame with OHLC data
            choch_bullish: Series of bullish CHoCH events
            choch_bearish: Series of bearish CHoCH events
            
        Returns:
            Series indicating trend direction (1=bullish, -1=bearish, 0=neutral)
        """
        trend = pd.Series(0, index=df.index)
        current_trend = 0
        
        for i in range(len(df)):
            if choch_bullish.iloc[i]:
                current_trend = 1
            elif choch_bearish.iloc[i]:
                current_trend = -1
            
            trend.iloc[i] = current_trend
        
        smc_logger.info(f"Trend analysis: {sum(trend == 1)} bullish, {sum(trend == -1)} bearish, {sum(trend == 0)} neutral")
        return trend
    
    def optimize_parameters(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> Tuple[float, float]:
        """
        Optimize volume threshold and min price change parameters.
        
        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            Tuple of (optimal_volume_threshold, optimal_min_price_change)
        """
        best_volume_threshold = self.volume_threshold
        best_min_price_change = self.min_price_change
        best_score = 0
        
        for vol_thresh in [1.2, 1.5, 2.0, 2.5]:
            for price_change in [0.005, 0.01, 0.015, 0.02]:
                analyzer = StructureAnalyzer(
                    volume_threshold=vol_thresh,
                    min_price_change=price_change
                )
                choch_bullish, choch_bearish, _, _ = analyzer.distinguish_choch_bos(df, pivot_highs, pivot_lows)
                
                # Score based on reasonable number of CHoCH events
                total_choch = choch_bullish.sum() + choch_bearish.sum()
                ideal_choch = len(df) // 100  # Roughly 1% of bars
                score = 1 - abs(total_choch - ideal_choch) / ideal_choch
                
                if score > best_score:
                    best_score = score
                    best_volume_threshold = vol_thresh
                    best_min_price_change = price_change
        
        smc_logger.info(f"Optimized parameters: volume_threshold={best_volume_threshold}, min_price_change={best_min_price_change} (score: {best_score:.3f})")
        return best_volume_threshold, best_min_price_change
