# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: VN-INDEX REGIME DETECTOR AUDIT TOOL v5.0
=====================================================
Trains a 4-state Hybrid HMM (2-state HMM × Trend) or 3-state HMM on VN-Index
using strictly causal Walk-Forward Validation.
Generates a clean, presentation-grade visualization of the walk-forward results.

Author: Antigravity
Version: 5.0 (Strict Walk-Forward Only)
"""

import os, sys, warnings, argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
from matplotlib.collections import LineCollection
from vnstock import Market
from datetime import datetime, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if sys.platform == 'win32':
    import io
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.makedirs("results", exist_ok=True)

# ─────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────────────────────
BG      = '#0d1117'   # near-black
PANEL   = '#161b22'   # dark panel
BORDER  = '#30363d'   # subtle border
TEXT    = '#e6edf3'
MUTED   = '#8b949e'

# Palettes
C_4STATE = {
    0: '#58a6ff',   # Bullish Low-Vol  → Blue (vol nhỏ)
    1: '#3fb950',   # Bullish High-Vol → Green (vol to)
    2: '#e3b341',   # Bearish Low-Vol  → Yellow (giảm vol thấp)
    3: '#f85149',   # Bearish Crisis   → Red (giảm vol to)
}
LABEL_4STATE = {
    0: 'Bullish (Low Vol)',
    1: 'Bullish (High Vol)',
    2: 'Bearish (Low Vol)',
    3: 'Bearish Crisis (High Vol)',
}

C_3STATE = {
    0: '#3fb950',   # Low Vol  → bright green
    1: '#e3b341',   # Medium Vol → amber
    2: '#f85149',   # High Vol → red (crisis)
}
LABEL_3STATE = {
    0: 'Low Vol (Calm)',
    1: 'Med Vol (Sideways)',
    2: 'High Vol (Crisis)',
}

BG_ALPHA_4 = {0: 0.12, 1: 0.18, 2: 0.18, 3: 0.25}
BG_ALPHA_3 = {0: 0.15, 1: 0.20, 2: 0.25}

def _smooth(arr: np.ndarray, min_run: int = 4) -> np.ndarray:
    """Merge regime runs shorter than min_run into the previous regime."""
    s = arr.copy()
    for _ in range(10):
        changed = False
        i = 0
        while i < len(s):
            k = s[i]; j = i
            while j < len(s) and s[j] == k:
                j += 1
            if (j - i) < min_run:
                if i > 0:
                    s[i:j] = s[i-1]
                elif j < len(s):
                    s[i:j] = s[j]
                changed = True
            i = j
        if not changed:
            break
    return s


def _setup_ax(ax):
    ax.set_facecolor(PANEL)
    ax.spines['bottom'].set_color(BORDER)
    ax.spines['top'].set_color(BORDER)
    ax.spines['left'].set_color(BORDER)
    ax.spines['right'].set_color(BORDER)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(True, color=BORDER, linestyle=':', alpha=0.5)


def run_regime_audit(symbol: str = 'VNINDEX', days: int = 1250, three_state: bool = False):
    print(f"🚀 Starting {symbol} HMM Regime Audit (Strict Walk-Forward Validation)...")
    mode_str = "3-State HMM" if three_state else "2-State Hybrid HMM × Trend"
    print(f"  Mode: {mode_str}")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    # ── Fetch Data ────────────────────────────────────────────
    df = pd.DataFrame()
    if symbol == 'VNINDEX':
        try:
            market = Market()
            idx    = market.index(symbol='VNINDEX')
            df     = idx.ohlcv(start=start_date, end=end_date, resolution='1D', count=days)
        except Exception as e:
            print(f"❌ {e}"); sys.exit(1)
    else:
        try:
            import sqlite3
            conn = sqlite3.connect('data/finvista.db')
            query = f"SELECT date, close, volume FROM stock_history WHERE symbol = '{symbol}' AND date >= '{start_date}' AND date <= '{end_date}' ORDER BY date ASC"
            df = pd.read_sql(query, conn)
            conn.close()
            if df.empty:
                import yfinance as yf
                df = yf.download(symbol, start=start_date, end=end_date, progress=False)
                df = df.reset_index()
                df = df.rename(columns={'Date': 'date', 'Close': 'close', 'Volume': 'volume'})
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
        except Exception as e:
            print(f"❌ {e}"); sys.exit(1)

    if df.empty or len(df) < 100:
        print("❌ Data too short."); sys.exit(1)

    tc = 'time' if 'time' in df.columns else 'date'
    df = df.sort_values(tc).reset_index(drop=True)
    df['date'] = pd.to_datetime(df[tc])
    print(f"📊 {len(df)} sessions  {df['date'].min():%Y-%m-%d} → {df['date'].max():%Y-%m-%d}")

    # ── Features ──────────────────────────────────────────────
    from backend.modules.regime_analysis.portfolio.regime_model import prepare_vnindex_features, calculate_kama
    df = prepare_vnindex_features(df)
    df['kama'] = calculate_kama(df['close'], er_period=21, fast=5, slow=100)
    
    df['log_ret'] = df['log_return']
    df['vol20'] = df['rolling_vol']
    df['log_vrat'] = df['log_volume_ratio']

    # Colors & Labels based on mode
    C = C_3STATE if three_state else C_4STATE
    LABEL = LABEL_3STATE if three_state else LABEL_4STATE
    BG_ALPHA = BG_ALPHA_3 if three_state else BG_ALPHA_4
    n_states = 3 if three_state else 4

    # ── HMM Walk-Forward ──────────────────────────────────────
    from backend.modules.regime_analysis.portfolio.regime_model import fit_vnindex_hmm_walkforward
    
    WF_TRAIN = 252
    WF_TEST  = 21
    WF_VOL   = 0.28
    
    print("\n🔄 Running Walk-Forward Validation...")
    print(f"  Parameters: train_window={WF_TRAIN}, test_window={WF_TEST}, n_restarts=3, vol_threshold={WF_VOL*100:.0f}%")
    
    wf_states, wf_probs, wf_coverage, wf_meta = fit_vnindex_hmm_walkforward(
        df, train_window=WF_TRAIN, test_window=WF_TEST, n_restarts=3, vol_threshold=WF_VOL, three_state=three_state
    )
    
    # Handle possible NaN states safely
    valid_mask = ~np.isnan(wf_states)
    wf_smooth = np.full(len(wf_states), np.nan)
    if valid_mask.any():
        wf_smooth[valid_mask] = _smooth(wf_states[valid_mask].astype(int), min_run=4)
    
    print(f"\n📊 Walk-Forward Coverage: {wf_coverage.sum()}/{len(df)} sessions ({wf_coverage.mean():.1%})")

    # Filter data to walk-forward coverage period for stats & plotting
    coverage_idx = np.where(wf_coverage & valid_mask)[0]
    if len(coverage_idx) == 0:
        print("❌ No walk-forward data generated."); sys.exit(1)
        
    wf_dates = df['date'].iloc[coverage_idx]
    wf_prices = df['close'].values[coverage_idx]
    wf_smooth_valid = wf_smooth[coverage_idx].astype(int)
    wf_probs_valid = wf_probs[coverage_idx]

    print("\n" + "="*78)
    print(f"📈 {n_states}-STATE WALK-FORWARD REGIME STATISTICS")
    print("="*78)
    print(f"{'REGIME':<32} {'N':>5} {'PCT':>6} {'MEAN/D':>9} {'ANN VOL':>9} {'SHARPE':>7}")
    print("-"*78)
    
    for k in range(n_states):
        m = wf_smooth_valid == k
        if not m.any():
            continue
        r = df.iloc[coverage_idx].loc[m, 'log_ret']
        n = m.sum()
        mu = r.mean()
        vol = r.std() * np.sqrt(252)
        ann = mu * 252
        sh = ann / vol if vol > 0 else 0
        print(f"{LABEL[k]:<32} {n:>5} {n/len(wf_smooth_valid):>6.1%} {mu:>9.4%} {vol:>9.2%} {sh:>7.2f}")
    print("="*78)

    # ── Render Walk-Forward Chart ──────────────────────────────
    print("\n🎨 Rendering Walk-Forward Chart...")
    plt.rcParams.update({
        'figure.facecolor': BG, 'savefig.facecolor': BG,
        'text.color': TEXT, 'font.family': 'DejaVu Sans',
    })

    fig = plt.figure(figsize=(18, 12), dpi=150)
    gs  = gridspec.GridSpec(3, 1, figure=fig, height_ratios=[3, 1.2, 1], hspace=0.05, top=0.93, bottom=0.07, left=0.06, right=0.97)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    for ax in (ax1, ax2, ax3):
        _setup_ax(ax)
    
    # Background shading
    for k in range(n_states):
        col = C[k]; alpha = BG_ALPHA[k]
        i = 0
        while i < len(wf_smooth_valid):
            if wf_smooth_valid[i] == k:
                j = i
                while j < len(wf_smooth_valid) and wf_smooth_valid[j] == k:
                    j += 1
                ax1.axvspan(wf_dates.iloc[i], wf_dates.iloc[j-1], color=col, alpha=alpha, linewidth=0, zorder=1)
                i = j
            else:
                i += 1
    
    # Price Line
    xn     = mdates.date2num(wf_dates)
    pts    = np.array([xn, wf_prices]).T.reshape(-1, 1, 2)
    segs   = np.concatenate([pts[:-1], pts[1:]], axis=1)
    cols   = [C[wf_smooth_valid[i]] for i in range(len(segs))]
    lc     = LineCollection(segs, colors=cols, linewidths=2.0, zorder=3)
    ax1.add_collection(lc)
    
    # KAMA
    ax1.plot(wf_dates, df['kama'].iloc[coverage_idx], color=MUTED, lw=1.0, ls='--', alpha=0.6, label='KAMA (MA)', zorder=2)
    ax1.set_xlim(wf_dates.iloc[0], wf_dates.iloc[-1])
    ax1.set_ylim(wf_prices.min() * 0.97, wf_prices.max() * 1.03)
    ax1.set_ylabel(f"{symbol} Price (Walk-Forward)", color=TEXT, fontsize=12)
    plt.setp(ax1.get_xticklabels(), visible=False)
    
    # Legend
    handles = [mpatches.Patch(facecolor=C[k], alpha=0.9, label=LABEL[k]) for k in range(n_states)]
    handles += [plt.Line2D([0],[0], color=MUTED, ls='--', lw=1.0, label='KAMA (MA)')]
    ax1.legend(handles=handles, loc='upper left', framealpha=0.8, facecolor='#21262d', edgecolor=BORDER, fontsize=9, ncol=2)
    
    # Stats text
    stats_lines = []
    for k in range(n_states):
        m  = wf_smooth_valid == k
        if not m.any(): continue
        sh = (df.iloc[coverage_idx].loc[m,'log_ret'].mean()*252) / (df.iloc[coverage_idx].loc[m,'log_ret'].std()*np.sqrt(252))
        pct = m.sum() / len(wf_smooth_valid)
        stats_lines.append(f"{LABEL[k][:20]:<20}  {pct:>5.1%}   Sharpe {sh:>+.2f}")
    ax1.text(0.99, 0.98, "\n".join(stats_lines), transform=ax1.transAxes, ha='right', va='top',
             fontsize=8, family='monospace', color=TEXT, bbox=dict(boxstyle='round,pad=0.5', facecolor='#21262d', edgecolor=BORDER, alpha=0.85))
    
    title_prefix = "3-State HMM" if three_state else "4-State Hybrid"
    fig.suptitle(f"FINVISTA · {symbol} Walk-Forward Regime Detection\n"
                 f"{title_prefix}: Train={WF_TRAIN}d, Test={WF_TEST}d, Restarts=3 | Coverage: {wf_coverage.mean():.1%}",
                 fontsize=14, fontweight='bold', color=TEXT, y=0.98)
    
    # Probabilities panel
    ax2.stackplot(wf_dates, *[wf_probs_valid[:, k] for k in range(n_states)], colors=[C[k] for k in range(n_states)], alpha=0.82)
    ax2.set_ylim(0, 1)
    ax2.set_yticks([0, 0.5, 1.0])
    ax2.set_yticklabels(['0%', '50%', '100%'], fontsize=8, color=MUTED)
    ax2.set_ylabel("Regime\nProb.", color=TEXT, fontsize=10)
    plt.setp(ax2.get_xticklabels(), visible=False)
    
    # Volatility panel
    vol_smooth_wf = df['vol20'].iloc[coverage_idx].rolling(5, min_periods=1).mean()
    ax3.fill_between(wf_dates, vol_smooth_wf, color='#e3b341', alpha=0.22)
    ax3.plot(wf_dates, vol_smooth_wf, color='#e3b341', lw=1.5, label='20-Day Volatility')
    ax3.fill_between(wf_dates, vol_smooth_wf, 0.30, where=vol_smooth_wf > 0.30, color='#f85149', alpha=0.35, label='Crisis threshold (30%)')
    ax3.axhline(0.30, color='#f85149', lw=0.8, ls=':', alpha=0.7)
    ax3.set_ylabel("Ann. Vol", color=TEXT, fontsize=10)
    ax3.set_xlabel("Date", color=MUTED, fontsize=10)
    ax3.legend(loc='upper right', fontsize=8, facecolor='#21262d', edgecolor=BORDER, framealpha=0.8)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8, color=MUTED)
    
    last_date_str = df['date'].iloc[-1].strftime("%Y%m%d")
    wf_out = f"results/{symbol.lower()}_regime_audit_{last_date_str}.png"
    fig.savefig(wf_out, facecolor=BG, edgecolor='none', bbox_inches='tight')
    plt.close(fig)
    print(f"✅  Walk-Forward Chart Saved → {wf_out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', type=str, default='VNINDEX', help='Symbol to audit')
    parser.add_argument('--days', type=int, default=1250, help='Days of history to fetch')
    parser.add_argument('--three-state', action='store_true', help='Use 3-state HMM instead of 2-state hybrid')
    args = parser.parse_args()
    run_regime_audit(symbol=args.symbol, days=args.days, three_state=args.three_state)
