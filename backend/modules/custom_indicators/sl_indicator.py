"""
SL Indicator - Dynamic Liquidity Bands Indicator
Implements the SL (Support/Liquidity) indicator for liquidity analysis.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from backend.core.utils import get_logger

indicator_logger = get_logger(__name__)


class SLIndicator:
    """
    SL Indicator - Dynamic Liquidity Bands with Volume Normalization.
    
    Creates dynamic bands based on price volatility and volume,
    detecting compression and expansion phases in the market.
    """
    
    def __init__(self, band_period: int = 20, volume_period: int = 14):
        """
        Initialize SL Indicator.
        
        Args:
            band_period: Period for band calculation
            volume_period: Period for volume moving average
        """
        self.band_period = band_period
        self.volume_period = volume_period
        indicator_logger.info(f"Initialized SLIndicator with band_period={band_period}, volume_period={volume_period}")
    
    def calculate_dynamic_bands(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate dynamic liquidity bands.
        
        Bands are based on rolling standard deviation of price,
        creating upper and lower bounds that adapt to volatility.
        
        Args:
            df: DataFrame with 'close' column
            
        Returns:
            Tuple of (upper_band, lower_band) Series
        """
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        # Calculate price statistics
        price_ma = df['close'].rolling(self.band_period).mean()
        price_std = df['close'].rolling(self.band_period).std()
        
        # Calculate bands (2 standard deviations)
        upper_band = price_ma + 2 * price_std
        lower_band = price_ma - 2 * price_std
        
        indicator_logger.info(f"Calculated dynamic bands with period {self.band_period}")
        return upper_band, lower_band
    
    def volume_normalization(self, df: pd.DataFrame) -> pd.Series:
        """
        Normalize volume relative to moving average.
        
        High volume indicates liquidity and institutional activity.
        
        Args:
            df: DataFrame with 'volume' column
            
        Returns:
            Series of normalized volume values
        """
        if 'volume' not in df.columns:
            raise ValueError("DataFrame must contain 'volume' column")
        
        volume_ma = df['volume'].rolling(self.volume_period).mean()
        
        # Avoid division by zero
        volume_ma = volume_ma.replace(0, 1)
        
        normalized = df['volume'] / volume_ma
        
        indicator_logger.info(f"Applied volume normalization with period {self.volume_period}")
        return normalized
    
    def detect_compression(self, df: pd.DataFrame, upper_band: pd.Series, lower_band: pd.Series) -> pd.Series:
        """
        Detect band compression phase.
        
        Compression occurs when the band width narrows significantly,
        indicating consolidation before a breakout.
        
        Args:
            df: DataFrame with OHLC data
            upper_band: Upper band series
            lower_band: Lower band series
            
        Returns:
            Series of compression signals
        """
        band_width = upper_band - lower_band
        bandwidth_ma = band_width.rolling(self.band_period).mean()
        
        # Compression: band width < 50% of average
        compression = band_width < bandwidth_ma * 0.5
        
        indicator_logger.info(f"Detected compression: {compression.sum()} bars out of {len(df)}")
        return compression
    
    def detect_expansion(self, df: pd.DataFrame, upper_band: pd.Series, lower_band: pd.Series) -> pd.Series:
        """
        Detect band expansion phase.
        
        Expansion occurs when the band width widens significantly,
        indicating increased volatility and trend strength.
        
        Args:
            df: DataFrame with OHLC data
            upper_band: Upper band series
            lower_band: Lower band series
            
        Returns:
            Series of expansion signals
        """
        band_width = upper_band - lower_band
        bandwidth_ma = band_width.rolling(self.band_period).mean()
        
        # Expansion: band width > 150% of average
        expansion = band_width > bandwidth_ma * 1.5
        
        indicator_logger.info(f"Detected expansion: {expansion.sum()} bars out of {len(df)}")
        return expansion
    
    def detect_band_reversal(self, df: pd.DataFrame, upper_band: pd.Series, lower_band: pd.Series) -> pd.Series:
        """
        Detect price reversal at band edges.
        
        Reversals at band edges often signal support/resistance bounces.
        
        Args:
            df: DataFrame with OHLC data
            upper_band: Upper band series
            lower_band: Lower band series
            
        Returns:
            Series of reversal signals
        """
        reversals = pd.Series(0, index=df.index)
        
        # Upper band reversal: price touches upper then closes below
        upper_touch = df['high'] >= upper_band
        for i in range(1, len(df)):
            if upper_touch.iloc[i-1] and df['close'].iloc[i] < df['open'].iloc[i]:
                reversals.iloc[i] = -1  # Bearish reversal
        
        # Lower band reversal: price touches lower then closes above
        lower_touch = df['low'] <= lower_band
        for i in range(1, len(df)):
            if lower_touch.iloc[i-1] and df['close'].iloc[i] > df['open'].iloc[i]:
                reversals.iloc[i] = 1  # Bullish reversal
        
        reversal_count = (reversals != 0).sum()
        indicator_logger.info(f"Detected band reversals: {reversal_count} out of {len(df)}")
        return reversals
    
    def compute(self, df: pd.DataFrame) -> dict:
        """
        Compute complete SL indicator system.
        
        Returns dictionary with bands, normalized volume, and signals.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary containing all SL indicator components
        """
        # Calculate bands
        upper_band, lower_band = self.calculate_dynamic_bands(df)
        
        # Volume normalization
        volume_norm = self.volume_normalization(df)
        
        # Detect phases
        compression = self.detect_compression(df, upper_band, lower_band)
        expansion = self.detect_expansion(df, upper_band, lower_band)
        
        # Detect reversals
        reversals = self.detect_band_reversal(df, upper_band, lower_band)
        
        indicator_logger.info(f"Computed SL indicator system for {len(df)} bars")
        
        return {
            'upper_band': upper_band,
            'lower_band': lower_band,
            'volume_normalized': volume_norm,
            'compression': compression,
            'expansion': expansion,
            'reversals': reversals
        }
    
    def optimize_parameters(self, df: pd.DataFrame) -> tuple:
        """
        Optimize band and volume period parameters.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (optimal_band_period, optimal_volume_period)
        """
        best_band_period = self.band_period
        best_volume_period = self.volume_period
        best_score = 0
        
        for band_period in [10, 20, 30, 40]:
            for volume_period in [10, 14, 21, 28]:
                indicator = SLIndicator(band_period=band_period, volume_period=volume_period)
                sl_system = indicator.compute(df)
                
                # Score based on reasonable compression/expansion ratio
                total_phases = sl_system['compression'].sum() + sl_system['expansion'].sum()
                ideal_phases = len(df) // 10  # Roughly 10% phase changes
                score = 1 - abs(total_phases - ideal_phases) / ideal_phases
                
                if score > best_score:
                    best_score = score
                    best_band_period = band_period
                    best_volume_period = volume_period
        
        indicator_logger.info(f"Optimized parameters: band_period={best_band_period}, volume_period={best_volume_period} (score: {best_score:.3f})")
        return best_band_period, best_volume_period
