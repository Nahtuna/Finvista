"""
Custom Indicators Service - Unified MK-SL-SC Indicator System
Integrates MK, SL, and SC indicators for comprehensive analysis.
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.core.database import SessionLocal
from backend.core.utils import get_logger
from .mk_indicator import MKIndicator
from .sl_indicator import SLIndicator
from .sc_indicator import SCIndicator

indicator_logger = get_logger(__name__)


class CustomIndicatorService:
    """
    Unified service for MK-SL-SC indicator computation and integration.
    """
    
    def __init__(self, mk_atr_period: int = 14, mk_volume_period: int = 20,
                 sl_band_period: int = 20, sl_volume_period: int = 14,
                 sc_lookback: int = 20, sc_volume_multiplier: float = 2.0):
        """
        Initialize Custom Indicator Service.
        
        Args:
            mk_atr_period: ATR period for MK indicator
            mk_volume_period: Volume period for MK indicator
            sl_band_period: Band period for SL indicator
            sl_volume_period: Volume period for SL indicator
            sc_lookback: Lookback for SC indicator
            sc_volume_multiplier: Volume multiplier for SC indicator
        """
        self.mk_indicator = MKIndicator(atr_period=mk_atr_period, volume_period=mk_volume_period)
        self.sl_indicator = SLIndicator(band_period=sl_band_period, volume_period=sl_volume_period)
        self.sc_indicator = SCIndicator(lookback=sc_lookback, volume_multiplier=sc_volume_multiplier)
        indicator_logger.info("Initialized CustomIndicatorService with MK-SL-SC indicators")
    
    def compute_all_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute all custom indicators (MK-SL-SC).
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary containing all indicator computations
        """
        indicator_logger.info("Computing all custom indicators")
        
        # Validate input
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"DataFrame must contain columns: {required_columns}")
        
        # Compute MK indicator
        mk_values = self.mk_indicator.compute(df)
        
        # Compute SL indicator system
        sl_system = self.sl_indicator.compute(df)
        
        # Compute SC indicator system
        sc_system = self.sc_indicator.compute(df)
        
        # Combine into unified dictionary
        indicators = {
            'mk_indicator': mk_values.to_dict(),
            'sl_upper_band': sl_system['upper_band'].to_dict(),
            'sl_lower_band': sl_system['lower_band'].to_dict(),
            'sl_volume_normalized': sl_system['volume_normalized'].to_dict(),
            'sl_compression': sl_system['compression'].to_dict(),
            'sl_expansion': sl_system['expansion'].to_dict(),
            'sl_reversals': sl_system['reversals'].to_dict(),
            'sc_extreme_selling': sc_system['extreme_selling'].to_dict(),
            'sc_support_breach': sc_system['support_breach'].to_dict(),
            'sc_resistance_breakthrough': sc_system['resistance_breakthrough'].to_dict(),
            'sc_signals': sc_system['signals'].to_dict(),
            'sc_intensity': sc_system['intensity'].to_dict()
        }
        
        indicator_logger.info(f"Computed {len(indicators)} indicator types for {len(df)} bars")
        return indicators
    
    def analyze_divergence(self, df: pd.DataFrame, mk_values: pd.Series, price: pd.Series = None) -> Dict[str, Any]:
        """
        Analyze divergence between MK indicator and price.
        
        Divergence occurs when indicator and price move in opposite directions,
        often signaling potential reversals.
        
        Args:
            df: DataFrame with OHLC data
            mk_values: MK indicator values
            price: Price series (defaults to close)
            
        Returns:
            Dictionary with divergence analysis results
        """
        if price is None:
            price = df['close']
        
        # Calculate trends
        mk_trend = mk_values.diff()
        price_trend = price.diff()
        
        # Bullish divergence: price makes lower low, MK makes higher low
        bullish_divergence = pd.Series(False, index=df.index)
        for i in range(10, len(df)):
            if price_trend.iloc[i-10:i].sum() < 0 and mk_trend.iloc[i-10:i].sum() > 0:
                bullish_divergence.iloc[i] = True
        
        # Bearish divergence: price makes higher high, MK makes lower high
        bearish_divergence = pd.Series(False, index=df.index)
        for i in range(10, len(df)):
            if price_trend.iloc[i-10:i].sum() > 0 and mk_trend.iloc[i-10:i].sum() < 0:
                bearish_divergence.iloc[i] = True
        
        indicator_logger.info(f"Detected divergence: {bullish_divergence.sum()} bullish, {bearish_divergence.sum()} bearish")
        
        return {
            'bullish_divergence': bullish_divergence.to_dict(),
            'bearish_divergence': bearish_divergence.to_dict()
        }
    
    def generate_combined_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate combined trading signals from all indicators.
        
        Combines MK, SL, and SC signals into a unified signal generation system.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Series of combined signals
        """
        # Compute individual indicators
        mk_values = self.mk_indicator.compute(df)
        sl_system = self.sl_indicator.compute(df)
        sc_system = self.sc_indicator.compute(df)
        
        # Get individual signals
        mk_signals = self.mk_indicator.get_signals(mk_values)
        sl_reversals = sl_system['reversals']
        sc_signals = sc_system['signals']
        
        # Combined signal logic
        combined = pd.Series(0, index=df.index)
        
        # Buy signal: MK > 0.5 OR SL bullish reversal OR SC buy signal
        combined[(mk_signals == 1) | (sl_reversals == 1) | (sc_signals == 1)] = 1
        
        # Sell signal: MK < -0.5 OR SL bearish reversal OR SC sell signal
        combined[(mk_signals == -1) | (sl_reversals == -1) | (sc_signals == -1)] = -1
        
        buy_count = (combined == 1).sum()
        sell_count = (combined == -1).sum()
        
        indicator_logger.info(f"Generated combined signals: {buy_count} buy, {sell_count} sell")
        return combined
    
    def save_indicators_to_db(self, symbol: str, date: str, indicators: Dict[str, Any]) -> bool:
        """
        Save custom indicators to database (if implemented).
        
        Args:
            symbol: Symbol name
            date: Date string (YYYY-MM-DD)
            indicators: Dictionary of indicator values
            
        Returns:
            True if successful, False otherwise
        """
        # Placeholder for database integration
        # Could be implemented similar to SMC service
        indicator_logger.info(f"Indicators saved for {symbol} on {date} (placeholder)")
        return True
    
    def multi_timeframe_analysis(self, df_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Perform multi-timeframe analysis.
        
        Analyzes indicators across multiple timeframes for confirmation.
        
        Args:
            df_dict: Dictionary of DataFrames for different timeframes
            
        Returns:
            Dictionary with multi-timeframe analysis results
        """
        mtf_results = {}
        
        for timeframe, df in df_dict.items():
            try:
                indicators = self.compute_all_indicators(df)
                mtf_results[timeframe] = {
                    'mk_strength': np.mean(list(indicators['mk_indicator'].values())),
                    'sl_phase': 'compression' if np.mean(list(indicators['sl_compression'].values())) > 0.5 else 'expansion',
                    'sc_intensity': np.mean(list(indicators['sc_intensity'].values()))
                }
            except Exception as e:
                indicator_logger.error(f"Error in {timeframe} analysis: {e}")
                mtf_results[timeframe] = None
        
        indicator_logger.info(f"Multi-timeframe analysis completed for {len(df_dict)} timeframes")
        return mtf_results
    
    def get_indicator_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get summary statistics for all indicators.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with summary statistics
        """
        indicators = self.compute_all_indicators(df)
        
        # Convert to Series for easier analysis
        mk_values = pd.Series(indicators['mk_indicator'])
        
        summary = {
            'mk_indicator': {
                'mean': float(mk_values.mean()),
                'std': float(mk_values.std()),
                'min': float(mk_values.min()),
                'max': float(mk_values.max()),
                'current': float(mk_values.iloc[-1])
            },
            'sl_phase': 'compression' if np.mean(list(indicators['sl_compression'].values())) > 0.5 else 'expansion',
            'sc_status': 'extreme_selling' if indicators['sc_extreme_selling'].iloc[-1] else 'normal'
        }
        
        indicator_logger.info("Generated indicator summary")
        return summary
