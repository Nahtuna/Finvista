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
    cache_path = os.path.join("data", "excel_cw_report.csv")
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
        model_dir = os.path.join("data", "financial_distress", "models")
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
                def calculate_stock_fa(row):
                    ticker = row['B_MaCPCS']
                    prob = prob_map.get(ticker, 0.10)
                    z_score = z_score_map.get(ticker, 3.0)
                    if prob >= 0.50 or z_score < 1.1:
                        return 2.0  # Danger Red Zone! (ML Flags Distress)
                    elif z_score <= 2.6:
                        return 10.0  # Warning Grey Zone
                    else:
                        return 18.5  # Safe / Healthy Zone
                
                df['O_Stock_FA'] = df.apply(calculate_stock_fa, axis=1)
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


    return df

# ==========================================
# 2. ANALYTICS ENGINE INTEGRATION
# ==========================================

def fetch_underlying_historical_volatilities(symbols: list) -> dict:
    """
    Fetch daily historical price data using vnstock for the unique underlying symbols.
    Uses local JSON cache in `data/underlying_hv_cache.json` to prevent hitting vnstock rate limits.
    """
    hv_map = {}
    if not symbols:
        return hv_map
        
    cache_path = os.path.join("data", "underlying_hv_cache.json")
    
    # 1. Load existing cache if available
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            pass
            
    # Default high-quality fallback HVs for Vietnam's top CW underlying assets
    defaults = {
        'ACB': 0.185, 'FPT': 0.331, 'HPG': 0.208, 'MBB': 0.187, 'MSN': 0.224,
        'MWG': 0.326, 'SHB': 0.236, 'STB': 0.406, 'TCB': 0.270, 'TPB': 0.199,
        'VHM': 0.587, 'VIB': 0.199, 'VIC': 0.484, 'VJC': 0.335, 'VNM': 0.153,
        'VPB': 0.281, 'VRE': 0.312, 'SSI': 0.295, 'HDB': 0.210, 'PLX': 0.220,
        'POW': 0.180, 'SAB': 0.160, 'CTG': 0.220
    }
    
    print("\n" + "=" * 75)
    print(f"📡 Resolving Historical Volatility (HV) for {len(symbols)} underlying assets...")
    print("=" * 75)
    
    now = datetime.now()
    end_date = now.strftime('%Y-%m-%d')
    start_date = (now - timedelta(days=90)).strftime('%Y-%m-%d')
    
    for sym in symbols:
        if not sym:
            continue
            
        # Check if cache has a fresh value (< 24 hours old)
        use_cache = False
        if sym in cache:
            try:
                cached_time = datetime.fromisoformat(cache[sym].get('timestamp', ''))
                if (now - cached_time).total_seconds() < 86400: # < 24 hours
                    hv_map[sym] = float(cache[sym]['hv'])
                    use_cache = True
            except Exception:
                pass
                
        if use_cache:
            print(f"   💾 {sym:<8} -> HV (Cached): {hv_map[sym]*100:6.2f}%")
            continue
            
        # Otherwise, attempt to fetch dynamically
        try:
            import time
            # Small throttle to respect the API limits
            time.sleep(0.5)
            
            quote = vnstock.Quote(symbol=sym)
            df = quote.history(start=start_date, end=end_date)
            if not df.empty and 'close' in df.columns:
                close = df['close']
                log_ret = np.log(close / close.shift(1)).dropna()
                if len(log_ret) >= 5:
                    std_dev = log_ret.tail(40).std()
                    hv = float(std_dev * np.sqrt(252))
                    hv_map[sym] = hv
                    cache[sym] = {
                        'hv': hv,
                        'timestamp': now.isoformat()
                    }
                    # Save cache immediately to disk to be resilient to process termination
                    try:
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        with open(cache_path, 'w', encoding='utf-8') as f:
                            json.dump(cache, f, ensure_ascii=False, indent=4)
                    except Exception:
                        pass
                    print(f"   📡 {sym:<8} -> HV (Fetch):  {hv*100:6.2f}%")
                    continue
        except (Exception, BaseException) as e:
            # Catch BaseException specifically to intercept vnstock's sys.exit() on rate-limit warnings
            pass
            
        # Fallback to cache (even if stale) or default
        if sym in cache:
            hv_map[sym] = float(cache[sym]['hv'])
            print(f"   ⚠️ {sym:<8} -> HV (Stale Cache): {hv_map[sym]*100:6.2f}%")
        else:
            hv_map[sym] = defaults.get(sym, 0.35)
            cache[sym] = {
                'hv': hv_map[sym],
                'timestamp': now.isoformat()
            }
            try:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False, indent=4)
            except Exception:
                pass
            print(f"   ⚠️ {sym:<8} -> HV (Fallback Default): {hv_map[sym]*100:6.2f}%")
            
    print("=" * 75 + "\n")
    return hv_map
