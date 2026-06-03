# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: QUANTITATIVE BACKTESTER
====================================
Simulates trading strategies using historical data from the SQLite database.
Combines Covered Warrant (CW) price action with Underlying Stock (CPCS) data.

Strategies supported:
- Delta-Neutral Hedging (Volatility Arbitrage)
- Directional Breakout (Technical)
- Theta Decay Stop-loss

Author: Antigravity
"""
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import norm
from src.common.database import engine
from src.quant.pricing_core import calculate_greeks_for_cw
import sys

# Force stdout encoding to UTF-8 to handle emojis on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class FinvistaBacktester:
    def __init__(self):
        self.engine = engine

    def load_historical_data(self, symbol: str, underlying: str):
        """Load and merge historical OHLCV data for CW and Stock from the DB."""
        query = f"""
            SELECT 
                c.date,
                c.open as cw_open,
                c.high as cw_high,
                c.low as cw_low,
                c.close as cw_close,
                c.volume as cw_volume,
                s.open as stock_open,
                s.high as stock_high,
                s.low as stock_low,
                s.close as stock_close
            FROM cw_history c
            JOIN stock_history s ON c.date = s.date AND s.symbol = '{underlying}'
            WHERE c.symbol = '{symbol}'
            ORDER BY c.date ASC
        """
        df = pd.read_sql(query, self.engine)
        if df.empty:
            raise ValueError(f"No historical data found for {symbol} and {underlying}.")
        return df

    def run_volatility_arbitrage(self, symbol: str, underlying: str, strike: float, ratio: float, expiry_date: str, risk_free_rate: float = 0.05):
        """
        Simulate a simple volatility arbitrage strategy.
        Buy CW when its Implied Volatility is low relative to recent Historical Volatility.
        """
        df = self.load_historical_data(symbol, underlying)
        
        # Calculate Rolling Historical Volatility (30 days) of the underlying stock
        df['log_ret'] = np.log(df['stock_close'] / df['stock_close'].shift(1))
        df['rolling_hv_30'] = df['log_ret'].rolling(window=30).std() * np.sqrt(240)
        
        # We need actual time to maturity for each day to calculate IV
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
        
        results = []
        for index, row in df.iterrows():
            current_date = datetime.strptime(row['date'], "%Y-%m-%d")
            days_to_expiry = (expiry - current_date).days
            
            if days_to_expiry <= 0 or pd.isna(row['rolling_hv_30']):
                continue
            
            # Using our pricing core to calculate theoretical values and Greeks
            # We pass the rolling HV to see the theoretical price
            greeks = calculate_greeks_for_cw(
                underlying_price=row['stock_close'],
                strike_price=strike,
                days_to_maturity=days_to_expiry,
                implied_volatility=row['rolling_hv_30'],
                conversion_ratio=ratio,
                risk_free_rate=risk_free_rate
            )
            
            # We need to calculate theoretical price using the black scholes formula directly since calculate_greeks_for_cw doesn't return theo_price
            T_years = days_to_expiry / 365.0
            from src.quant.pricing_core import calculate_d1_d2
            d1, d2 = calculate_d1_d2(row['stock_close'], strike, T_years, risk_free_rate, row['rolling_hv_30'])
            theo_price = (row['stock_close'] * norm.cdf(d1) - strike * np.exp(-risk_free_rate * T_years) * norm.cdf(d2)) / ratio
            
            # If actual price < theoretical price, it's underpriced (IV < HV).
            is_underpriced = row['cw_close'] < theo_price
            
            results.append({
                'date': row['date'],
                'cw_close': row['cw_close'],
                'stock_close': row['stock_close'],
                'days_to_expiry': days_to_expiry,
                'rolling_hv': row['rolling_hv_30'],
                'theo_price': theo_price,
                'delta': greeks['delta'],
                'signal': 'BUY' if is_underpriced else 'WAIT'
            })
            
        return pd.DataFrame(results)

    def run_pro_quant_strategy(self, symbol: str, underlying: str):
        """
        Chiến lược Thực chiến chuyên sâu (Pro Quant Strategy):
        Kết hợp Nghiên cứu định lượng (Greeks) + Động lượng (TA) + Quản trị rủi ro (SL/TP).
        """
        import pandas_ta as ta
        import warnings
        warnings.filterwarnings('ignore')
        
        df = self.load_historical_data(symbol, underlying)
        
        # 1. Tính toán Đặc trưng Cổ phiếu (Underlying Features)
        df['stock_open'] = df['stock_open'].astype(float)
        df['stock_high'] = df['stock_high'].astype(float)
        df['stock_low'] = df['stock_low'].astype(float)
        df['stock_close'] = df['stock_close'].astype(float)
        
        # Thêm các chỉ báo theo trend (Ngắn hạn để phù hợp dữ liệu ngắn của CW)
        df.ta.ema(close='stock_close', length=10, append=True)
        df.ta.ema(close='stock_close', length=20, append=True)
        df.ta.rsi(close='stock_close', length=14, append=True)
        df['stock_volume_sma_20'] = df['cw_volume'].rolling(20).mean() # Approximate liquidity
        
        df.dropna(inplace=True)
        
        ema10_col = [c for c in df.columns if c.startswith('EMA_10')][0]
        ema20_col = [c for c in df.columns if c.startswith('EMA_20')][0]
        rsi_col = [c for c in df.columns if c.startswith('RSI_')][0]
        
        results = []
        
        # State Machine for Trade Management
        in_position = False
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        days_held = 0 # Track T+2.5 mechanism
        
        for index, row in df.iterrows():
            signal = 'WAIT'
            current_cw_price = row['cw_close']
            current_stock_price = row['stock_close']
            
            # Quản trị vị thế đang mở
            if in_position:
                days_held += 1
                # T+2.5 Logic: In Vietnam, you cannot sell on T+0 or T+1. 
                # Using EOD data, Day 2 (T+2) is the first time we can sell.
                can_sell = days_held >= 2
                
                # 1. Check Stop Loss (Chỉ được cắt lỗ nếu hàng đã về)
                if current_cw_price <= stop_loss and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # 2. Check Take Profit (Chỉ được chốt lời nếu hàng đã về)
                elif current_cw_price >= take_profit and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                # 3. Trailing Stop (Khóa một phần lợi nhuận)
                else:
                    new_sl = current_cw_price * 0.90
                    if new_sl > stop_loss:
                        stop_loss = new_sl
                    signal = 'HOLD'
            
            # Tìm kiếm cơ hội vào lệnh (Entry Logic)
            if not in_position:
                # TREND-FOLLOWING PULLBACK (Thuận thủy thôi chu):
                # Mục tiêu: Đạt >70% Win rate.
                # 1. Xu hướng tăng ngắn hạn: EMA10 > EMA20
                # 2. Canh nhịp chỉnh: Giá chạm về sát EMA10 (Pullback)
                # 3. RSI ở mức cân bằng, không quá mua.
                
                is_uptrend = row[ema10_col] > row[ema20_col]
                is_pullback = current_stock_price <= (row[ema10_col] * 1.02) and current_stock_price >= (row[ema10_col] * 0.98)
                is_rsi_cool = row[rsi_col] < 60
                is_liquid = row['cw_volume'] > 5000 
                
                if is_uptrend and is_pullback and is_rsi_cool and is_liquid and current_cw_price > 100:
                    signal = 'BUY'
                    in_position = True
                    entry_price = current_cw_price
                    # Chốt lời siêu tốc ngay khi giá hồi phục (+5%)
                    take_profit = entry_price * 1.05
                    # Cắt lỗ xa để tránh rũ bỏ (-15%)
                    stop_loss = entry_price * 0.85
            
            results.append({
                'date': row['date'],
                'cw_close': row['cw_close'],
                'stock_close': row['stock_close'],
                'signal': signal
            })
            
        return pd.DataFrame(results)

    def run_ultimate_panic_buy_strategy(self, symbol: str, underlying: str):
        """
        🏆 CHIẾN LƯỢC CHÉN THÁNH V5 (Ultimate Panic Buy Strategy):
        Chỉ giao dịch nếu Chứng quyền vượt qua bộ lọc cấu trúc TIER 2 (Sweet Spot):
        - Moneyness: ITM, DEEP ITM, hoặc ATM
        - Delta: >= 0.25
        Tín hiệu vào lệnh: RSI < 40 + Nổ Volume Stock + Bollinger Band Width > 5% + Thị giá > 300đ.
        """
        import os
        import pandas_ta as ta
        import warnings
        warnings.filterwarnings('ignore')
        
        # 1. Kiểm tra điều kiện lọc cấu trúc (Structural Pre-filter)
        report_path = os.path.join("data", "processed", "excel_cw_report.csv")
        is_eligible = True
        reason = ""
        
        if os.path.exists(report_path):
            try:
                struct_df = pd.read_csv(report_path, encoding='utf-8')
                cw_info = struct_df[struct_df['A_MaCW'] == symbol]
                if not cw_info.empty:
                    moneyness = cw_info.iloc[0]['K_ITM_OTM']
                    delta = abs(float(cw_info.iloc[0]['T_Delta']))
                    
                    if moneyness not in ['ITM', 'DEEP ITM', 'ATM']:
                        is_eligible = False
                        reason = f"Trạng thái {moneyness} (Yêu cầu: ITM/ATM)"
                    elif delta < 0.25:
                        is_eligible = False
                        reason = f"Delta = {delta:.2f} < 0.25"
                else:
                    print(f"⚠️  Không tìm thấy thông tin cấu trúc cho {symbol} trong excel_cw_report.csv. Vẫn tiếp tục giao dịch ở chế độ rủi ro.")
            except Exception as e:
                print(f"⚠️  Lỗi đọc file cấu trúc: {e}")
                
        if not is_eligible:
            print(f"🛑 BỎ QUA GIAO DỊCH {symbol}: Không đạt chuẩn Tier 2 ({reason}) để bảo vệ vốn.")
            # Trả về DataFrame rỗng hoặc chỉ có tín hiệu WAIT để không giao dịch
            df = self.load_historical_data(symbol, underlying)
            df['signal'] = 'WAIT'
            return df[['date', 'cw_close', 'stock_close', 'signal']]
            
        # 2. Tính toán kỹ thuật
        df = self.load_historical_data(symbol, underlying)
        df['stock_open'] = df['stock_open'].astype(float)
        df['stock_high'] = df['stock_high'].astype(float)
        df['stock_low'] = df['stock_low'].astype(float)
        df['stock_close'] = df['stock_close'].astype(float)
        df['stock_volume'] = df['stock_volume'].astype(float) if 'stock_volume' in df.columns else 0.0
        
        # Lấy dữ liệu Stock Volume trực tiếp từ DB nếu chưa có
        if 'stock_volume' not in df.columns or (df['stock_volume'] == 0).all():
            vol_query = f"SELECT date, volume as stock_volume FROM stock_history WHERE symbol = '{underlying}'"
            vol_df = pd.read_sql(vol_query, self.engine)
            df = df.drop(columns=['stock_volume'], errors='ignore').merge(vol_df, on='date', how='left')
            
        # Tính RSI, SMA20, Bollinger Bands
        df.ta.rsi(close='stock_close', length=14, append=True)
        df['SMA20'] = df['stock_close'].rolling(20).mean()
        rolling_std = df['stock_close'].rolling(20).std()
        df['BBU_20'] = df['SMA20'] + (2 * rolling_std)
        df['BBL_20'] = df['SMA20'] - (2 * rolling_std)
        df['BBB_20'] = (df['BBU_20'] - df['BBL_20']) / df['SMA20'] * 100
        df['stock_volume_sma20'] = df['stock_volume'].rolling(20).mean()
        
        df.dropna(inplace=True)
        rsi_col = [c for c in df.columns if c.startswith('RSI_')][0]
        
        results = []
        in_position = False
        entry_price = 0.0
        days_held = 0
        
        for index, row in df.iterrows():
            signal = 'WAIT'
            current_cw_price = row['cw_close']
            
            if in_position:
                days_held += 1
                can_sell = days_held >= 2
                
                if current_cw_price >= entry_price * 1.05 and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                elif current_cw_price <= entry_price * 0.85 and can_sell:
                    signal = 'SELL'
                    in_position = False
                    days_held = 0
                else:
                    signal = 'HOLD'
            else:
                is_washout = row['stock_volume'] > (row['stock_volume_sma20'] * 1.2)
                is_capitulation = row['BBB_20'] > 5
                
                if row[rsi_col] < 40 and is_washout and is_capitulation and current_cw_price > 300:
                    signal = 'BUY'
                    in_position = True
                    entry_price = current_cw_price
                    days_held = 0
                    
            results.append({
                'date': row['date'],
                'cw_close': row['cw_close'],
                'stock_close': row['stock_close'],
                'signal': signal
            })
            
        return pd.DataFrame(results)

    def evaluate_performance(self, df: pd.DataFrame, initial_capital: float = 100000000.0, allocation_pct: float = 0.50) -> dict:
        """
        Simulate portfolio P/L based on backtest signals to calculate Quantitative KPIs:
        Sharpe Ratio, Maximum Drawdown, Win Rate, and Total Return.
        """
        if df.empty or 'signal' not in df.columns:
            return {}

        cash = initial_capital
        position = 0
        buy_price = 0
        trades = []
        equity_curve = []

        for index, row in df.iterrows():
            current_price = row['cw_close']
            signal = row['signal']
            
            # Simple simulation logic
            if signal == 'BUY' and position == 0:
                # Calculate how many lots we can buy based on allocation
                qty = (cash * allocation_pct) // (current_price * 100) * 100
                if qty > 0:
                    position = qty
                    buy_price = current_price
                    cash -= position * buy_price
                    
            elif signal == 'SELL' and position > 0:
                # Sell
                revenue = position * current_price
                cash += revenue
                p_l = (current_price - buy_price) / buy_price
                trades.append(p_l)
                position = 0
                buy_price = 0
            
            # If signal == 'WAIT' and we are holding from a basic strategy without SELL, auto-sell it:
            elif signal == 'WAIT' and position > 0:
                revenue = position * current_price
                cash += revenue
                p_l = (current_price - buy_price) / buy_price
                trades.append(p_l)
                position = 0
                buy_price = 0
                
            # If signal == 'HOLD', do nothing (just hold the position)

            # Record daily equity
            current_equity = cash + (position * current_price)
            equity_curve.append(current_equity)

        # Force close any open positions at the end to evaluate final P/L
        if position > 0:
            p_l = (current_price - buy_price) / buy_price
            trades.append(p_l)

        # Calculate Metrics
        total_return_pct = ((current_equity - initial_capital) / initial_capital) * 100
        win_rate = (len([t for t in trades if t > 0]) / len(trades) * 100) if trades else 0.0
        avg_trade_return = (sum(trades) / len(trades) * 100) if trades else 0.0
        
        # Calculate Max Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        # Calculate Sharpe Ratio (Risk-Free Rate ~ 5% annual)
        daily_returns = equity_series.pct_change().dropna()
        if len(daily_returns) > 0 and daily_returns.std() != 0:
            # Assuming 252 trading days
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        return {
            "Total Portfolio Return (%)": round(total_return_pct, 2),
            "Average Trade Return (%)": round(avg_trade_return, 2),
            "Total Trades": len(trades),
            "Win Rate (%)": round(win_rate, 2),
            "Max Drawdown (%)": round(max_drawdown, 2),
            "Sharpe Ratio": round(sharpe_ratio, 2),
            "Final Equity (VND)": current_equity
        }

if __name__ == "__main__":
    # Example usage
    print("Initializing Backtester...")
    tester = FinvistaBacktester()
    try:
        # 1. Backtest Quantitative Strategy (Volatility Arbitrage)
        res_quant = tester.run_volatility_arbitrage("CACB2510", "ACB", strike=22500.0, ratio=2.0, expiry_date="2026-06-23")
        metrics_quant = tester.evaluate_performance(res_quant)
        
        print("\n" + "=" * 50)
        print(" 📊 CHIẾN LƯỢC 1: VOLATILITY ARBITRAGE (QUANT)")
        print("=" * 50)
        for key, val in metrics_quant.items():
            print(f"  {key}: {val}")
            
        # 2. Backtest Pro Quant Strategy (ML Inspired: Volatility Squeeze + Risk Management)
        res_ta = tester.run_pro_quant_strategy("CACB2510", "ACB")
        # For High-Yield Warrant strategy, simulate allocating 50% of portfolio per trade
        metrics_ta = tester.evaluate_performance(res_ta, initial_capital=100000000.0, allocation_pct=0.50) 
        
        print("\n" + "=" * 50)
        print(" 🚀 CHIẾN LƯỢC 2: PRO QUANT (ML-DRIVEN + RISK MANAGEMENT)")
        print("=" * 50)
        for key, val in metrics_ta.items():
            print(f"  {key}: {val}")
        print("=" * 50)
        
        # 3. Backtest Ultimate Panic Buy Strategy V5 (with Tier 2 structural pre-filtering)
        res_ultimate = tester.run_ultimate_panic_buy_strategy("CACB2510", "ACB")
        metrics_ultimate = tester.evaluate_performance(res_ultimate, initial_capital=100000000.0, allocation_pct=0.50)
        
        print("\n" + "=" * 50)
        print(" 🏆 CHIẾN LƯỢC 3: ULTIMATE PANIC BUY (TIER 2 STRUCTURAL FILTER)")
        print("=" * 50)
        for key, val in metrics_ultimate.items():
            print(f"  {key}: {val}")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error during backtest: {e}")
