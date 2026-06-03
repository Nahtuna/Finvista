import pandas as pd
import numpy as np
import itertools
from src.common.database import engine
import warnings
import sys

# Force stdout encoding to UTF-8 to handle emojis on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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

def run_grid_search():
    print("="*90)
    print(" 🔬 AI GRID SEARCH: TỰ ĐỘNG TÌM KIẾM 'CHÉN THÁNH' (>70% WIN RATE) CHO CHỨNG QUYỀN")
    print("="*90)
    
    df = get_all_data()
    
    # Calculate basic indicators for stock
    # We'll use simple Momentum + Mean Reversion logic to find what works
    processed = []
    for stock, group in df.groupby('stock_symbol'):
        group = group.copy()
        group['SMA10'] = group['stock_close'].rolling(10).mean()
        group['SMA20'] = group['stock_close'].rolling(20).mean()
        group['SMA50'] = group['stock_close'].rolling(50).mean()
        
        # Calculate Bollinger Bands
        rolling_std = group['stock_close'].rolling(20).std()
        group['BBL_20'] = group['SMA20'] - (2 * rolling_std)
        group['BBU_20'] = group['SMA20'] + (2 * rolling_std)
        group['BBB_20'] = (group['BBU_20'] - group['BBL_20']) / group['SMA20'] * 100
        
        # Proxy for RSI and Volume
        delta = group['stock_close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        group['RSI14'] = 100 - (100 / (1 + rs))
        group['stock_volume_sma20'] = group['stock_volume'].rolling(20).mean()
        processed.append(group)
        
    df = pd.concat(processed).dropna()
    
    # Grid Search Parameters
    tp_levels = [1.05, 1.10, 1.15, 1.20] # Take Profit
    sl_levels = [0.85, 0.90, 0.95]       # Stop Loss
    rsi_thresholds = [30, 40, 50]        # Entry RSI (Panic level)
    
    best_strategy = None
    best_win_rate = 0
    best_metrics = {}
    
    print("⏳ Đang cày nát dữ liệu qua hàng ngàn tổ hợp chiến lược trên TOÀN BỘ thị trường...\n")
    
    cw_groups = [group.sort_values('date').reset_index(drop=True) for _, group in df.groupby('cw_symbol') if len(group) >= 30]
    
    for tp, sl, rsi_th in itertools.product(tp_levels, sl_levels, rsi_thresholds):
        all_trades = []
        
        for cw_group in cw_groups:
            in_position = False
            entry_price = 0
            days_held = 0
            
            for idx, row in cw_group.iterrows():
                if in_position:
                    days_held += 1
                    can_sell = days_held >= 2
                    
                    if row['cw_close'] >= entry_price * tp and can_sell:
                        all_trades.append((row['cw_close'] - entry_price)/entry_price)
                        in_position = False
                    elif row['cw_close'] <= entry_price * sl and can_sell:
                        all_trades.append((row['cw_close'] - entry_price)/entry_price)
                        in_position = False
                else:
                    # Universal Panic Buy Logic V4:
                    # 1. Wash-out confirmed: Stock volume is unusually high (> 1.2x SMA20)
                    # 2. Premium filter: CW is not dead junk (Price > 300)
                    # 3. Capitulation: Bollinger Bands are expanding rapidly (BBB_20 > 5%)
                    is_washout = row['stock_volume'] > (row['stock_volume_sma20'] * 1.2)
                    is_capitulation = row['BBB_20'] > 5
                    
                    if row['RSI14'] < rsi_th and is_washout and is_capitulation and row['cw_close'] > 300:
                        in_position = True
                        entry_price = row['cw_close']
                        days_held = 0
        
        if len(all_trades) >= 10: # Universal robustness requires at least 10 trades across all warrants
            wins = len([t for t in all_trades if t > 0])
            win_rate = (wins / len(all_trades)) * 100
            total_ret = sum(all_trades) * 100
            
            if win_rate > best_win_rate:
                best_win_rate = win_rate
                best_strategy = (tp, sl, rsi_th)
                best_metrics = {'win_rate': win_rate, 'trades': len(all_trades), 'total_ret': total_ret}

    if best_strategy and best_win_rate >= 60.0:
        print(f"🎯 TÌM THẤY 'CHÉN THÁNH' THỰC SỰ CHO TOÀN BỘ THỊ TRƯỜNG!")
        print("-" * 50)
        print(f"🔹 Tỷ lệ thắng (Win Rate): {best_metrics['win_rate']:.2f}% (Aggregated)")
        print(f"🔹 Lợi nhuận tổng (Trade Return): {best_metrics['total_ret']:.2f}%")
        print(f"🔹 Tổng số lệnh: {best_metrics['trades']} lệnh trên toàn bộ DB")
        print("\n🔧 CẤU HÌNH TỔ HỢP TỐI ƯU (UNIVERSAL PARAMETERS):")
        print(f"   ► Canh nhịp hoảng loạn: Mua khi RSI cổ phiếu giảm dưới {best_strategy[2]}")
        print(f"   ► Chốt lời dứt khoát: +{(best_strategy[0]-1)*100:.0f}% (Take Profit)")
        print(f"   ► Cắt lỗ chặt chẽ: -{(1-best_strategy[1])*100:.0f}% (Stop Loss)")
        print("-" * 50)
    else:
        print(f"❌ Vẫn không tìm ra cấu hình nào qua được 60% Win Rate trên TOÀN THỊ TRƯỜNG. Cao nhất chỉ được: {best_win_rate:.2f}%")

if __name__ == "__main__":
    run_grid_search()
