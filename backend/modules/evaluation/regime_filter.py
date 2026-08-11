"""
Regime-Based Signal Filter - Market Regime Aware Signal Filtering
Implements signal filtering based on market regime to improve signal quality.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from backend.core.utils import get_logger

regime_logger = get_logger(__name__)


class RegimeSignalFilter:
    """
    Filter signals based on market regime to improve signal quality.
    
    Regimes:
    - Bull: Trending up - favor long signals, reduce short signals
    - Bear: Trending down - favor short signals, reduce long signals
    - Neutral: Sideways - reduce all signals
    - Volatile: High volatility - reduce position sizes
    """
    
    def __init__(self, regime_lookback: int = 20, volatility_threshold: float = 0.02):
        """
        Initialize Regime Signal Filter.
        
        Args:
            regime_lookback: Lookback period for regime detection
            volatility_threshold: Volatility threshold for volatile regime
        """
        self.regime_lookback = regime_lookback
        self.volatility_threshold = volatility_threshold
        regime_logger.info(f"Initialized RegimeSignalFilter with lookback={regime_lookback}")
    
    def detect_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect market regime based on price action.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Series of regime labels
        """
        regimes = pd.Series('neutral', index=df.index)
        
        # Calculate trend indicators
        sma_short = df['close'].rolling(10).mean()
        sma_long = df['close'].rolling(30).mean()
        
        # Calculate volatility
        returns = df['close'].pct_change()
        volatility = returns.rolling(self.regime_lookback).std()
        
        for i in range(len(df)):
            if i < self.regime_lookback:
                regimes.iloc[i] = 'neutral'
                continue
            
            # Check volatility
            if volatility.iloc[i] > self.volatility_threshold:
                regimes.iloc[i] = 'volatile'
                continue
            
            # Check trend
            if sma_short.iloc[i] > sma_long.iloc[i]:
                if df['close'].iloc[i] > sma_short.iloc[i]:
                    regimes.iloc[i] = 'bull'
                else:
                    regimes.iloc[i] = 'neutral'
            elif sma_short.iloc[i] < sma_long.iloc[i]:
                if df['close'].iloc[i] < sma_short.iloc[i]:
                    regimes.iloc[i] = 'bear'
                else:
                    regimes.iloc[i] = 'neutral'
            else:
                regimes.iloc[i] = 'neutral'
        
        regime_logger.info(f"Detected regimes: {regimes.value_counts().to_dict()}")
        return regimes
    
    def filter_signals(self, signals: pd.Series, regimes: pd.Series) -> pd.Series:
        """
        Filter signals based on regime.
        
        Args:
            signals: Series of trading signals
            regimes: Series of regime labels
            
        Returns:
            Series of filtered signals
        """
        filtered_signals = signals.copy()
        
        for i in range(len(signals)):
            regime = regimes.iloc[i]
            signal = signals.iloc[i]
            
            if regime == 'bull':
                # Reduce short signals in bull market
                if signal == -1:
                    filtered_signals.iloc[i] = 0
            
            elif regime == 'bear':
                # Reduce long signals in bear market
                if signal == 1:
                    filtered_signals.iloc[i] = 0
            
            elif regime == 'neutral':
                # Reduce all signals in neutral market
                if signal != 0:
                    filtered_signals.iloc[i] = 0
            
            elif regime == 'volatile':
                # Reduce all signals in volatile market
                if signal != 0:
                    filtered_signals.iloc[i] = 0
        
        original_count = (signals != 0).sum()
        filtered_count = (filtered_signals != 0).sum()
        
        regime_logger.info(f"Filtered signals: {original_count} -> {filtered_count}")
        return filtered_signals
    
    def adjust_position_sizes(self, signals: pd.Series, regimes: pd.Series, 
                            base_position_size: float = 1.0) -> pd.Series:
        """
        Adjust position sizes based on regime.
        
        Args:
            signals: Series of trading signals
            regimes: Series of regime labels
            base_position_size: Base position size multiplier
            
        Returns:
            Series of position size multipliers
        """
        position_multipliers = pd.Series(1.0, index=signals.index)
        
        for i in range(len(signals)):
            regime = regimes.iloc[i]
            signal = signals.iloc[i]
            
            if signal == 0:
                position_multipliers.iloc[i] = 0
                continue
            
            if regime == 'bull' and signal == 1:
                position_multipliers.iloc[i] = base_position_size * 1.2  # Increase long position
            elif regime == 'bear' and signal == -1:
                position_multipliers.iloc[i] = base_position_size * 1.2  # Increase short position
            elif regime == 'neutral':
                position_multipliers.iloc[i] = base_position_size * 0.5  # Reduce position
            elif regime == 'volatile':
                position_multipliers.iloc[i] = base_position_size * 0.3  # Significantly reduce position
        
        regime_logger.info("Adjusted position sizes based on regime")
        return position_multipliers
    
    def get_regime_confidence(self, regimes: pd.Series) -> Dict[str, float]:
        """
        Get confidence score for each regime.
        
        Args:
            regimes: Series of regime labels
            
        Returns:
            Dictionary with regime confidence scores
        """
        regime_counts = regimes.value_counts()
        total = len(regimes)
        
        confidence = {}
        for regime in ['bull', 'bear', 'neutral', 'volatile']:
            confidence[regime] = regime_counts.get(regime, 0) / total
        
        regime_logger.info(f"Regime confidence: {confidence}")
        return confidence
