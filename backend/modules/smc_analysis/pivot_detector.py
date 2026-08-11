"""
Pivot Detector - Swing High/Low Detection using Fractal Logic
Implements fractal-based pivot point detection for SMC analysis.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from backend.core.utils import get_logger

smc_logger = get_logger(__name__)


class PivotDetector:
    """
    Detects swing high and swing low points using fractal logic.
    
    A pivot high is the highest point in a local window.
    A pivot low is the lowest point in a local window.
    """
    
    def __init__(self, window: int = 5):
        """
        Initialize PivotDetector.
        
        Args:
            window: Number of bars on each side to check for pivot points
        """
        self.window = window
        smc_logger.info(f"Initialized PivotDetector with window={window}")
    
    def detect_pivot_highs(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect swing high points using fractal logic.
        
        Args:
            df: DataFrame with 'high' column
            
        Returns:
            Series of booleans indicating pivot high locations
        """
        if 'high' not in df.columns:
            raise ValueError("DataFrame must contain 'high' column")
        
        highs = df['high']
        pivots = pd.Series(False, index=df.index)
        
        for i in range(self.window, len(df) - self.window):
            window_highs = highs.iloc[i - self.window:i + self.window + 1]
            if highs.iloc[i] == window_highs.max():
                pivots.iloc[i] = True
        
        smc_logger.info(f"Detected {pivots.sum()} pivot highs out of {len(df)} bars")
        return pivots
    
    def detect_pivot_lows(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect swing low points using fractal logic.
        
        Args:
            df: DataFrame with 'low' column
            
        Returns:
            Series of booleans indicating pivot low locations
        """
        if 'low' not in df.columns:
            raise ValueError("DataFrame must contain 'low' column")
        
        lows = df['low']
        pivots = pd.Series(False, index=df.index)
        
        for i in range(self.window, len(df) - self.window):
            window_lows = lows.iloc[i - self.window:i + self.window + 1]
            if lows.iloc[i] == window_lows.min():
                pivots.iloc[i] = True
        
        smc_logger.info(f"Detected {pivots.sum()} pivot lows out of {len(df)} bars")
        return pivots
    
    def detect_all_pivots(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Detect both pivot highs and pivot lows.
        
        Args:
            df: DataFrame with 'high' and 'low' columns
            
        Returns:
            Tuple of (pivot_highs, pivot_lows) Series
        """
        pivot_highs = self.detect_pivot_highs(df)
        pivot_lows = self.detect_pivot_lows(df)
        
        return pivot_highs, pivot_lows
    
    def apply_fractal_filter(self, pivots: pd.Series, min_strength: float = 0.5) -> pd.Series:
        """
        Filter pivots based on fractal dimension/strength.
        
        Args:
            pivots: Series of pivot points
            min_strength: Minimum strength threshold (0-1)
            
        Returns:
            Filtered pivot Series
        """
        # Simple strength filter based on price movement
        filtered = pivots.copy()
        
        # Calculate strength based on price range
        strength = self._calculate_pivot_strength(pivots)
        filtered = filtered & (strength >= min_strength)
        
        smc_logger.info(f"Filtered {pivots.sum()} pivots to {filtered.sum()} with strength >= {min_strength}")
        return filtered
    
    def _calculate_pivot_strength(self, pivots: pd.Series) -> pd.Series:
        """
        Calculate strength of pivot points based on price movement.
        
        Args:
            pivots: Series of pivot points
            
        Returns:
            Series of strength values (0-1)
        """
        strength = pd.Series(0.0, index=pivots.index)
        
        # This method needs price data - for now return 1.0 for all pivots
        # In a full implementation, this would calculate strength based on
        # the price range around the pivot point
        strength = pivots.astype(float).fillna(0.0)
        
        return strength
    
    def optimize_window(self, df: pd.DataFrame, min_window: int = 3, max_window: int = 10) -> int:
        """
        Optimize window parameter for pivot detection.
        
        Args:
            df: DataFrame with OHLC data
            min_window: Minimum window to test
            max_window: Maximum window to test
            
        Returns:
            Optimal window size
        """
        best_window = self.window
        best_score = 0
        
        for window in range(min_window, max_window + 1):
            detector = PivotDetector(window=window)
            pivot_highs, pivot_lows = detector.detect_all_pivots(df)
            
            # Score based on number of pivots (not too many, not too few)
            total_pivots = pivot_highs.sum() + pivot_lows.sum()
            ideal_pivots = len(df) // (window * 2)
            score = 1 - abs(total_pivots - ideal_pivots) / ideal_pivots
            
            if score > best_score:
                best_score = score
                best_window = window
        
        smc_logger.info(f"Optimized window from {self.window} to {best_window} (score: {best_score:.3f})")
        return best_window
