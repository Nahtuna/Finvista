"""
Support & Resistance Detector
==============================
Tính vùng hỗ trợ / kháng cự dựa trên:
  1. Fractal Pivots (Williams Fractal) - đỉnh/đáy cục bộ
  2. Volume Cluster (POC - Point of Control) - vùng giá giao dịch nhiều nhất
  3. Round numbers (các mức tròn 50/100 điểm)

Output: danh sách levels với loại (support/resistance), strength, và khoảng cách % so với giá hiện tại.
"""

import numpy as np
import pandas as pd
from typing import List, Dict
from sklearn.cluster import AgglomerativeClustering
import trendln



def _fractal_pivots(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Williams Fractal: high/low pivot points with at least `window` bars on each side."""
    highs = df['high']
    lows = df['low']
    n = len(df)

    pivot_highs = []
    pivot_lows = []

    for i in range(window, n - window):
        local_high = highs.iloc[i - window: i + window + 1]
        local_low  = lows.iloc[i - window: i + window + 1]

        if 'date' in df.columns:
            date_val = df['date'].iloc[i]
        else:
            date_val = df.index[i]

        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime('%Y-%m-%d')
        elif hasattr(date_val, 'date'):
            date_str = str(date_val.date())
        else:
            date_str = str(date_val).split(' ')[0]

        if highs.iloc[i] == local_high.max():
            pivot_highs.append({'date': date_str, 'price': float(highs.iloc[i]), 'type': 'resistance'})
        if lows.iloc[i] == local_low.min():
            pivot_lows.append({'date': date_str, 'price': float(lows.iloc[i]), 'type': 'support'})

    return pd.DataFrame(pivot_highs + pivot_lows)



def _volume_poc(df: pd.DataFrame, num_bins: int = 50) -> List[Dict]:
    """
    Volume Profile: chia dải giá thành bins, tính tổng volume mỗi bin.
    Trả về top bins (POC + VAH + VAL) như các vùng key.
    """
    if 'volume' not in df.columns or df['volume'].sum() == 0:
        return []

    price_min = df['low'].min()
    price_max = df['high'].max()
    bins = np.linspace(price_min, price_max, num_bins + 1)
    bin_volume = np.zeros(num_bins)

    for _, row in df.iterrows():
        # Distribute bar volume uniformly across the high-low range
        lo, hi, vol = row['low'], row['high'], row['volume']
        if hi <= lo:
            continue
        in_range = (bins[:-1] >= lo) & (bins[1:] <= hi)
        n_bins = in_range.sum() or 1
        bin_volume[in_range] += vol / n_bins

    # POC = bin with max volume
    poc_idx = int(np.argmax(bin_volume))
    poc_price = float((bins[poc_idx] + bins[poc_idx + 1]) / 2)

    # Value Area: 70% of total volume around POC
    total_vol = bin_volume.sum()
    va_threshold = total_vol * 0.70
    va_vol = bin_volume[poc_idx]
    lo_idx, hi_idx = poc_idx, poc_idx

    while va_vol < va_threshold and (lo_idx > 0 or hi_idx < num_bins - 1):
        add_lo = bin_volume[lo_idx - 1] if lo_idx > 0 else 0
        add_hi = bin_volume[hi_idx + 1] if hi_idx < num_bins - 1 else 0
        if add_lo >= add_hi and lo_idx > 0:
            lo_idx -= 1
            va_vol += add_lo
        elif hi_idx < num_bins - 1:
            hi_idx += 1
            va_vol += add_hi
        else:
            break

    val_price = float((bins[lo_idx] + bins[lo_idx + 1]) / 2)  # Value Area Low
    vah_price = float((bins[hi_idx] + bins[hi_idx + 1]) / 2)  # Value Area High

    return [
        {'price': poc_price, 'type': 'poc',   'label': 'POC (Giá giao dịch nhiều nhất)'},
        {'price': val_price, 'type': 'support',  'label': 'VAL (Đáy Vùng Giá Trị)'},
        {'price': vah_price, 'type': 'resistance', 'label': 'VAH (Đỉnh Vùng Giá Trị)'},
    ]


def _round_levels(current_price: float, step: int = 50, count: int = 4) -> List[Dict]:
    """Các mức tròn gần giá hiện tại (tâm lý thị trường)."""
    base = round(current_price / step) * step
    levels = []
    for i in range(-count, count + 1):
        lvl = base + i * step
        if lvl <= 0:
            continue
        t = 'resistance' if lvl > current_price else 'support'
        levels.append({'price': float(lvl), 'type': t, 'label': f'Mức tròn {int(lvl)}'})
    return levels


def _cluster_levels(prices: List[float], tolerance_pct: float = 0.008) -> List[Dict]:
    """
    Gộp các mức đỉnh/đáy gần nhau sử dụng Agglomerative Clustering (tương tự các repo chuyên nghiệp).
    """
    if not prices:
        return []
        
    prices_arr = np.array(prices).reshape(-1, 1)
    mean_price = np.mean(prices)
    distance_threshold = float(tolerance_pct * mean_price)
    
    # Nếu chỉ có 1 phần tử hoặc tất cả bằng nhau, tránh lỗi AgglomerativeClustering
    if len(prices) <= 1 or np.all(prices_arr == prices_arr[0]):
        return [{
            'price': float(np.mean(prices)),
            'zone_min': float(min(prices)),
            'zone_max': float(max(prices)),
            'touch_count': len(prices)
        }]
        
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        linkage='average'
    )
    clustering.fit(prices_arr)
    
    df = pd.DataFrame({'price': prices, 'cluster': clustering.labels_})
    
    grouped = df.groupby('cluster').agg(
        price_mean=('price', 'mean'),
        price_min=('price', 'min'),
        price_max=('price', 'max'),
        touch_count=('price', 'count')
    ).reset_index()
    
    result = []
    for _, row in grouped.iterrows():
        result.append({
            'price': float(row['price_mean']),
            'zone_min': float(row['price_min']),
            'zone_max': float(row['price_max']),
            'touch_count': int(row['touch_count'])
        })
    return result


def _score_levels(df: pd.DataFrame, clustered_levels: List[Dict], tolerance_pct: float = 0.008) -> List[Dict]:
    """
    Scoring levels based on touch count and price reversals (rebound strength).
    Inspired by TouchScorer in day0market/support_resistance.
    Better levels get higher touch_count weights.
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    n = len(df)
    
    scored_levels = []
    for cl in clustered_levels:
        price = cl['price']
        score = float(cl['touch_count'])  # Start with count of initial clustered candidates
        
        for i in range(1, n):
            h, l, c = highs[i], lows[i], closes[i]
            
            # 1. Simple Touch: Price trades through or hits the level zone
            if l <= price * (1 + tolerance_pct) and h >= price * (1 - tolerance_pct):
                score += 1.0
                
                # 2. Pivot Reversal: check if it hit the level and reversed in next 3 bars
                if i < n - 3:
                    prev_c = closes[i-1]
                    post_c3 = closes[i+3]
                    # Bullish rebound from support
                    if prev_c > price and l <= price * 1.005 and post_c3 > prev_c:
                        score += 2.0
                    # Bearish rebound from resistance
                    elif prev_c < price and h >= price * 0.995 and post_c3 < prev_c:
                        score += 2.0
                        
        cl['touch_count'] = int(score)
        scored_levels.append(cl)
    return scored_levels



def _anchored_vwap(df: pd.DataFrame) -> List[Dict]:
    """
    Anchored VWAP: Giá vốn gia quyền khối lượng từ 2 mốc cực đại (Đỉnh cao nhất & Đáy thấp nhất).
    """
    if 'volume' not in df.columns or df['volume'].sum() == 0:
        return []
    
    tp = (df['high'] + df['low'] + df['close']) / 3.0
    vol = df['volume']
    
    # Anchor 1: Peak Anchor (Đỉnh cao nhất)
    max_idx = int(df['high'].idxmax())
    tp_max = tp.iloc[max_idx:]
    vol_max = vol.iloc[max_idx:]
    avwap_peak = float((tp_max * vol_max).sum() / max(1.0, vol_max.sum()))
    
    # Anchor 2: Trough Anchor (Đáy thấp nhất)
    min_idx = int(df['low'].idxmin())
    tp_min = tp.iloc[min_idx:]
    vol_min = vol.iloc[min_idx:]
    avwap_trough = float((tp_min * vol_min).sum() / max(1.0, vol_min.sum()))
    
    return [
        {'price': avwap_peak, 'type': 'avwap_peak', 'label': 'Anchored VWAP (Giá vốn từ Đỉnh)'},
        {'price': avwap_trough, 'type': 'avwap_trough', 'label': 'Anchored VWAP (Giá vốn từ Đáy)'},
    ]


def _kde_profile(df: pd.DataFrame, num_points: int = 200) -> List[Dict]:
    """
    Kernel Density Estimation (KDE) với Exponential Time Decay & Peak Prominence:
    - Thuật toán đỉnh cao nghiên cứu định lượng (neurotrader888 / Academic Papers)
    - Trọng số suy hao thời gian: e^(-lambda * t) để ưu tiên biến động giá gần nhất.
    - scipy.signal.find_peaks lọc đỉnh phân bố mật độ xác suất giá chấp nhận.
    """
    if len(df) < 20:
        return []
    try:
        from scipy.stats import gaussian_kde
        from scipy.signal import find_peaks
        closes = np.array(df['close'].values, dtype=float)
        n = len(closes)
        weights = np.exp(-0.005 * np.arange(n)[::-1])
        weights /= weights.sum()
        
        kde = gaussian_kde(closes, weights=weights)
        price_grid = np.linspace(closes.min(), closes.max(), num_points)
        density = kde(price_grid)
        
        peaks, _ = find_peaks(density, prominence=density.max() * 0.15)
        return [{'price': float(price_grid[i]), 'type': 'kde_peak', 'label': f'KDE Density Node {round(price_grid[i], 1)}'} for i in peaks]
    except Exception:
        return []

def _calculate_trendlines(df: pd.DataFrame, fractals_df: pd.DataFrame) -> Dict[str, List]:
    """
    Tìm đường xu hướng chéo bằng thư viện trendln (N^2 log N sorted slope search).
    Trả về danh sách các điểm {time: YYYY-MM-DD, value: float} cho từng đường xu hướng.
    """
    if len(df) < 20:
        return {'support_lines': [], 'resistance_lines': []}

    lows  = df['low'].values.astype(float)
    highs = df['high'].values.astype(float)

    def _series_to_points(trend_list, n, df_slice):
        """Convert trendln result list to [{time, value}] points for each line."""
        lines = []
        for points_idxs, (slope, intercept, *_rest) in trend_list:
            if len(points_idxs) < 2:
                continue
            first_i = int(min(points_idxs))
            pts = []
            for i in range(first_i, n):
                date_val = df_slice['date'].iloc[i]
                date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val).split(' ')[0]
                pts.append({'time': date_str, 'value': round(slope * i + intercept, 2)})
            if pts:
                lines.append(pts)
        return lines

    n = len(df)
    # Giới hạn 120 nến gần nhất để trendln không vẽ đường từ năm ngoái
    max_bars = min(n, 120)
    df_tl = df.tail(max_bars).reset_index(drop=True)
    lows_tl  = df_tl['low'].values.astype(float)
    highs_tl = df_tl['high'].values.astype(float)

    try:
        mins, maxs = trendln.calc_support_resistance(
            (lows_tl, highs_tl),
            extmethod=trendln.METHOD_NUMDIFF,
            method=trendln.METHOD_NSQUREDLOGN,
            window=min(60, max_bars // 2),
            errpct=0.003,
            accuracy=2,
        )
        (_minIdxs, _pmin, min_trend, _minwindows) = mins
        (_maxIdxs, _pmax, max_trend, _maxwindows) = maxs

        sup_lines = _series_to_points(min_trend[:2], max_bars, df_tl)
        res_lines = _series_to_points(max_trend[:2], max_bars, df_tl)
    except Exception:
        sup_lines, res_lines = [], []

    return {
        'support_lines': sup_lines,
        'resistance_lines': res_lines,
    }

def calculate_support_resistance(
    df: pd.DataFrame,
    current_price: float | None = None,
    fractal_window: int = 5,
    lookback_days: int = 250,
    top_n: int = 8,
) -> Dict:
    """
    Main entry point.
    """
    df = df.tail(lookback_days).copy()
    if 'date' in df.columns:
        df = df.sort_values('date').reset_index(drop=True)

    current_price = current_price or float(df['close'].iloc[-1])

    # 1. Fractal pivots with optimal 5-bar window to reduce noise and identify clean swings
    fractal_df = _fractal_pivots(df, window=5)
    fractal_prices = fractal_df['price'].tolist() if not fractal_df.empty else []

    # 1b. Recent 20-bar local extremes for pinpoint recent peak/trough detection
    recent_20 = df.tail(20)
    recent_highs = [float(recent_20['high'].max()), float(df['high'].iloc[-2])]
    recent_lows = [float(recent_20['low'].min()), float(df['low'].iloc[-2])]

    # 2. Volume POC/VAL/VAH
    vol_levels = _volume_poc(df)
    vol_prices = [v['price'] for v in vol_levels]

    # 2b. Anchored VWAP (Giá vốn Quỹ lớn / Institutional Anchors)
    avwap_levels = _anchored_vwap(df)
    avwap_prices = [v['price'] for v in avwap_levels]

    # 2c. Kernel Density Estimation (KDE) Density Nodes
    kde_levels = _kde_profile(df)
    kde_prices = [v['price'] for v in kde_levels]

    # 3. Merge all price candidates
    all_prices = fractal_prices + vol_prices + avwap_prices + kde_prices + recent_highs + recent_lows

    # Calculate dynamic tolerance based on 14-period Average True Range (ATR)
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean().iloc[-1]
    
    if pd.isna(atr) or atr <= 0:
        atr = current_price * 0.015
        
    dynamic_tolerance = float(atr / current_price)
    # Clamp tolerance between 1.0% and 3.5% to ensure sanity
    dynamic_tolerance = max(0.01, min(0.035, dynamic_tolerance))

    # 4. Cluster nearby levels (consolidate fragmented levels into zones dynamically)
    clustered = _cluster_levels(all_prices, tolerance_pct=dynamic_tolerance)

    # 4b. Score levels historically based on actual price touches & rebounds (TouchScorer)
    clustered = _score_levels(df, clustered, tolerance_pct=dynamic_tolerance * 0.8)

    # 5. Classify support vs resistance relative to current price, prioritizing multi-touch clusters
    supports = sorted([c for c in clustered if c['price'] < current_price], key=lambda x: (x['touch_count'], -abs(x['price'] - current_price)), reverse=True)
    supports_prices = [s['price'] for s in supports]

    resistances = sorted([c for c in clustered if c['price'] > current_price], key=lambda x: (x['touch_count'], -abs(x['price'] - current_price)), reverse=True)
    resistances_prices = [r['price'] for r in resistances]

    # 6. Round numbers (psychological)
    round_lvls = _round_levels(current_price, step=50, count=3)
    round_sup = sorted([r['price'] for r in round_lvls if r['price'] < current_price], reverse=True)
    round_res = sorted([r['price'] for r in round_lvls if r['price'] > current_price])

    # Major 52-Week High Peak & Low Trough Macro Extremes
    major_52w_high = float(df['high'].max())
    major_52w_low = float(df['low'].min())

    # Map clustered prices to their min and max zone boundaries
    zone_bounds = {c['price']: (c['zone_min'], c['zone_max']) for c in clustered}

    def _make_zone(price: float, zone_type: str, source: str = 'fractal', strength_override: str | None = None) -> Dict:
        dist_pct = (price - current_price) / current_price * 100
        strength = strength_override or ('STRONG' if abs(dist_pct) < 3 else ('MODERATE' if abs(dist_pct) < 8 else 'WEAK'))
        z_min, z_max = zone_bounds.get(price, (price, price))
        return {
            'price': round(price, 2),
            'zone_min': round(z_min, 2),
            'zone_max': round(z_max, 2),
            'type': zone_type,
            'distance_pct': round(dist_pct, 2),
            'strength': strength,
            'source': source,
        }

    # Merge round levels into result, dedupe
    def _merge(primary: List[float], secondary: List[float], zone_type: str) -> List[Dict]:
        result = [_make_zone(p, zone_type, 'fractal+volume') for p in primary]
        for rp in secondary:
            # Add if not too close to existing (within 1.5%)
            if all(abs(rp - r['price']) / rp > 0.015 for r in result):
                result.append(_make_zone(rp, zone_type, 'round_number'))
        result.sort(key=lambda x: abs(x['distance_pct']))
        return result[:top_n // 2]

    support_zones    = _merge(supports_prices, round_sup, 'support')
    resistance_zones = _merge(resistances_prices, round_res, 'resistance')

    # Explicitly ensure 52W High peak (1,933.11) & 52W Low floor (1,547.15) are included as Major Macro Zones
    high_match = next((r for r in resistance_zones if abs(r['price'] - major_52w_high) / major_52w_high < 0.01), None)
    if high_match:
        high_match['strength'] = 'MAJOR_ATH'
        high_match['price'] = round(major_52w_high, 2)
    else:
        resistance_zones.append(_make_zone(major_52w_high, 'resistance', '52w_high', 'MAJOR_ATH'))
    resistance_zones.sort(key=lambda x: x['price'])

    low_match = next((s for s in support_zones if abs(s['price'] - major_52w_low) / major_52w_low < 0.01), None)
    if low_match:
        low_match['strength'] = 'MAJOR_FLOOR'
        low_match['price'] = round(major_52w_low, 2)
    else:
        support_zones.append(_make_zone(major_52w_low, 'support', '52w_low', 'MAJOR_FLOOR'))
    support_zones.sort(key=lambda x: x['price'], reverse=True)

    # POC info
    poc_info = next((v for v in vol_levels if v['type'] == 'poc'), None)

    # 7. Calculate diagonal trendlines
    trendlines_data = _calculate_trendlines(df, fractal_df)

    # 8. Calculate BOS and CHoCH points dynamically
    # BOS  = trend continuation: new fractal breaks beyond the previous one (same direction)
    # CHoCH = trend reversal signal: fractal reverses against the prevailing structure
    bos_lines = []
    choch_lines = []
    if not fractal_df.empty:
        sorted_fractals = fractal_df.sort_values('date').to_dict('records')
        last_high = None
        last_low = None
        for f in sorted_fractals:
            # Cast to Timestamp for safe comparison (BUG 2 fix)
            f_date = pd.Timestamp(f['date'])
            if f['type'] == 'resistance':
                if last_high:
                    lh_date = pd.Timestamp(last_high['date'])
                    sub_df = df[(pd.to_datetime(df['date']) >= lh_date) & (pd.to_datetime(df['date']) <= f_date)]
                    if not sub_df.empty:
                        if f['price'] > last_high['price']:
                            # Higher High → BOS (continuation)
                            bos_lines.append({
                                'start_time': last_high['date'] if isinstance(last_high['date'], str) else str(last_high['date'])[:10],
                                'end_time': f['date'] if isinstance(f['date'], str) else str(f['date'])[:10],
                                'price': last_high['price'],
                                'label': 'BOS'
                            })
                        else:
                            # Lower High → CHoCH (potential reversal, BUG 1 fix)
                            choch_lines.append({
                                'start_time': last_high['date'] if isinstance(last_high['date'], str) else str(last_high['date'])[:10],
                                'end_time': f['date'] if isinstance(f['date'], str) else str(f['date'])[:10],
                                'price': last_high['price'],
                                'label': 'CHoCH'
                            })
                last_high = f
            elif f['type'] == 'support':
                if last_low:
                    ll_date = pd.Timestamp(last_low['date'])
                    sub_df = df[(pd.to_datetime(df['date']) >= ll_date) & (pd.to_datetime(df['date']) <= f_date)]
                    if not sub_df.empty:
                        if f['price'] < last_low['price']:
                            # Lower Low → BOS (continuation)
                            bos_lines.append({
                                'start_time': last_low['date'] if isinstance(last_low['date'], str) else str(last_low['date'])[:10],
                                'end_time': f['date'] if isinstance(f['date'], str) else str(f['date'])[:10],
                                'price': last_low['price'],
                                'label': 'BOS'
                            })
                        else:
                            # Higher Low → CHoCH (potential reversal, BUG 1 fix)
                            choch_lines.append({
                                'start_time': last_low['date'] if isinstance(last_low['date'], str) else str(last_low['date'])[:10],
                                'end_time': f['date'] if isinstance(f['date'], str) else str(f['date'])[:10],
                                'price': last_low['price'],
                                'label': 'CHoCH'
                            })
                last_low = f

    return {
        'current_price': current_price,
        'major_52w_high': major_52w_high,
        'major_52w_low': major_52w_low,
        'support_zones': support_zones,
        'resistance_zones': resistance_zones,
        'poc': poc_info,
        'fractals': fractal_df.to_dict('records') if not fractal_df.empty else [],
        'trendlines': trendlines_data,
        'bos_lines': bos_lines,
        'choch_lines': choch_lines,
        'lookback_days': lookback_days,
        'total_levels_found': len(clustered),
    }
