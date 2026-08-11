"""
Pattern Detector - FVG and Order Block Detection
Implements Fair Value Gap and Order Block detection for SMC analysis.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from backend.core.utils import get_logger

smc_logger = get_logger(__name__)


class PatternDetector:
    """
    Detects advanced SMC patterns: Fair Value Gaps (FVG) and Order Blocks.
    
    FVG: Price gaps between candles indicating institutional activity
    Order Blocks: Price zones where institutional orders are believed to be located
    """
    
    def __init__(self, min_gap_size: float = 0.001, volume_threshold: float = 1.5):
        """
        Initialize PatternDetector.
        
        Args:
            min_gap_size: Minimum gap size as percentage of price
            volume_threshold: Volume multiplier for Order Block detection
        """
        self.min_gap_size = min_gap_size
        self.volume_threshold = volume_threshold
        smc_logger.info(f"Initialized PatternDetector with min_gap_size={min_gap_size}, volume_threshold={volume_threshold}")
    
    def detect_fvg(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect Fair Value Gaps (FVG).
        
        FVG occurs when there's a gap between the high of candle i-1 and low of candle i+1
        (bullish) or between the low of candle i-1 and high of candle i+1 (bearish).
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            
        Returns:
            List of FVG events with date, type, high, low
        """
        if not all(col in df.columns for col in ['high', 'low', 'close']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close' columns")
        
        fvg_data = []
        
        for i in range(1, len(df) - 1):
            # Bullish FVG: candle i-1 high < candle i+1 low
            if df['high'].iloc[i-1] < df['low'].iloc[i+1]:
                gap_size = (df['low'].iloc[i+1] - df['high'].iloc[i-1]) / df['high'].iloc[i-1]
                
                if gap_size >= self.min_gap_size:
                    fvg_data.append({
                        'date': str(df.index[i]),
                        'type': 'bullish',
                        'high': float(df['low'].iloc[i+1]),
                        'low': float(df['high'].iloc[i-1]),
                        'gap_size': float(gap_size),
                        'fill_status': 'unfilled'
                    })
            
            # Bearish FVG: candle i-1 low > candle i+1 high
            if df['low'].iloc[i-1] > df['high'].iloc[i+1]:
                gap_size = (df['low'].iloc[i-1] - df['high'].iloc[i+1]) / df['low'].iloc[i-1]
                
                if gap_size >= self.min_gap_size:
                    fvg_data.append({
                        'date': str(df.index[i]),
                        'type': 'bearish',
                        'high': float(df['low'].iloc[i-1]),
                        'low': float(df['high'].iloc[i+1]),
                        'gap_size': float(gap_size),
                        'fill_status': 'unfilled'
                    })
        
        smc_logger.info(f"Detected {len(fvg_data)} FVG events")
        return fvg_data
    
    def assess_fvg_quality(self, fvg_list: List[Dict[str, Any]], df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Assess FVG quality based on volume and gap size.
        
        Args:
            fvg_list: List of FVG events
            df: DataFrame with volume data
            
        Returns:
            List of FVG events with quality scores
        """
        volume_ma = df['volume'].rolling(20).mean()
        
        for fvg in fvg_list:
            try:
                # Convert string date to datetime if needed
                date_str = fvg['date']
                if isinstance(date_str, str):
                    idx = df.index.get_loc(pd.to_datetime(date_str))
                else:
                    idx = df.index.get_loc(date_str)
                
                # Quality score based on gap size and volume
                volume_at_gap = df['volume'].iloc[idx]
                volume_ma_val = volume_ma.iloc[idx]
                volume_score = volume_at_gap / volume_ma_val if volume_ma_val > 0 else 1.0
                
                # Combined quality score
                fvg['quality_score'] = (fvg['gap_size'] * 100) * volume_score
                fvg['volume_score'] = float(volume_score)
                
                # Quality rating
                if fvg['quality_score'] > 2.0:
                    fvg['quality'] = 'high'
                elif fvg['quality_score'] > 1.0:
                    fvg['quality'] = 'medium'
                else:
                    fvg['quality'] = 'low'
                    
            except (KeyError, IndexError, ValueError):
                fvg['quality_score'] = 0.0
                fvg['volume_score'] = 0.0
                fvg['quality'] = 'unknown'
        
        high_quality = sum(1 for fvg in fvg_list if fvg.get('quality') == 'high')
        smc_logger.info(f"Assessed FVG quality: {high_quality} high quality out of {len(fvg_list)}")
        
        return fvg_list
    
    def check_fvg_fill(self, fvg_list: List[Dict[str, Any]], df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Check if FVG gaps have been filled by subsequent price action.
        
        Args:
            fvg_list: List of FVG events
            df: DataFrame with price data
            
        Returns:
            List of FVG events with updated fill status
        """
        for fvg in fvg_list:
            try:
                # Convert string date to datetime if needed
                date_str = fvg['date']
                if isinstance(date_str, str):
                    idx = df.index.get_loc(pd.to_datetime(date_str))
                else:
                    idx = df.index.get_loc(date_str)
                
                # Check subsequent bars for fill
                for j in range(idx + 1, len(df)):
                    if fvg['type'] == 'bullish':
                        # Bullish FVG filled if price goes below gap low
                        if df['low'].iloc[j] <= fvg['low']:
                            fvg['fill_status'] = 'filled'
                            fvg['fill_date'] = str(df.index[j])
                            break
                    else:  # bearish
                        # Bearish FVG filled if price goes above gap high
                        if df['high'].iloc[j] >= fvg['high']:
                            fvg['fill_status'] = 'filled'
                            fvg['fill_date'] = str(df.index[j])
                            break
                
                if fvg['fill_status'] == 'unfilled':
                    fvg['fill_status'] = 'unfilled'
                    fvg['fill_date'] = None
                    
            except (KeyError, IndexError, ValueError):
                fvg['fill_status'] = 'unknown'
                fvg['fill_date'] = None
        
        filled = sum(1 for fvg in fvg_list if fvg.get('fill_status') == 'filled')
        smc_logger.info(f"FVG fill status: {filled} filled out of {len(fvg_list)}")
        
        return fvg_list
    
    def detect_order_blocks(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> List[Dict[str, Any]]:
        """
        Detect Order Blocks at pivot points.
        
        Order Blocks are the last opposing candle before a significant move,
        typically characterized by high volume and aggressive price action.
        
        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            List of Order Block events
        """
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            raise ValueError("DataFrame must contain OHLCV columns")
        
        volume_ma = df['volume'].rolling(20).mean()
        ob_data = []
        
        # Detect bearish Order Blocks at pivot highs
        for i in range(len(df)):
            if pivot_highs.iloc[i]:
                if i > 0:
                    # Check candle before pivot high
                    prev_candle = df.iloc[i-1]
                    
                    # Criteria for bearish OB: high volume, bearish candle
                    if (prev_candle['close'] < prev_candle['open'] and  # Bearish candle
                        prev_candle['volume'] > volume_ma.iloc[i-1] * self.volume_threshold):
                        
                        ob_data.append({
                            'date': str(df.index[i-1]),
                            'type': 'bearish',
                            'high': float(prev_candle['high']),
                            'low': float(prev_candle['low']),
                            'close': float(prev_candle['close']),
                            'volume': float(prev_candle['volume']),
                            'volume_ratio': float(prev_candle['volume'] / volume_ma.iloc[i-1]),
                            'retest_status': 'untested'
                        })
        
        # Detect bullish Order Blocks at pivot lows
        for i in range(len(df)):
            if pivot_lows.iloc[i]:
                if i > 0:
                    # Check candle before pivot low
                    prev_candle = df.iloc[i-1]
                    
                    # Criteria for bullish OB: high volume, bullish candle
                    if (prev_candle['close'] > prev_candle['open'] and  # Bullish candle
                        prev_candle['volume'] > volume_ma.iloc[i-1] * self.volume_threshold):
                        
                        ob_data.append({
                            'date': str(df.index[i-1]),
                            'type': 'bullish',
                            'high': float(prev_candle['high']),
                            'low': float(prev_candle['low']),
                            'close': float(prev_candle['close']),
                            'volume': float(prev_candle['volume']),
                            'volume_ratio': float(prev_candle['volume'] / volume_ma.iloc[i-1]),
                            'retest_status': 'untested'
                        })
        
        smc_logger.info(f"Detected {len(ob_data)} Order Blocks")
        return ob_data
    
    def detect_ob_retest(self, ob_list: List[Dict[str, Any]], df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect Order Block retests.
        
        Args:
            ob_list: List of Order Block events
            df: DataFrame with price data
            
        Returns:
            List of Order Block events with retest status
        """
        for ob in ob_list:
            try:
                # Convert string date to datetime if needed
                date_str = ob['date']
                if isinstance(date_str, str):
                    idx = df.index.get_loc(pd.to_datetime(date_str))
                else:
                    idx = df.index.get_loc(date_str)
                
                # Check subsequent bars for retest
                for j in range(idx + 1, len(df)):
                    if ob['type'] == 'bearish':
                        # Bearish OB retest if price approaches OB high
                        if df['high'].iloc[j] >= ob['low'] and df['high'].iloc[j] <= ob['high']:
                            ob['retest_status'] = 'retested'
                            ob['retest_date'] = str(df.index[j])
                            break
                    else:  # bullish
                        # Bullish OB retest if price approaches OB low
                        if df['low'].iloc[j] >= ob['low'] and df['low'].iloc[j] <= ob['high']:
                            ob['retest_status'] = 'retested'
                            ob['retest_date'] = str(df.index[j])
                            break
                
                if ob['retest_status'] == 'untested':
                    ob['retest_status'] = 'untested'
                    ob['retest_date'] = None
                    
            except (KeyError, IndexError, ValueError):
                ob['retest_status'] = 'unknown'
                ob['retest_date'] = None
        
        retested = sum(1 for ob in ob_list if ob.get('retest_status') == 'retested')
        smc_logger.info(f"OB retest status: {retested} retested out of {len(ob_list)}")
        
        return ob_list
    
    def optimize_parameters(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> tuple:
        """
        Optimize FVG and OB detection parameters.
        
        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            Tuple of (optimal_min_gap_size, optimal_volume_threshold)
        """
        best_gap_size = self.min_gap_size
        best_volume_threshold = self.volume_threshold
        best_score = 0
        
        for gap_size in [0.0005, 0.001, 0.002, 0.005]:
            for vol_thresh in [1.2, 1.5, 2.0, 2.5]:
                detector = PatternDetector(
                    min_gap_size=gap_size,
                    volume_threshold=vol_thresh
                )
                fvg_list = detector.detect_fvg(df)
                ob_list = detector.detect_order_blocks(df, pivot_highs, pivot_lows)
                
                # Score based on reasonable number of patterns
                total_patterns = len(fvg_list) + len(ob_list)
                ideal_patterns = len(df) // 20  # Roughly 5% of bars
                score = 1 - abs(total_patterns - ideal_patterns) / ideal_patterns
                
                if score > best_score:
                    best_score = score
                    best_gap_size = gap_size
                    best_volume_threshold = vol_thresh
        
        smc_logger.info(f"Optimized parameters: min_gap_size={best_gap_size}, volume_threshold={best_volume_threshold} (score: {best_score:.3f})")
        return best_gap_size, best_volume_threshold
