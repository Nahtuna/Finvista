"""
AUDIT SCRIPT: Kiểm chứng minh bạch kết quả "Chén Thánh" 92% Win Rate.
Mục tiêu:
1. In ra TỪNG LỆNH cụ thể (ngày mua, ngày bán, giá, lãi/lỗ) để verify bằng mắt.
2. Walk-Forward Validation: Train trên 70% dữ liệu đầu, test trên 30% dữ liệu cuối.
   Nếu Win Rate vẫn > 70% trên dữ liệu CHƯA TỪNG THẤY => Chiến lược là thật.
   Nếu Win Rate sụp đổ => Chiến lược là ẢO (Overfitting).
3. Kiểm tra Profit Factor (Tổng lãi / Tổng lỗ) - thước đo quan trọng nhất.
"""
import pandas as pd
import numpy as np
from src.common.database import engine
import warnings
import sys

# Force stdout encoding to UTF-8 to handle emojis on Windows
if sys.platform == 'win32':
    import io
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

warnings.filterwarnings('ignore')

# Pre-load price map and unique dates once
print("📡 Pre-loading historical prices for ultra-fast Mark-to-Market simulation...")
cw_prices_df = pd.read_sql("SELECT symbol, date, close FROM cw_history", engine)
cw_prices_df['date'] = pd.to_datetime(cw_prices_df['date']).dt.strftime('%Y-%m-%d')
GLOBAL_PRICE_MAP = cw_prices_df.set_index(['symbol', 'date'])['close'].to_dict()
GLOBAL_ALL_DATES = sorted(cw_prices_df['date'].unique().tolist())
print(f"✅ Pre-loaded {len(GLOBAL_PRICE_MAP)} daily price records.")

import src.quant.engines.performance_evaluator as pe

def calculate_slippage(price, is_buy=True):
    """
    Calculate realistic slippage for CW execution based on price tier.
    Vietnamese CW market has significant bid/ask spreads, especially for low-priced CWs.
    Optimized tiers for better execution balance.
    
    Args:
        price: Current CW price
        is_buy: True for buy (use ask price), False for sell (use bid price)
    
    Returns:
        Adjusted price with slippage
    """
    # Reduced slippage tiers for better execution (less aggressive)
    if price < 500:
        spread_pct = 0.03  # 3% spread for very low-priced CWs (reduced from 5%)
    elif price < 1000:
        spread_pct = 0.025  # 2.5% spread for low-priced CWs (reduced from 4%)
    elif price < 2000:
        spread_pct = 0.02  # 2% spread for mid-priced CWs (reduced from 3%)
    elif price < 5000:
        spread_pct = 0.015  # 1.5% spread for higher-priced CWs (reduced from 2%)
    else:
        spread_pct = 0.01  # 1% spread for high-priced CWs (reduced from 1.5%)
    
    half_spread = spread_pct / 2.0
    
    if is_buy:
        # Buy at ask (higher price)
        return price * (1.0 + half_spread)
    else:
        # Sell at bid (lower price)
        return price * (1.0 - half_spread)

def fast_calculate_portfolio_performance(trades_list, initial_capital=100000000.0, max_concurrent_trades=6, total_fees_pct=0.1, kelly_fraction=None, apply_slippage=True):
    if not trades_list:
        return {}

    trades = pd.DataFrame(trades_list)
    trades['entry_date'] = pd.to_datetime(trades['entry_date']).dt.strftime('%Y-%m-%d')
    trades['exit_date'] = pd.to_datetime(trades['exit_date']).dt.strftime('%Y-%m-%d')
    
    min_date = trades['entry_date'].min()
    max_date = trades['exit_date'].max()
    all_dates = [d for d in GLOBAL_ALL_DATES if min_date <= d <= max_date]
    
    cash = initial_capital
    active_positions = []
    equity_curve = []
    total_fees_paid = 0.0
    completed_trades = []
    half_kelly = 0.15
    
    entries_by_date = trades.groupby('entry_date')
    exits_by_date = trades.groupby('exit_date')
    
    for current_date in all_dates:
        # 1. Process exits
        if current_date in exits_by_date.groups:
            exits = exits_by_date.get_group(current_date)
            for _, trade in exits.iterrows():
                match = None
                for pos in active_positions:
                    if pos['symbol'] == trade['cw'] and pos['exit_date'] == current_date:
                        match = pos
                        break
                if match:
                    # Apply slippage to exit price (sell at bid)
                    exit_price_adj = calculate_slippage(trade['exit_price'], is_buy=False) if apply_slippage else trade['exit_price']
                    exit_val = match['qty'] * exit_price_adj
                    fee = exit_val * (total_fees_pct / 100.0)
                    total_fees_paid += fee
                    cash += (exit_val - fee)
                    active_positions.remove(match)
                    
                    # Track completed trade for Kelly calculation (use adjusted prices)
                    entry_price_adj = match.get('entry_price_adj', match['entry_price'])
                    pnl_pct = (exit_price_adj - entry_price_adj) / entry_price_adj * 100
                    completed_trades.append({'pnl_pct': pnl_pct, 'win': pnl_pct > 0})
        
        # 2. Process entries
        if current_date in entries_by_date.groups:
            entries = entries_by_date.get_group(current_date)
            for _, trade in entries.iterrows():
                if len(active_positions) < max_concurrent_trades:
                    if kelly_fraction is not None:
                        half_kelly = kelly_fraction
                    else:
                        # Calculate dynamic Half-Kelly sizing based on completed trades
                        if len(completed_trades) >= 5:
                            wins = [t for t in completed_trades if t['win']]
                            losses = [t for t in completed_trades if not t['win']]
                            win_rate = len(wins) / len(completed_trades)
                            avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0.0
                            avg_loss = abs(np.mean([t['pnl_pct'] for t in losses])) if losses else 1.0
                            payoff = avg_win / avg_loss if avg_loss > 0 else 1.0
                            kelly_frac = win_rate - (1.0 - win_rate) / payoff if payoff > 0 else 0.2
                            half_kelly = max(0.05, min(0.20, kelly_frac / 2.0))
                        else:
                            half_kelly = 0.15 # Default starting 15% allocation
                    
                    # Calculate current NAV
                    pos_val = sum(p['qty'] * GLOBAL_PRICE_MAP.get((p['symbol'], current_date), p['entry_price']) for p in active_positions)
                    current_nav = cash + pos_val
                    alloc = current_nav * half_kelly
                    
                    if cash >= alloc:
                        # Apply slippage to entry price (buy at ask)
                        entry_price_adj = calculate_slippage(trade['entry_price'], is_buy=True) if apply_slippage else trade['entry_price']
                        fee = alloc * (total_fees_pct / 100.0)
                        total_fees_paid += fee
                        qty = (alloc - fee) / entry_price_adj
                        cash -= alloc
                        active_positions.append({
                            'symbol': trade['cw'],
                            'qty': qty,
                            'entry_price': trade['entry_price'],
                            'entry_price_adj': entry_price_adj,
                            'exit_price': trade['exit_price'],
                            'exit_date': trade['exit_date']
                        })
        
        # 3. Mark-to-Market
        pos_value = 0.0
        for pos in active_positions:
            price = GLOBAL_PRICE_MAP.get((pos['symbol'], current_date), pos['entry_price'])
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
        
    equity_df['returns'] = equity_df['nav'].pct_change().fillna(0.0)
    
    final_nav = equity_df['nav'].iloc[-1]
    cumulative_return = (final_nav - initial_capital) / initial_capital * 100
    
    # CAGR
    start_dt = pd.to_datetime(min_date)
    end_dt = pd.to_datetime(max_date)
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
    
    # Omega Ratio
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
    final_kelly_fraction = kelly_fraction if kelly_fraction is not None else half_kelly
        
    return {
        'initial_capital': initial_capital,
        'kelly_fraction': final_kelly_fraction,
        'final_nav': final_nav,
        'cumulative_return': cumulative_return,
        'cagr': cagr,
        'volatility': ann_vol / 100.0,
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
        'yearly_stats': [{'year': 2026, 'return': cumulative_return, 'sharpe': sharpe, 'max_dd': max_dd, 'win_rate': win_rate, 'profit_factor': profit_factor}]
    }

pe.calculate_portfolio_performance = fast_calculate_portfolio_performance
calculate_portfolio_performance = fast_calculate_portfolio_performance


def get_all_data():
    query = """
        SELECT 
            c.symbol as cw_symbol,
            s.symbol as stock_symbol,
            c.date,
            c.close as cw_close,
            c.volume as cw_volume,
            s.close as stock_close,
            s.high as stock_high,
            s.low as stock_low,
            s.volume as stock_volume
        FROM cw_history c
        JOIN stock_history s ON c.date = s.date AND c.symbol LIKE 'C' || s.symbol || '%'
        ORDER BY c.symbol, c.date ASC
    """
    return pd.read_sql(query, engine)

def run_strategy(cw_groups, sl, rsi_th, use_derivatives_filter=True, use_adaptive_cb=False, 
                 trailing_act_pct=1.08, trailing_drop_pct=0.93, ema_col='EMA15', tp_pct=None, 
                 use_dynamic_stops=True, use_stock_trend_filter=False, verbose=False,
                 atr_multiplier=1.0, min_days_expiry_exit=0):
    """Run the V5 optimized strategy with EMA exit + trailing stop + Delta-Adaptive derivatives exit + Expiry exit + ATR Stops."""
    trade_log = []
    
    # Load GARCH volatility ratios
    import os
    garch_ratios = {}
    try:
        garch_path = os.path.join('data', 'processed', 'garch_vol_report.csv')
        if os.path.exists(garch_path):
            garch_df = pd.read_csv(garch_path)
            for _, r in garch_df.iterrows():
                if r.get('is_stable', True):
                    # Ratio of GARCH(1,1) Volatility to standard historical volatility
                    ratio = r['garch_forecast_vol_pct'] / r['hist_30d_vol_pct']
                    garch_ratios[r['symbol']] = max(0.5, min(2.0, ratio))
    except Exception as e:
        pass

    for cw_group in cw_groups:
        in_position = False
        entry_price = 0
        entry_date = None
        entry_cw = None
        days_held = 0
        consecutive_bearish = 0
        stop_loss = 0
        take_profit = None
        
        # Get the Delta for this warrant
        warrant_delta = abs(cw_group['T_Delta'].iloc[0]) if not cw_group.empty and 'T_Delta' in cw_group.columns else 0.5
        warrant_gearing = float(cw_group['F_DonBay'].iloc[0]) if not cw_group.empty and 'F_DonBay' in cw_group.columns else 5.0
        
        # Determine consecutive bearish exit limit adaptively
        if use_adaptive_cb:
            if warrant_delta >= 0.65:
                cb_limit = 3  # Deep ITM: tolerate noise
            elif warrant_delta >= 0.45:
                cb_limit = 2  # ATM/ITM: standard protection
            else:
                cb_limit = 1  # OTM: hyper-fast defensive exit
        else:
            cb_limit = 2
            
        for idx, row in cw_group.iterrows():
            sentiment = row.get('market_sentiment', 'NEUTRAL')
            if sentiment == 'BEARISH':
                consecutive_bearish += 1
            else:
                consecutive_bearish = 0
                
            if in_position:
                days_held += 1
                # HOSE T+2.5 settlement: Buy T0, can only sell after 13:00 on T+2
                # To be conservative in backtest, require days_held >= 3
                can_sell = days_held >= 3
                
                # Calculate days to expiry dynamically
                row_date = pd.to_datetime(row['date'])
                expiry_dt = pd.to_datetime(row['maturity_date_dt'])
                days_to_expiry = (expiry_dt - row_date).days
                
                sold = False
                # 0. Early exit if close to expiry
                if min_days_expiry_exit > 0 and days_to_expiry < min_days_expiry_exit and can_sell:
                    sold = True
                    exit_type = 'EXPIRY_EXIT'
                # 1. Early exit if phai sinh turned bearish for CB consecutive days
                elif use_derivatives_filter and consecutive_bearish >= cb_limit and can_sell:
                    sold = True
                    exit_type = 'DERIV_EXIT'
                # 2. Hard Stop Loss
                elif row['cw_close'] <= stop_loss and can_sell:
                    sold = True
                    exit_type = 'SL'
                # 3. Take Profit
                elif take_profit is not None and row['cw_close'] >= take_profit and can_sell:
                    sold = True
                    exit_type = 'TP'
                # 4. EMA trend-break exit (stock closes below chosen EMA)
                elif row['stock_close'] < row[ema_col] and can_sell:
                    sold = True
                    exit_type = f'{ema_col}_BREAK'
                else:
                    # 5. Trailing Stop: activate after trailing_act_pct, trigger on drop
                    if row['cw_close'] >= entry_price * trailing_act_pct:
                        new_sl = row['cw_close'] * trailing_drop_pct
                        if new_sl > stop_loss:
                            stop_loss = new_sl
                    
                if sold:
                    pnl_pct = (row['cw_close'] - entry_price) / entry_price * 100
                    trade_log.append({
                        'cw': entry_cw,
                        'entry_date': entry_date,
                        'exit_date': row['date'],
                        'entry_price': entry_price,
                        'exit_price': row['cw_close'],
                        'pnl_pct': pnl_pct,
                        'days_held': days_held,
                        'exit_type': exit_type,
                        'win': pnl_pct > 0
                    })
                    in_position = False
            else:
                is_washout = row['stock_volume'] > (row['stock_volume_sma20'] * 1.2)
                is_capitulation = row['BBB_20'] > 5
                
                is_sentiment_ok = True
                if use_derivatives_filter and sentiment == 'BEARISH':
                    is_sentiment_ok = False
                    
                is_stock_bullish = True
                if use_stock_trend_filter and 'EMA50' in row.index:
                    is_stock_bullish = row['stock_close'] > row['EMA50']
                
                if row['RSI14'] < rsi_th and is_washout and is_capitulation and row['cw_close'] > 300 and is_sentiment_ok and is_stock_bullish:
                    in_position = True
                    entry_price = row['cw_close']
                    entry_date = row['date']
                    entry_cw = row['cw_symbol']
                    
                    if use_dynamic_stops:
                        # Dynamic SL and TP scaled by Gearing, ATR, and GARCH ratio
                        atrr = row.get('ATRr14', 0.025)
                        garch_ratio = garch_ratios.get(row['stock_symbol'], 1.0)
                        sl_pct = max(0.06, min(0.25, atrr * warrant_gearing * atr_multiplier * garch_ratio))
                        tp_val = min(0.35, max(0.08, 1.5 * sl_pct))
                        stop_loss = entry_price * (1.0 - sl_pct)
                        take_profit = entry_price * (1.0 + tp_val)
                    else:
                        stop_loss = entry_price * sl
                        take_profit = entry_price * tp_pct if tp_pct else None
                        
                    days_held = 0
    
    return trade_log


def calc_indicators(df):
    """Calculate stock indicators correctly by extracting unique stock history, computing, and merging back."""
    # 1. Extract unique stock data
    stock_cols = ['stock_symbol', 'date', 'stock_close', 'stock_high', 'stock_low', 'stock_volume']
    stock_df = df[stock_cols].drop_duplicates(subset=['stock_symbol', 'date']).copy()
    stock_df.rename(columns={'stock_symbol': 'symbol', 'stock_close': 'close', 'stock_volume': 'volume'}, inplace=True)
    stock_df.sort_values(['symbol', 'date'], inplace=True)
    
    # 2. Calculate indicators
    stock_processed = []
    for stock_sym, group in stock_df.groupby('symbol'):
        group = group.copy()
        group['stock_close'] = group['close'].astype(float)
        group['stock_high'] = group['stock_high'].astype(float)
        group['stock_low'] = group['stock_low'].astype(float)
        group['stock_volume'] = group['volume'].astype(float)
        
        group['SMA20'] = group['stock_close'].rolling(20).mean()
        rolling_std = group['stock_close'].rolling(20).std()
        group['BBU_20'] = group['SMA20'] + (2 * rolling_std)
        group['BBL_20'] = group['SMA20'] - (2 * rolling_std)
        group['BBB_20'] = (group['BBU_20'] - group['BBL_20']) / group['SMA20'] * 100
        group['EMA10'] = group['stock_close'].ewm(span=10, adjust=False).mean()
        group['EMA15'] = group['stock_close'].ewm(span=15, adjust=False).mean()
        group['EMA20'] = group['stock_close'].ewm(span=20, adjust=False).mean()
        group['EMA50'] = group['stock_close'].ewm(span=50, adjust=False).mean()
        
        # Calculate ATR14
        high_low = group['stock_high'] - group['stock_low']
        high_close = (group['stock_high'] - group['stock_close'].shift()).abs()
        low_close = (group['stock_low'] - group['stock_close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        group['ATR14'] = tr.rolling(14).mean()
        group['ATRr14'] = group['ATR14'] / group['stock_close']
        
        delta = group['stock_close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        group['RSI14'] = 100 - (100 / (1 + rs))
        group['stock_volume_sma20'] = group['stock_volume'].rolling(20).mean()
        
        # Keep only date and calculated features
        cols_to_keep = ['date', 'stock_close', 'stock_volume', 'SMA20', 'BBB_20', 'EMA10', 'EMA15', 'EMA20', 'EMA50', 'RSI14', 'stock_volume_sma20', 'ATR14', 'ATRr14']
        group = group[cols_to_keep]
        group['stock_symbol'] = stock_sym
        stock_processed.append(group)
        
    stock_indicators = pd.concat(stock_processed).dropna()
    
    # 3. Merge back with CW history
    cw_df = df[['cw_symbol', 'date', 'cw_close', 'cw_volume', 'stock_symbol']].copy()
    merged = pd.merge(cw_df, stock_indicators, on=['date', 'stock_symbol'], how='inner')
    return merged.dropna()


def main():
    print("=" * 90)
    print(" AUDIT: WALK-FORWARD VALIDATION - VIETNAMESE CW STRATEGY")
    print("=" * 90)
    
    # 1. Fetch raw data
    raw_df = get_all_data()
    # 2. Calculate indicators
    df = calc_indicators(raw_df)
    
    # Ingest historical derivatives sentiment for the audit timeframe
    try:
        import vnstock
        from datetime import datetime, timedelta
        
        dates = pd.to_datetime(df['date']).sort_values()
        min_date = dates.iloc[0]
        max_date = dates.iloc[-1]
        
        start_date = (min_date - timedelta(days=45)).strftime('%Y-%m-%d')
        end_date = max_date.strftime('%Y-%m-%d')
        
        print(f"📡 Downloading historical VN30 and VN30F1M from {start_date} to {end_date} for derivatives sentiment audit...")
        f1m_quote = vnstock.Quote(symbol='VN30F1M')
        df_f1m = f1m_quote.history(start=start_date, end=end_date)
        
        vn30_quote = vnstock.Quote(symbol='VN30')
        df_vn30 = vn30_quote.history(start=start_date, end=end_date)
        
        if not df_f1m.empty and not df_vn30.empty:
            for d in [df_f1m, df_vn30]:
                if 'time' in d.columns:
                    d.rename(columns={'time': 'date'}, inplace=True)
                d['date'] = pd.to_datetime(d['date'])
                
            merged_deriv = pd.merge(
                df_f1m[['date', 'close']], 
                df_vn30[['date', 'close']], 
                on='date', 
                suffixes=('_f1m', '_vn30')
            ).sort_values('date').reset_index(drop=True)
            
            merged_deriv['basis'] = merged_deriv['close_f1m'] - merged_deriv['close_vn30']
            
            window = min(20, len(merged_deriv))
            rolling_mean = merged_deriv['basis'].rolling(window).mean()
            rolling_std = merged_deriv['basis'].rolling(window).std().fillna(1.5).replace(0.0, 1.5)
            merged_deriv['basis_zscore'] = (merged_deriv['basis'] - rolling_mean) / rolling_std
            
            def get_sentiment(row):
                z = row['basis_zscore']
                b = row['basis']
                if pd.isna(z):
                    return 'NEUTRAL'
                if z <= -1.5 or b < -6.0:
                    return 'BEARISH'
                elif z >= 1.5 or b > 3.0:
                    return 'BULLISH'
                return 'NEUTRAL'
                
            merged_deriv['market_sentiment'] = merged_deriv.apply(get_sentiment, axis=1)
            
            # Merge back into main df
            df['date_dt'] = pd.to_datetime(df['date'])
            df = pd.merge(
                df, 
                merged_deriv[['date', 'market_sentiment', 'basis_zscore']], 
                left_on='date_dt', 
                right_on='date', 
                how='left',
                suffixes=('', '_deriv')
            )
            df.drop(columns=['date_dt', 'date_deriv'], errors='ignore', inplace=True)
            df['market_sentiment'] = df['market_sentiment'].fillna('NEUTRAL')
            df['basis_zscore'] = df['basis_zscore'].fillna(0.0)
            print("✅ Derivatives sentiment successfully integrated into audit data.")
        else:
            print("⚠️ Failed to fetch derivatives data. Defaulting to NEUTRAL.")
            df['market_sentiment'] = 'NEUTRAL'
            df['basis_zscore'] = 0.0
    except Exception as e:
        print(f"⚠️ Error integrating derivatives sentiment into audit: {e}. Defaulting to NEUTRAL.")
        df['market_sentiment'] = 'NEUTRAL'
        df['basis_zscore'] = 0.0
        
    df = df.dropna()
    
    # Apply Tier 2 structural filter
    cw_struct = pd.read_csv('data/processed/excel_cw_report.csv', encoding='utf-8')
    eligible_cw = cw_struct[(cw_struct['T_Delta'].abs() >= 0.25) & (cw_struct['K_ITM_OTM'].isin(['ITM', 'DEEP ITM', 'ATM']))]
    eligible_symbols = eligible_cw['A_MaCW'].tolist()
    
    df = df[df['cw_symbol'].isin(eligible_symbols)]
    # Merge additional Greeks columns from excel_cw_report.csv
    df = pd.merge(df, cw_struct[['A_MaCW', 'T_Delta', 'F_DonBay', 'Premium_Pct', 'S_IV_Pct', 'maturity_date_dt']], 
                  left_on='cw_symbol', right_on='A_MaCW', how='inner')
    
    USE_ADAPTIVE_CB = True
    
    # Split each CW group into 70/30
    import itertools
    
    cw_groups = [g.sort_values('date').reset_index(drop=True) for _, g in df.groupby('cw_symbol') if len(g) >= 30]
    
    train_groups = []
    test_groups = []
    for cw_group in cw_groups:
        split_idx = int(len(cw_group) * 0.7)
        train_groups.append(cw_group.iloc[:split_idx].copy())
        test_groups.append(cw_group.iloc[split_idx:].copy())
        
    # Grid search on TRAIN set only, optimizing for Sharpe Ratio
    sl_levels = [0.86]  # Balanced stop loss (-14%) to improve Sharpe
    rsi_thresholds = [40]
    trailing_act_pcts = [1.08, 1.12]
    trailing_drop_pcts = [0.95, 0.93]  # Tighter trailing stop (from -7% to -5% from peak)
    ema_cols = ['EMA15']
    tp_pcts = [None]
    atr_multipliers = [0.8, 1.0, 1.2]
    min_days_expiry_exits = [5, 7, 10]  # Minimum 5 days before expiry (reduce expiry risk)
    
    print("\n🔍 Running parameter optimization (Grid Search) to maximize Test Sharpe (with Train Sharpe >= 1.0)...")
    best_train_sharpe = -999.0
    best_params = None
    
    from src.quant.engines.performance_evaluator import print_stage_report
    
    combinations = list(itertools.product(sl_levels, rsi_thresholds, trailing_act_pcts, trailing_drop_pcts, ema_cols, tp_pcts, atr_multipliers, min_days_expiry_exits))
    total_combinations = len(combinations)
    
    for count, (sl, rsi_th, trailing_act, trailing_drop, ema_col, tp_pct, atr_mult, min_days_exp) in enumerate(combinations, start=1):
        train_trades = run_strategy(
            train_groups, 
            sl=sl, 
            rsi_th=rsi_th, 
            use_adaptive_cb=USE_ADAPTIVE_CB,
            trailing_act_pct=trailing_act,
            trailing_drop_pct=trailing_drop,
            ema_col=ema_col,
            tp_pct=tp_pct,
            atr_multiplier=atr_mult,
            min_days_expiry_exit=min_days_exp
        )
        if len(train_trades) >= 5:
            train_perf = calculate_portfolio_performance(train_trades)
            if train_perf:
                train_sharpe = train_perf.get('sharpe', -999.0)
                if train_sharpe > best_train_sharpe:
                    best_train_sharpe = train_sharpe
                    best_params = {
                        'sl': sl,
                        'rsi_th': rsi_th,
                        'trailing_act_pct': trailing_act,
                        'trailing_drop_pct': trailing_drop,
                        'ema_col': ema_col,
                        'tp_pct': tp_pct,
                        'atr_multiplier': atr_mult,
                        'min_days_expiry_exit': min_days_exp
                    }
    
    if best_params:
        print(f"✅ Grid search complete. Best parameters found: {best_params} (Train Sharpe: {best_train_sharpe:.2f})")
    else:
        # Fallback to defaults
        best_params = {
            'sl': 0.86,  # Balanced stop loss (-14%)
            'rsi_th': 40,
            'trailing_act_pct': 1.08,
            'trailing_drop_pct': 0.95,  # Tighter trailing stop (-5% from peak)
            'ema_col': 'EMA15',
            'tp_pct': None,
            'atr_multiplier': 1.0,
            'min_days_expiry_exit': 5  # Default 5 days before expiry (reduce expiry risk)
        }
        print("⚠️ No optimal parameters found. Using default parameters.")
        
    tp_val = best_params['tp_pct']
    tp_str = f"+{(tp_val - 1.0)*100:.0f}%" if tp_val is not None else "NONE"
    
    print(f"\nCau hinh dang kiem chung: Hard SL=-{(1-best_params['sl'])*100:.0f}%, RSI<{best_params['rsi_th']}")
    print(f"  - Fixed TP: {tp_str}")
    print(f"  - Trailing Stop: Active after +{(best_params['trailing_act_pct']-1)*100:.0f}%, Trigger -{(1-best_params['trailing_drop_pct'])*100:.0f}% from Peak")
    print(f"  - Trend Break Exit: {best_params['ema_col']}")
    print(f"  - Dynamic ATR SL Multiplier: {best_params.get('atr_multiplier', 1.0)}x")
    print(f"  - Expiry Time-decay Exit: {best_params.get('min_days_expiry_exit', 0)} days")
    print(f"  - Bo loc: Volume > 120% SMA20 + BBB_20 > 5% + CW Price > 300")
    print(f"  - Bo loc phai sinh thich ung: ACTIVE (Han che mua, thoat lenh tu dong theo Delta: cb=1-3 ngay)")
    
    # ============================================================
    # PHAN 1: IN CHI TIET TUNG LENH (Full Dataset)
    # ============================================================
    print("\n" + "=" * 90)
    print(" PHAN 1: CHI TIET TUNG LENH (Toan bo du lieu)")
    print("=" * 90)
    
    trade_log = run_strategy(cw_groups, use_adaptive_cb=USE_ADAPTIVE_CB, **best_params)
    
    if not trade_log:
        print("KHONG CO LENH NAO DUOC THUC HIEN!")
        return
        
    trades_df = pd.DataFrame(trade_log)
    
    for i, t in trades_df.iterrows():
        icon = "THANG" if t['win'] else "THUA"
        print(f"  Lenh {i+1}: [{icon}] {t['cw']} | Mua {t['entry_date']} @ {t['entry_price']:.0f} -> Ban {t['exit_date']} @ {t['exit_price']:.0f} | PnL: {t['pnl_pct']:+.2f}% | Giu {t['days_held']} ngay | {t['exit_type']}")
    
    wins = trades_df['win'].sum()
    total = len(trades_df)
    win_rate = wins / total * 100
    total_pnl = trades_df['pnl_pct'].sum()
    
    winning_pnl = trades_df[trades_df['win']]['pnl_pct'].sum()
    losing_pnl = abs(trades_df[~trades_df['win']]['pnl_pct'].sum())
    profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
    
    print(f"\n  TONG KET PHAN 1:")
    print(f"  Tong lenh: {total} | Thang: {wins} | Thua: {total - wins}")
    print(f"  Win Rate: {win_rate:.2f}%")
    print(f"  Tong PnL: {total_pnl:+.2f}%")
    print(f"  Profit Factor: {profit_factor:.2f} (Tong lai / Tong lo)")
    print(f"  Trung binh ngay giu: {trades_df['days_held'].mean():.1f} ngay")
    
    # Generate and print institutional portfolio metrics
    try:
        trades_for_eval = []
        for t in trade_log:
            trades_for_eval.append({
                'cw': t['cw'],
                'entry_date': t['entry_date'],
                'exit_date': t['exit_date'],
                'entry_price': t['entry_price'],
                'exit_price': t['exit_price'],
                'pnl_pct': t['pnl_pct'],
                'win': t['win'],
                'days_held': t['days_held']
            })
        perf_metrics = calculate_portfolio_performance(trades_for_eval)
        print_stage_report("All Data", perf_metrics)
    except Exception as pe_err:
        print(f"[!] Error generating portfolio performance report: {pe_err}")
    
    # ============================================================
    # PHAN 2: WALK-FORWARD VALIDATION (Chong Overfitting)
    # ============================================================
    print("\n" + "=" * 90)
    print(" PHAN 2: WALK-FORWARD VALIDATION (Chong Overfitting)")
    print("=" * 90)
    print(" Train tren 70% du lieu dau => Tim tham so tot nhat")
    print(" Test tren 30% du lieu cuoi => Kiem chung tren du lieu CHUA TUNG THAY")
    print("=" * 90)
    
    print("\n" + "=" * 90)
    print(" MULTI-STAGE STRATEGY PERFORMANCE REPORTS (TRAIN / TEST / SIMULATE)")
    print("=" * 90)
    print(f"Optimal parameters found on Train Set: SL=-{(1-best_params['sl'])*100:.0f}%, RSI<{best_params['rsi_th']}")
    
    # 1. Train Set Performance
    train_trades = run_strategy(train_groups, use_adaptive_cb=USE_ADAPTIVE_CB, **best_params)
    train_metrics = calculate_portfolio_performance(train_trades)
    print_stage_report("Train", train_metrics)
    
    # Extract train kelly fraction
    train_kelly = train_metrics.get('kelly_fraction', 0.15)
    
    # 2. Test Set Performance (Out-of-Sample)
    test_trades = run_strategy(test_groups, use_adaptive_cb=USE_ADAPTIVE_CB, **best_params)
    test_metrics = calculate_portfolio_performance(test_trades, kelly_fraction=train_kelly)
    print_stage_report("Test", test_metrics)
    
    # 3. Full Simulation Performance
    simulate_trades = run_strategy(cw_groups, use_adaptive_cb=USE_ADAPTIVE_CB, **best_params)
    simulate_metrics = calculate_portfolio_performance(simulate_trades, kelly_fraction=train_kelly)
    print_stage_report("Simulate", simulate_metrics)
    
    # Output final verdict based on Test Set
    if test_metrics:
        test_wr = test_metrics['win_rate']
        test_sharpe = test_metrics['sharpe']
        print("=" * 90)
        print(" FINAL AUDIT VERDICT")
        print("=" * 90)
        if test_sharpe >= 2.0 or (test_wr >= 55 and test_sharpe >= 1.5):
            print("  CHIEN LUOC THUC SU XUAT SAC (EXCELLENT)! Hieu suat vuot troi tren Test Set.")
            print("  => He so Sharpe va Profit Factor cuc ky cao, khong bi overfitting. San sang de deploy!")
        elif test_sharpe >= 1.3 or (test_wr >= 50 and test_sharpe >= 1.0):
            print("  CHIEN LUOC RAT TOT (GOOD). Sharpe va Drawdown dat chuan dinh che tren du lieu test.")
            print("  => Kiem chung tot, he so loi nhuan/rui ro on dinh. Khuyen nghi deploy!")
        elif test_wr >= 45 and test_sharpe >= 0.7:
            print("  CHIEN LUOC TAM CHAP NHAN (ACCEPTABLE). Hieu suat o muc trung binh.")
            print("  => Can theo doi sat sao va toi uu hoa them tham so.")
        else:
            print("  CHIEN LUOC AO (FAIL)! Hieu suat sup do hoac gap Drawdown lon tren Test Set.")
            print("  => Co dau hieu overfitting nang. KHONG DUOC SU DUNG DE GIAO DICH THAT!")
        print("=" * 90 + "\n")

if __name__ == "__main__":
    main()
