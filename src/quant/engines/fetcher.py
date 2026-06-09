# -*- coding: utf-8 -*-
"""Vietcap API data ingestion and underlying historical volatility fetch."""

import os
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    import vnstock
except ImportError:
    vnstock = None

def fetch_market_cw_data() -> pd.DataFrame:
    """Fetch live symbols, prices, ratios and strikes for all listed Vietnamese Warrants."""
    print("📡 Ingesting live Covered Warrant data from trading APIs...")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Referer": "https://trading.vietcap.com.vn/quote"
    }
    
    symbols = []
    # Step 1: Fetch Symbol List with Retries
    url_list = "https://trading.vietcap.com.vn/api/price/symbols/getByGroup?group=CW"
    max_retries = 3
    backoff = 1.5
    for attempt in range(max_retries):
        try:
            resp = requests.get(url_list, headers=headers, timeout=10)
            if resp.status_code == 200:
                symbols = [item['symbol'] for item in resp.json()]
                break
            elif resp.status_code in [502, 503, 504, 429]:
                print(f"⚠️ Primary symbol registry returned {resp.status_code}. Retrying in {backoff}s... (Attempt {attempt+1}/{max_retries})")
                import time
                time.sleep(backoff)
                backoff *= 2
        except Exception:
            if attempt == max_retries - 1:
                break
            import time
            time.sleep(backoff)
            backoff *= 2

    # Step 2: Fetch details in batch (with retries if symbols fetched successfully)
    df = pd.DataFrame()
    if symbols:
        print(f"📥 Loading market details for {len(symbols)} warrant instruments...")
        url_details = "https://trading.vietcap.com.vn/api/price/symbols/getList"
        backoff = 1.5
        resp_details = None
        for attempt in range(max_retries):
            try:
                resp_details = requests.post(url_details, headers=headers, json={"symbols": symbols}, timeout=15)
                if resp_details.status_code == 200:
                    break
                elif resp_details.status_code in [502, 503, 504, 429]:
                    print(f"⚠️ Market details API returned {resp_details.status_code}. Retrying in {backoff}s... (Attempt {attempt+1}/{max_retries})")
                    import time
                    time.sleep(backoff)
                    backoff *= 2
            except Exception:
                if attempt == max_retries - 1:
                    break
                import time
                time.sleep(backoff)
                backoff *= 2
        
        rows = []
        if resp_details and resp_details.status_code == 200:
            for item in resp_details.json():
                listing = item.get('listingInfo', {})
                match = item.get('matchPrice', {})
                bidask = item.get('bidAsk', {})
                
                curr_price = float(match.get('matchPrice', 0) or listing.get('refPrice', 0) or 0)
                
                raw_val = float(match.get('accumulatedValue', 0) or 0)
                if raw_val > 0:
                    gtgd = raw_val
                else:
                    gtgd = (float(match.get('accumulatedVolume', 0) or 0) * curr_price) / 1e6
                
                rows.append({
                    'A_MaCW': listing.get('symbol'),
                    'B_MaCPCS': listing.get('underlyingSymbol'),
                    'C_GiaCW': curr_price,
                    'ref_price': float(match.get('referencePrice', 0) or listing.get('refPrice', 0) or 0),
                    'D_Volume': float(match.get('accumulatedVolume', 0) or 0),
                    'E_GTGD': gtgd,
                    'Q_DaoHan': listing.get('maturityDate'),
                    'R_Strike': float(listing.get('exercisePrice', 0) or 0),
                    'hidden_ratio': listing.get('exerciseRatio', '1:1'),
                    'issuer': listing.get('issuerName', ''),
                    'bid': float(bidask.get('bidPrices', [{}])[0].get('price', 0) or 0) if bidask.get('bidPrices') else 0,
                    'ask': float(bidask.get('askPrices', [{}])[0].get('price', 0) or 0) if bidask.get('askPrices') else 0,
                })
            df = pd.DataFrame(rows)

    # Fallback to local cache if live fetch failed completely
    cache_path = os.path.join("data", "processed", "excel_cw_report.csv")
    if df.empty:
        if os.path.exists(cache_path):
            print("\n⚠️ Live trading API is temporarily down (503 Service Unavailable).")
            print("🚀 Activating local offline cache fallback...")
            try:
                df = pd.read_csv(cache_path)
                print(f"💡 Successfully loaded {len(df)} warrants from cache ({cache_path})!")
                print("🖥️ Terminal running in OFFLINE mode with full pricing & Greeks simulator enabled!\n")
                
                # Ensure the critical columns exist in the cache df
                if 'hidden_underlying_price' not in df.columns:
                    df['hidden_underlying_price'] = df['ref_price']
                if 'O_Stock_FA' not in df.columns:
                    df['O_Stock_FA'] = 18.5
                return df
            except Exception as e:
                print(f"❌ Failed to parse local cache: {e}")
        else:
            print("❌ Live API down and no local offline cache found in data/excel_cw_report.csv.")
            return pd.DataFrame()

    # Step 3: Batch-fetch target underlying stock quotes (only if live succeeded)
    stocks = df['B_MaCPCS'].dropna().unique().tolist()
    if stocks:
        print(f"📥 Mapping last traded prices for {len(stocks)} underlying assets...")
        url_details = "https://trading.vietcap.com.vn/api/price/symbols/getList"
        resp_stocks = None
        for attempt in range(max_retries):
            try:
                resp_stocks = requests.post(url_details, headers=headers, json={"symbols": stocks}, timeout=10)
                if resp_stocks.status_code == 200:
                    break
                elif resp_stocks.status_code in [502, 503, 504, 429]:
                    import time
                    time.sleep(1)
            except Exception:
                pass
        
        if resp_stocks and resp_stocks.status_code == 200:
            p_map = {item['listingInfo']['symbol']: float(item['matchPrice'].get('matchPrice', 0) or 0) for item in resp_stocks.json()}
            df['hidden_underlying_price'] = df['B_MaCPCS'].map(p_map)
        else:
            print("⚠️ Failed underlying mapping. Reverting to reference prices.")
            df['hidden_underlying_price'] = df['ref_price']
            
    # Step 4: Map corporate credit health using the trained ML model
    try:
        import joblib
        from src.common import config
        distress_file = config.FINAL_DATASET_FILE
        model_dir = os.path.join(config.DATA_DIR, "models")
        model_path = os.path.join(model_dir, "best_distress_model.pkl")
        scaler_path = os.path.join(model_dir, "scaler.pkl")
        
        if os.path.exists(distress_file) and os.path.exists(model_path) and os.path.exists(scaler_path):
            distress_df = pd.read_csv(distress_file)
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            
            if not distress_df.empty:
                # Take the latest year's metrics per company
                latest_records = distress_df.sort_values('year').groupby('ticker').last().reset_index()
                
                # Exclude target and leakage features to align with the 32-feature trained model
                exclude_cols = {
                    "ticker", "company_name", "year", "exchange", "industry", 
                    "distress_label", "distress_label_next_year",
                    "ebit_to_interest", "icr", "current_ratio", "total_equity",
                    "springate_distressed", "zmijewski_distressed"
                }
                feature_cols = [c for c in latest_records.columns if c not in exclude_cols]
                
                try:
                    # BATCH PROCESSING FOR MASSIVE SPEEDUP!
                    features_df = latest_records[feature_cols].astype(float)
                    scaled_features = scaler.transform(features_df)
                    scaled_df = pd.DataFrame(scaled_features, columns=feature_cols)
                    
                    # Predict all probabilities at once
                    probs = model.predict_proba(scaled_df)[:, 1]
                    
                    prob_map = dict(zip(latest_records['ticker'], probs))
                    
                    if 'altman_z_score' in latest_records.columns:
                        z_scores = latest_records['altman_z_score'].fillna(3.0)
                    else:
                        z_scores = [3.0] * len(latest_records)
                    z_score_map = dict(zip(latest_records['ticker'], z_scores))
                except Exception as e:
                    print(f"⚠️ Vectorized ML prediction failed: {e}. Reverting to fallback loop.")
                    prob_map = {}
                    z_score_map = {}
                    for idx, r in latest_records.iterrows():
                        ticker = r['ticker']
                        z_score_map[ticker] = float(r.get('altman_z_score', 3.0))
                        try:
                            feat = r[feature_cols].to_frame().T.astype(float)
                            scaled = scaler.transform(feat)
                            scaled_df = pd.DataFrame(scaled, columns=feature_cols)
                            prob_map[ticker] = float(model.predict_proba(scaled_df)[0, 1])
                        except Exception:
                            prob_map[ticker] = 0.85 if r.get('distress_label') == 1 else 0.10
                
                df['underlying_distress_prob'] = df['B_MaCPCS'].map(prob_map).fillna(0.10)
                # Flag as distressed if ML probability is above threshold 50%
                df['underlying_is_distressed'] = df['underlying_distress_prob'].apply(lambda p: 1 if p >= 0.50 else 0)
                df['underlying_altman_z'] = df['B_MaCPCS'].map(z_score_map).fillna(3.0)
                
                # Integrate with existing fundamental score 'O_Stock_FA'
                # Base score from XGBoost ML + Altman Z
                def calculate_stock_fa_base(row):
                    ticker = row['B_MaCPCS']
                    prob = prob_map.get(ticker, 0.10)
                    z_score = z_score_map.get(ticker, 3.0)
                    if prob >= 0.50 or z_score < 1.1:
                        return 2.0   # Danger Red Zone
                    elif z_score <= 2.6:
                        return 10.0  # Warning Grey Zone
                    else:
                        return 18.5  # Safe / Healthy Zone
                
                df['O_Stock_FA'] = df.apply(calculate_stock_fa_base, axis=1)
                # Store prob_map for systemic integration in Step 5
                df['_prob_map_ref'] = df['B_MaCPCS'].map(prob_map).fillna(0.10)
                print(f"📊 Integrated live ML credit risk check! Dynamic distress mapping complete for {len(prob_map)} underlying companies.")
            else:
                df['O_Stock_FA'] = 18.5
                df['underlying_is_distressed'] = 0
                df['underlying_distress_prob'] = 0.10
                df['underlying_altman_z'] = 3.0
        else:
            df['O_Stock_FA'] = 18.5
            df['underlying_is_distressed'] = 0
            df['underlying_distress_prob'] = 0.10
            df['underlying_altman_z'] = 3.0
    except Exception as e:
        df['O_Stock_FA'] = 15.0
        df['underlying_is_distressed'] = 0
        df['underlying_distress_prob'] = 0.10
        df['underlying_altman_z'] = 3.0

    # Step 5: Integrate DebtRank Systemic Risk as secondary hard gate signal
    try:
        from src.common import config
        systemic_file = os.path.join(config.DATA_DIR, "systemic_health_report.csv")
        if os.path.exists(systemic_file):
            sys_df = pd.read_csv(systemic_file, usecols=["ticker", "systemic_distress_prob", "risk_delta", "systemic_health_status"])
            # Create fast lookup dict
            sys_prob_map = dict(zip(sys_df["ticker"], sys_df["systemic_distress_prob"]))
            sys_delta_map = dict(zip(sys_df["ticker"], sys_df["risk_delta"]))
            sys_status_map = dict(zip(sys_df["ticker"], sys_df["systemic_health_status"]))

            df["underlying_systemic_prob"] = df["B_MaCPCS"].map(sys_prob_map).fillna(0.10)
            df["underlying_systemic_delta"] = df["B_MaCPCS"].map(sys_delta_map).fillna(0.0)
            df["underlying_systemic_status"] = df["B_MaCPCS"].map(sys_status_map).fillna("✅ GREEN (SAFE)")

            # Flag as systemically distressed if propagated risk >= 50%
            df["underlying_systemic_is_distressed"] = df["underlying_systemic_prob"].apply(lambda p: 1 if p >= 0.50 else 0)

            # ── CẢI TIẾN THỰC CHẤT: Dùng systemic_delta như hệ số phạt liên tục vào O_Stock_FA ──
            # Công thức: FA_final = FA_base × (1 - 3 × systemic_delta)
            # Ý nghĩa: mã bị lan truyền +10% rủi ro → mất 30% điểm FA
            # Điều này phân biệt được các blue-chip an toàn khác nhau về mức độ rủi ro mạng lưới
            def recalc_fa_with_systemic(row):
                base_fa = row.get('O_Stock_FA', 18.5)
                if base_fa <= 2.0:          # Đã bị đánh dấu Danger → không thay đổi
                    return base_fa
                delta = float(row.get('underlying_systemic_delta', 0.0) or 0.0)
                sys_prob = float(row.get('underlying_systemic_prob', 0.10) or 0.10)
                # Phạt liên tục: mỗi 1% risk_delta → giảm 3% điểm FA
                penalty = min(delta * 3.0, 0.60)   # tối đa phạt 60%
                # Thêm phạt từ systemic_prob tuyệt đối (nếu > 20% thì phạt thêm)
                if sys_prob > 0.20:
                    penalty += (sys_prob - 0.20) * 0.5
                return max(base_fa * (1.0 - penalty), 2.0)

            if 'O_Stock_FA' in df.columns:
                df['O_Stock_FA'] = df.apply(recalc_fa_with_systemic, axis=1)

            # Cleanup temp column
            df.drop(columns=['_prob_map_ref'], errors='ignore', inplace=True)

            count_sys = int(df["underlying_systemic_is_distressed"].sum())
            print(f"🕸️ DebtRank systemic risk integrated! Contagion penalty applied to O_Stock_FA. {count_sys} CWs in systemic danger zone.")
        else:
            df["underlying_systemic_prob"] = 0.10
            df["underlying_systemic_delta"] = 0.0
            df["underlying_systemic_status"] = "✅ GREEN (SAFE)"
            df["underlying_systemic_is_distressed"] = 0
            print("⚠️ Systemic health report not found — run `python run.py credit --contagion` to generate it.")
    except Exception as e:
        df["underlying_systemic_prob"] = 0.10
        df["underlying_systemic_delta"] = 0.0
        df["underlying_systemic_status"] = "✅ GREEN (SAFE)"
        df["underlying_systemic_is_distressed"] = 0
        print(f"⚠️ DebtRank layer failed gracefully: {e}")

    return df

# ==========================================
# 2. ANALYTICS ENGINE INTEGRATION
# ==========================================

def fetch_underlying_historical_volatilities(symbols: list) -> dict:
    """
    Fetch and calculate multi-window Historical Volatility (10-day, 20-day, 40-day lookbacks)
    for the unique underlying symbols.
    Prioritizes the local compiled CSV cache in `data/processed/all_stock_historical_prices.csv` 
    to avoid vnstock rate limit blocks, falling back to dynamic API fetch if needed.
    """
    hv_map = {}
    if not symbols:
        return hv_map

    # Default high-quality fallback HVs (representing 40-day benchmark defaults)
    defaults = {
        'ACB': 0.185, 'FPT': 0.331, 'HPG': 0.208, 'MBB': 0.187, 'MSN': 0.224,
        'MWG': 0.326, 'SHB': 0.236, 'STB': 0.406, 'TCB': 0.270, 'TPB': 0.199,
        'VHM': 0.587, 'VIB': 0.199, 'VIC': 0.484, 'VJC': 0.335, 'VNM': 0.153,
        'VPB': 0.281, 'VRE': 0.312, 'SSI': 0.295, 'HDB': 0.210, 'PLX': 0.220,
        'POW': 0.180, 'SAB': 0.160, 'CTG': 0.220
    }

    print("\n" + "=" * 85)
    print(f"📡 Resolving Multi-Window Historical Volatility (10N, 20N, 40N) for {len(symbols)} assets...")
    print("=" * 85)

    # 1. Try to compute from consolidated local stock history CSV
    local_history_path = os.path.join("data", "processed", "all_stock_historical_prices.csv")
    local_df = pd.DataFrame()
    if os.path.exists(local_history_path):
        try:
            local_df = pd.read_csv(local_history_path)
            local_df['date'] = pd.to_datetime(local_df['date'])
            print(f"   💾 Loaded local stock history: {len(local_df)} rows. Analyzing volatility profiles...")
        except Exception as e:
            print(f"   ⚠️ Failed to load local history CSV ({e}). Reverting to dynamic endpoints.")

    now = datetime.now()
    end_date = now.strftime('%Y-%m-%d')
    start_date = (now - timedelta(days=90)).strftime('%Y-%m-%d')

    for sym in symbols:
        if not sym:
            continue
        
        # Method A: Calculate from local database cache
        if not local_df.empty and 'symbol' in local_df.columns:
            sym_data = local_df[local_df['symbol'] == sym].sort_values('date')
            if len(sym_data) >= 15:
                try:
                    close_prices = sym_data['close']
                    log_ret = np.log(close_prices / close_prices.shift(1)).dropna()
                    
                    hv_10 = float(log_ret.tail(10).std() * np.sqrt(252))
                    hv_20 = float(log_ret.tail(20).std() * np.sqrt(252))
                    hv_40 = float(log_ret.tail(40).std() * np.sqrt(252))
                    
                    # Sanity check: replace NaN or zero
                    hv_10 = hv_10 if not np.isnan(hv_10) and hv_10 > 0 else defaults.get(sym, 0.35)
                    hv_20 = hv_20 if not np.isnan(hv_20) and hv_20 > 0 else defaults.get(sym, 0.35)
                    hv_40 = hv_40 if not np.isnan(hv_40) and hv_40 > 0 else defaults.get(sym, 0.35)
                    
                    hv_map[sym] = {
                        'hv_10': hv_10,
                        'hv_20': hv_20,
                        'hv_40': hv_40
                    }
                    print(f"   📊 {sym:<8} -> HV10: {hv_10*100:5.1f}% | HV20: {hv_20*100:5.1f}% | HV40: {hv_40*100:5.1f}% (Local Cache)")
                    continue
                except Exception:
                    pass

        # Method B: Dynamic API Fetch (with lookback)
        fetched_success = False
        if vnstock:
            try:
                import time
                time.sleep(0.3)  # Rate limiting safety throttle
                quote = vnstock.Quote(symbol=sym)
                df = quote.history(start=start_date, end=end_date)
                if not df.empty and 'close' in df.columns:
                    close = df['close']
                    log_ret = np.log(close / close.shift(1)).dropna()
                    if len(log_ret) >= 5:
                        hv_10 = float(log_ret.tail(10).std() * np.sqrt(252))
                        hv_20 = float(log_ret.tail(20).std() * np.sqrt(252))
                        hv_40 = float(log_ret.tail(40).std() * np.sqrt(252))
                        
                        hv_map[sym] = {
                            'hv_10': hv_10 if not np.isnan(hv_10) else defaults.get(sym, 0.35),
                            'hv_20': hv_20 if not np.isnan(hv_20) else defaults.get(sym, 0.35),
                            'hv_40': hv_40 if not np.isnan(hv_40) else defaults.get(sym, 0.35)
                        }
                        print(f"   📡 {sym:<8} -> HV10: {hv_10*100:5.1f}% | HV20: {hv_20*100:5.1f}% | HV40: {hv_40*100:5.1f}% (Live Fetch)")
                        fetched_success = True
            except (Exception, BaseException):
                pass

        # Method C: Default Fallback
        if not fetched_success:
            def_val = defaults.get(sym, 0.35)
            hv_map[sym] = {
                'hv_10': def_val,
                'hv_20': def_val,
                'hv_40': def_val
            }
            print(f"   ⚠️ {sym:<8} -> HV10: {def_val*100:5.1f}% | HV20: {def_val*100:5.1f}% | HV40: {def_val*100:5.1f}% (Fallback Default)")

    print("=" * 85 + "\n")
    return hv_map

def fetch_derivatives_sentiment() -> dict:
    """
    Fetch VN30 and VN30F1M historical index prices using vnstock,
    calculate the daily Basis Spread, and determine current market sentiment.
    """
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    
    # Defaults in case of failure
    fallback_sentiment = {
        "status": "fallback",
        "vn30_close": 0.0,
        "vn30f1m_close": 0.0,
        "current_basis": 0.0,
        "basis_sma5": 0.0,
        "basis_momentum": 0.0,
        "vol_spike_pct": 0.0,
        "basis_zscore": 0.0,
        "market_sentiment": "NEUTRAL"
    }
    
    if not vnstock:
        return fallback_sentiment
        
    try:
        f1m_quote = vnstock.Quote(symbol='VN30F1M')
        df_f1m = f1m_quote.history(start=start_date, end=end_date)
        
        vn30_quote = vnstock.Quote(symbol='VN30')
        df_vn30 = vn30_quote.history(start=start_date, end=end_date)
        
        if df_f1m.empty or df_vn30.empty:
            return fallback_sentiment
            
        for df in [df_f1m, df_vn30]:
            if 'time' in df.columns:
                df.rename(columns={'time': 'date'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            
        merged = pd.merge(
            df_f1m[['date', 'close', 'volume']], 
            df_vn30[['date', 'close', 'volume']], 
            on='date', 
            suffixes=('_f1m', '_vn30')
        ).sort_values('date').reset_index(drop=True)
        
        if len(merged) < 5:
            return fallback_sentiment
            
        merged['basis'] = merged['close_f1m'] - merged['close_vn30']
        merged['basis_sma5'] = merged['basis'].rolling(5).mean()
        
        # Calculate dynamic Z-Score using 20-day rolling window (or maximum available)
        window = min(20, len(merged))
        rolling_mean = merged['basis'].rolling(window).mean()
        rolling_std = merged['basis'].rolling(window).std().fillna(1.5).replace(0.0, 1.5)
        merged['basis_zscore'] = (merged['basis'] - rolling_mean) / rolling_std
        
        latest = merged.iloc[-1]
        current_basis = float(latest['basis'])
        basis_sma5 = float(latest['basis_sma5']) if not pd.isna(latest['basis_sma5']) else current_basis
        basis_momentum = current_basis - basis_sma5
        latest_z = float(latest['basis_zscore']) if not pd.isna(latest['basis_zscore']) else 0.0
        
        avg_vol_5d = merged['volume_f1m'].iloc[-6:-1].mean() if len(merged) >= 6 else merged['volume_f1m'].mean()
        latest_vol = latest['volume_f1m']
        vol_spike_pct = float(((latest_vol - avg_vol_5d) / avg_vol_5d * 100)) if avg_vol_5d > 0 else 0.0
        
        # Statistical regime boundary: Z-Score <= -1.5 represents strong bearish panic
        if latest_z <= -1.5 or current_basis < -6.0:
            sentiment = 'BEARISH'
        elif latest_z >= 1.5 or (current_basis > 3.0 and basis_momentum > 0):
            sentiment = 'BULLISH'
        else:
            sentiment = 'NEUTRAL'
            
        return {
            "status": "success",
            "date": latest['date'].strftime('%Y-%m-%d'),
            "vn30_close": float(latest['close_vn30']),
            "vn30f1m_close": float(latest['close_f1m']),
            "current_basis": round(current_basis, 2),
            "basis_sma5": round(basis_sma5, 2),
            "basis_momentum": round(basis_momentum, 2),
            "vol_spike_pct": round(vol_spike_pct, 1),
            "basis_zscore": round(latest_z, 2),
            "market_sentiment": sentiment
        }
    except Exception:
        return fallback_sentiment
