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

def calc_indicators(df):
    processed = []
    for stock, group in df.groupby('stock_symbol'):
        group = group.copy()
        group['SMA10'] = group['stock_close'].rolling(10).mean()
        group['SMA20'] = group['stock_close'].rolling(20).mean()
        
        rolling_std = group['stock_close'].rolling(20).std()
        group['BBL_20'] = group['SMA20'] - (2 * rolling_std)
        group['BBU_20'] = group['SMA20'] + (2 * rolling_std)
        group['BBB_20'] = (group['BBU_20'] - group['BBL_20']) / group['SMA20'] * 100
        
        delta = group['stock_close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        group['RSI14'] = 100 - (100 / (1 + rs))
        group['stock_volume_sma20'] = group['stock_volume'].rolling(20).mean()
        processed.append(group)
    return pd.concat(processed).dropna()

def run_strategy(cw_groups, tp, sl, rsi_th, verbose=False):
    """Run the V4 Holy Grail strategy and return detailed trade log."""
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

def main():
    print("=" * 90)
    print(" AUDIT: KIEM CHUNG MINH BACH KET QUA 'CHEN THANH' 92% WIN RATE")
    print("=" * 90)
    
    # 1. Fetch unique stock history and calculate stock indicators correctly
    stock_query = "SELECT symbol, date, close, volume FROM stock_history ORDER BY symbol, date ASC"
    stock_df = pd.read_sql(stock_query, engine)
    
    stock_processed = []
    for stock_sym, group in stock_df.groupby('symbol'):
        group = group.copy()
        group['stock_close'] = group['close'].astype(float)
        group['stock_volume'] = group['volume'].astype(float)
        
        group['SMA20'] = group['stock_close'].rolling(20).mean()
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
        cols_to_keep = ['date', 'stock_close', 'stock_volume', 'SMA20', 'BBB_20', 'RSI14', 'stock_volume_sma20']
        group = group[cols_to_keep]
        group['stock_symbol'] = stock_sym
        stock_processed.append(group)
        
    stock_indicators = pd.concat(stock_processed).dropna()
    
    # 2. Merge indicators into CW history
    cw_query = "SELECT symbol as cw_symbol, date, close as cw_close, volume as cw_volume FROM cw_history ORDER BY symbol, date ASC"
    cw_df = pd.read_sql(cw_query, engine)
    
    # Map CW to Stock symbol
    valid_stocks = stock_df['symbol'].unique()
    cw_df['stock_symbol'] = cw_df['cw_symbol'].apply(lambda x: next((s for s in valid_stocks if x[1:].startswith(s)), None))
    cw_df = cw_df.dropna(subset=['stock_symbol'])
    
    # Merge
    df = pd.merge(cw_df, stock_indicators, on=['date', 'stock_symbol'], how='inner')
    df = df.dropna()
    
    # Apply Tier 2 structural filter
    cw_struct = pd.read_csv('data/processed/excel_cw_report.csv', encoding='utf-8')
    eligible_cw = cw_struct[(cw_struct['T_Delta'].abs() >= 0.25) & (cw_struct['K_ITM_OTM'].isin(['ITM', 'DEEP ITM', 'ATM']))]
    eligible_symbols = eligible_cw['A_MaCW'].tolist()
    
    df = df[df['cw_symbol'].isin(eligible_symbols)]
    
    # Best params from grid search (Optimized to maximize Sharpe Ratio)
    TP = 1.07
    SL = 0.80
    RSI_TH = 40
    
    print(f"\nCau hinh dang kiem chung: TP=+{(TP-1)*100:.0f}%, SL=-{(1-SL)*100:.0f}%, RSI<{RSI_TH}")
    print(f"Bo loc: Volume > 120% SMA20 + BBB_20 > 5% + CW Price > 300")
    
    # ============================================================
    # PHAN 1: IN CHI TIET TUNG LENH (Full Dataset)
    # ============================================================
    print("\n" + "=" * 90)
    print(" PHAN 1: CHI TIET TUNG LENH (Toan bo du lieu)")
    print("=" * 90)
    
    cw_groups = [g.sort_values('date').reset_index(drop=True) for _, g in df.groupby('cw_symbol') if len(g) >= 30]
    
    trade_log = run_strategy(cw_groups, TP, SL, RSI_TH)
    
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
        from src.quant.performance_evaluator import calculate_portfolio_performance, print_performance_report
        # Convert trade log objects to include entry/exit dates in matching format
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
        print_performance_report(perf_metrics)
    except Exception as pe:
        print(f"[!] Error generating portfolio performance report: {pe}")
    
    # ============================================================
    # PHAN 2: WALK-FORWARD VALIDATION (Chong Overfitting)
    # ============================================================
    print("\n" + "=" * 90)
    print(" PHAN 2: WALK-FORWARD VALIDATION (Chong Overfitting)")
    print("=" * 90)
    print(" Train tren 70% du lieu dau => Tim tham so tot nhat")
    print(" Test tren 30% du lieu cuoi => Kiem chung tren du lieu CHUA TUNG THAY")
    print("=" * 90)
    
    # Split each CW group into 70/30
    import itertools
    
    train_groups = []
    test_groups = []
    for cw_group in cw_groups:
        split_idx = int(len(cw_group) * 0.7)
        train_groups.append(cw_group.iloc[:split_idx].copy())
        test_groups.append(cw_group.iloc[split_idx:].copy())
    
    # Grid search on TRAIN set only
    tp_levels = [1.03, 1.05, 1.07, 1.10, 1.15, 1.20]
    sl_levels = [0.80, 0.85, 0.88, 0.90, 0.95]
    rsi_thresholds = [30, 40, 50]
    
    best_wr = 0
    best_params = None
    
    for tp, sl, rsi_th in itertools.product(tp_levels, sl_levels, rsi_thresholds):
        train_trades = run_strategy(train_groups, tp, sl, rsi_th)
        if len(train_trades) >= 5:
            train_wins = sum(1 for t in train_trades if t['win'])
            wr = train_wins / len(train_trades) * 100
            if wr > best_wr:
                best_wr = wr
                best_params = (tp, sl, rsi_th)
    
    if best_params:
        from src.quant.performance_evaluator import calculate_portfolio_performance, print_stage_report
        
        print("\n" + "=" * 90)
        print(" MULTI-STAGE STRATEGY PERFORMANCE REPORTS (TRAIN / TEST / SIMULATE)")
        print("=" * 90)
        print(f"Optimal parameters found on Train Set: TP=+{(best_params[0]-1)*100:.0f}%, SL=-{(1-best_params[1])*100:.0f}%, RSI<{best_params[2]}")
        
        # 1. Train Set Performance
        train_trades = run_strategy(train_groups, *best_params)
        train_metrics = calculate_portfolio_performance(train_trades)
        print_stage_report("Train", train_metrics)
        
        # 2. Test Set Performance (Out-of-Sample)
        test_trades = run_strategy(test_groups, *best_params)
        test_metrics = calculate_portfolio_performance(test_trades)
        print_stage_report("Test", test_metrics)
        
        # 3. Full Simulation Performance
        simulate_trades = run_strategy(cw_groups, *best_params)
        simulate_metrics = calculate_portfolio_performance(simulate_trades)
        print_stage_report("Simulate", simulate_metrics)
        
        # Output final verdict based on Test Set
        if test_metrics:
            test_wr = test_metrics['win_rate']
            test_sharpe = test_metrics['sharpe']
            print("=" * 90)
            print(" FINAL AUDIT VERDICT")
            print("=" * 90)
            if test_wr >= 65 and test_sharpe >= 1.3:
                print("  CHIEN LUOC THAT! Win Rate va Sharpe Ratio deu dat muc tieu tren Test Set.")
                print("  => KHONG bi Overfitting. San sang de deploy!")
            elif test_wr >= 50:
                print("  CHIEN LUOC TAM CHAP NHAN. Win Rate du duy tri nhung Sharpe chua dat muc tieu.")
                print("  => Co dau hieu Overfitting nhe. Can tinh chinh them de tang Sharpe.")
            else:
                print("  CHIEN LUOC AO! Win Rate sup do tren du lieu test.")
                print("  => CO DAU HIEU OVERFITTING NANG. KHONG DUOC SU DUNG DE GIAO DICH THAT!")
            print("=" * 90 + "\n")
    else:
        print("  KHONG TIM DUOC THAM SO NAO CO DU LENH TREN TRAIN SET.")

if __name__ == "__main__":
    main()
