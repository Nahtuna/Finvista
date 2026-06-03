"""
HOLY GRAIL V5: UNIVERSAL WARRANT STRATEGY WITH STRUCTURAL FILTERS
=================================================================
Triết lý: Thay vì dùng 1 chiến lược "one-size-fits-all", sử dụng dữ liệu CẤU TRÚC
(Delta, Moneyness, Days to Expiry, Score) của mỗi mã CW để LỌC TRƯỚC — chỉ đánh
những mã CW có "thể trạng tốt" rồi mới áp chiến thuật Panic Buy.

Nguồn dữ liệu:
- excel_cw_report.csv: Chứa Delta, Moneyness (ITM/ATM/OTM), days_to_expiry, G_Score
- cw_history (DB): Lịch sử giá CW
- stock_history (DB): Lịch sử giá Cổ phiếu Cơ sở
"""
import pandas as pd
import numpy as np
import itertools
from src.common.database import engine
import warnings

warnings.filterwarnings('ignore')

def get_all_data():
    query = """
        SELECT 
            c.symbol as cw_symbol,
            s.symbol as stock_symbol,
            c.date,
            c.close as cw_close,
            c.volume as cw_volume,
            s.close as stock_close,
            s.volume as stock_volume
        FROM cw_history c
        JOIN stock_history s ON c.date = s.date AND c.symbol LIKE 'C' || s.symbol || '%'
        ORDER BY c.symbol, c.date ASC
    """
    return pd.read_sql(query, engine)

def load_cw_structure():
    """Load CW structural data (Greeks, Moneyness, etc.) from excel_cw_report.csv"""
    df = pd.read_csv('data/processed/excel_cw_report.csv', encoding='utf-8')
    return df[['A_MaCW', 'B_MaCPCS', 'K_ITM_OTM', 'days_to_expiry', 
               'T_Delta', 'prob_itm', 'G_Score', 'Premium_Pct', 'F_DonBay']].copy()

def run_strategy(cw_groups, tp, sl, rsi_th, verbose=False):
    """Run strategy and return detailed trade log."""
    trade_log = []
    
    for cw_group in cw_groups:
        in_position = False
        entry_price = 0
        entry_date = None
        entry_cw = None
        days_held = 0
        
        for idx, row in cw_group.iterrows():
            if in_position:
                days_held += 1
                can_sell = days_held >= 2
                
                sold = False
                if row['cw_close'] >= entry_price * tp and can_sell:
                    sold = True
                    exit_type = 'TP'
                elif row['cw_close'] <= entry_price * sl and can_sell:
                    sold = True
                    exit_type = 'SL'
                    
                if sold:
                    pnl_pct = (row['cw_close'] - entry_price) / entry_price * 100
                    trade_log.append({
                        'cw': entry_cw,
                        'stock': row['stock_symbol'],
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
                
                if row['RSI14'] < rsi_th and is_washout and is_capitulation and row['cw_close'] > 300:
                    in_position = True
                    entry_price = row['cw_close']
                    entry_date = row['date']
                    entry_cw = row['cw_symbol']
                    days_held = 0
    
    return trade_log

def print_summary(label, trade_log):
    if not trade_log:
        print(f"  [{label}] Khong co lenh nao.")
        return 0, 0
    
    trades_df = pd.DataFrame(trade_log)
    wins = trades_df['win'].sum()
    total = len(trades_df)
    win_rate = wins / total * 100
    total_pnl = trades_df['pnl_pct'].sum()
    
    winning_pnl = trades_df[trades_df['win']]['pnl_pct'].sum()
    losing_pnl = abs(trades_df[~trades_df['win']]['pnl_pct'].sum())
    pf = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
    
    print(f"  [{label}]")
    print(f"    Tong lenh: {total} | Thang: {wins} | Thua: {total - wins}")
    print(f"    Win Rate: {win_rate:.2f}%")
    print(f"    Tong PnL: {total_pnl:+.2f}%")
    print(f"    Profit Factor: {pf:.2f}")
    
    # Show per-stock breakdown
    stock_stats = trades_df.groupby('stock').agg(
        trades=('win', 'count'),
        wins=('win', 'sum'),
        pnl=('pnl_pct', 'sum')
    )
    stock_stats['wr'] = (stock_stats['wins'] / stock_stats['trades'] * 100).round(1)
    stock_stats = stock_stats.sort_values('wr', ascending=False)
    print(f"    --- Breakdown theo CPCS ---")
    for stock, row in stock_stats.iterrows():
        icon = "+" if row['pnl'] > 0 else "-"
        print(f"      {stock}: {row['trades']} lenh, WR={row['wr']:.0f}%, PnL={row['pnl']:+.1f}%")
    
    return win_rate, total_pnl

def main():
    print("=" * 90)
    print(" HOLY GRAIL V5: UNIVERSAL STRATEGY WITH STRUCTURAL CW FILTERS")
    print("=" * 90)
    
    # Load data
    df = get_all_data()
    cw_struct = load_cw_structure()
    
    print(f"\nData loaded: {df['cw_symbol'].nunique()} CW symbols, {df['stock_symbol'].nunique()} stocks")
    print(f"CW Structure data: {len(cw_struct)} warrants with Greeks/Moneyness info")
    
    # Define filter tiers
    filters = {
        'TIER_0_NO_FILTER': lambda s: s,
        'TIER_1_ITM_ONLY': lambda s: s[s['K_ITM_OTM'].isin(['ITM', 'DEEP ITM', 'ATM'])],
        'TIER_2_HIGH_DELTA': lambda s: s[(s['T_Delta'].abs() >= 0.25) & (s['K_ITM_OTM'].isin(['ITM', 'DEEP ITM', 'ATM']))],
        'TIER_3_SWEET_SPOT': lambda s: s[
            (s['T_Delta'].abs() >= 0.25) & 
            (s['K_ITM_OTM'].isin(['ITM', 'DEEP ITM', 'ATM'])) & 
            (s['days_to_expiry'] >= 30) &
            (s['days_to_expiry'] <= 200)
        ],
        'TIER_4_ELITE': lambda s: s[
            (s['T_Delta'].abs() >= 0.30) & 
            (s['K_ITM_OTM'].isin(['ITM', 'DEEP ITM'])) & 
            (s['days_to_expiry'] >= 50) &
            (s['days_to_expiry'] <= 200) &
            (s['G_Score'] >= 60)
        ],
    }
    
    # 1. Fetch unique stock history and calculate stock indicators correctly
    stock_query = "SELECT symbol, date, close, volume FROM stock_history ORDER BY symbol, date ASC"
    stock_df = pd.read_sql(stock_query, engine)
    
    stock_processed = []
    for stock_sym, group in stock_df.groupby('symbol'):
        group = group.copy()
        group['stock_close'] = group['close'].astype(float)
        group['stock_volume'] = group['volume'].astype(float)
        
        group['SMA20'] = group['stock_close'].rolling(20).mean()
        group['EMA10'] = group['stock_close'].ewm(span=10, adjust=False).mean()
        group['EMA20'] = group['stock_close'].ewm(span=20, adjust=False).mean()
        rolling_std = group['stock_close'].rolling(20).std()
        group['BBU_20'] = group['SMA20'] + (2 * rolling_std)
        group['BBL_20'] = group['SMA20'] - (2 * rolling_std)
        group['BBB_20'] = (group['BBU_20'] - group['BBL_20']) / group['SMA20'] * 100
        
        delta = group['stock_close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        group['RSI14'] = 100 - (100 / (1 + rs))
        group['stock_volume_sma20'] = group['stock_volume'].rolling(20).mean()
        
        # Keep only date and calculated features
        cols_to_keep = ['date', 'stock_close', 'stock_volume', 'SMA20', 'EMA10', 'EMA20', 'BBB_20', 'RSI14', 'stock_volume_sma20']
        group = group[cols_to_keep]
        group['stock_symbol'] = stock_sym
        stock_processed.append(group)
        
    stock_indicators = pd.concat(stock_processed).dropna()
    
    # 2. Merge indicators into CW history
    cw_query = "SELECT symbol as cw_symbol, date, close as cw_close, volume as cw_volume FROM cw_history ORDER BY symbol, date ASC"
    cw_df = pd.read_sql(cw_query, engine)
    
    # Map CW to Stock symbol
    cw_df['stock_symbol'] = cw_df['cw_symbol'].apply(lambda x: x[1:4] if x[1:4] in stock_df['symbol'].unique() else x[1:3])
    # Validate mapping
    valid_stocks = stock_df['symbol'].unique()
    cw_df['stock_symbol'] = cw_df['cw_symbol'].apply(lambda x: next((s for s in valid_stocks if x[1:].startswith(s)), None))
    cw_df = cw_df.dropna(subset=['stock_symbol'])
    
    # Merge
    df = pd.merge(cw_df, stock_indicators, on=['date', 'stock_symbol'], how='inner')
    df = df.dropna()
    
    # Best params from previous grid search (Optimized to maximize Sharpe Ratio)
    TP = 1.07
    SL = 0.80
    RSI_TH = 40
    
    print(f"\nChien luoc: Panic Buy (RSI<{RSI_TH}, Volume Washout, BB Expansion)")
    print(f"TP=+{(TP-1)*100:.0f}%, SL=-{(1-SL)*100:.0f}%, T+2.5 Lock")
    
    # Run strategy with each filter tier
    for tier_name, filter_fn in filters.items():
        print(f"\n{'='*80}")
        print(f" {tier_name}")
        print(f"{'='*80}")
        
        # Apply structural filter
        eligible_cw = filter_fn(cw_struct)
        eligible_symbols = eligible_cw['A_MaCW'].tolist()
        
        # Filter df to only eligible CW symbols
        filtered_df = df[df['cw_symbol'].isin(eligible_symbols)]
        
        if filtered_df.empty:
            print(f"  Khong co CW nao thoa dieu kien loc.")
            continue
        
        cw_count = filtered_df['cw_symbol'].nunique()
        print(f"  CW thoa dieu kien: {cw_count}/{df['cw_symbol'].nunique()} ma")
        
        # Split into groups
        all_groups = [g.sort_values('date').reset_index(drop=True) 
                      for _, g in filtered_df.groupby('cw_symbol') if len(g) >= 20]
        
        if not all_groups:
            print(f"  Khong du du lieu de backtest.")
            continue
            
        # Split 70/30 for walk-forward
        train_groups = [g.iloc[:int(len(g)*0.7)].copy() for g in all_groups]
        test_groups = [g.iloc[int(len(g)*0.7):].copy() for g in all_groups]
        
        # Full dataset results
        full_trades = run_strategy(all_groups, TP, SL, RSI_TH)
        print_summary("FULL DATA", full_trades)
        
        # Walk-forward results
        test_trades = run_strategy(test_groups, TP, SL, RSI_TH)
        wr, pnl = print_summary("TEST SET (30% cuoi - Out-of-Sample)", test_trades)

if __name__ == "__main__":
    main()
