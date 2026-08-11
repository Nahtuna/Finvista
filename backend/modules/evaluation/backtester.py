"""
Backtester - Historical Performance Testing Framework
Implements backtesting logic for evaluating indicator performance.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from backend.core.utils import get_logger

backtest_logger = get_logger(__name__)


class Backtester:
    """
    Simple backtesting framework for indicator evaluation.
    
    Simulates trading based on indicator signals and calculates performance metrics.
    """
    
    def __init__(self, initial_capital: float = 100000, commission: float = 0.001):
        """
        Initialize Backtester.
        
        Args:
            initial_capital: Starting capital for simulation
            commission: Commission rate per trade (default 0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        backtest_logger.info(f"Initialized Backtester with capital={initial_capital}, commission={commission}")
    
    def run_backtest(self, df: pd.DataFrame, signals: pd.Series) -> Dict[str, Any]:
        """
        Run backtest simulation.
        
        Args:
            df: DataFrame with OHLCV data
            signals: Series of trading signals (1=buy, -1=sell, 0=hold)
            
        Returns:
            Dictionary with backtest results
        """
        backtest_logger.info("Starting backtest simulation")
        
        # Initialize tracking
        capital = self.initial_capital
        position = 0  # Position size (positive = long, negative = short)
        equity_curve = []
        trades = []
        
        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            signal = signals.iloc[i] if i < len(signals) else 0
            
            # Execute trades based on signals
            if signal == 1 and position <= 0:  # Buy signal
                if position < 0:  # Close short position
                    pnl = -position * (current_price - df['close'].iloc[i-1])
                    capital += pnl
                    trades.append({
                        'type': 'close_short',
                        'price': current_price,
                        'pnl': pnl,
                        'capital': capital
                    })
                
                # Open long position
                position_size = capital / current_price
                cost = position_size * current_price * (1 + self.commission)
                capital -= cost
                position = position_size
                
            elif signal == -1 and position >= 0:  # Sell signal
                if position > 0:  # Close long position
                    pnl = position * (current_price - df['close'].iloc[i-1])
                    capital += pnl
                    trades.append({
                        'type': 'close_long',
                        'price': current_price,
                        'pnl': pnl,
                        'capital': capital
                    })
                
                # Open short position
                position_size = capital / current_price
                capital += position_size * current_price * (1 - self.commission)
                position = -position_size
            
            # Calculate current equity
            if position > 0:
                current_equity = capital + position * current_price
            elif position < 0:
                current_equity = capital - abs(position) * current_price
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
        
        # Close final position
        if position != 0:
            final_price = df['close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - df['close'].iloc[-2])
            else:
                pnl = -abs(position) * (final_price - df['close'].iloc[-2])
            capital += pnl
            trades.append({
                'type': 'close_final',
                'price': final_price,
                'pnl': pnl,
                'capital': capital
            })
        
        # Calculate returns
        equity_series = pd.Series(equity_curve, index=df.index)
        returns = equity_series.pct_change().fillna(0)
        
        # Calculate statistics
        total_return = (capital - self.initial_capital) / self.initial_capital
        num_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': float(capital),
            'total_return': float(total_return),
            'total_return_pct': float(total_return * 100),
            'num_trades': num_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / num_trades if num_trades > 0 else 0.0,
            'avg_win': np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0.0,
            'avg_loss': np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0.0,
            'equity_curve': equity_series.to_dict(),
            'returns': returns.to_dict(),
            'trades': trades
        }
        
        backtest_logger.info(f"Backtest completed: {total_return:.2%} return, {num_trades} trades")
        return results
    
    def calculate_risk_metrics(self, backtest_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate risk metrics from backtest results.
        
        Args:
            backtest_results: Results from run_backtest
            
        Returns:
            Dictionary with risk metrics
        """
        returns = pd.Series(backtest_results['returns'])
        equity_curve = pd.Series(backtest_results['equity_curve'])
        
        # Maximum drawdown
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Volatility
        volatility = returns.std() * np.sqrt(252)  # Annualized
        
        # Sortino Ratio (downside risk)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.001
        sortino_ratio = returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Calmar Ratio (return / max drawdown)
        calmar_ratio = backtest_results['total_return'] / abs(max_drawdown) if max_drawdown != 0 else 0
        
        risk_metrics = {
            'max_drawdown': float(max_drawdown),
            'volatility': float(volatility),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio)
        }
        
        backtest_logger.info(f"Risk metrics: MaxDD={max_drawdown:.3f}, Sortino={sortino_ratio:.3f}")
        return risk_metrics
    
    def compare_with_benchmark(self, backtest_results: Dict[str, Any], benchmark_returns: pd.Series) -> Dict[str, float]:
        """
        Compare backtest results with benchmark.
        
        Args:
            backtest_results: Results from run_backtest
            benchmark_returns: Series of benchmark returns
            
        Returns:
            Dictionary with comparison metrics
        """
        strategy_returns = pd.Series(backtest_results['returns'])
        
        # Align indices
        common_index = strategy_returns.index.intersection(benchmark_returns.index)
        strategy_aligned = strategy_returns.loc[common_index]
        benchmark_aligned = benchmark_returns.loc[common_index]
        
        # Calculate excess returns
        excess_returns = strategy_aligned - benchmark_aligned
        
        # Information Ratio
        tracking_error = excess_returns.std() * np.sqrt(252)
        information_ratio = excess_returns.mean() / tracking_error if tracking_error > 0 else 0
        
        # Beta
        covariance = np.cov(strategy_aligned, benchmark_aligned)[0, 1]
        benchmark_variance = benchmark_aligned.var()
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
        
        # Alpha
        alpha = strategy_aligned.mean() - beta * benchmark_aligned.mean()
        
        comparison = {
            'information_ratio': float(information_ratio),
            'tracking_error': float(tracking_error),
            'beta': float(beta),
            'alpha': float(alpha),
            'excess_return': float(excess_returns.sum())
        }
        
        backtest_logger.info(f"Benchmark comparison: Alpha={alpha:.3f}, Beta={beta:.3f}")
        return comparison
