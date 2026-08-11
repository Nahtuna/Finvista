"""
Wyckoff Analyzer - Wyckoff Event Detection
Implements Wyckoff schematics detection for SMC analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict
from backend.core.utils import get_logger

smc_logger = get_logger(__name__)


class WyckoffAnalyzer:
    """
    Detects Wyckoff market events and schematics.
    
    Wyckoff events include:
    - Selling Climax (SC): Extreme selling with high volume
    - Spring: Price dips below support then reverses
    - UTAD (Up-thrust After Distribution): False breakout
    - SOW (Sign of Weakness): Deterioration after distribution
    """
    
    def __init__(self, volume_percentile: float = 0.95, price_change_percentile: float = 0.10):
        """
        Initialize WyckoffAnalyzer.
        
        Args:
            volume_percentile: Volume threshold percentile for spike detection
            price_change_percentile: Price change threshold percentile
        """
        self.volume_percentile = volume_percentile
        self.price_change_percentile = price_change_percentile
        smc_logger.info(f"Initialized WyckoffAnalyzer with volume_percentile={volume_percentile}, price_change_percentile={price_change_percentile}")
    
    def detect_selling_climax(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect Selling Climax events.
        
        SC occurs when there's extreme selling pressure with unusually high volume,
        typically marking the end of a markdown phase.
        
        Args:
            df: DataFrame with 'close', 'volume' columns
            
        Returns:
            pd.Series of booleans indicating SC events
        """
        if not all(col in df.columns for col in ['close', 'volume']):
            raise ValueError("DataFrame must contain 'close', 'volume' columns")
        
        # Calculate thresholds
        volume_threshold = df['volume'].quantile(self.volume_percentile)
        price_change = df['close'].pct_change()
        price_decline_threshold = price_change.quantile(self.price_change_percentile)
        
        sc = pd.Series(False, index=df.index)
        
        for i in range(len(df)):
            # High volume + significant price decline
            if df['volume'].iloc[i] > volume_threshold:
                if price_change.iloc[i] < price_decline_threshold:
                    sc.iloc[i] = True
        
        smc_logger.info(f"Detected {sc.sum()} Selling Climax events out of {len(df)} bars")
        return sc
    
    def detect_spring(self, df: pd.DataFrame, pivot_lows: pd.Series) -> pd.Series:
        """
        Detect Spring events.
        
        Spring occurs when price briefly dips below a support level (pivot low)
        and then reverses, indicating institutional absorption of selling.
        
        Args:
            df: DataFrame with 'high', 'low', 'close', 'volume' columns
            pivot_lows: Series of pivot low locations
            
        Returns:
            pd.Series of booleans indicating Spring events
        """
        if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close', 'volume' columns")
        
        volume_ma = df['volume'].rolling(20).mean()
        spring = pd.Series(False, index=df.index)
        
        for i in range(len(df)):
            if pivot_lows.iloc[i]:
                pivot_low = df['low'].iloc[i]
                
                # Check next bars for spring
                for j in range(i + 1, min(i + 5, len(df))):
                    # Price dips below pivot low
                    if df['low'].iloc[j] < pivot_low:
                        # Then reverses with higher close
                        if df['close'].iloc[j] > df['open'].iloc[j]:
                            # Volume confirmation
                            if df['volume'].iloc[j] > volume_ma.iloc[j]:
                                spring.iloc[j] = True
                                break
        
        smc_logger.info(f"Detected {spring.sum()} Spring events out of {len(df)} bars")
        return spring
    
    def detect_utad(self, df: pd.DataFrame, pivot_highs: pd.Series) -> pd.Series:
        """
        Detect Up-thrust After Distribution (UTAD).
        
        UTAD occurs when price briefly breaks above a resistance level (pivot high)
        but fails to sustain the move, indicating weak buying interest.
        
        Args:
            df: DataFrame with 'high', 'low', 'close', 'volume' columns
            pivot_highs: Series of pivot high locations
            
        Returns:
            pd.Series of booleans indicating UTAD events
        """
        if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close', 'volume' columns")
        
        volume_ma = df['volume'].rolling(20).mean()
        utad = pd.Series(False, index=df.index)
        
        for i in range(len(df)):
            if pivot_highs.iloc[i]:
                pivot_high = df['high'].iloc[i]
                
                # Check next bars for up-thrust
                for j in range(i + 1, min(i + 5, len(df))):
                    # Price breaks above pivot high
                    if df['high'].iloc[j] > pivot_high:
                        # But fails to sustain (close below open or low)
                        if df['close'].iloc[j] < df['open'].iloc[j]:
                            # Low volume on breakout attempt
                            if df['volume'].iloc[j] < volume_ma.iloc[j]:
                                utad.iloc[j] = True
                                break
        
        smc_logger.info(f"Detected {utad.sum()} UTAD events out of {len(df)} bars")
        return utad
    
    def detect_sow(self, df: pd.DataFrame, pivot_highs: pd.Series) -> pd.Series:
        """
        Detect Sign of Weakness (SOW).
        
        SOW occurs after distribution phase, characterized by failed rallies
        and increasing selling pressure.
        
        Args:
            df: DataFrame with 'high', 'low', 'close', 'volume' columns
            pivot_highs: Series of pivot high locations
            
        Returns:
            pd.Series of booleans indicating SOW events
        """
        if not all(col in df.columns for col in ['high', 'low', 'close', 'volume']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close', 'volume' columns")
        
        volume_ma = df['volume'].rolling(20).mean()
        sow = pd.Series(False, index=df.index)
        
        for i in range(len(df)):
            if pivot_highs.iloc[i]:
                pivot_high = df['high'].iloc[i]
                
                # Check subsequent bars for failed rally
                for j in range(i + 1, min(i + 10, len(df))):
                    # Price fails to break pivot high
                    if df['high'].iloc[j] < pivot_high:
                        # With high volume (selling pressure)
                        if df['volume'].iloc[j] > volume_ma.iloc[j] * 1.2:
                            # And declining price
                            if df['close'].iloc[j] < df['close'].iloc[j-1]:
                                sow.iloc[j] = True
                                break
        
        smc_logger.info(f"Detected {sow.sum()} SOW events out of {len(df)} bars")
        return sow
    
    def detect_all_wyckoff_events(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> dict:
        """
        Detect all Wyckoff events.
        
        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            Dictionary with all Wyckoff event Series
        """
        sc = self.detect_selling_climax(df)
        spring = self.detect_spring(df, pivot_lows)
        utad = self.detect_utad(df, pivot_highs)
        sow = self.detect_sow(df, pivot_highs)
        
        events = {
            'selling_climax': sc,
            'spring': spring,
            'utad': utad,
            'sow': sow
        }
        
        smc_logger.info(f"Detected Wyckoff events: SC={sc.sum()}, Spring={spring.sum()}, UTAD={utad.sum()}, SOW={sow.sum()}")
        return events
    
    def analyze_wyckoff_phase(self, df: pd.DataFrame, wyckoff_events: dict) -> pd.Series:
        """
        Analyze current Wyckoff phase based on detected events.
        
        Args:
            df: DataFrame with price data
            wyckoff_events: Dictionary of Wyckoff event Series
            
        Returns:
            pd.Series indicating Wyckoff phase
        """
        phases = pd.Series('unknown', index=df.index)
        
        sc = wyckoff_events['selling_climax']
        spring = wyckoff_events['spring']
        utad = wyckoff_events['utad']
        sow = wyckoff_events['sow']
        
        current_phase = 'unknown'
        
        for i in range(len(df)):
            # Phase determination logic
            if sc.iloc[i]:
                current_phase = 'accumulation'
            elif spring.iloc[i]:
                current_phase = 'markup'
            elif utad.iloc[i]:
                current_phase = 'distribution'
            elif sow.iloc[i]:
                current_phase = 'markdown'
            
            phases.iloc[i] = current_phase
        
        smc_logger.info(f"Wyckoff phase analysis: {phases.value_counts().to_dict()}")
        return phases
    
    def optimize_parameters(self, df: pd.DataFrame, pivot_highs: pd.Series, pivot_lows: pd.Series) -> tuple:
        """
        Optimize Wyckoff detection parameters.
        
        Args:
            df: DataFrame with OHLCV data
            pivot_highs: Series of pivot high locations
            pivot_lows: Series of pivot low locations
            
        Returns:
            Tuple of (optimal_volume_percentile, optimal_price_change_percentile)
        """
        best_vol_percentile = self.volume_percentile
        best_price_percentile = self.price_change_percentile
        best_score = 0
        
        for vol_pct in [0.90, 0.95, 0.97, 0.99]:
            for price_pct in [0.03, 0.05, 0.07, 0.10]:
                analyzer = WyckoffAnalyzer(
                    volume_percentile=vol_pct,
                    price_change_percentile=price_pct
                )
                events = analyzer.detect_all_wyckoff_events(df, pivot_highs, pivot_lows)
                
                # Score based on reasonable number of events
                total_events = sum(events[event].sum() for event in events)
                ideal_events = len(df) // 50  # Roughly 2% of bars
                score = 1 - abs(total_events - ideal_events) / ideal_events
                
                if score > best_score:
                    best_score = score
                    best_vol_percentile = vol_pct
                    best_price_percentile = price_pct
        
        smc_logger.info(f"Optimized parameters: volume_percentile={best_vol_percentile}, price_change_percentile={best_price_percentile} (score: {best_score:.3f})")
        return best_vol_percentile, best_price_percentile
