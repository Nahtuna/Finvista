# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: STANDALONE REGIME ANALYSIS CLI
============================================
Run interactive or standalone Market Regime analysis for VNINDEX or any stock symbol.

Usage:
  python scripts/regime_cli.py
  python scripts/regime_cli.py --symbol HPG --days 500
  python scripts/regime_cli.py --symbol VNINDEX --plot
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np

# Ensure root workspace is on python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass


from backend.core.database import engine
from backend.modules.regime_analysis.indicators.creed_regime import calculate_creed_regime_from_df
from backend.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime


def fetch_stock_data(symbol: str = "VNINDEX", days: int = 500) -> pd.DataFrame:
    """Fetch OHLCV data from database or generate realistic fallback if DB empty."""
    query = f"""
        SELECT date, open, high, low, close, volume 
        FROM stock_history 
        WHERE symbol = '{symbol}' 
        ORDER BY date DESC LIMIT {days}
    """
    try:
        df = pd.read_sql(query, engine)
        if not df.empty and len(df) >= 20:
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date').reset_index(drop=True)
    except Exception as e:
        print(f"⚠️ Database query notice: {e}")

    # Query fallback symbol if specific ticker empty
    try:
        fallback_query = f"SELECT date, open, high, low, close, volume FROM stock_history ORDER BY date DESC LIMIT {days}"
        df = pd.read_sql(fallback_query, engine)
        if not df.empty and len(df) >= 20:
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date').reset_index(drop=True)
    except Exception:
        pass

    # Synthetic fallback for zero-dependency standalone execution
    print("ℹ️ Standard data fallback: generating sample price history...")
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq='B')
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.015, days)
    price = 1200.0 * np.exp(np.cumsum(returns))
    high = price * (1 + np.abs(np.random.normal(0, 0.008, days)))
    low = price * (1 - np.abs(np.random.normal(0, 0.008, days)))
    volume = np.random.randint(100000, 5000000, days)
    df = pd.DataFrame({'date': dates, 'open': price, 'high': high, 'low': low, 'close': price, 'volume': volume})
    return df


def run_regime_analysis(symbol: str = "VNINDEX", days: int = 500, timeframe: str = "4H", save_plot: bool = True):
    print("=" * 75)
    print(f"🌐 FINVISTA MARKET REGIME ENGINE | TARGET: {symbol.upper()} [{timeframe.upper()}]")
    print("=" * 75)

    # 1. Fetch data
    df = fetch_stock_data(symbol, days)

    # Resample to 4H or 1H if requested
    tf_upper = timeframe.upper()
    if tf_upper in ("4H", "240M", "240"):
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df_resampled = df.resample('4h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        if len(df_resampled) >= 20:
            df = df_resampled
            print(f"⏱️ Resampled data to 4-Hour (4H) candles ({len(df)} bars)")
    elif tf_upper in ("1H", "60M", "60"):
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df_resampled = df.resample('1h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        if len(df_resampled) >= 20:
            df = df_resampled
            print(f"⏱️ Resampled data to 1-Hour (1H) candles ({len(df)} bars)")

    print(f"📊 Loaded {len(df)} {timeframe.upper()} bars from {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")

    # 2. Creed Master Grid Detection
    creed_res = calculate_creed_regime_from_df(df, trend_period=200)
    print(f"\n🟢 [1/2] CREED MASTER GRID REGIME ({timeframe.upper()}):")
    print(f"  • Timeframe    : {timeframe.upper()}")
    print(f"  • Regime Phase : {creed_res.get('regime', 'UNKNOWN')}")
    print(f"  • Market Bias  : {creed_res.get('bias', 'NEUTRAL')}")
    print(f"  • Confidence   : {creed_res.get('confidence', 0.5):.2%}")
    print(f"  • Description  : {creed_res.get('description', 'N/A')}")

    # 3. Hybrid Gaussian HMM Regime Detection
    print(f"\n🧠 [2/2] GAUSSIAN HIDDEN MARKOV MODEL (HMM) ({timeframe.upper()}):")
    try:
        hmm_res = calculate_vnindex_regime(days=days)
        print(f"  • HMM State    : State {hmm_res.get('state', 1)}")
        print(f"  • HMM Regime   : {hmm_res.get('regime', 'N/A')}")
        print(f"  • Signal Bias  : {hmm_res.get('bias', 'N/A')}")
        print(f"  • Confidence   : {hmm_res.get('confidence', 0.7):.2%}")
    except Exception as e:
        print(f"  ⚠️ HMM calculation note: {e}")

    # 4. Optional Plot Generation
    if save_plot:
        try:
            import matplotlib.pyplot as plt
            closes = df['close'].values
            dates = df['date'].values
            ema200 = pd.Series(closes).ewm(span=min(200, len(closes)//2), adjust=False).mean().values

            regimes = []
            for i in range(len(df)):
                if i < 20:
                    regimes.append("SIDEWAYS")
                    continue
                sub_df = df.iloc[max(0, i-200):i+1]
                r_res = calculate_creed_regime_from_df(sub_df, trend_period=200)
                regimes.append(r_res.get("regime", "SIDEWAYS"))

            # Merge contiguous regime spans to remove hairline gaps
            spans = []
            if len(dates) > 1:
                curr_r = regimes[0]
                start_d = dates[0]
                for i in range(1, len(dates)):
                    if regimes[i] != curr_r:
                        spans.append((start_d, dates[i], curr_r))
                        curr_r = regimes[i]
                        start_d = dates[i]
                spans.append((start_d, dates[-1], curr_r))

            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(13, 6.5), dpi=140)

            for start_d, end_d, r in spans:
                color = '#1b4332' if r == 'BULLISH_VOL_EXPANSION' else ('#7f1d1d' if r == 'BEARISH_HIGH_VOL' else '#1f2937')
                alpha = 0.45 if r != 'SIDEWAYS' else 0.15
                ax.axvspan(start_d, end_d, facecolor=color, alpha=alpha, edgecolor='none', linewidth=0)

            ax.plot(dates, closes, label=f'{symbol.upper()} Close ({timeframe.upper()})', color='#60a5fa', linewidth=2)
            ax.plot(dates, ema200, label='EMA 200 (Master Trend)', color='#f59e0b', linestyle='--', linewidth=1.8)
            ax.set_title(f"Finvista Master Grid Regime Audit · {symbol.upper()} [{timeframe.upper()}]", fontsize=13, fontweight='bold', pad=12, color='#f3f4f6')
            ax.set_ylabel("Price (VND)", fontsize=11, color='#d1d5db')
            ax.set_xlabel("Date / Time", fontsize=11, color='#d1d5db')
            ax.grid(True, linestyle=':', alpha=0.3, color='#4b5563')
            ax.legend(loc='upper left', frameon=True, facecolor='#1f2937', edgecolor='#374151')

            # Add regime distribution statistics box
            bull_cnt = sum(1 for r in regimes if r == 'BULLISH_VOL_EXPANSION')
            bear_cnt = sum(1 for r in regimes if r == 'BEARISH_HIGH_VOL')
            tot = max(1, len(regimes))
            bull_pct = round(bull_cnt / tot * 100, 1)
            bear_pct = round(bear_cnt / tot * 100, 1)
            side_pct = round(100 - bull_pct - bear_pct, 1)
            latest_phase = creed_res.get('regime', 'UNKNOWN')

            info_text = f"Current Phase: {latest_phase}\nBullish: {bull_pct}%\nBearish: {bear_pct}%\nSideways: {side_pct}%"
            ax.text(0.98, 0.05, info_text, transform=ax.transAxes, fontsize=10,
                    verticalalignment='bottom', horizontalalignment='right',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#111827', alpha=0.88, edgecolor='#374151'))


            plt.tight_layout()
            os.makedirs("results", exist_ok=True)
            out_path = f"results/regime_audit_{symbol.lower()}.png"
            plt.savefig(out_path, bbox_inches='tight')
            plt.close(fig)
            print(f"\n📈 High-quality chart generated & saved to: {out_path}")

        except Exception as e:
            print(f"⚠️ Chart rendering skipped: {e}")

    print("\n✅ Regime analysis complete.")


def main():
    parser = argparse.ArgumentParser(description="Finvista Quantitative Market Regime CLI")
    parser.add_argument("--symbol", "-s", type=str, default="VNINDEX", help="Symbol to analyze (default: VNINDEX)")
    parser.add_argument("--tf", "--timeframe", type=str, default="4H", choices=["4H", "1D", "1H"], help="Timeframe (default: 4H)")
    parser.add_argument("--days", "-d", type=int, default=500, help="Historical lookback days (default: 500)")
    parser.add_argument("--no-plot", action="store_true", help="Disable PNG chart rendering")
    args = parser.parse_args()

    run_regime_analysis(symbol=args.symbol, days=args.days, timeframe=args.tf, save_plot=not args.no_plot)


if __name__ == "__main__":
    main()

