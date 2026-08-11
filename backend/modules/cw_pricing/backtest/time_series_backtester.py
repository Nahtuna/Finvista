# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: TIME-SERIES BACKTESTER
====================================
Real historical backtest using actual CW and stock price data from database.
Simulates trading strategies over multiple years with realistic PnL calculation.

Features:
- Historical data from 2021-2026 (5.5 years of CW data)
- Rolling signal generation at each time point
- Realistic entry/exit with stop-loss and take-profit
- Comprehensive performance metrics (Sharpe, Sortino, Max DD, etc.)
- Equity curve analysis and trade-by-trade breakdown

Author: samvo
Version: 1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import sys

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from backend.core.database import engine
from backend.core.utils import get_logger

logger = get_logger("time_series_backtester")


@dataclass
class Trade:
    """Represents a single trade in the backtest."""
    symbol: str
    underlying: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    quantity: int
    direction: str  # 'LONG' for CW (we only buy)
    pnl: float
    pnl_pct: float
    holding_days: int
    exit_reason: str  # 'TAKE_PROFIT', 'STOP_LOSS', 'EXPIRY', 'SIGNAL_EXIT'
    score_at_entry: float
    signal_at_entry: str


@dataclass
class BacktestConfig:
    """Configuration for backtest parameters."""
    initial_capital: float = 100_000_000.0  # 100M VND
    max_position_size: float = 0.2  # Max 20% of capital per position
    stop_loss_pct: float = -0.10  # 10% stop loss
    take_profit_pct: float = 0.30  # 30% take profit
    max_holding_days: int = 30  # Max 30 days holding
    min_holding_days: int = 3  # Min 3 days to avoid day trading
    strategy: str = "balanced"  # balanced, safe, aggressive
    commission_pct: float = 0.001  # 0.1% commission
    slippage_pct: float = 0.002  # 0.2% slippage
    min_signal_score: float = 55.0  # Minimum score to enter trade


class TimeSeriesBacktester:
    """
    Main backtesting engine that simulates trading strategies over historical data.
    """
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.engine = engine
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[str, float]] = []
        self.daily_returns: List[float] = []
        
    def get_available_cw_symbols(self) -> List[str]:
        """Get list of CW symbols with historical data."""
        query = """
            SELECT DISTINCT symbol 
            FROM cw_history 
            WHERE close IS NOT NULL AND close > 0
            ORDER BY symbol
        """
        df = pd.read_sql(query, self.engine)
        return df['symbol'].tolist()
    
    def get_cw_underlying_mapping(self) -> Dict[str, str]:
        """Get mapping of CW symbols to their underlying stocks."""
        query = """
            SELECT DISTINCT symbol
            FROM cw_history
            WHERE close IS NOT NULL AND close > 0
        """
        df = pd.read_sql(query, self.engine)
        # Extract underlying from CW symbol (first 3 characters)
        mapping = {symbol: symbol[:3] for symbol in df['symbol']}
        return mapping
    
    def load_historical_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load historical CW and stock data for the specified date range.
        Returns merged dataframe with OHLCV data for both CW and underlying.
        """
        # Load CW data
        cw_query = f"""
            SELECT 
                symbol,
                date,
                open as cw_open,
                high as cw_high,
                low as cw_low,
                close as cw_close,
                volume as cw_volume,
                ref_price as cw_ref
            FROM cw_history
            WHERE date BETWEEN '{start_date}' AND '{end_date}'
                AND close IS NOT NULL 
                AND close > 0
            ORDER BY symbol, date
        """
        cw_df = pd.read_sql(cw_query, self.engine)
        
        if cw_df.empty:
            logger.warning(f"No CW historical data found for {start_date} to {end_date}")
            return pd.DataFrame()
        
        # Extract underlying from CW symbol (CW symbols typically contain underlying code)
        # Example: "FPT230225P" -> underlying is "FPT"
        cw_df['underlying'] = cw_df['symbol'].str.extract(r'^([A-Z]{3})')[0]
        
        # Load stock data for all unique underlyings
        underlyings = cw_df['underlying'].dropna().unique()
        if len(underlyings) == 0:
            logger.warning("No underlyings found in CW symbols")
            return cw_df
        
        underlying_list = "','".join(underlyings)
        stock_query = f"""
            SELECT 
                symbol,
                date,
                open as stock_open,
                high as stock_high,
                low as stock_low,
                close as stock_close,
                volume as stock_volume
            FROM stock_history
            WHERE symbol IN ('{underlying_list}')
                AND date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY symbol, date
        """
        stock_df = pd.read_sql(stock_query, self.engine)
        
        # Merge CW and stock data
        df = pd.merge(
            cw_df,
            stock_df,
            left_on=['underlying', 'date'],
            right_on=['symbol', 'date'],
            how='left'
        )
        
        # Clean up
        df = df.drop(columns=['symbol_y'], errors='ignore')
        df = df.rename(columns={'symbol_x': 'symbol'})
        
        logger.info(f"📊 Loaded {len(df)} rows of historical data")
        return df
    
    def calculate_daily_signals(self, df: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        Calculate trading signals for a specific date using simplified logic.
        This simulates the real-time signal generation process without complex dependencies.
        """
        # Filter data for the specific date
        daily_data = df[df['date'] == date].copy()
        if daily_data.empty:
            return pd.DataFrame()
        
        # Simple momentum-based signal generation
        daily_data['prev_close'] = daily_data.groupby('symbol')['cw_close'].shift(1)
        daily_data['return_1d'] = (daily_data['cw_close'] - daily_data['prev_close']) / daily_data['prev_close']
        
        # Calculate stock momentum
        daily_data['stock_prev_close'] = daily_data.groupby('symbol')['stock_close'].shift(1)
        daily_data['stock_return_1d'] = (daily_data['stock_close'] - daily_data['stock_prev_close']) / daily_data['stock_prev_close']
        
        # Simple scoring logic
        def calculate_signal(row):
            cw_return = row.get('return_1d', 0)
            stock_return = row.get('stock_return_1d', 0)
            volume = row.get('cw_volume', 0)
            
            # Basic criteria
            if pd.isna(cw_return) or pd.isna(stock_return):
                return 'WAIT'
            
            if volume < 1000:  # Low volume filter
                return 'WAIT'
            
            # Momentum strategy
            if stock_return > 0.02 and cw_return > 0.01:  # Strong up momentum
                return 'STRONG BUY'
            elif stock_return > 0.01 and cw_return > 0:  # Moderate up momentum
                return 'BUY'
            elif stock_return < -0.02:  # Down momentum
                return 'SELL'
            else:
                return 'WAIT'
        
        daily_data['Signal'] = daily_data.apply(calculate_signal, axis=1)
        
        # Calculate simple score (0-100)
        def calculate_score(row):
            stock_return = row.get('stock_return_1d', 0)
            cw_return = row.get('return_1d', 0)
            volume = row.get('cw_volume', 0)
            
            score = 50  # Base score
            
            # Momentum bonus
            if stock_return > 0.02:
                score += 20
            elif stock_return > 0.01:
                score += 10
            elif stock_return < -0.01:
                score -= 10
            
            # CW momentum bonus
            if cw_return > 0.01:
                score += 10
            elif cw_return < -0.01:
                score -= 5
            
            # Volume bonus
            if volume > 10000:
                score += 5
            elif volume > 5000:
                score += 3
            
            return min(100, max(0, score))
        
        daily_data['G_Score'] = daily_data.apply(calculate_score, axis=1)
        
        return daily_data
    
    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Run the full backtest over the specified date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary with backtest results and metrics
        """
        logger.info(f"🚀 Starting time-series backtest from {start_date} to {end_date}")
        logger.info(f"📊 Strategy: {self.config.strategy}, Initial Capital: {self.config.initial_capital:,.0f} VND")
        
        # Load historical data
        df = self.load_historical_data(start_date, end_date)
        if df.empty:
            return self._empty_results()
        
        # Get unique trading dates
        trading_dates = sorted(df['date'].unique())
        logger.info(f"📅 Total trading days: {len(trading_dates)}")
        
        # Initialize state
        capital = self.config.initial_capital
        positions = {}  # symbol -> position info
        self.equity_curve = [(trading_dates[0], capital)]
        
        # Run day-by-day simulation
        for i, date in enumerate(trading_dates):
            daily_equity = capital
            
            # Update existing positions
            for symbol, pos in list(positions.items()):
                # Get current price for this position
                pos_data = df[(df['symbol'] == symbol) & (df['date'] == date)]
                if pos_data.empty:
                    continue
                
                current_price = pos_data['cw_close'].iloc[0]
                entry_price = pos['entry_price']
                entry_date = pos['entry_date']
                
                # Calculate PnL
                pnl_pct = (current_price - entry_price) / entry_price
                holding_days = (datetime.strptime(date, '%Y-%m-%d') - 
                               datetime.strptime(entry_date, '%Y-%m-%d')).days
                
                # Check exit conditions
                exit_reason = None
                should_exit = False
                
                if pnl_pct <= self.config.stop_loss_pct:
                    exit_reason = 'STOP_LOSS'
                    should_exit = True
                elif pnl_pct >= self.config.take_profit_pct:
                    exit_reason = 'TAKE_PROFIT'
                    should_exit = True
                elif holding_days >= self.config.max_holding_days:
                    exit_reason = 'MAX_HOLDING'
                    should_exit = True
                elif holding_days >= self.config.min_holding_days:
                    # Check for signal exit
                    signals = self.calculate_daily_signals(df, date)
                    if not signals.empty:
                        symbol_signal = signals[signals['symbol'] == symbol]
                        if not symbol_signal.empty:
                            current_signal = symbol_signal['Signal'].iloc[0]
                            if 'SELL' in current_signal or 'SKIP' in current_signal:
                                exit_reason = 'SIGNAL_EXIT'
                                should_exit = True
                
                # Update position value
                position_value = pos['quantity'] * current_price
                daily_equity += position_value
                
                # Execute exit if needed
                if should_exit:
                    # Calculate final PnL with commissions and slippage
                    exit_price = current_price * (1 - self.config.slippage_pct)
                    commission = pos['quantity'] * exit_price * self.config.commission_pct
                    pnl = (exit_price - entry_price) * pos['quantity'] - commission
                    pnl_pct_final = (exit_price - entry_price) / entry_price
                    
                    # Record trade
                    trade = Trade(
                        symbol=symbol,
                        underlying=symbol[:3],  # Extract from symbol
                        entry_date=entry_date,
                        exit_date=date,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        quantity=pos['quantity'],
                        direction='LONG',
                        pnl=pnl,
                        pnl_pct=pnl_pct_final,
                        holding_days=holding_days,
                        exit_reason=exit_reason,
                        score_at_entry=pos['score'],
                        signal_at_entry=pos['signal']
                    )
                    self.trades.append(trade)
                    
                    # Update capital
                    capital += pnl
                    del positions[symbol]
                    
                    logger.info(f"💰 EXIT {symbol} on {date}: {exit_reason}, PnL: {pnl:,.0f} VND ({pnl_pct_final:.1%})")
            
            # Generate new signals and enter positions
            if len(positions) < 5:  # Max 5 concurrent positions
                signals = self.calculate_daily_signals(df, date)
                if not signals.empty:
                    # Filter for BUY signals with sufficient score
                    buy_signals = signals[
                        (signals['Signal'].str.contains('BUY', case=False, na=False)) &
                        (signals['G_Score'] >= self.config.min_signal_score)
                    ]
                    
                    for _, signal_row in buy_signals.iterrows():
                        if len(positions) >= 5:
                            break
                        
                        symbol = signal_row['symbol']
                        if symbol in positions:
                            continue
                        
                        # Calculate position size
                        position_value = capital * self.config.max_position_size
                        entry_price = signal_row['cw_close'] * (1 + self.config.slippage_pct)
                        quantity = int(position_value / entry_price)
                        
                        if quantity <= 0:
                            continue
                        
                        # Check if we have enough capital
                        required_capital = quantity * entry_price * (1 + self.config.commission_pct)
                        if required_capital > capital * 0.9:  # Keep 10% cash buffer
                            continue
                        
                        # Enter position
                        capital -= required_capital
                        positions[symbol] = {
                            'underlying': symbol[:3],  # Extract from symbol
                            'entry_price': entry_price,
                            'entry_date': date,
                            'quantity': quantity,
                            'score': signal_row['G_Score'],
                            'signal': signal_row['Signal']
                        }
                        
                        logger.info(f"📈 ENTRY {symbol} on {date}: {signal_row['Signal']}, "
                                  f"Price: {entry_price:,.0f}, Qty: {quantity}, Score: {signal_row['G_Score']:.1f}")
            
            # Record equity
            self.equity_curve.append((date, daily_equity))
            
            # Calculate daily return
            if len(self.equity_curve) > 1:
                prev_equity = self.equity_curve[-2][1]
                daily_return = (daily_equity - prev_equity) / prev_equity
                self.daily_returns.append(daily_return)
        
        # Close remaining positions at end
        for symbol, pos in positions.items():
            final_date = trading_dates[-1]
            pos_data = df[(df['symbol'] == symbol) & (df['date'] == final_date)]
            if not pos_data.empty:
                exit_price = pos_data['cw_close'].iloc[0] * (1 - self.config.slippage_pct)
                commission = pos['quantity'] * exit_price * self.config.commission_pct
                pnl = (exit_price - pos['entry_price']) * pos['quantity'] - commission
                pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price']
                
                trade = Trade(
                    symbol=symbol,
                    underlying=symbol[:3],  # Extract from symbol
                    entry_date=pos['entry_date'],
                    exit_date=final_date,
                    entry_price=pos['entry_price'],
                    exit_price=exit_price,
                    quantity=pos['quantity'],
                    direction='LONG',
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    holding_days=(datetime.strptime(final_date, '%Y-%m-%d') - 
                                 datetime.strptime(pos['entry_date'], '%Y-%m-%d')).days,
                    exit_reason='BACKTEST_END',
                    score_at_entry=pos['score'],
                    signal_at_entry=pos['signal']
                )
                self.trades.append(trade)
                capital += pnl
        
        # Calculate final metrics
        results = self._calculate_metrics(capital)
        return results
    
    def _calculate_metrics(self, final_capital: float) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        if not self.trades:
            return self._empty_results()
        
        # Trade statistics
        trade_df = pd.DataFrame([t.__dict__ for t in self.trades])
        winning_trades = trade_df[trade_df['pnl'] > 0]
        losing_trades = trade_df[trade_df['pnl'] <= 0]
        
        total_trades = len(self.trades)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # PnL statistics
        total_pnl = trade_df['pnl'].sum()
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0 else float('inf')
        
        # Risk metrics
        returns = np.array(self.daily_returns)
        if len(returns) > 0:
            sharpe_ratio = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = returns[returns < 0]
            downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
            sortino_ratio = (np.mean(returns) / downside_std * np.sqrt(252)) if downside_std > 0 else 0
            
            # Max drawdown
            equity_values = [eq[1] for eq in self.equity_curve]
            peaks = np.maximum.accumulate(equity_values)
            drawdowns = (equity_values - peaks) / peaks
            max_drawdown = abs(drawdowns.min()) * 100 if len(drawdowns) > 0 else 0
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
            max_drawdown = 0
        
        # Return statistics
        total_return = (final_capital - self.config.initial_capital) / self.config.initial_capital * 100
        annualized_return = total_return / (len(self.equity_curve) / 252) * 100 if len(self.equity_curve) > 0 else 0
        
        # Holding period statistics
        avg_holding_days = trade_df['holding_days'].mean()
        
        return {
            'status': 'success',
            'total_trades': total_trades,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'total_return_pct': round(total_return, 2),
            'annualized_return_pct': round(annualized_return, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2),
            'max_drawdown_pct': round(max_drawdown, 2),
            'avg_holding_days': round(avg_holding_days, 1),
            'final_capital': round(final_capital, 2),
            'initial_capital': round(self.config.initial_capital, 2),
            'trading_days': len(self.equity_curve),
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no trades were executed."""
        return {
            'status': 'no_trades',
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'total_return_pct': 0,
            'annualized_return_pct': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'max_drawdown_pct': 0,
            'avg_holding_days': 0,
            'final_capital': self.config.initial_capital,
            'initial_capital': self.config.initial_capital,
            'trading_days': 0,
            'trades': [],
            'equity_curve': []
        }
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted backtest results."""
        print("\n" + "=" * 80)
        print("🏆 FINVISTA TIME-SERIES BACKTEST RESULTS")
        print("=" * 80)
        print(f"📊 Strategy: {self.config.strategy.upper()}")
        print(f"📅 Period: {len(results['equity_curve'])} trading days")
        print(f"💰 Initial Capital: {results['initial_capital']:,.0f} VND")
        print(f"💰 Final Capital: {results['final_capital']:,.0f} VND")
        print("-" * 80)
        print(f"📈 Total Return: {results['total_return_pct']:.2f}%")
        print(f"📊 Annualized Return: {results['annualized_return_pct']:.2f}%")
        print(f"🎯 Total Trades: {results['total_trades']}")
        print(f"🏆 Win Rate: {results['win_rate']:.1f}%")
        print(f"💵 Profit Factor: {results['profit_factor']:.2f}")
        print(f"📏 Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"📉 Sortino Ratio: {results['sortino_ratio']:.2f}")
        print(f"⚠️  Max Drawdown: {results['max_drawdown_pct']:.1f}%")
        print(f"⏱️  Avg Holding Days: {results['avg_holding_days']:.1f}")
        print("=" * 80)
        
        if results['trades']:
            print("\n📋 RECENT TRADES:")
            print("-" * 80)
            for trade in results['trades'][-10:]:
                print(f"{trade.symbol:8} | {trade.entry_date} → {trade.exit_date} | "
                      f"{trade.pnl_pct:+6.1%} | {trade.exit_reason:15} | "
                      f"Score: {trade.score_at_entry:.1f}")


def run_time_series_backtest(
    start_date: str = "2023-01-01",
    end_date: str = "2026-08-03",
    strategy: str = "balanced"
) -> Dict[str, Any]:
    """
    Convenience function to run a time-series backtest with default parameters.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format  
        strategy: Trading strategy (balanced, safe, aggressive)
    
    Returns:
        Dictionary with backtest results
    """
    config = BacktestConfig(strategy=strategy)
    backtester = TimeSeriesBacktester(config)
    results = backtester.run_backtest(start_date, end_date)
    backtester.print_results(results)
    return results


if __name__ == "__main__":
    # Run backtest with default parameters
    results = run_time_series_backtest(
        start_date="2023-01-01",
        end_date="2026-08-03",
        strategy="balanced"
    )
