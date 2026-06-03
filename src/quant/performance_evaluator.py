import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

def calculate_portfolio_performance(trades_list, initial_capital=100000000.0, max_concurrent_trades=5, total_fees_pct=0.1):
    """
    Simulates a daily portfolio equity curve from a list of trades.
    Uses the exact close prices from the database to mark-to-market active positions.
    Calculates:
      - Transaction Analysis (Initial Capital, Net Equity, Profit, Fees, Trades, Win/Loss, etc.)
      - Performance Metrics (Cumulative Return, CAGR, Win Rate, Profit Factor, Sharpe, Sortino, Calmar, Payoff, Volatility, Max DD)
      - Advanced Metrics (Recovery Factor, Kelly Criterion, Omega Ratio, Ulcer Index, VaR, CVaR)
    """
    if not trades_list:
        return {}

    # Import engine to fetch daily prices for mark-to-market
    from src.common.database import engine
    
    # Load all daily CW prices for MTM
    cw_prices_df = pd.read_sql("SELECT symbol, date, close FROM cw_history", engine)
    cw_prices_df['date'] = pd.to_datetime(cw_prices_df['date']).dt.strftime('%Y-%m-%d')
    price_map = cw_prices_df.set_index(['symbol', 'date'])['close'].to_dict()
    
    # Parse trade dates
    trades = pd.DataFrame(trades_list)
    trades['entry_date'] = pd.to_datetime(trades['entry_date']).dt.strftime('%Y-%m-%d')
    trades['exit_date'] = pd.to_datetime(trades['exit_date']).dt.strftime('%Y-%m-%d')
    
    # Get all unique dates in the backtest period sorted chronologically
    all_dates = sorted(list(set(trades['entry_date'].tolist() + trades['exit_date'].tolist() + cw_prices_df['date'].tolist())))
    # Filter dates to range of trades
    min_date = trades['entry_date'].min()
    max_date = trades['exit_date'].max()
    all_dates = [d for d in all_dates if min_date <= d <= max_date]
    
    # Portfolio state
    cash = initial_capital
    active_positions = [] # list of dicts
    equity_curve = []
    total_fees_paid = 0.0
    
    # Map entries and exits by date for fast lookup
    entries_by_date = trades.groupby('entry_date')
    exits_by_date = trades.groupby('exit_date')
    
    for current_date in all_dates:
        # 1. Process exits first (sell positions)
        if current_date in exits_by_date.groups:
            exits = exits_by_date.get_group(current_date)
            for _, trade in exits.iterrows():
                match = None
                for pos in active_positions:
                    if pos['symbol'] == trade['cw'] and pos['exit_date'] == current_date:
                        match = pos
                        break
                if match:
                    exit_val = match['qty'] * trade['exit_price']
                    fee = exit_val * (total_fees_pct / 100.0)
                    total_fees_paid += fee
                    cash += (exit_val - fee)
                    active_positions.remove(match)
        
        # 2. Process entries (buy positions if slots available)
        if current_date in entries_by_date.groups:
            entries = entries_by_date.get_group(current_date)
            for _, trade in entries.iterrows():
                if len(active_positions) < max_concurrent_trades:
                    alloc = initial_capital / max_concurrent_trades
                    if cash >= alloc:
                        fee = alloc * (total_fees_pct / 100.0)
                        total_fees_paid += fee
                        qty = (alloc - fee) / trade['entry_price']
                        cash -= alloc
                        active_positions.append({
                            'symbol': trade['cw'],
                            'qty': qty,
                            'entry_price': trade['entry_price'],
                            'exit_price': trade['exit_price'],
                            'exit_date': trade['exit_date']
                        })
        
        # 3. Mark-to-Market
        pos_value = 0.0
        for pos in active_positions:
            price = price_map.get((pos['symbol'], current_date), pos['entry_price'])
            pos_value += pos['qty'] * price
            
        nav = cash + pos_value
        equity_curve.append({
            'date': current_date,
            'nav': nav,
            'cash': cash,
            'pos_value': pos_value
        })
        
    equity_df = pd.DataFrame(equity_curve)
    if equity_df.empty:
        return {}
        
    # Calculate returns
    equity_df['returns'] = equity_df['nav'].pct_change().fillna(0.0)
    
    # ----------------------------------------------------
    # Metric Calculations
    # ----------------------------------------------------
    final_nav = equity_df['nav'].iloc[-1]
    cumulative_return = (final_nav - initial_capital) / initial_capital * 100
    
    # CAGR
    start_dt = datetime.strptime(min_date, '%Y-%m-%d')
    end_dt = datetime.strptime(max_date, '%Y-%m-%d')
    days = max((end_dt - start_dt).days, 1)
    cagr = ((final_nav / initial_capital) ** (365.0 / days) - 1.0) * 100 if final_nav > 0 else -100.0
    
    # Volatility
    daily_vol = equity_df['returns'].std()
    ann_vol = daily_vol * np.sqrt(252) * 100
    
    # Sharpe & Sortino
    mean_return = equity_df['returns'].mean()
    sharpe = (mean_return / daily_vol) * np.sqrt(252) if daily_vol > 0 else 0.0
    
    downside_returns = equity_df['returns'][equity_df['returns'] < 0]
    downside_vol = downside_returns.std() if len(downside_returns) > 1 else daily_vol
    sortino = (mean_return / downside_vol) * np.sqrt(252) if downside_vol > 0 else 0.0
    
    # Max Drawdown
    equity_df['peak'] = equity_df['nav'].cummax()
    equity_df['dd'] = (equity_df['nav'] - equity_df['peak']) / equity_df['peak'] * 100
    max_dd = equity_df['dd'].min()
    
    # Calmar
    calmar = (cagr / abs(max_dd)) if max_dd < 0 else float('inf')
    
    # Trade statistics
    total_trades = len(trades_list)
    wins = sum(1 for t in trades_list if t['win'])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    
    winning_trades = [t['pnl_pct'] for t in trades_list if t['win']]
    losing_trades = [t['pnl_pct'] for t in trades_list if not t['win']]
    
    largest_win = max(winning_trades) if winning_trades else 0.0
    largest_loss = min(losing_trades) if losing_trades else 0.0
    avg_win = np.mean(winning_trades) if winning_trades else 0.0
    avg_loss = np.mean(losing_trades) if losing_trades else 0.0
    
    payoff_ratio = (avg_win / abs(avg_loss)) if avg_loss != 0 else float('inf')
    
    winning_pnl = sum(winning_trades)
    losing_pnl = abs(sum(losing_trades))
    profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
    
    # Advanced Metrics
    recovery_factor = (cumulative_return / abs(max_dd)) if max_dd < 0 else float('inf')
    
    # Kelly Criterion
    wr_decimal = win_rate / 100.0
    kelly = (wr_decimal - (1.0 - wr_decimal) / payoff_ratio) * 100 if payoff_ratio > 0 and payoff_ratio != float('inf') else 0.0
    
    # Omega Ratio (threshold = 0)
    positive_returns = equity_df['returns'][equity_df['returns'] > 0].sum()
    negative_returns = abs(equity_df['returns'][equity_df['returns'] < 0].sum())
    omega = positive_returns / negative_returns if negative_returns > 0 else float('inf')
    
    # Ulcer Index
    ulcer_index = np.sqrt(np.mean((equity_df['dd'] / 100.0) ** 2))
    
    # VaR & CVaR (95% confidence)
    var_95 = np.percentile(equity_df['returns'], 5) * 100
    cvar_95 = equity_df['returns'][equity_df['returns'] <= (var_95 / 100.0)].mean() * 100
    if np.isnan(cvar_95):
        cvar_95 = var_95
        
    # Yearly stats
    equity_df['year'] = pd.to_datetime(equity_df['date']).dt.year
    yearly_stats = []
    for year, group in equity_df.groupby('year'):
        y_initial = group['nav'].iloc[0]
        y_final = group['nav'].iloc[-1]
        y_return = (y_final - y_initial) / y_initial * 100
        
        y_mean = group['returns'].mean()
        y_vol = group['returns'].std()
        y_sharpe = (y_mean / y_vol) * np.sqrt(252) if y_vol > 0 else 0.0
        
        group['y_peak'] = group['nav'].cummax()
        group['y_dd'] = (group['nav'] - group['y_peak']) / group['y_peak'] * 100
        y_max_dd = group['y_dd'].min()
        
        y_trades = [t for t in trades_list if pd.to_datetime(t['entry_date']).year == year]
        y_wins = sum(1 for t in y_trades if t['win'])
        y_wr = (y_wins / len(y_trades) * 100) if len(y_trades) > 0 else 0.0
        
        y_winning_pnl = sum(t['pnl_pct'] for t in y_trades if t['win'])
        y_losing_pnl = abs(sum(t['pnl_pct'] for t in y_trades if not t['win']))
        y_pf = y_winning_pnl / y_losing_pnl if y_losing_pnl > 0 else float('inf')
        
        yearly_stats.append({
            'year': year,
            'return': y_return,
            'sharpe': y_sharpe,
            'max_dd': y_max_dd,
            'win_rate': y_wr,
            'profit_factor': y_pf
        })
        
    return {
        'initial_capital': initial_capital,
        'final_nav': final_nav,
        'cumulative_return': cumulative_return,
        'cagr': cagr,
        'volatility': ann_vol / 100.0, # as fraction
        'sharpe': sharpe,
        'sortino': sortino,
        'max_dd': max_dd,
        'calmar': calmar,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'largest_win': largest_win,
        'largest_loss': largest_loss,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_fees_paid': total_fees_paid,
        'recovery_factor': recovery_factor,
        'kelly': kelly,
        'omega': omega,
        'ulcer_index': ulcer_index,
        'var_95': var_95,
        'cvar_95': cvar_95,
        'payoff_ratio': payoff_ratio,
        'yearly_stats': yearly_stats
    }

def print_stage_report(stage_name, metrics):
    """
    Prints the structured Stage report with three sub-sections:
    - OVERVIEW
    - PERFORMANCE
    - ANALYSIS
    """
    if not metrics:
        print(f"[!] No metrics calculated for stage: {stage_name}")
        return
        
    print("\n" + "=" * 90)
    print(f" STAGE: {stage_name.upper()}")
    print("=" * 90)
    
    # ----------------------------------------------------
    # 1. OVERVIEW
    # ----------------------------------------------------
    print("\n[1] OVERVIEW")
    print("-" * 90)
    print(f"Aggregate Data:")
    print(f"  Sharpe: {metrics['sharpe']:.2f} | CAGR: {metrics['cagr']:+.2f}% | Max Drawdown: {metrics['max_dd']:.2f}% | Profit Factor: {metrics['profit_factor']:.2f} | Calmar: {metrics['calmar']:.2f}")
    print("\nYearly Breakdown:")
    print(f"{'Year':<6} | {'Sharpe':<8} | {'CAGR':<10} | {'Max Drawdown':<14} | {'Profit Factor':<13} | {'Calmar':<8}")
    print("-" * 90)
    for y in metrics['yearly_stats']:
        pf_str = f"{y['profit_factor']:.2f}" if y['profit_factor'] != float('inf') else "N/A"
        y_calmar = (y['return'] / abs(y['max_dd'])) if y['max_dd'] < 0 else float('inf')
        y_calmar_str = f"{y_calmar:.2f}" if y_calmar != float('inf') else "N/A"
        print(f"{y['year']:<6} | {y['sharpe']:<8.2f} | {y['return']:+10.2f}% | {y['max_dd']:<14.2f}% | {pf_str:<13} | {y_calmar_str:<8}")
    print("-" * 90)
    
    # ----------------------------------------------------
    # 2. PERFORMANCE
    # ----------------------------------------------------
    print("\n[2] PERFORMANCE")
    print("-" * 90)
    print(f"{'Transaction Analysis':<35} | {'Performance Metrics':<35}")
    print("-" * 90)
    print(f"  Initial Capital : {metrics['initial_capital']:,.0f} VND          |  Cumulative Return: {metrics['cumulative_return']:+.2f}%")
    print(f"  Net Equity      : {metrics['final_nav']:,.0f} VND          |  CAGR             : {metrics['cagr']:+.2f}%")
    print(f"  Total Profit    : {metrics['cumulative_return']:+.2f}%                 |  Win Rate         : {metrics['win_rate']:.2f}%")
    print(f"  Total Fees      : {metrics['total_fees_paid']:,.0f} VND          |  Profit Factor (PF): {metrics['profit_factor']:.2f}")
    print(f"  Total Trades    : {metrics['total_trades']:<5}                   |  Sharpe Ratio     : {metrics['sharpe']:.2f}")
    print(f"  Largest Win     : {metrics['largest_win']:+.2f}%                  |  Sortino Ratio    : {metrics['sortino']:.2f}")
    print(f"  Largest Loss    : {metrics['largest_loss']:+.2f}%                  |  Calmar Ratio     : {metrics['calmar']:.2f}")
    print(f"  Avg Win         : {metrics['avg_win']:+.2f}%                  |  Payoff Ratio     : {metrics['payoff_ratio']:.2f}")
    print(f"  Avg Loss        : {metrics['avg_loss']:+.2f}%                  |  Volatility       : {metrics['volatility']:.2f}")
    print(f"  Unrealized PnL  : 0 VND                      |  Max Drawdown     : {metrics['max_dd']:.2f}%")
    print("-" * 90)
    print("Advanced Metrics:")
    print(f"  Recovery Factor : {metrics['recovery_factor']:.2f}")
    print(f"  Kelly Criterion : {metrics['kelly']:+.2f}%")
    print(f"  Omega Ratio     : {metrics['omega']:.2f}")
    print(f"  Ulcer Index     : {metrics['ulcer_index']:.4f}")
    print(f"  VaR (95%)       : {metrics['var_95']:.2f}%")
    print(f"  CVaR (95%)      : {metrics['cvar_95']:.2f}%")
    print("-" * 90)
    
    # ----------------------------------------------------
    # 3. ANALYSIS (Target Verification)
    # ----------------------------------------------------
    print("\n[3] ANALYSIS (Benchmark Status)")
    print("-" * 90)
    
    # Evaluation against targets
    targets = [
        {"name": "Sharpe Ratio", "val": metrics['sharpe'], "op": ">=", "target": 1.30, "fmt": "{:.2f}"},
        {"name": "CAGR", "val": metrics['cagr'], "op": ">=", "target": 15.0, "fmt": "{:+.2f}%"},
        {"name": "Max Drawdown", "val": metrics['max_dd'], "op": ">=", "target": -35.0, "fmt": "{:.2f}%"}, # DD is negative, so DD >= -35% (e.g. -20% is better)
        {"name": "Profit Factor", "val": metrics['profit_factor'], "op": ">=", "target": 1.20, "fmt": "{:.2f}"},
        {"name": "Calmar Ratio", "val": metrics['calmar'], "op": ">=", "target": 1.10, "fmt": "{:.2f}"}
    ]
    
    pass_count = 0
    fail_count = 0
    
    print(f"{'Metric':<25} | {'Target':<15} | {'Actual':<12} | {'Status':<10}")
    print("-" * 90)
    for t in targets:
        passed = False
        if t['op'] == ">=":
            passed = t['val'] >= t['target']
            
        status_str = "PASS" if passed else "FAIL"
        if passed:
            pass_count += 1
        else:
            fail_count += 1
            
        target_str = f">= {t['target']}"
        if "%" in t['fmt']:
            target_str = f">= {t['target']}%"
            
        actual_str = t['fmt'].format(t['val'])
        print(f"{t['name']:<25} | {target_str:<15} | {actual_str:<12} | {status_str:<10}")
        
    print("-" * 90)
    print(f"IS Testing Status: All 5 | Pass {pass_count} | Fail {fail_count} | Pending 0")
    print("=" * 90 + "\n")
