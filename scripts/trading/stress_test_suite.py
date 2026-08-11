import sys
import os
sys.path.insert(0, r"c:\Users\samvo\Downloads\Finvista")

import pandas as pd
import numpy as np
from backend.core.database import engine
from backend.modules.regime_analysis.evaluation import evaluate_regime_performance
from backend.modules.regime_analysis.indicators.regime_detection import RegimeDetector
from backend.modules.regime_analysis.portfolio.regime_model import prepare_vnindex_features, fit_vnindex_hmm


def evaluate_symbol_ensemble(symbol: str):
    query = f"SELECT date, open, high, low, close, volume FROM stock_history WHERE symbol = '{symbol}' ORDER BY date DESC LIMIT 500"
    df = pd.read_sql(query, engine)
    if df.empty or len(df) < 200:
        print(f"⚠️ Không đủ dữ liệu cho mã {symbol}")
        return None
    df = df.iloc[::-1].reset_index(drop=True)
    df['close'] = df['close'].astype(float)

    # 1. CREED
    df_creed = df.copy()
    ema_trend = df_creed['close'].ewm(span=200, adjust=False).mean()
    ema10 = df_creed['close'].ewm(span=10, adjust=False).mean()
    ema20 = df_creed['close'].ewm(span=20, adjust=False).mean()
    dist_pct = (df_creed['close'] - ema_trend) / ema_trend
    bull = (df_creed['close'] > ema_trend) & (ema10 > ema20) & (dist_pct > 0.005)
    bear = ((df_creed['close'] < ema_trend) & (ema10 < ema20)) | (dist_pct < -0.005)
    df_creed['regime'] = 'SIDEWAYS'
    df_creed.loc[bull, 'regime'] = 'BULLISH_VOL_EXPANSION'
    df_creed.loc[bear, 'regime'] = 'BEARISH_HIGH_VOL'
    sig_creed = (df_creed['regime'].str.contains('BULLISH')).astype(int)

    # 2. KAIROS
    df_kairos = df.copy()
    regime_df = RegimeDetector.calculate_kairos_regimes(df_kairos)
    df_kairos['regime'] = regime_df['regime'].values
    sig_kairos = (df_kairos['regime'].isin(['S2: Đầu_Xu_Hướng', 'S3: Xu_Hướng_Mạnh', 'S4: Cao_Trào'])).astype(int)

    # 3. HMM
    df_hmm = df.copy()
    df_feats = prepare_vnindex_features(df_hmm)
    hybrid_model, _ = fit_vnindex_hmm(df_feats)
    states = hybrid_model.predict(df_feats)
    regime_map = {
        0: 'BULLISH_VOL_CONTRACTION',
        1: 'BULLISH_VOL_EXPANSION',
        2: 'BEARISH_VOL_CONTRACTION',
        3: 'BEARISH_VOL_EXPANSION'
    }
    common_idx = df_feats.index
    df_hmm_sub = df_hmm.loc[common_idx].copy()
    df_hmm_sub['regime'] = [regime_map.get(s, 'UNKNOWN') for s in states]
    sig_hmm = (df_hmm_sub['regime'].str.contains('BULLISH')).astype(int)

    # Ensembles
    sig_df = pd.DataFrame({
        'CREED': sig_creed.loc[common_idx],
        'KAIROS': sig_kairos.loc[common_idx],
        'HMM': sig_hmm.loc[common_idx]
    })

    # HYBRID Ensemble (Majority Vote >= 2)
    df_hybrid = df.loc[common_idx].copy()
    sig_hybrid = ((sig_df['CREED'] + sig_df['HMM'] + sig_df['KAIROS']) >= 2).astype(int)
    df_hybrid['regime'] = np.where(sig_hybrid == 1, 'BULLISH_VOL_EXPANSION', 'BEARISH_HIGH_VOL')

    # HMM + KAIROS Ensemble
    df_hk = df.loc[common_idx].copy()
    sig_hk = ((sig_df['HMM'] + sig_df['KAIROS']) >= 1).astype(int)
    df_hk['regime'] = np.where(sig_hk == 1, 'BULLISH_VOL_EXPANSION', 'BEARISH_HIGH_VOL')

    res_creed = evaluate_regime_performance(df_creed.loc[common_idx])
    res_kairos = evaluate_regime_performance(df_kairos.loc[common_idx])
    res_hmm = evaluate_regime_performance(df_hmm_sub)
    res_hk = evaluate_regime_performance(df_hk)
    res_hybrid = evaluate_regime_performance(df_hybrid)

    return {
        'CREED': res_creed,
        'KAIROS': res_kairos,
        'HMM': res_hmm,
        'HMM+KAIROS': res_hk,
        'HYBRID': res_hybrid
    }


def run_multi_symbol_suite():
    symbols = ["VNINDEX", "VN30", "FPT", "HPG", "ACB", "MWG", "VHM"]
    print("\n" + "="*95)
    print("🌍 FINVISTA MULTI-SYMBOL QUANTITATIVE ABLATION STUDY (500 TRADING DAYS)")
    print("="*95)

    summary_rows = []
    for sym in symbols:
        res_dict = evaluate_symbol_ensemble(sym)
        if not res_dict:
            continue
        
        # Determine best performing ensemble for this symbol
        best_mode = max(res_dict.keys(), key=lambda k: res_dict[k]['financial_performance']['sharpe_ratio'])
        best_res = res_dict[best_mode]['financial_performance']

        summary_rows.append({
            'Symbol': sym,
            'CREED Sharpe': res_dict['CREED']['financial_performance']['sharpe_ratio'],
            'HMM Sharpe': res_dict['HMM']['financial_performance']['sharpe_ratio'],
            'HYBRID Sharpe': res_dict['HYBRID']['financial_performance']['sharpe_ratio'],
            'Best Mode': best_mode,
            'Best Sharpe': best_res['sharpe_ratio'],
            'Best CAGR %': best_res['cagr_pct'],
            'Best MaxDD %': best_res['max_drawdown_pct']
        })

    summary_df = pd.DataFrame(summary_rows)
    print("\n---------------------------------------------------------------------------------")
    print("📊 BẢNG KẾT QUẢ SO SÁNH HIỆU SUẤT ĐA MÃ CỔ PHIẾU / CHỈ SỐ (MULTI-SYMBOL MATRIX)")
    print("---------------------------------------------------------------------------------")
    print(summary_df.to_string(index=False))

if __name__ == "__main__":
    run_multi_symbol_suite()
