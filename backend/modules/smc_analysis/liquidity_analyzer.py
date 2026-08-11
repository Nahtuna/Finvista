"""
Liquidity Analyzer - BSL/SSL Sweep Detection
Implements buy-side and sell-side liquidity sweep detection for SMC analysis.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from backend.core.utils import get_logger

smc_logger = get_logger(__name__)


class LiquidityAnalyzer:
    """
    Detects liquidity sweeps (BSL - Buy Side Liquidity, SSL - Sell Side Liquidity).
    
    Liquidity sweeps occur when price briefly exceeds a pivot level (liquidity pool)
    and then reverses, indicating institutional order execution.
    """
    
    def __init__(self, lookback: int = 5, volume_multiplier: float = 1.5):
        """
        Initialize LiquidityAnalyzer.
        
        Args:
            lookback: Number of bars to check after pivot for sweep
            volume_multiplier: Volume threshold multiplier for sweep confirmation
        """
        self.lookback = lookback
        self.volume_multiplier = volume_multiplier
        smc_logger.info(f"Initialized LiquidityAnalyzer with lookback={lookback}, volume_multiplier={volume_multiplier}")
    
    def detect_bsl_sweeps(self, df: pd.DataFrame, pivot_highs: pd.Series) -> pd.Series:
        """
        Detect buy-side liquidity sweeps (price sweeps above pivot highs).
        
        Args:
            df: DataFrame with 'high', 'low', 'volume' columns
            pivot_highs: Series indicating pivot high locations
            
        Returns:
            Series of booleans indicating BSL sweep locations
        """
        if not all(col in df.columns for col in ['high', 'low', 'volume']):
            raise ValueError("DataFrame must contain 'high', 'low', 'volume' columns")
        
        sweeps = pd.Series(False, index=df.index)
        volume_ma = df['volume'].rolling(20).mean()
        
        for i in range(len(df)):
            if pivot_highs.iloc[i]:
                pivot_high = df['high'].iloc[i]
                
                # Check next lookback bars for sweep
                for j in range(i + 1, min(i + self.lookback + 1, len(df))):
                    if df['high'].iloc[j] > pivot_high:
                        # Price swept above pivot high
                        # Check for volume spike and reversal (handle NaN in volume_ma)
                        vol_ma_val = volume_ma.iloc[j]
                        if pd.notna(vol_ma_val) and df['volume'].iloc[j] > vol_ma_val * self.volume_multiplier:
                            if df['close'].iloc[j] < df['high'].iloc[j]:
                                sweeps.iloc[j] = True
                                break
        
        smc_logger.info(f"Detected {sweeps.sum()} BSL sweeps out of {len(df)} bars")
        return sweeps
    
    def detect_ssl_sweeps(self, df: pd.DataFrame, pivot_lows: pd.Series) -> pd.Series:
        """
        Detect sell-side liquidity sweeps (price sweeps below pivot lows).
        
        Args:
            df: DataFrame with 'high', 'low', 'volume' columns
            pivot_lows: Series indicating pivot low locations
            
        Returns:
            Series of booleans indicating SSL sweep locations
        """
        if not all(col in df.columns for col in ['high', 'low', 'volume']):
            raise ValueError("DataFrame must contain 'high', 'low', 'volume' columns")
        
        sweeps = pd.Series(False, index=df.index)
        volume_ma = df['volume'].rolling(20).mean()
        
        for i in range(len(df)):
            if pivot_lows.iloc[i]:
                pivot_low = df['low'].iloc[i]
                
                # Check next lookback bars for sweep
                for j in range(i + 1, min(i + self.lookback + 1, len(df))):
                    if df['low'].iloc[j] < pivot_low:
                        # Price swept below pivot low
                        # Check for volume spike and reversal (handle NaN in volume_ma)
                        vol_ma_val = volume_ma.iloc[j]
                        if pd.notna(vol_ma_val) and df['volume'].iloc[j] > vol_ma_val * self.volume_multiplier:
                            if df['close'].iloc[j] > df['low'].iloc[j]:
                                sweeps.iloc[j] = True
                                break
        
        smc_logger.info(f"Detected {sweeps.sum()} SSL sweeps out of {len(df)} bars")
        return sweeps
    
    def detect_all_sweeps(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Detect both BSL and SSL sweeps.
        
        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            Tuple of (bsl_sweeps, ssl_sweeps) Series
        """
        bsl_sweeps = self.detect_bsl_sweeps(df, pivot_highs)
        ssl_sweeps = self.detect_ssl_sweeps(df, pivot_lows)
        
        return bsl_sweeps, ssl_sweeps
    
    def volume_spike_detection(self, df: pd.DataFrame, multiplier: float = 2.0) -> pd.Series:
        """
        Detect volume spikes using rolling average.
        
        Args:
            df: DataFrame with 'volume' column
            multiplier: Volume threshold multiplier
            
        Returns:
            Series of booleans indicating volume spike locations
        """
        if 'volume' not in df.columns:
            raise ValueError("DataFrame must contain 'volume' column")
        
        volume_ma = df['volume'].rolling(20).mean()
        spikes = df['volume'] > volume_ma * multiplier
        
        smc_logger.info(f"Detected {spikes.sum()} volume spikes out of {len(df)} bars")
        return spikes
    
    def track_liquidity_levels(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> pd.DataFrame:
        """
        Track and update liquidity levels based on pivots.
        
        Args:
            df: DataFrame with OHLC data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            DataFrame with liquidity level information
        """
        liquidity_data = []
        
        for i in range(len(df)):
            if pivot_highs.iloc[i]:
                liquidity_data.append({
                    'date': df.index[i],
                    'type': 'buy_side',
                    'level': df['high'].iloc[i],
                    'swept': False
                })
            elif pivot_lows.iloc[i]:
                liquidity_data.append({
                    'date': df.index[i],
                    'type': 'sell_side',
                    'level': df['low'].iloc[i],
                    'swept': False
                })
        
        liquidity_df = pd.DataFrame(liquidity_data)
        
        if not liquidity_df.empty:
            liquidity_df.set_index('date', inplace=True)
        
        smc_logger.info(f"Tracked {len(liquidity_df)} liquidity levels")
        return liquidity_df
    
    def optimize_lookback(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> int:
        """
        Optimize lookback parameter for sweep detection.
        
        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            Optimal lookback size
        """
        best_lookback = self.lookback
        best_score = 0
        
        for lookback in range(3, 11):
            analyzer = LiquidityAnalyzer(lookback=lookback)
            bsl_sweeps = analyzer.detect_bsl_sweeps(df, pivot_highs)
            ssl_sweeps = analyzer.detect_ssl_sweeps(df, pivot_lows)
            
            # Score based on reasonable number of sweeps
            total_sweeps = bsl_sweeps.sum() + ssl_sweeps.sum()
            ideal_sweeps = len(df) // 50  # Roughly 2% of bars
            score = 1 - abs(total_sweeps - ideal_sweeps) / ideal_sweeps
            
            if score > best_score:
                best_score = score
                best_lookback = lookback
        
        smc_logger.info(f"Optimized lookback from {self.lookback} to {best_lookback} (score: {best_score:.3f})")
        return best_lookback
