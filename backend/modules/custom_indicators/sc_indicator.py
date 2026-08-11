"""
SC Indicator - Extreme Selling Detection Indicator
Implements the SC (Selling Climax) indicator for selling pressure analysis.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from backend.core.utils import get_logger

indicator_logger = get_logger(__name__)


class SCIndicator:
    """
    SC Indicator - Extreme Selling Pressure Detection.
    
    Detects extreme selling pressure events with dynamic thresholds,
    combining volume spikes, price declines, and support level breaches.
    """
    
    def __init__(self, lookback: int = 20, volume_multiplier: float = 2.0):
        """
        Initialize SC Indicator.
        
        Args:
            lookback: Lookback period for threshold calculation
            volume_multiplier: Volume threshold multiplier
        """
        self.lookback = lookback
        self.volume_multiplier = volume_multiplier
        indicator_logger.info(f"Initialized SCIndicator with lookback={lookback}, volume_multiplier={volume_multiplier}")
    
    def detect_extreme_selling(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect extreme selling pressure based on volume and price.
        
        Extreme selling is characterized by:
        - Volume spike (above threshold)
        - Price decline (close below open)
        
        Args:
            df: DataFrame with 'close', 'volume' columns
            
        Returns:
            Series of extreme selling signals
        """
        if not all(col in df.columns for col in ['close', 'volume']):
            raise ValueError("DataFrame must contain 'close' and 'volume' columns")
        
        # Calculate volume threshold
        volume_ma = df['volume'].rolling(self.lookback).mean()
        volume_threshold = volume_ma * self.volume_multiplier
        
        # Detect volume spikes
        volume_spike = df['volume'] > volume_threshold
        
        # Detect price decline
        price_decline = df['close'] < df['open']
        
        # Extreme selling: both conditions met
        extreme_selling = volume_spike & price_decline
        
        indicator_logger.info(f"Detected extreme selling: {extreme_selling.sum()} bars out of {len(df)}")
        return extreme_selling
    
    def calculate_thresholds(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate dynamic upper and lower thresholds.
        
        Thresholds are based on recent price extremes to detect
        when price breaks out of normal range.
        
        Args:
            df: DataFrame with 'high', 'low' columns
            
        Returns:
            Tuple of (lower_threshold, upper_threshold) Series
        """
        if not all(col in df.columns for col in ['high', 'low']):
            raise ValueError("DataFrame must contain 'high' and 'low' columns")
        
        # Calculate rolling minimum and maximum
        lower_threshold = df['low'].rolling(self.lookback).min()
        upper_threshold = df['high'].rolling(self.lookback).max()
        
        indicator_logger.info(f"Calculated dynamic thresholds with lookback {self.lookback}")
        return lower_threshold, upper_threshold
    
    def detect_support_breach(self, df: pd.DataFrame, lower_threshold: pd.Series) -> pd.Series:
        """
        Detect support level breach.
        
        Support breach occurs when price goes below the rolling minimum,
        indicating potential breakdown.
        
        Args:
            df: DataFrame with 'low' column
            lower_threshold: Lower threshold series
            
        Returns:
            Series of support breach signals
        """
        support_breach = df['low'] < lower_threshold
        
        indicator_logger.info(f"Detected support breaches: {support_breach.sum()} bars out of {len(df)}")
        return support_breach
    
    def detect_resistance_breakthrough(self, df: pd.DataFrame, upper_threshold: pd.Series) -> pd.Series:
        """
        Detect resistance breakthrough.
        
        Resistance breakthrough occurs when price goes above the rolling maximum,
        indicating potential breakout.
        
        Args:
            df: DataFrame with 'high' column
            upper_threshold: Upper threshold series
            
        Returns:
            Series of resistance breakthrough signals
        """
        resistance_breakthrough = df['high'] > upper_threshold
        
        indicator_logger.info(f"Detected resistance breakthroughs: {resistance_breakthrough.sum()} bars out of {len(df)}")
        return resistance_breakthrough
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals from SC indicator.
        
        Signals are based on combination of extreme selling and support breaches.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Series of signals (1=buy, -1=sell, 0=hold)
        """
        # Detect components
        extreme_selling = self.detect_extreme_selling(df)
        lower_threshold, upper_threshold = self.calculate_thresholds(df)
        support_breach = self.detect_support_breach(df, lower_threshold)
        
        signals = pd.Series(0, index=df.index)
        
        # Sell signal: extreme selling + support breach
        for i in range(len(df)):
            if extreme_selling.iloc[i] and support_breach.iloc[i]:
                signals.iloc[i] = -1
        
        # Buy signal: price recovers after extreme selling
        for i in range(1, len(df)):
            if extreme_selling.iloc[i-1] and df['close'].iloc[i] > df['open'].iloc[i]:
                signals.iloc[i] = 1
        
        buy_count = (signals == 1).sum()
        sell_count = (signals == -1).sum()
        
        indicator_logger.info(f"Generated SC signals: {buy_count} buy, {sell_count} sell")
        return signals
    
    def calculate_selling_intensity(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate selling intensity score.
        
        Combines volume spike magnitude and price decline percentage
        into a single intensity score.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Series of selling intensity scores
        """
        # Volume spike magnitude
        volume_ma = df['volume'].rolling(self.lookback).mean()
        volume_ratio = df['volume'] / volume_ma
        
        # Price decline percentage
        price_change = df['close'].pct_change()
        price_decline = -price_change.where(price_change < 0, 0)
        
        # Combined intensity score
        intensity = volume_ratio * price_decline * 100
        
        indicator_logger.info("Calculated selling intensity scores")
        return intensity
    
    def compute(self, df: pd.DataFrame) -> dict:
        """
        Compute complete SC indicator system.
        
        Returns dictionary with all SC indicator components.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary containing all SC indicator components
        """
        # Calculate thresholds
        lower_threshold, upper_threshold = self.calculate_thresholds(df)
        
        # Detect components
        extreme_selling = self.detect_extreme_selling(df)
        support_breach = self.detect_support_breach(df, lower_threshold)
        resistance_breakthrough = self.detect_resistance_breakthrough(df, upper_threshold)
        
        # Generate signals
        signals = self.generate_signals(df)
        
        # Calculate intensity
        intensity = self.calculate_selling_intensity(df)
        
        indicator_logger.info(f"Computed SC indicator system for {len(df)} bars")
        
        return {
            'extreme_selling': extreme_selling,
            'support_breach': support_breach,
            'resistance_breakthrough': resistance_breakthrough,
            'signals': signals,
            'intensity': intensity,
            'lower_threshold': lower_threshold,
            'upper_threshold': upper_threshold
        }
    
    def optimize_parameters(self, df: pd.DataFrame) -> tuple:
        """
        Optimize lookback and volume multiplier parameters.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (optimal_lookback, optimal_volume_multiplier)
        """
        best_lookback = self.lookback
        best_volume_multiplier = self.volume_multiplier
        best_score = 0
        
        for lookback in [10, 20, 30, 40]:
            for vol_mult in [1.5, 2.0, 2.5, 3.0]:
                indicator = SCIndicator(lookback=lookback, volume_multiplier=vol_mult)
                sc_system = indicator.compute(df)
                
                # Score based on reasonable signal distribution
                signals = sc_system['signals']
                signal_count = (signals != 0).sum()
                ideal_signals = len(df) // 20  # Roughly 5% signals
                score = 1 - abs(signal_count - ideal_signals) / ideal_signals
                
                if score > best_score:
                    best_score = score
                    best_lookback = lookback
                    best_volume_multiplier = vol_mult
        
        indicator_logger.info(f"Optimized parameters: lookback={best_lookback}, volume_multiplier={best_volume_multiplier} (score: {best_score:.3f})")
        return best_lookback, best_volume_multiplier
