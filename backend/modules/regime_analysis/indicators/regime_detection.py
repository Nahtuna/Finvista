# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: REGIME DETECTION & CHANGE MONITORING
==================================================
Combines regime detection (Kairos 8-state) with change detection and alerting.

Components:
- HamiltonMarkovSwitching: 2-state Markov Switching model (normal vs turbulent)
- RegimeDetector: 8-state Kairos regime detection (S0-S7)
- RegimeChangeDetector: Detects significant regime changes and triggers alerts
- RegimeForecastMonitor: Monitors regime forecasts for high-risk transitions

Author: samvo
"""

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os


# ─── HAMILTON MARKOV SWITCHING (2-STATE) ─────────────────────────────────────

class HamiltonMarkovSwitching:
    """
    A 2-state Markov Switching model using GaussianHMM to detect normal vs turbulent regimes.
    """
    def __init__(self):
        self.model = GaussianHMM(n_components=2, covariance_type="diag", n_iter=100, random_state=42)
        self.high_vol_state = 1

    def fit(self, returns: np.ndarray):
        x = np.asarray(returns, dtype=float).reshape(-1, 1)
        try:
            self.model.fit(x)
            # Identify the state with higher variance as the turbulent state
            if hasattr(self.model, "_covars_"):
                vols = np.sqrt(np.squeeze(self.model._covars_))
                self.high_vol_state = np.argmax(vols)
        except Exception:
            pass

    def predict_probs(self, returns: np.ndarray) -> np.ndarray:
        x = np.asarray(returns, dtype=float).reshape(-1, 1)
        try:
            probs = self.model.predict_proba(x)
            return probs[:, self.high_vol_state]
        except Exception:
            # Fallback probability: higher when absolute returns are higher
            abs_ret = np.abs(returns)
            ma = pd.Series(abs_ret).rolling(20, min_periods=1).mean().values
            fallback = abs_ret / (ma + 1e-8)
            fallback = np.clip(fallback / 2.0, 0.0, 1.0)
            return fallback


# ─── REGIME DETECTOR (8-STATE KAIROS) ───────────────────────────────────────

class RegimeDetector:
    """
    A class to detect market regimes using advanced metrics.
    """
    def __init__(self):
        pass

    def HamiltonMarkovSwitching(self) -> HamiltonMarkovSwitching:
        return HamiltonMarkovSwitching()

    @staticmethod
    def calculate_kairos_regimes(close_series_or_df) -> pd.DataFrame:
        """
        Calculates the 8 KAIROS regimes (S0 to S7) based on close prices,
        integrating SMC structural markers and options Gamma/Delta exposure from database.
        """
        if isinstance(close_series_or_df, pd.DataFrame):
            close = close_series_or_df['close']
        else:
            close = close_series_or_df

        # Determine symbol
        symbol = 'VNINDEX'
        if isinstance(close_series_or_df, pd.DataFrame) and 'symbol' in close_series_or_df.columns:
            symbol = close_series_or_df['symbol'].iloc[0]

        # Fetch SMC features & Gamma exposure from DB if available
        smc_df = pd.DataFrame()
        gamma_df = pd.DataFrame()
        
        try:
            from backend.core.database import engine
            # Query SMC Features
            smc_query = f"SELECT date, bsl_sweeps, ssl_sweeps, choch_bullish, choch_bearish, bos_bullish, bos_bearish FROM smc_features WHERE symbol = '{symbol}'"
            smc_df = pd.read_sql(smc_query, engine)
            if not smc_df.empty:
                smc_df['date'] = pd.to_datetime(smc_df['date'])
                smc_df = smc_df.drop_duplicates(subset=['date']).reset_index(drop=True)
                smc_df.set_index('date', inplace=True)
                
            # Query Gamma Exposure
            gamma_query = "SELECT date, total_gamma_exposure, net_delta_exposure FROM vn30_gamma_exposure"
            gamma_df = pd.read_sql(gamma_query, engine)
            if not gamma_df.empty:
                gamma_df['date'] = pd.to_datetime(gamma_df['date'])
                gamma_df = gamma_df.drop_duplicates(subset=['date']).reset_index(drop=True)
                gamma_df.set_index('date', inplace=True)
        except Exception:
            # Fallback if DB is not available or tables don't exist
            pass

        # Align database features to input dates
        close_dates = pd.to_datetime(close.index)
        
        if not smc_df.empty:
            smc_aligned = smc_df.reindex(close_dates).fillna("")
        else:
            smc_aligned = pd.DataFrame(index=close_dates)
            for col in ['bsl_sweeps', 'ssl_sweeps', 'choch_bullish', 'choch_bearish', 'bos_bullish', 'bos_bearish']:
                smc_aligned[col] = ""
                
        if not gamma_df.empty:
            gamma_aligned = gamma_df.reindex(close_dates).fillna(0.0)
        else:
            gamma_aligned = pd.DataFrame(index=close_dates)
            gamma_aligned['total_gamma_exposure'] = 0.0
            gamma_aligned['net_delta_exposure'] = 0.0

        returns = close.pct_change().fillna(0)

        # Fit Hamilton Markov Switching to get probability of turbulence
        hms = HamiltonMarkovSwitching()
        hms.fit(returns.values)
        p_turbulent = hms.predict_probs(returns.values)

        # Compute volatility (30-day rolling annualized standard deviation)
        vol_30 = returns.rolling(30).std() * np.sqrt(252)
        vol_30 = vol_30.fillna(vol_30.mean() if not pd.isna(vol_30.mean()) else 0.20)

        # Compute momentum (10-day price percentage change)
        momentum = close.pct_change(10) * 100
        momentum = momentum.fillna(0.0)

        regimes = []
        for i in range(len(close)):
            v = vol_30.iloc[i]
            m = momentum.iloc[i]
            p_t = p_turbulent[i]

            # Fetch SMC flags at i
            bsl = str(smc_aligned['bsl_sweeps'].iloc[i]).strip()
            ssl = str(smc_aligned['ssl_sweeps'].iloc[i]).strip()
            choch_bull = str(smc_aligned['choch_bullish'].iloc[i]).strip()
            choch_bear = str(smc_aligned['choch_bearish'].iloc[i]).strip()
            bos_bull = str(smc_aligned['bos_bullish'].iloc[i]).strip()
            bos_bear = str(smc_aligned['bos_bearish'].iloc[i]).strip()
            
            # Fetch Gamma at i
            gamma = float(gamma_aligned['total_gamma_exposure'].iloc[i])
            
            # Helper to check if string contains actual JSON array or non-empty indicator
            def has_data(val):
                return len(val) > 2 and val not in ["[]", "None", "null"]

            # Checks
            is_sweep = has_data(bsl) or has_data(ssl)
            has_choch = has_data(choch_bull) or has_data(choch_bear)
            has_bos = has_data(bos_bull) or has_data(bos_bear)

            # Enhanced mapping logic
            if is_sweep:
                reg = "S7: Quét_Thanh_Khoản"
            elif gamma < -150000.0 and abs(m) < 4.0:
                reg = "S6: Nhiễu_Động"
            elif has_choch and v >= 0.15:
                reg = "S2: Đầu_Xu_Hướng"
            elif has_bos and v >= 0.18:
                reg = "S3: Xu_Hướng_Mạnh"
            elif v < 0.12:
                reg = "S0: Đóng_Băng"
            elif v < 0.20 and abs(m) < 2.0:
                reg = "S1: Nén_Chặt"
            elif v >= 0.20 and abs(m) >= 2.0 and abs(m) < 4.0:
                reg = "S2: Đầu_Xu_Hướng"
            elif abs(m) >= 6.0 and v >= 0.35:
                reg = "S4: Cao_Trào"
            elif abs(m) >= 4.0:
                reg = "S3: Xu_Hướng_Mạnh"
            elif p_t > 0.70 and abs(m) < 3.0:
                reg = "S6: Nhiễu_Động"
            elif p_t > 0.50 and abs(m) >= 3.0:
                reg = "S7: Quét_Thanh_Khoản"
            else:
                reg = "S5: Hồi_Quy"

            regimes.append(reg)

        res = pd.DataFrame({
            'price': close,
            'momentum': momentum,
            'vol_30': vol_30,
            'p_turbulent': p_turbulent,
            'regime': regimes
        }, index=close.index)
        return res


# ─── REGIME CHANGE DETECTOR ─────────────────────────────────────────────────

class RegimeChangeDetector:
    """
    Detects significant regime changes and triggers appropriate alerts.
    """

    def __init__(self, alert_threshold: float = 0.7, min_regime_duration: int = 3):
        """
        Initialize regime change detector.

        Args:
            alert_threshold: Confidence threshold for triggering alerts
            min_regime_duration: Minimum days before considering a regime change valid
        """
        self.alert_threshold = alert_threshold
        self.min_regime_duration = min_regime_duration
        self.regime_history = self._load_regime_history()
        self.last_alerted_regime = None
        self.last_alert_time = None

    def _load_regime_history(self) -> List[Dict]:
        """Load historical regime data for pattern analysis."""
        # In production, load from database
        return []

    def detect_regime_change(self, current_regime: Dict, previous_regime: Dict) -> Dict[str, Any]:
        """
        Detect if there's a significant regime change.

        Args:
            current_regime: Current ensemble regime decision
            previous_regime: Previous ensemble regime decision

        Returns:
            Dictionary with change detection results
        """
        if not previous_regime:
            return {
                'change_detected': False,
                'reason': 'No previous regime data available'
            }

        current_bias = current_regime.get('bias', 'NEUTRAL')
        previous_bias = previous_regime.get('bias', 'NEUTRAL')
        current_regime_name = current_regime.get('regime', 'UNKNOWN')
        previous_regime_name = previous_regime.get('regime', 'UNKNOWN')

        # Detect bias change
        bias_change = current_bias != previous_bias

        # Detect regime name change
        regime_change = current_regime_name != previous_regime_name

        # Detect confidence drop
        current_confidence = current_regime.get('confidence', 0.5)
        previous_confidence = previous_regime.get('confidence', 0.5)
        confidence_drop = previous_confidence - current_confidence > 0.2

        # Detect conflict level change
        current_conflict = current_regime.get('conflict_level', 'NONE')
        previous_conflict = previous_regime.get('conflict_level', 'NONE')
        conflict_escalation = (
            (previous_conflict == 'NONE' and current_conflict != 'NONE') or
            (previous_conflict == 'LOW' and current_conflict in ['MEDIUM', 'HIGH']) or
            (previous_conflict == 'MEDIUM' and current_conflict == 'HIGH')
        )

        # Determine significance
        significant_change = bias_change or regime_change or confidence_drop or conflict_escalation

        # Assess risk level
        risk_level = self._assess_change_risk(
            current_bias, previous_bias, current_regime_name, previous_regime_name
        )

        return {
            'change_detected': significant_change,
            'bias_change': bias_change,
            'regime_change': regime_change,
            'confidence_drop': confidence_drop,
            'conflict_escalation': conflict_escalation,
            'risk_level': risk_level,
            'previous_bias': previous_bias,
            'current_bias': current_bias,
            'previous_regime': previous_regime_name,
            'current_regime': current_regime_name,
            'timestamp': datetime.now().isoformat()
        }

    def _assess_change_risk(self, current_bias: str, previous_bias: str,
                           current_regime: str, previous_regime: str) -> str:
        """Assess the risk level of a regime change."""
        # High-risk transitions
        high_risk_transitions = [
            ('LONG_CW', 'SKIP_CW'),
            ('LONG_CW', 'SHORT_CW'),
            ('NEUTRAL', 'SHORT_CW'),
            ('BULLISH_VOL_EXPANSION', 'BEARISH_HIGH_VOL'),
            ('BULLISH_VOL_CONTRACTION', 'BEARISH_HIGH_VOL')
        ]

        # Medium-risk transitions
        medium_risk_transitions = [
            ('LONG_CW', 'NEUTRAL'),
            ('NEUTRAL', 'SKIP_CW'),
            ('BULLISH_VOL_EXPANSION', 'SIDEWAYS'),
            ('SIDEWAYS', 'BEARISH_VOL_CONTRACTION')
        ]

        transition = (previous_bias, current_bias)

        if transition in high_risk_transitions:
            return 'HIGH'
        elif transition in medium_risk_transitions:
            return 'MEDIUM'
        elif current_bias == 'SHORT_CW' or 'BEARISH_HIGH_VOL' in current_regime:
            return 'ELEVATED'
        else:
            return 'LOW'

    def should_alert(self, change_detection: Dict, current_regime: Dict) -> Tuple[bool, str]:
        """
        Determine if an alert should be triggered.

        Args:
            change_detection: Result from detect_regime_change
            current_regime: Current regime decision

        Returns:
            Tuple of (should_alert, alert_reason)
        """
        if not change_detection.get('change_detected', False):
            return False, "No significant change detected"

        # Check alert threshold
        current_confidence = current_regime.get('confidence', 0.5)
        if current_confidence < self.alert_threshold:
            return False, f"Confidence below threshold ({current_confidence:.2%} < {self.alert_threshold:.2%})"

        # Check for cooldown period (avoid alert spam)
        if self.last_alert_time:
            time_since_last_alert = (datetime.now() - self.last_alert_time).total_seconds() / 3600
            if time_since_last_alert < 4:  # 4 hour cooldown
                return False, f"Cooldown period active ({time_since_last_alert:.1f}h since last alert)"

        # Risk-based alerting
        risk_level = change_detection.get('risk_level', 'LOW')

        if risk_level == 'HIGH':
            return True, f"High-risk regime transition detected: {change_detection.get('previous_bias')} → {change_detection.get('current_bias')}"
        elif risk_level == 'MEDIUM' and current_confidence > 0.8:
            return True, f"Medium-risk regime transition with high confidence: {change_detection.get('previous_bias')} → {change_detection.get('current_bias')}"
        elif change_detection.get('bias_change', False):
            return True, f"Bias change detected: {change_detection.get('previous_bias')} → {change_detection.get('current_bias')}"
        elif change_detection.get('conflict_escalation', False):
            return True, f"Model conflict escalation: {change_detection.get('previous_bias', 'N/A')} → {change_detection.get('current_bias')}"

        return False, "Change detected but below alert threshold"

    def get_alert_message(self, change_detection: Dict, current_regime: Dict,
                         symbol: str = "VNINDEX") -> str:
        """
        Generate formatted alert message (without Telegram integration).

        Args:
            change_detection: Result from detect_regime_change
            current_regime: Current regime decision
            symbol: Stock/index symbol

        Returns:
            Formatted alert message for logging or external use
        """
        message = f"[REGIME CHANGE ALERT] {symbol}\n"
        message += f"Time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        message += f"Transition: {change_detection.get('previous_regime', 'N/A')} ({change_detection.get('previous_bias', 'N/A')}) → {change_detection.get('current_regime', 'N/A')} ({change_detection.get('current_bias', 'N/A')})\n"
        message += f"Risk Level: {change_detection.get('risk_level', 'UNKNOWN')}\n"
        message += f"Confidence: {current_regime.get('confidence', 0.5):.1%}\n"
        message += f"Recommendation: {current_regime.get('recommendation', 'HOLD')}\n"

        return message

    def process_regime_update(self, current_regime: Dict, previous_regime: Dict,
                            symbol: str = "VNINDEX") -> Dict[str, Any]:
        """
        Process a regime update and log alert if necessary.

        Args:
            current_regime: Current ensemble regime decision
            previous_regime: Previous ensemble regime decision
            symbol: Stock/index symbol

        Returns:
            Processing result
        """
        # Detect change
        change_detection = self.detect_regime_change(current_regime, previous_regime)

        # Determine if alert is needed
        should_alert, alert_reason = self.should_alert(change_detection, current_regime)

        result = {
            'change_detection': change_detection,
            'should_alert': should_alert,
            'alert_reason': alert_reason,
            'alert_logged': False,
            'timestamp': datetime.now().isoformat()
        }

        # Log alert if needed
        if should_alert:
            message = self.get_alert_message(change_detection, current_regime, symbol)
            print(f"[RegimeMonitor] {message}")
            result['alert_logged'] = True
            result['alert_message'] = message
            self.last_alerted_regime = current_regime.get('regime')
            self.last_alert_time = datetime.now()

        # Log significant changes even if no alert
        if change_detection.get('change_detected', False):
            print(f"[RegimeMonitor] Regime change detected: {change_detection.get('previous_regime')} → {change_detection.get('current_regime')} (Risk: {change_detection.get('risk_level')})")

        return result


# ─── REGIME FORECAST MONITOR ───────────────────────────────────────────────

class RegimeForecastMonitor:
    """
    Monitors regime forecasts and alerts on predicted significant transitions.
    """

    def __init__(self, forecast_horizon: int = 5, alert_threshold: float = 0.6):
        """
        Initialize forecast monitor.

        Args:
            forecast_horizon: Days ahead to monitor
            alert_threshold: Probability threshold for alerts
        """
        self.forecast_horizon = forecast_horizon
        self.alert_threshold = alert_threshold

    def monitor_forecast_risk(self, forecast: Dict[str, Any], current_regime: Dict) -> Dict[str, Any]:
        """
        Monitor forecast for high-risk transitions.

        Args:
            forecast: Regime forecast from ensemble engine
            current_regime: Current regime decision

        Returns:
            Risk assessment result
        """
        current_bias = current_regime.get('bias', 'NEUTRAL')
        transition_probs = forecast.get('transition_probabilities', {})

        # Calculate probability of adverse transitions
        adverse_prob = 0.0
        adverse_regimes = []

        for regime, prob in transition_probs.items():
            if 'BEAR' in regime and 'HIGH_VOL' in regime:
                adverse_prob += prob
                adverse_regimes.append((regime, prob))

        # Determine risk level
        if adverse_prob > 0.4:
            risk_level = 'HIGH'
        elif adverse_prob > 0.25:
            risk_level = 'MEDIUM'
        elif adverse_prob > 0.15:
            risk_level = 'ELEVATED'
        else:
            risk_level = 'LOW'

        # Generate alert if high risk
        should_alert = risk_level in ['HIGH', 'MEDIUM'] and adverse_prob > self.alert_threshold

        return {
            'risk_level': risk_level,
            'adverse_transition_probability': adverse_prob,
            'adverse_regimes': adverse_regimes,
            'should_alert': should_alert,
            'forecast_horizon': forecast.get('forecast_horizon', f'T+{self.forecast_horizon}'),
            'most_likely_transition': forecast.get('most_likely_transition', 'UNKNOWN'),
            'transition_risk': forecast.get('transition_risk', 'UNKNOWN')
        }


def calculate_confluence_score(df: pd.DataFrame, sr_data: dict = None) -> dict:  # type: ignore[assignment]
    """
    Workflow #3: Confluence Score — Gộp nhiều chỉ báo thành điểm tổng hợp 0-100.
    
    Components (weights):
      - Regime quality  (35%): Kairos S0-S7 mapped to score
      - EMA trend       (30%): Price vs EMA20 vs EMA50 alignment
      - RSI momentum    (20%): RSI14 zone (oversold/neutral/overbought)
      - SR position     (15%): How close price is to nearest support/resistance
    
    Returns dict with score, verdict, and component breakdown.
    """
    if df is None or df.empty or len(df) < 20:
        return {"score": 50, "verdict": "TRUNG_LẬP", "components": {}}

    close = df['close']
    latest = close.iloc[-1]

    # --- EMA Trend (30%) ---
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1] if len(close) >= 50 else ema20
    if latest > ema20 > ema50:
        ema_score = 100
        ema_signal = "BULLISH"
        ema_detail = "Giá > EMA20 > EMA50"
    elif latest > ema20:
        ema_score = 70
        ema_signal = "TĂNG NHẸ"
        ema_detail = "Giá > EMA20, EMA20 < EMA50"
    elif latest < ema20 < ema50:
        ema_score = 0
        ema_signal = "BEARISH"
        ema_detail = "Giá < EMA20 < EMA50"
    else:
        ema_score = 30
        ema_signal = "GIẢM NHẸ"
        ema_detail = "Giá < EMA20, EMA20 > EMA50"

    # --- RSI Momentum (20%) ---
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain / loss.replace(0, float('nan'))))
    rsi_val = float(rsi.iloc[-1]) if not rsi.isna().iloc[-1] else 50.0
    if rsi_val < 30:
        rsi_score = 90   # Oversold → potential reversal up → bullish confluence
        rsi_signal = "QUÁ BÁN"
    elif rsi_val < 45:
        rsi_score = 55
        rsi_signal = "TRUNG BÌNH THẤP"
    elif rsi_val <= 60:
        rsi_score = 70
        rsi_signal = "TRUNG LẬP"
    elif rsi_val <= 70:
        rsi_score = 80
        rsi_signal = "TĂNG"
    else:
        rsi_score = 20   # Overbought → potential reversal down → bearish confluence
        rsi_signal = "QUÁ MUA"

    # --- Regime Quality (35%) ---
    regime_score_map = {
        "S3: Xu_Hướng_Mạnh": 100,
        "S2: Đầu_Xu_Hướng":   85,
        "S7: Quét_Thanh_Khoản": 75,
        "S5: Hồi_Quy":         45,
        "S4: Cao_Trào":         30,
        "S1: Nén_Chặt":         20,
        "S6: Nhiễu_Động":        5,
        "S0: Đóng_Băng":         5,
    }
    regime_val = "UNKNOWN"
    if 'regime' in df.columns:
        regime_val = str(df['regime'].iloc[-1])
    regime_score = regime_score_map.get(regime_val, 50)

    # --- SR Position (15%) ---
    sr_score = 50  # neutral default
    sr_signal = "KHÔNG RÕ"
    if sr_data:
        supports = sr_data.get('support_zones', [])
        resistances = sr_data.get('resistance_zones', [])
        if supports:
            nearest_sup = min(supports, key=lambda z: abs(z.get('price', 0) - latest))
            sup_pct = abs(latest - nearest_sup.get('price', latest)) / latest * 100
            if sup_pct < 1.5:
                sr_score = 85
                sr_signal = "GẦN HỖ TRỢ"
        if resistances:
            nearest_res = min(resistances, key=lambda z: abs(z.get('price', 0) - latest))
            res_pct = abs(latest - nearest_res.get('price', latest)) / latest * 100
            if res_pct < 1.5:
                sr_score = 20
                sr_signal = "GẦN KHÁNG CỰ"

    # --- Total Score ---
    total = (regime_score * 0.35) + (ema_score * 0.30) + (rsi_score * 0.20) + (sr_score * 0.15)
    total = round(total, 1)

    if total >= 70:
        verdict = "ĐỒNG_THUẬN_TĂNG"
    elif total >= 55:
        verdict = "TRUNG_LẬP_TÍCH_CỰC"
    elif total >= 40:
        verdict = "TRUNG_LẬP"
    elif total >= 25:
        verdict = "TRUNG_LẬP_TIÊU_CỰC"
    else:
        verdict = "ĐỒNG_THUẬN_GIẢM"

    return {
        "score": total,
        "verdict": verdict,
        "rsi_value": round(rsi_val, 1),
        "ema20": round(ema20, 2),
        "ema50": round(ema50, 2),
        "regime": regime_val,
        "components": {
            "regime":   {"score": regime_score,  "value": regime_val,  "weight": "35%"},
            "ema_trend":{"score": ema_score,      "signal": ema_signal, "detail": ema_detail, "weight": "30%"},
            "rsi":      {"score": rsi_score,      "signal": rsi_signal, "value": round(rsi_val, 1), "weight": "20%"},
            "sr_pos":   {"score": sr_score,       "signal": sr_signal,  "weight": "15%"},
        }
    }


# ─── SINGLETON INSTANCES ───────────────────────────────────────────────────

regime_change_detector = RegimeChangeDetector()
regime_forecast_monitor = RegimeForecastMonitor()
