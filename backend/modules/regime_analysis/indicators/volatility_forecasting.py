# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: VOLATILITY FORECASTING SUITE
===========================================
Combines GARCH-EVT VaR, GARCH volatility forecasting, and EWMA/GARCH volatility models.

Components:
- VolatilityModeler: EWMA & GARCH(1,1) for volatility forecasting and scaling
- GARCH-EVT VaR: Value at Risk using GARCH + Extreme Value Theory
- GARCH Forecaster: GARCH(1,1) with Student's t distribution for options calibration

Author: samvo
"""

import os
import sys
import sqlite3
import numpy as np
import pandas as pd
import warnings
from scipy.stats import genpareto, norm
from arch import arch_model
from backend.core.database import engine

# Force terminal UTF-8 encoding on Windows
if sys.platform == 'win32':
    import io
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

warnings.filterwarnings('ignore')


# ─── VOLATILITY MODELER CLASS (EWMA & GARCH) ───────────────────────────────────

class VolatilityModeler:
    """
    A math core class to calculate, forecast, and scale volatility using EWMA and GARCH(1,1).
    Theory: John C. Hull - Risk Management and Financial Institutions (Ch. 10)
    """

    @staticmethod
    def ewma_variance(returns: pd.Series, lambda_: float = 0.94) -> pd.Series:
        """
        Calculate conditional variance using the Exponentially Weighted Moving Average (EWMA) model.
        Theory: RiskMetrics approach where lambda is typically 0.94 for daily data.
        σ_n^2 = λ * σ_{n-1}^2 + (1 - λ) * u_{n-1}^2
        """
        returns_sq = returns ** 2
        var_series = np.zeros_like(returns_sq)

        # Initialize the first variance as the sample variance of the first 20 days
        initial_var = returns.head(20).var() if len(returns) >= 20 else returns.var()
        var_series[0] = initial_var

        for i in range(1, len(returns_sq)):
            var_series[i] = lambda_ * var_series[i-1] + (1 - lambda_) * returns_sq.iloc[i-1]

        return pd.Series(var_series, index=returns.index)

    @staticmethod
    def garch_variance(returns: pd.Series, p: int = 1, q: int = 1) -> pd.Series:
        """
        Calculate conditional variance using the GARCH(p,q) model with Student's t distribution.
        Handles fat tails and mean reversion.
        """
        # Scale returns for optimization stability
        scaled_returns = returns * 100.0

        # Fit GARCH
        model = arch_model(scaled_returns, mean='Constant', vol='GARCH', p=p, q=q, dist='studentst')
        try:
            res = model.fit(disp='off')
            # Extract conditional volatility and square it for variance, then unscale
            cond_var = (res.conditional_volatility / 100.0) ** 2
            return pd.Series(cond_var, index=returns.index)
        except Exception as e:
            print(f"⚠️ GARCH fit failed: {e}. Falling back to EWMA.")
            return VolatilityModeler.ewma_variance(returns)

    @staticmethod
    def forecast_volatility(returns: pd.Series, method: str = 'GARCH') -> float:
        """
        Forecast the T+1 annualized volatility.
        """
        if len(returns) < 50:
            return returns.std() * np.sqrt(252)  # Fallback to standard historical vol

        if method.upper() == 'GARCH':
            scaled_returns = returns * 100.0
            model = arch_model(scaled_returns, mean='Constant', vol='GARCH', p=1, q=1, dist='studentst')
            try:
                res = model.fit(disp='off')
                forecast = res.forecast(horizon=1)
                next_day_var = forecast.variance.iloc[-1, 0]
                # Unscale and annualize
                return (np.sqrt(next_day_var) / 100.0) * np.sqrt(252)
            except:
                pass

        # EWMA Forecast (T+1 variance is just the formula applied to the last known point)
        var_series = VolatilityModeler.ewma_variance(returns)
        next_day_var = 0.94 * var_series.iloc[-1] + (1 - 0.94) * (returns.iloc[-1] ** 2)
        return np.sqrt(next_day_var) * np.sqrt(252)

    @staticmethod
    def get_volatility_scaling_factors(returns: pd.Series, method: str = 'EWMA') -> pd.Series:
        """
        Calculates the Hull-White volatility scaling factors for historical simulation.
        Factor_i = sigma_current / sigma_i
        """
        if method.upper() == 'GARCH':
            var_series = VolatilityModeler.garch_variance(returns)
        else:
            var_series = VolatilityModeler.ewma_variance(returns)

        vol_series = np.sqrt(var_series)
        current_vol = vol_series.iloc[-1]

        # Scaling factor: ratio of today's volatility to historical day i's volatility
        scaling_factors = current_vol / vol_series
        return scaling_factors


# ─── GARCH-EVT VALUE AT RISK ───────────────────────────────────────────────────

def get_underlying_garch_evt_var(underlying_symbol: str, alpha: float = 0.95) -> float:
    """
    Calculate the base GARCH-EVT Value at Risk (VaR) for a given stock.
    Returns the VaR as a positive decimal representing the loss percentage (e.g. 0.05 for 5% loss).
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir and not os.path.exists(os.path.join(current_dir, "data")):
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
    db_path = os.path.join(current_dir, "data", "finvista.db")
    df = pd.DataFrame()

    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            query = f"SELECT date, close FROM stock_history WHERE symbol = '{underlying_symbol}' ORDER BY date ASC"
            df = pd.read_sql(query, conn)
            conn.close()
        except Exception:
            pass

    if df.empty or len(df) < 50:
        # Generic fallback VaR (e.g. 3.5% daily VaR)
        return 0.035

    try:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        # Calculate returns
        returns = df['close'].pct_change().dropna()
        if len(returns) < 30:
            return 0.035

        # 1. Fit GARCH(1,1) to estimate conditional volatility
        scaled_returns = returns * 100.0
        garch = arch_model(scaled_returns, mean='Constant', vol='GARCH', p=1, q=1, dist='studentst')
        res = garch.fit(disp='off')

        # Forecast tomorrow's volatility
        forecast = res.forecast(horizon=1)
        next_day_sigma = np.sqrt(forecast.variance.iloc[-1, 0]) / 100.0

        # Calculate standardized residuals (negative residuals represent losses)
        sigma = res.conditional_volatility / 100.0
        std_residuals = returns / sigma.loc[returns.index]
        losses = -std_residuals

        # 2. Extreme Value Theory (POT - Peak Over Threshold)
        # Select threshold u as the 90th percentile of losses
        u = np.percentile(losses, 90)
        exceedances = losses[losses > u] - u

        if len(exceedances) < 5:
            # Fallback to standard parametric VaR if not enough tail data
            z_score = norm.ppf(alpha)
            return float(next_day_sigma * z_score)

        # Fit GPD
        c, loc, scale_param = genpareto.fit(exceedances, floc=0)

        # Calculate GPD-VaR threshold formula
        # VaR = u + (scale_param / c) * ( ( (N / N_u) * (1 - alpha) )^-c - 1 )
        n_total = len(losses)
        n_u = len(exceedances)

        # Guard against shape parameter c being zero
        if abs(c) < 1e-5:
            c = 1e-5

        term = ((n_total / n_u) * (1.0 - alpha)) ** (-c)
        var_z = u + (scale_param / c) * (term - 1.0)

        # Scale back by today's conditional volatility
        var_final = next_day_sigma * var_z
        return float(max(0.01, var_final))

    except Exception:
        # Fallback to standard historical simulation VaR
        try:
            returns = df['close'].pct_change().dropna()
            return float(abs(np.percentile(returns, (1 - alpha) * 100)))
        except Exception:
            return 0.035


def get_conformal_calibrated_var(underlying: str, current_state: int, alpha: float = 0.95) -> float:
    """
    Get the conformal calibrated VaR based on the current market state/regime.
    state: 0 (Bull low vol), 1 (Bull high vol), 2 (Bear low vol), 3 (Bear high vol/Crisis)
    """
    base_var = get_underlying_garch_evt_var(underlying, alpha)

    # Conformal calibration shifts (deltas) for each state
    # Added protection for high volatility bearish states
    delta_map = {
        0: -0.005,  # Stable Bull: lower risk profile
        1: 0.000,   # High Vol Bull: standard risk
        2: 0.005,   # Low Vol Bear: slightly higher risk
        3: 0.020    # Bearish Crisis: add safety buffer
    }

    delta = delta_map.get(current_state, 0.0)
    calibrated_var = base_var + delta

    return float(max(0.01, calibrated_var))


# ─── GARCH VOLATILITY FORECASTER (OPTIONS CALIBRATOR) ───────────────────────────

def get_underlying_symbols():
    """Fetch unique underlying stock symbols from database."""
    query = "SELECT DISTINCT symbol FROM stock_history"
    df = pd.read_sql(query, engine)
    return df['symbol'].tolist()


def fetch_stock_returns(symbol):
    """Fetch historical stock price and calculate daily log returns."""
    query = f"""
        SELECT date, close
        FROM stock_history
        WHERE symbol = '{symbol}'
        ORDER BY date ASC
    """
    df = pd.read_sql(query, engine)
    if df.empty or len(df) < 50:
        return None

    df['date'] = pd.to_datetime(df['date'])
    df['close'] = df['close'].astype(float)
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    return df.dropna().reset_index(drop=True)


def fit_garch_model(df_returns, symbol):
    """Fits GARCH(1,1) with Student's t-distribution on returns."""
    # Scale returns by 100 for better optimization stability
    returns = df_returns['log_return'] * 100.0

    # Define GARCH(1,1) model with Student's t distribution (to handle fat tails)
    model = arch_model(returns, mean='Constant', vol='GARCH', p=1, q=1, dist='studentst')

    try:
        res = model.fit(disp='off')

        # Get parameter estimates
        omega = res.params['omega']
        alpha = res.params['alpha[1]']
        beta = res.params['beta[1]']
        nu = res.params['nu']  # Degrees of freedom

        # Check stability condition: alpha + beta < 1
        persistence = alpha + beta
        is_stable = persistence < 1.0

        # Forecast 1-day ahead conditional variance
        forecast = res.forecast(horizon=1)
        next_day_variance = forecast.variance.iloc[-1, 0]  # Scale is still returns * 100

        # Convert next-day standard deviation to annualized volatility
        garch_vol_ann = (np.sqrt(next_day_variance) / 100.0) * np.sqrt(240) * 100.0

        # Calculate standard historical 30-day volatility for comparison
        hist_30d_vol_ann = df_returns['log_return'].tail(30).std() * np.sqrt(240) * 100.0

        # Current daily return
        latest_return = df_returns['log_return'].iloc[-1] * 100.0

        return {
            'symbol': symbol,
            'omega': float(omega),
            'alpha': float(alpha),
            'beta': float(beta),
            'persistence': float(persistence),
            'degrees_of_freedom_nu': float(nu),
            'is_stable': bool(is_stable),
            'garch_forecast_vol_pct': float(garch_vol_ann),
            'hist_30d_vol_pct': float(hist_30d_vol_ann),
            'deviation_pct': float(garch_vol_ann - hist_30d_vol_ann),
            'latest_return_pct': float(latest_return)
        }
    except Exception as e:
        print(f"⚠️ Failed to fit GARCH(1,1) for {symbol}: {e}")
        return None


def main():
    """Main function to run GARCH volatility forecasting across all symbols."""
    print("=" * 95)
    print(" 📉 KHỞI CHẠY HỆ THỐNG DỰ BÁO BIẾN ĐỘNG ĐIỀU KIỆN GARCH(1,1) & ĐÁNH GIÁ ĐÁM MÂY BIẾN ĐỘNG")
    print("=" * 95)

    symbols = get_underlying_symbols()
    if not symbols:
        print("❌ Error: No underlying stock symbols found in database.")
        sys.exit(1)

    print(f"📊 Tìm thấy {len(symbols)} cổ phiếu cơ sở trong CSDL. Bắt đầu xử lý dữ liệu...")

    results = []
    for sym in symbols:
        df_ret = fetch_stock_returns(sym)
        if df_ret is not None:
            metrics = fit_garch_model(df_ret, sym)
            if metrics:
                results.append(metrics)

    if not results:
        print("❌ Error: No GARCH models converged successfully.")
        sys.exit(1)

    results_df = pd.DataFrame(results).sort_values('deviation_pct', key=abs, ascending=False)

    # Display comparison table
    print("\n" + "=" * 115)
    print(f"{'Cổ Phiếu':<10} | {'GARCH Vol (T+1)':>15} | {'Hist 30d Vol':>15} | {'Chênh Lệch':>12} | {'Hệ Số ARCH (α)':>15} | {'Hệ Số GARCH (β)':>15} | {'Tính Bền Vững':>15}")
    print("-" * 115)

    for _, r in results_df.iterrows():
        stable_status = "BỀN VỮNG" if r['is_stable'] else "PHÁT TÁN ⚠️"
        print(f"{r['symbol']:<10} | {r['garch_forecast_vol_pct']:13.2f}% | {r['hist_30d_vol_pct']:13.2f}% | {r['deviation_pct']:+11.2f}% | {r['alpha']:15.4f} | {r['beta']:15.4f} | {stable_status:<15}")
    print("=" * 115)

    # Save parameters to processed files
    output_dir = "data/processed"
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "garch_vol_report.csv")
    results_df.to_csv(csv_path, index=False, encoding='utf-8')

    print(f"\n💾 Đã lưu báo cáo so sánh biến động GARCH vào: {csv_path}")
    print("\n💡 PHÂN TÍCH CHUYÊN SÂU TỪ HỆ THỐNG QUAN T:")
    print("1. Hiện tượng Đám mây biến động (Volatility Clustering):")
    print("   - Khi chênh lệch (GARCH Vol - Hist 30d) mang giá trị DƯƠNG (+): Cổ phiếu đang gặp cú sốc biến động mạnh gần đây.")
    print("     GARCH lập tức tăng dự báo độ biến động ngày mai lên cao, giúp giá lý thuyết chứng quyền phản ánh đúng rủi ro.")
    print("   - Khi chênh lệch mang giá trị ÂM (-): Cổ phiếu đang rơi vào pha bình yên kéo dài.")
    print("     GARCH hạ giá trị dự báo thấp hơn trung bình lịch sử, tránh định giá đắt vô lý cho Option.")
    print("2. Ứng dụng thực tế:")
    print("   - Thay thế việc dùng Flat Volatility trong mô hình Black-Scholes để định giá chính xác chênh lệch Implied Volatility (IV).")


if __name__ == "__main__":
    main()
