"""
SMC Analysis Service - Unified SMC Feature Extraction
Integrates pivot detection, liquidity analysis, and structure analysis.
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.core.database import SessionLocal, SMCFeatures
from backend.core.utils import get_logger
from .pivot_detector import PivotDetector
from .liquidity_analyzer import LiquidityAnalyzer
from .structure_analyzer import StructureAnalyzer
from .pattern_detector import PatternDetector
from .wyckoff_analyzer import WyckoffAnalyzer

smc_logger = get_logger(__name__)


class SMCAnalysisService:
    """
    Unified service for SMC feature extraction and database integration.
    """
    
    def __init__(self, pivot_window: int = 5, liquidity_lookback: int = 5):
        """
        Initialize SMC Analysis Service.
        
        Args:
            pivot_window: Window size for pivot detection
            liquidity_lookback: Lookback period for liquidity sweep detection
        """
        self.pivot_detector = PivotDetector(window=pivot_window)
        self.liquidity_analyzer = LiquidityAnalyzer(lookback=liquidity_lookback)
        self.structure_analyzer = StructureAnalyzer()
        self.pattern_detector = PatternDetector()
        self.wyckoff_analyzer = WyckoffAnalyzer()
        smc_logger.info("Initialized SMCAnalysisService with advanced pattern detection")
    
    def extract_all_features(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Extract all SMC features from OHLCV data.
        
        Args:
            df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
            symbol: Symbol name for the data
            
        Returns:
            Dictionary containing all SMC features
        """
        smc_logger.info(f"Extracting SMC features for {symbol}")
        
        # Validate input
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"DataFrame must contain columns: {required_columns}")
        
        # Extract pivot points
        pivot_highs, pivot_lows = self.pivot_detector.detect_all_pivots(df)
        
        # Extract liquidity sweeps
        bsl_sweeps, ssl_sweeps = self.liquidity_analyzer.detect_all_sweeps(df, pivot_highs, pivot_lows)
        
        # Extract structure changes
        choch_bullish, choch_bearish, bos_bullish, bos_bearish = self.structure_analyzer.distinguish_choch_bos(
            df, pivot_highs, pivot_lows
        )
        
        # Extract advanced patterns (FVG and Order Blocks)
        fvg_list = self.pattern_detector.detect_fvg(df)
        fvg_list = self.pattern_detector.assess_fvg_quality(fvg_list, df)
        fvg_list = self.pattern_detector.check_fvg_fill(fvg_list, df)
        
        ob_list = self.pattern_detector.detect_order_blocks(df, pivot_highs, pivot_lows)
        ob_list = self.pattern_detector.detect_ob_retest(ob_list, df)
        
        # Extract Wyckoff events
        wyckoff_events = self.wyckoff_analyzer.detect_all_wyckoff_events(df, pivot_highs, pivot_lows)
        
        # Convert Wyckoff events dict to JSON-serializable format
        wyckoff_json = {}
        for event_name, event_series in wyckoff_events.items():
            wyckoff_json[event_name] = self._series_to_json(event_series)
        
        # Convert Series to JSON-serializable format
        features = {
            'pivot_highs': self._series_to_json(pivot_highs),
            'pivot_lows': self._series_to_json(pivot_lows),
            'bsl_sweeps': self._series_to_json(bsl_sweeps),
            'ssl_sweeps': self._series_to_json(ssl_sweeps),
            'choch_bullish': self._series_to_json(choch_bullish),
            'choch_bearish': self._series_to_json(choch_bearish),
            'bos_bullish': self._series_to_json(bos_bullish),
            'bos_bearish': self._series_to_json(bos_bearish),
            'fvg': json.dumps(fvg_list),
            'order_blocks': json.dumps(ob_list),
            'wyckoff_events': json.dumps(wyckoff_json)
        }
        
        smc_logger.info(f"Extracted SMC features for {symbol}: {len(features)} feature types")
        return features
    
    def _series_to_json(self, series: pd.Series) -> str:
        """
        Convert pandas Series to JSON string.
        
        Args:
            series: pandas Series to convert
            
        Returns:
            JSON string representation
        """
        # Convert to list of indices where True
        true_indices = series[series].index.tolist()
        
        # Convert Timestamp objects to strings
        indices_str = [str(idx) if hasattr(idx, 'strftime') else idx for idx in true_indices]
        
        return json.dumps(indices_str)
    
    def save_features_to_db(self, symbol: str, date: str, features: Dict[str, Any]) -> bool:
        """
        Save SMC features to database.
        
        Args:
            symbol: Symbol name
            date: Date string (YYYY-MM-DD)
            features: Dictionary of SMC features
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = SessionLocal()
            
            # Check if record exists
            existing = session.query(SMCFeatures).filter(
                SMCFeatures.symbol == symbol,
                SMCFeatures.date == date
            ).first()
            
            if existing:
                # Update existing record
                existing.pivot_highs = features['pivot_highs']
                existing.pivot_lows = features['pivot_lows']
                existing.bsl_sweeps = features['bsl_sweeps']
                existing.ssl_sweeps = features['ssl_sweeps']
                existing.choch_bullish = features['choch_bullish']
                existing.choch_bearish = features['choch_bearish']
                existing.bos_bullish = features['bos_bullish']
                existing.bos_bearish = features['bos_bearish']
                existing.fvg = features['fvg']
                existing.order_blocks = features['order_blocks']
                existing.wyckoff_events = features['wyckoff_events']
                existing.updated_at = datetime.now(timezone.utc)
                smc_logger.info(f"Updated SMC features for {symbol} on {date}")
            else:
                # Create new record
                smc_record = SMCFeatures(
                    symbol=symbol,
                    date=date,
                    pivot_highs=features['pivot_highs'],
                    pivot_lows=features['pivot_lows'],
                    bsl_sweeps=features['bsl_sweeps'],
                    ssl_sweeps=features['ssl_sweeps'],
                    choch_bullish=features['choch_bullish'],
                    choch_bearish=features['choch_bearish'],
                    bos_bullish=features['bos_bullish'],
                    bos_bearish=features['bos_bearish'],
                    fvg=features['fvg'],
                    order_blocks=features['order_blocks'],
                    wyckoff_events=features['wyckoff_events']
                )
                session.add(smc_record)
                smc_logger.info(f"Created SMC features for {symbol} on {date}")
            
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            smc_logger.error(f"Error saving SMC features to database: {e}")
            session.rollback()
            session.close()
            return False
    
    def get_features_from_db(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Retrieve SMC features from database.
        
        Args:
            symbol: Symbol name
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            
        Returns:
            DataFrame with SMC features
        """
        try:
            session = SessionLocal()
            
            records = session.query(SMCFeatures).filter(
                SMCFeatures.symbol == symbol,
                SMCFeatures.date >= start_date,
                SMCFeatures.date <= end_date
            ).all()
            
            data = []
            for record in records:
                data.append({
                    'date': record.date,
                    'pivot_highs': json.loads(record.pivot_highs) if record.pivot_highs else [],
                    'pivot_lows': json.loads(record.pivot_lows) if record.pivot_lows else [],
                    'bsl_sweeps': json.loads(record.bsl_sweeps) if record.bsl_sweeps else [],
                    'ssl_sweeps': json.loads(record.ssl_sweeps) if record.ssl_sweeps else [],
                    'choch_bullish': json.loads(record.choch_bullish) if record.choch_bullish else [],
                    'choch_bearish': json.loads(record.choch_bearish) if record.choch_bearish else [],
                    'bos_bullish': json.loads(record.bos_bullish) if record.bos_bullish else [],
                    'bos_bearish': json.loads(record.bos_bearish) if record.bos_bearish else [],
                    'fvg': json.loads(record.fvg) if record.fvg else [],
                    'order_blocks': json.loads(record.order_blocks) if record.order_blocks else [],
                    'wyckoff_events': json.loads(record.wyckoff_events) if record.wyckoff_events else {}
                })
            
            session.close()
            
            df = pd.DataFrame(data)
            smc_logger.info(f"Retrieved {len(df)} SMC feature records for {symbol}")
            return df
            
        except Exception as e:
            smc_logger.error(f"Error retrieving SMC features from database: {e}")
            return pd.DataFrame()
    
    def process_and_save(self, df: pd.DataFrame, symbol: str) -> int:
        """
        Process data and save SMC features to database.
        
        Args:
            df: DataFrame with OHLCV data (indexed by date)
            symbol: Symbol name
            
        Returns:
            Number of records saved
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # Extract features for entire dataset
        features = self.extract_all_features(df, symbol)
        
        # Save features with the latest date from the dataset
        latest_date = df.index[-1].strftime('%Y-%m-%d')
        
        if self.save_features_to_db(symbol, latest_date, features):
            smc_logger.info(f"Saved SMC features for {symbol} on {latest_date}")
            return 1
        else:
            smc_logger.error(f"Failed to save SMC features for {symbol}")
            return 0
