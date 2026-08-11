"""
Advanced Backtester - Professional Backtesting Framework
Implements improved backtesting with proper position sizing, leverage control, and risk management.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from backend.core.utils import get_logger

backtest_logger = get_logger(__name__)


class AdvancedBacktester:
    """
    Professional backtesting framework with proper risk management.
    
    Features:
    - Position sizing based on risk percentage
    - Leverage control
    - Stop-loss and take-profit
    - Trailing stop-loss
    - Maximum drawdown protection
    - Position limits
    """
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 commission: float = 0.001,
                 risk_per_trade: float = 0.02,
                 max_leverage: float = 1.0,
                 max_position_size: float = 0.3,
                 stop_loss_pct: float = 0.02,
                 take_profit_pct: float = 0.04,
                 trailing_stop_pct: float = 0.01,
                 max_daily_loss_pct: float = 0.05):
        """
        Initialize Advanced Backtester.
        
        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade
            risk_per_trade: Risk percentage per trade (default 2%)
            max_leverage: Maximum leverage (default 1.0 = no leverage)
            max_position_size: Maximum position size as % of capital
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            trailing_stop_pct: Trailing stop percentage
            max_daily_loss_pct: Maximum daily loss before stopping
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.risk_per_trade = risk_per_trade
        self.max_leverage = max_leverage
        self.max_position_size = max_position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        
        backtest_logger.info(f"Initialized AdvancedBacktester with risk_per_trade={risk_per_trade}, max_leverage={max_leverage}")
    
    def calculate_position_size(self, capital: float, price: float, stop_loss_price: float) -> float:
        """
        Calculate position size based on risk management.
        
        Args:
            capital: Available capital
            price: Current price
            stop_loss_price: Stop loss price
            
        Returns:
            Position size (number of shares)
        """
        risk_amount = capital * self.risk_per_trade
        stop_loss_amount = abs(price - stop_loss_price)
        
        if stop_loss_amount == 0:
            return 0
        
        # Calculate position size based on risk
        position_size = risk_amount / stop_loss_amount
        
        # Apply leverage
        position_size *= self.max_leverage
        
        # Apply maximum position size limit
        max_size = (capital * self.max_position_size) / price
        position_size = min(position_size, max_size)
        
        return position_size
    
    def run_backtest(self, df: pd.DataFrame, signals: pd.Series) -> Dict[str, Any]:
        """
        Run advanced backtest simulation.
        
        Args:
            df: DataFrame with OHLCV data
            signals: Series of trading signals (1=buy, -1=sell, 0=hold)
            
        Returns:
            Dictionary with backtest results
        """
        backtest_logger.info("Starting advanced backtest simulation")
        
        # Initialize tracking
        capital = self.initial_capital
        position = 0  # Position size (positive = long, negative = short)
        entry_price = 0
        stop_loss_price = 0
        take_profit_price = 0
        highest_price = 0
        lowest_price = 0
        
        equity_curve = []
        trades = []
        daily_returns = []
        
        daily_pnl = 0
        daily_pnl_limit = self.initial_capital * self.max_daily_loss_pct
        
        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            high_price = df['high'].iloc[i]
            low_price = df['low'].iloc[i]
            signal = signals.iloc[i] if i < len(signals) else 0
            
            # Update daily PnL
            if position != 0:
                if position > 0:
                    daily_pnl = position * (current_price - entry_price)
                else:
                    daily_pnl = -abs(position) * (current_price - entry_price)
            
            # Check daily loss limit
            if daily_pnl < -daily_pnl_limit:
                backtest_logger.warning(f"Daily loss limit reached at bar {i}")
                if position != 0:
                    # Close position
                    if position > 0:
                        pnl = position * (current_price - entry_price)
                    else:
                        pnl = -abs(position) * (current_price - entry_price)
                    
                    capital += pnl
                    trades.append({
                        'type': 'daily_limit_exit',
                        'price': current_price,
                        'pnl': pnl,
                        'capital': capital,
                        'bar': i
                    })
                    position = 0
                    entry_price = 0
                    stop_loss_price = 0
                    take_profit_price = 0
                    daily_pnl = 0
            
            # Check trailing stop-loss
            if position > 0:
                highest_price = max(highest_price, high_price)
                if highest_price > entry_price:
                    trailing_stop = highest_price * (1 - self.trailing_stop_pct)
                    if current_price <= trailing_stop:
                        # Close long position with trailing stop
                        pnl = position * (current_price - entry_price)
                        capital += pnl
                        trades.append({
                            'type': 'trailing_stop_long',
                            'price': current_price,
                            'pnl': pnl,
                            'capital': capital,
                            'bar': i
                        })
                        position = 0
                        entry_price = 0
                        stop_loss_price = 0
                        take_profit_price = 0
                        daily_pnl = 0
                        continue
            
            elif position < 0:
                lowest_price = min(lowest_price, low_price)
                if lowest_price < entry_price:
                    trailing_stop = lowest_price * (1 + self.trailing_stop_pct)
                    if current_price >= trailing_stop:
                        # Close short position with trailing stop
                        pnl = -abs(position) * (current_price - entry_price)
                        capital += pnl
                        trades.append({
                            'type': 'trailing_stop_short',
                            'price': current_price,
                            'pnl': pnl,
                            'capital': capital,
                            'bar': i
                        })
                        position = 0
                        entry_price = 0
                        stop_loss_price = 0
                        take_profit_price = 0
                        daily_pnl = 0
                        continue
            
            # Check stop-loss and take-profit
            if position != 0:
                if position > 0:  # Long position
                    if current_price <= stop_loss_price:
                        # Stop-loss hit
                        pnl = position * (current_price - entry_price)
                        capital += pnl
                        trades.append({
                            'type': 'stop_loss_long',
                            'price': current_price,
                            'pnl': pnl,
                            'capital': capital,
                            'bar': i
                        })
                        position = 0
                        entry_price = 0
                        stop_loss_price = 0
                        take_profit_price = 0
                        daily_pnl = 0
                        continue
                    
                    elif current_price >= take_profit_price:
                        # Take-profit hit
                        pnl = position * (current_price - entry_price)
                        capital += pnl
                        trades.append({
                            'type': 'take_profit_long',
                            'price': current_price,
                            'pnl': pnl,
                            'capital': capital,
                            'bar': i
                        })
                        position = 0
                        entry_price = 0
                        stop_loss_price = 0
                        take_profit_price = 0
                        daily_pnl = 0
                        continue
                
                else:  # Short position
                    if current_price >= stop_loss_price:
                        # Stop-loss hit
                        pnl = -abs(position) * (current_price - entry_price)
                        capital += pnl
                        trades.append({
                            'type': 'stop_loss_short',
                            'price': current_price,
                            'pnl': pnl,
                            'capital': capital,
                            'bar': i
                        })
                        position = 0
                        entry_price = 0
                        stop_loss_price = 0
                        take_profit_price = 0
                        daily_pnl = 0
                        continue
                    
                    elif current_price <= take_profit_price:
                        # Take-profit hit
                        pnl = -abs(position) * (current_price - entry_price)
                        capital += pnl
                        trades.append({
                            'type': 'take_profit_short',
                            'price': current_price,
                            'pnl': pnl,
                            'capital': capital,
                            'bar': i
                        })
                        position = 0
                        entry_price = 0
                        stop_loss_price = 0
                        take_profit_price = 0
                        daily_pnl = 0
                        continue
            
            # Execute trades based on signals
            if signal == 1 and position <= 0:  # Buy signal
                if position < 0:  # Close short position
                    pnl = -abs(position) * (current_price - entry_price)
                    capital += pnl
                    trades.append({
                        'type': 'close_short',
                        'price': current_price,
                        'pnl': pnl,
                        'capital': capital,
                        'bar': i
                    })
                
                # Open long position
                stop_loss_price = current_price * (1 - self.stop_loss_pct)
                take_profit_price = current_price * (1 + self.take_profit_pct)
                position_size = self.calculate_position_size(capital, current_price, stop_loss_price)
                
                cost = position_size * current_price * (1 + self.commission)
                capital -= cost
                position = position_size
                entry_price = current_price
                highest_price = current_price
                
            elif signal == -1 and position >= 0:  # Sell signal
                if position > 0:  # Close long position
                    pnl = position * (current_price - entry_price)
                    capital += pnl
                    trades.append({
                        'type': 'close_long',
                        'price': current_price,
                        'pnl': pnl,
                        'capital': capital,
                        'bar': i
                    })
                
                # Open short position
                stop_loss_price = current_price * (1 + self.stop_loss_pct)
                take_profit_price = current_price * (1 - self.take_profit_pct)
                position_size = self.calculate_position_size(capital, current_price, stop_loss_price)
                
                capital += position_size * current_price * (1 - self.commission)
                position = -position_size
                entry_price = current_price
                lowest_price = current_price
            
            # Calculate current equity
            if position > 0:
                current_equity = capital + position * current_price
            elif position < 0:
                current_equity = capital - abs(position) * current_price
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
            
            # Calculate daily return
            if i > 0 and i-1 < len(equity_curve):
                daily_return = (current_equity - equity_curve[i-1]) / equity_curve[i-1]
                daily_returns.append(daily_return)
            else:
                daily_returns.append(0)
        
        # Close final position
        if position != 0:
            final_price = df['close'].iloc[-1]
            if position > 0:
                pnl = position * (final_price - entry_price)
            else:
                pnl = -abs(position) * (final_price - entry_price)
            capital += pnl
            trades.append({
                'type': 'close_final',
                'price': final_price,
                'pnl': pnl,
                'capital': capital,
                'bar': len(df) - 1
            })
        
        # Calculate returns
        equity_series = pd.Series(equity_curve, index=df.index[:len(equity_curve)])
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
        
        backtest_logger.info(f"Advanced backtest completed: {total_return:.2%} return, {num_trades} trades")
        return results
    
    def calculate_advanced_risk_metrics(self, backtest_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate advanced risk metrics.
        
        Args:
            backtest_results: Results from run_backtest
            
        Returns:
            Dictionary with advanced risk metrics
        """
        returns = pd.Series(backtest_results['returns'])
        equity_curve = pd.Series(backtest_results['equity_curve'])
        
        # Maximum drawdown
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_dd = drawdown.min()
        
        # Volatility
        volatility = returns.std() * np.sqrt(252)  # Annualized
        
        # Sortino Ratio (downside risk)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0.001
        sortino_ratio = returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Calmar Ratio (return / max drawdown)
        calmar_ratio = backtest_results['total_return'] / abs(max_dd) if max_dd != 0 else 0
        
        # Maximum consecutive losses
        trades = backtest_results['trades']
        max_consecutive_losses = 0
        current_consecutive = 0
        for trade in trades:
            if trade['pnl'] < 0:
                current_consecutive += 1
                max_consecutive_losses = max(max_consecutive_losses, current_consecutive)
            else:
                current_consecutive = 0
        
        # Average holding period
        holding_periods = []
        for i in range(1, len(trades)):
            if trades[i]['type'] in ['close_long', 'close_short', 'stop_loss_long', 'stop_loss_short', 
                                    'take_profit_long', 'take_profit_short', 'trailing_stop_long', 'trailing_stop_short']:
                if trades[i-1]['type'] in ['close_long', 'close_short']:
                    pass  # Skip closing after closing
                else:
                    holding_period = trades[i]['bar'] - trades[i-1]['bar']
                    holding_periods.append(holding_period)
        
        avg_holding_period = np.mean(holding_periods) if holding_periods else 0
        
        risk_metrics = {
            'max_drawdown': float(max_dd),
            'volatility': float(volatility),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'max_consecutive_losses': int(max_consecutive_losses),
            'avg_holding_period': float(avg_holding_period)
        }
        
        backtest_logger.info(f"Advanced risk metrics: MaxDD={max_dd:.3f}, Sortino={sortino_ratio:.3f}")
        return risk_metrics
