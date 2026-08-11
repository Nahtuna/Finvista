"""
Benchmark Comparator - Compare Custom Indicators with Standard Indicators
Implements comparison framework for evaluating custom vs standard indicators.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from backend.core.utils import get_logger

benchmark_logger = get_logger(__name__)


class BenchmarkComparator:
    """
    Compare custom indicators against standard benchmarks.
    
    Benchmarks include:
    - Moving Averages (SMA, EMA)
    - RSI
    - MACD
    - Bollinger Bands
    - Buy & Hold
    """
    
    def __init__(self):
        """Initialize BenchmarkComparator."""
        benchmark_logger.info("Initialized BenchmarkComparator")
    
    def calculate_sma(self, price: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Simple Moving Average."""
        return price.rolling(window=period).mean()
    
    def calculate_ema(self, price: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return price.ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, price: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = price.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, price: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_fast = price.ewm(span=fast, adjust=False).mean()
        ema_slow = price.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, price: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        sma = price.rolling(window=period).mean()
        std = price.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'middle': sma,
            'upper': upper_band,
            'lower': lower_band
        }
    
    def calculate_buy_hold_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Buy & Hold strategy signals.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Series of signals (1 = buy at start, 0 = hold)
        """
        signals = pd.Series(0, index=df.index)
        if len(signals) > 0:
            signals.iloc[0] = 1  # Buy at the first bar
        return signals
    
    def calculate_buy_hold_performance(self, df: pd.DataFrame, initial_capital: float = 100000) -> Dict[str, Any]:
        """
        Calculate Buy & Hold strategy performance.
        
        Args:
            df: DataFrame with OHLCV data
            initial_capital: Starting capital
            
        Returns:
            Dictionary with performance metrics
        """
        if len(df) == 0:
            return {
                'initial_capital': initial_capital,
                'final_capital': initial_capital,
                'total_return': 0.0,
                'total_return_pct': 0.0,
                'num_trades': 1
            }
        
        initial_price = df['close'].iloc[0]
        final_price = df['close'].iloc[-1]
        
        # Calculate shares bought
        shares = initial_capital / initial_price
        
        # Calculate final capital
        final_capital = shares * final_price
        
        # Calculate return
        total_return = (final_capital - initial_capital) / initial_capital
        
        return {
            'initial_capital': initial_capital,
            'final_capital': float(final_capital),
            'total_return': float(total_return),
            'total_return_pct': float(total_return * 100),
            'num_trades': 1,
            'shares': float(shares),
            'initial_price': float(initial_price),
            'final_price': float(final_price)
        }
    
    def generate_sma_signals(self, price: pd.Series, short_period: int = 10, long_period: int = 30) -> pd.Series:
        """Generate signals from SMA crossover."""
        short_sma = self.calculate_sma(price, short_period)
        long_sma = self.calculate_sma(price, long_period)
        
        signals = pd.Series(0, index=price.index)
        
        # Buy signal: short SMA crosses above long SMA
        crossover = (short_sma > long_sma) & (short_sma.shift(1) <= long_sma.shift(1))
        signals[crossover] = 1
        
        # Sell signal: short SMA crosses below long SMA
        crossunder = (short_sma < long_sma) & (short_sma.shift(1) >= long_sma.shift(1))
        signals[crossunder] = -1
        
        benchmark_logger.info(f"Generated SMA signals: {signals.sum()} non-zero")
        return signals
    
    def generate_rsi_signals(self, rsi: pd.Series, overbought: float = 70, oversold: float = 30) -> pd.Series:
        """Generate signals from RSI."""
        signals = pd.Series(0, index=rsi.index)
        
        # Buy signal: RSI crosses above oversold
        buy_signal = (rsi > oversold) & (rsi.shift(1) <= oversold)
        signals[buy_signal] = 1
        
        # Sell signal: RSI crosses below overbought
        sell_signal = (rsi < overbought) & (rsi.shift(1) >= overbought)
        signals[sell_signal] = -1
        
        benchmark_logger.info(f"Generated RSI signals: {signals.sum()} non-zero")
        return signals
    
    def generate_macd_signals(self, macd_data: Dict[str, pd.Series]) -> pd.Series:
        """Generate signals from MACD."""
        macd_line = macd_data['macd']
        signal_line = macd_data['signal']
        
        signals = pd.Series(0, index=macd_line.index)
        
        # Buy signal: MACD crosses above signal line
        crossover = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        signals[crossover] = 1
        
        # Sell signal: MACD crosses below signal line
        crossunder = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
        signals[crossunder] = -1
        
        benchmark_logger.info(f"Generated MACD signals: {signals.sum()} non-zero")
        return signals
    
    def compare_indicators(self, df: pd.DataFrame, custom_signals: pd.Series, custom_name: str = "Custom") -> Dict[str, Any]:
        """
        Compare custom indicator against standard benchmarks.
        
        Args:
            df: DataFrame with OHLCV data
            custom_signals: Series of custom indicator signals
            custom_name: Name of custom indicator
            
        Returns:
            Dictionary with comparison results
        """
        benchmark_logger.info(f"Comparing {custom_name} indicator against benchmarks")
        
        results = {
            'custom_name': custom_name,
            'benchmarks': {}
        }
        
        # SMA
        sma_signals = self.generate_sma_signals(df['close'])
        results['benchmarks']['sma'] = {
            'num_signals': (sma_signals != 0).sum()
        }
        
        # RSI
        rsi = self.calculate_rsi(df['close'])
        rsi_signals = self.generate_rsi_signals(rsi)
        results['benchmarks']['rsi'] = {
            'num_signals': (rsi_signals != 0).sum()
        }
        
        # MACD
        macd_data = self.calculate_macd(df['close'])
        macd_signals = self.generate_macd_signals(macd_data)
        results['benchmarks']['macd'] = {
            'num_signals': (macd_signals != 0).sum()
        }
        
        benchmark_logger.info(f"Benchmark comparison completed for {custom_name}")
        return results
