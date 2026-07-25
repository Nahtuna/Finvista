# -*- coding: utf-8 -*-
"""
🎨 PLOT CREED MASTER GRID REGIME DETECTION
===========================================
Plots historical price, Master Trend (EMA200), and colored regime background bands.
Saves PNG chart to results/creed_master_grid_audit.png
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from src.modules.regime_analysis.indicators.creed_regime import calculate_creed_regime_from_df
from src.core.database import engine

def plot_creed_audit(symbol: str = "HDB", days: int = 1250):
    # Query 100% real database stock history filtered for 2026
    query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = '{symbol}' AND date >= '2026-01-01' ORDER BY date ASC"
    df = pd.read_sql(query, engine)

    if df.empty or len(df) < 20:
        query_fallback = "SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = 'HPG' AND date >= '2026-01-01' ORDER BY date ASC"
        df = pd.read_sql(query_fallback, engine)
        symbol = "HPG"

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    closes = df['close'].values
    dates = df['date'].values
    ema200 = pd.Series(closes).ewm(span=min(200, len(closes)//2), adjust=False).mean().values

    # Calculate sliding regime phases (vectorized / windowed)
    regimes = []
    for i in range(len(df)):
        if i < 20:
            regimes.append("SIDEWAYS")
            continue
        sub_df = df.iloc[max(0, i-250):i+1]
        res = calculate_creed_regime_from_df(sub_df, trend_period=200)
        regimes.append(res["regime"])

    # Setup dark theme plot
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(14, 7), dpi=150)

    # Color background based on Creed Master Grid Regime
    for i in range(len(dates) - 1):
        r = regimes[i]
        color = '#1b4332' if r == 'BULLISH_VOL_EXPANSION' else ('#7f1d1d' if r == 'BEARISH_HIGH_VOL' else '#1f2937')
        alpha = 0.45 if r != 'SIDEWAYS' else 0.15
        ax.axvspan(dates[i], dates[i+1], color=color, alpha=alpha, linewidth=0)

    # Plot Close Price & Master Trend Line
    ax.plot(dates, closes, label='Price (Close)', color='#60a5fa', linewidth=2.0)
    ax.plot(dates, ema200, label='Master Trend Line (EMA 200)', color='#f59e0b', linestyle='--', linewidth=1.8)

    ax.set_title(f"FINVISTA · Native Creed Master Grid Regime Audit ({symbol})", fontsize=14, fontweight='bold', pad=15, color='#f3f4f6')
    ax.set_ylabel("Price (VND)", fontsize=11, color='#d1d5db')
    ax.set_xlabel("Date", fontsize=11, color='#d1d5db')

    # Legend & Grid
    ax.grid(True, linestyle=':', alpha=0.3, color='#4b5563')
    ax.legend(loc='upper left', frameon=True, facecolor='#1f2937', edgecolor='#374151')

    # Add text annotation
    bull_pct = round((regimes.count("BULLISH_VOL_EXPANSION") / len(regimes)) * 100, 1)
    bear_pct = round((regimes.count("BEARISH_HIGH_VOL") / len(regimes)) * 100, 1)
    side_pct = round(100 - bull_pct - bear_pct, 1)

    info_text = f"BULL Phase: {bull_pct}%\nBEAR Phase: {bear_pct}%\nSIDEWAYS: {side_pct}%"
    ax.text(0.98, 0.05, info_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#111827', alpha=0.85, edgecolor='#374151'))

    plt.tight_layout()
    os.makedirs("results", exist_ok=True)
    out_path = "results/creed_master_grid_audit.png"
    plt.savefig(out_path)
    plt.close(fig)
    print(f"[OK] Saved plot to {out_path}")

if __name__ == "__main__":
    plot_creed_audit()
