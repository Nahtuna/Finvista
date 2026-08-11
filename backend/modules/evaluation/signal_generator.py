"""
Advanced Signal Generator - Sophisticated Signal Generation Logic
Implements improved signal generation with confirmations, stop-loss, and take-profit.
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, Any, Optional, Tuple
from backend.core.utils import get_logger

signal_logger = get_logger(__name__)


class AdvancedSignalGenerator:
    """
    Advanced signal generation with multiple confirmations and risk management.
    """
    
    def __init__(self, stop_loss_pct: float = 0.02, take_profit_pct: float = 0.04,
                 confirmation_bars: int = 2, min_signal_strength: float = 0.3):
        """
        Initialize Advanced Signal Generator.
        
        Args:
            stop_loss_pct: Stop loss percentage (default 2%)
            take_profit_pct: Take profit percentage (default 4%)
            confirmation_bars: Number of bars for signal confirmation
            min_signal_strength: Minimum indicator strength for signal
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.confirmation_bars = confirmation_bars
        self.min_signal_strength = min_signal_strength
        signal_logger.info(f"Initialized AdvancedSignalGenerator with SL={stop_loss_pct}, TP={take_profit_pct}")
    
    def generate_smc_signals(self, df: pd.DataFrame, smc_features: Dict[str, Any]) -> pd.Series:
        """
        Generate improved SMC signals with confirmations.
        
        Args:
            df: DataFrame with OHLCV data
            smc_features: Dictionary of SMC features
            
        Returns:
            Series of trading signals
        """
        import json
        
        signals = pd.Series(0, index=df.index)
        
        # Parse pivot points
        pivot_highs_json = smc_features.get('pivot_highs', '[]')
        pivot_lows_json = smc_features.get('pivot_lows', '[]')
        
        pivot_highs_indices = json.loads(pivot_highs_json) if pivot_highs_json else []
        pivot_lows_indices = json.loads(pivot_lows_json) if pivot_lows_json else []
        
        # Parse CHoCH and BOS
        choch_bullish_json = smc_features.get('choch_bullish', '[]')
        choch_bearish_json = smc_features.get('choch_bearish', '[]')
        bos_bullish_json = smc_features.get('bos_bullish', '[]')
        bos_bearish_json = smc_features.get('bos_bearish', '[]')
        
        choch_bullish = json.loads(choch_bullish_json) if choch_bullish_json else []
        choch_bearish = json.loads(choch_bearish_json) if choch_bearish_json else []
        bos_bullish = json.loads(bos_bullish_json) if bos_bullish_json else []
        bos_bearish = json.loads(bos_bearish_json) if bos_bearish_json else []
        
        # Convert to boolean series
        pivot_highs = pd.Series(False, index=df.index)
        pivot_lows = pd.Series(False, index=df.index)
        choch_bullish_series = pd.Series(False, index=df.index)
        choch_bearish_series = pd.Series(False, index=df.index)
        bos_bullish_series = pd.Series(False, index=df.index)
        bos_bearish_series = pd.Series(False, index=df.index)
        
        for idx_str in pivot_highs_indices:
            for i, date in enumerate(df.index):
                if str(date) == idx_str:
                    pivot_highs.iloc[i] = True
                    break
        
        for idx_str in pivot_lows_indices:
            for i, date in enumerate(df.index):
                if str(date) == idx_str:
                    pivot_lows.iloc[i] = True
                    break
        
        for idx_str in choch_bullish:
            for i, date in enumerate(df.index):
                if str(date) == idx_str:
                    choch_bullish_series.iloc[i] = True
                    break
        
        for idx_str in choch_bearish:
            for i, date in enumerate(df.index):
                if str(date) == idx_str:
                    choch_bearish_series.iloc[i] = True
                    break
        
        for idx_str in bos_bullish:
            for i, date in enumerate(df.index):
                if str(date) == idx_str:
                    bos_bullish_series.iloc[i] = True
                    break
        
        for idx_str in bos_bearish:
            for i, date in enumerate(df.index):
                if str(date) == idx_str:
                    bos_bearish_series.iloc[i] = True
                    break
        
        # Generate buy signals: Pivot low + (optional) Bullish CHoCH/BOS confirmation
        for i in range(len(df)):
            if pivot_lows.iloc[i]:
                # Check for bullish confirmation in next N bars
                confirmed = False
                for j in range(i + 1, min(i + self.confirmation_bars + 1, len(df))):
                    if choch_bullish_series.iloc[j] or bos_bullish_series.iloc[j]:
                        signals.iloc[j] = 1
                        confirmed = True
                        break
                
                # If no confirmation, still generate signal but with lower priority
                if not confirmed and i + 1 < len(df):
                    signals.iloc[i + 1] = 1
        
        # Generate sell signals: Pivot high + (optional) Bearish CHoCH/BOS confirmation
        for i in range(len(df)):
            if pivot_highs.iloc[i]:
                # Check for bearish confirmation in next N bars
                confirmed = False
                for j in range(i + 1, min(i + self.confirmation_bars + 1, len(df))):
                    if choch_bearish_series.iloc[j] or bos_bearish_series.iloc[j]:
                        signals.iloc[j] = -1
                        confirmed = True
                        break
                
                # If no confirmation, still generate signal but with lower priority
                if not confirmed and i + 1 < len(df):
                    signals.iloc[i + 1] = -1
        
        signal_logger.info(f"Generated SMC signals: {(signals != 0).sum()} non-zero")
        return signals
    
    def generate_custom_signals(self, df: pd.DataFrame, custom_indicators: Dict[str, Any]) -> pd.Series:
        """
        Generate improved custom indicator signals with confirmations.
        
        Args:
            df: DataFrame with OHLCV data
            custom_indicators: Dictionary of custom indicator values
            
        Returns:
            Series of trading signals
        """
        signals = pd.Series(0, index=df.index)
        
        # Parse MK indicator
        mk_values_data = custom_indicators.get('mk_indicator', {})
        
        # Convert to Series
        if isinstance(mk_values_data, dict):
            mk_values = pd.Series(mk_values_data)
            mk_values.index = df.index[:len(mk_values)]
        elif isinstance(mk_values_data, pd.Series):
            mk_values = mk_values_data
        else:
            mk_values = pd.Series(0, index=df.index)
        
        # Parse SL reversals
        sl_reversals = custom_indicators.get('sl_reversals', {})
        
        # Convert to Series if it's a dict
        sl_reversals_series = pd.Series(0, index=df.index)
        if isinstance(sl_reversals, dict):
            for date_str, value in sl_reversals.items():
                for i, date in enumerate(df.index):
                    if str(date) == date_str:
                        sl_reversals_series.iloc[i] = value
                        break
        elif isinstance(sl_reversals, pd.Series):
            sl_reversals_series = sl_reversals.reindex(df.index, fill_value=0)
        
        # Generate buy signals: MK > threshold + (optional) SL bullish reversal
        buy_threshold = self.min_signal_strength
        for i in range(len(df)):
            if i < len(mk_values) and mk_values.iloc[i] > buy_threshold:
                # Check for SL bullish reversal confirmation
                confirmed = False
                for j in range(i, min(i + self.confirmation_bars, len(df))):
                    if sl_reversals_series.iloc[j] == 1:
                        signals.iloc[j] = 1
                        confirmed = True
                        break
                
                # If no confirmation, still generate signal
                if not confirmed:
                    signals.iloc[i] = 1
        
        # Generate sell signals: MK < -threshold + (optional) SL bearish reversal
        sell_threshold = -self.min_signal_strength
        for i in range(len(df)):
            if i < len(mk_values) and mk_values.iloc[i] < sell_threshold:
                # Check for SL bearish reversal confirmation
                confirmed = False
                for j in range(i, min(i + self.confirmation_bars, len(df))):
                    if sl_reversals_series.iloc[j] == -1:
                        signals.iloc[j] = -1
                        confirmed = True
                        break
                
                # If no confirmation, still generate signal
                if not confirmed:
                    signals.iloc[i] = -1
        
        signal_logger.info(f"Generated custom signals: {(signals != 0).sum()} non-zero")
        return signals
    
    def calculate_position_size(self, capital: float, price: float, risk_per_trade: float = 0.02) -> float:
        """
        Calculate position size based on risk management.
        
        Args:
            capital: Available capital
            price: Current price
            risk_per_trade: Risk percentage per trade (default 2%)
            
        Returns:
            Position size (number of shares)
        """
        risk_amount = capital * risk_per_trade
        stop_loss_amount = price * self.stop_loss_pct
        
        if stop_loss_amount == 0:
            return 0
        
        position_size = risk_amount / stop_loss_amount
        return position_size
    
    def apply_risk_management(self, df: pd.DataFrame, signals: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Apply stop-loss and take-profit to signals.
        
        Args:
            df: DataFrame with OHLCV data
            signals: Series of entry signals
            
        Returns:
            Tuple of (entry_signals, exit_signals, position_sizes)
        """
        entry_signals = signals.copy()
        exit_signals = pd.Series(0, index=df.index)
        position_sizes = pd.Series(0, index=df.index)
        
        current_position = 0
        entry_price = 0
        
        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            
            # Check for exit signals
            if current_position != 0:
                # Check stop-loss
                if current_position > 0:  # Long position
                    if current_price <= entry_price * (1 - self.stop_loss_pct):
                        exit_signals.iloc[i] = -1  # Exit long
                        current_position = 0
                    elif current_price >= entry_price * (1 + self.take_profit_pct):
                        exit_signals.iloc[i] = -1  # Exit long
                        current_position = 0
                else:  # Short position
                    if current_price >= entry_price * (1 + self.stop_loss_pct):
                        exit_signals.iloc[i] = 1  # Exit short
                        current_position = 0
                    elif current_price <= entry_price * (1 - self.take_profit_pct):
                        exit_signals.iloc[i] = 1  # Exit short
                        current_position = 0
            
            # Check for entry signals (only if no current position)
            if current_position == 0 and entry_signals.iloc[i] != 0:
                entry_price = current_price
                position_sizes.iloc[i] = self.calculate_position_size(100000, current_price)
                
                if entry_signals.iloc[i] == 1:
                    current_position = 1
                else:
                    current_position = -1
        
        signal_logger.info(f"Applied risk management: {exit_signals.sum()} exit signals")
        return entry_signals, exit_signals, position_sizes
