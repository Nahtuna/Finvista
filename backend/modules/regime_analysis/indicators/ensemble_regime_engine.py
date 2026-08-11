# -*- coding: utf-8 -*-
"""
Finvista Ensemble Regime Engine
Advanced ensemble system combining multiple regime detectors with weighted voting and confidence scoring.
"""

import pandas as pd
import numpy as np

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import logging
from backend.core import config

logger = logging.getLogger(__name__)

class EnsembleRegimeEngine:
    """Ensemble engine for market regime detection and forecasting."""
    
    def __init__(self, use_ml_forecast: bool = True, ml_horizon: int = 1, instrument_type: str = "STOCK", performance_mode: str = None):
        self.use_ml_forecast = use_ml_forecast
        self.ml_horizon = ml_horizon
        self.market = "VN"
        self.instrument_type = instrument_type
        self.performance_mode = performance_mode or config.REGIME_PERFORMANCE_MODE
        self.cache_enabled = config.REGIME_CACHE_ENABLED
        self.async_enabled = config.REGIME_ASYNC_ENABLED
        self.model_weights = self._load_mode_weights()
        
    def _load_mode_weights(self) -> Dict[str, float]:
        """Load model weights based on performance mode."""
        if self.performance_mode == "FAST":
            return {
                'creed_master_grid': 0.40,
                'hmm_4state': 0.60,
                'kairos_8state': 0.0,
                'xgboost_forecast': 0.0
            }
        elif self.performance_mode == "HYBRID":
            return {
                'creed_master_grid': 0.30,
                'hmm_4state': 0.40,
                'kairos_8state': 0.15,
                'xgboost_forecast': 0.15
            }
        else:  # FULL
            return {
                'creed_master_grid': 0.25,
                'hmm_4state': 0.30,
                'kairos_8state': 0.20,
                'xgboost_forecast': 0.25
            }
    
    def _get_dynamic_weights(self, df: pd.DataFrame) -> Dict[str, float]:
        """Dynamically adjust model weights based on rolling market volatility (ATR).
        
        High volatility -> shift weight to HMM & Creed (defensive, risk containment).
        Low volatility  -> shift weight to XGBoost & Kairos (offensive, trend capturing).
        """
        base_weights = self._load_mode_weights()
        if df is None or df.empty or len(df) < 50:
            return base_weights
            
        try:
            closes = np.asarray(df['close'].values, dtype=float)
            highs = np.asarray(df['high'].values, dtype=float) if 'high' in df.columns else closes
            lows = np.asarray(df['low'].values, dtype=float) if 'low' in df.columns else closes
            
            # Compute ATR 14
            tr = np.maximum(
                highs[1:] - lows[1:],
                np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1]))
            )
            tr = np.insert(tr, 0, highs[0] - lows[0])
            atr = np.asarray(pd.Series(tr.tolist()).rolling(window=14, min_periods=1).mean().values, dtype=float)
            
            # Normalized Volatility (ATR / Close)
            norm_vol = atr / closes
            latest_vol = float(norm_vol[-1])
            avg_vol = float(np.mean(norm_vol[-50:])) # 50-day average volatility
            
            vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 1.0
            
            # Shift weights dynamically based on vol_ratio (cap shift at +/- 12%)
            shift = float(np.clip((vol_ratio - 1.0) * 0.25, -0.12, 0.12))
            
            dynamic_weights = base_weights.copy()
            if self.performance_mode == "FULL":
                dynamic_weights['hmm_4state'] += shift * 0.5
                dynamic_weights['creed_master_grid'] += shift * 0.5
                dynamic_weights['xgboost_forecast'] -= shift * 0.5
                dynamic_weights['kairos_8state'] -= shift * 0.5
            elif self.performance_mode == "HYBRID":
                dynamic_weights['hmm_4state'] += shift * 0.6
                dynamic_weights['creed_master_grid'] += shift * 0.4
                dynamic_weights['xgboost_forecast'] -= shift * 0.5
                dynamic_weights['kairos_8state'] -= shift * 0.5
                
            # Normalize weights to sum to 1.0
            total = sum(dynamic_weights.values())
            if total > 0:
                for k in dynamic_weights:
                    dynamic_weights[k] = max(0.0, dynamic_weights[k] / total)
                    
            return dynamic_weights
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate dynamic weights: {e}")
            return base_weights

    def calculate_ensemble_regime(self, df: pd.DataFrame, symbol: str = "VNINDEX") -> Dict[str, Any]:
        """Calculate ensemble regime decision using all available models."""
        if df.empty or len(df) < 50:
            return self._fallback_response("Insufficient data")
            
        self.model_weights = self._get_dynamic_weights(df)
        
        # Check cache first
        if self.cache_enabled:
            try:
                from backend.infra.redis_cache import get_cached_regime
                cached_result = get_cached_regime(symbol, self.ml_horizon, self.instrument_type)
                if cached_result:
                    logger.info(f"✅ [Regime] Cache hit for {symbol} (T+{self.ml_horizon})")
                    cached_result['cached'] = True
                    return cached_result
            except Exception as e:
                logger.warning(f"⚠️ [Regime] Cache check failed: {e}")
        
        model_predictions = {}
        
        # Run models based on performance mode
        model_predictions['creed_master_grid'] = self._run_creed_model_sync(df)
        model_predictions['hmm_4state'] = self._run_hmm_model_sync()
        
        if self.performance_mode in ["HYBRID", "FULL"]:
            model_predictions['kairos_8state'] = self._run_kairos_model_sync(df)
        else:
            model_predictions['kairos_8state'] = self._neutral_prediction()
        
        if self.performance_mode == "FULL" and self.use_ml_forecast:
            model_predictions['xgboost_forecast'] = self._get_ml_forecast(df, symbol)
        else:
            model_predictions['xgboost_forecast'] = self._neutral_prediction()
        
        # Calculate ensemble decision
        ensemble_decision = self._weighted_voting(model_predictions)
        
        # Apply MTFA trend filter
        if self.use_ml_forecast and self.ml_horizon == 1:
            try:
                t5_forecast = self._get_t5_trend_filter(df, symbol)
                ensemble_decision = self._apply_trend_filter(ensemble_decision, t5_forecast)
            except Exception as e:
                logger.warning(f"[WARNING] T+5 trend filter error: {e}")
        
        # Add metadata
        ensemble_decision['symbol'] = symbol
        ensemble_decision['timestamp'] = datetime.now().isoformat()
        ensemble_decision['model_breakdown'] = model_predictions
        ensemble_decision['weights_used'] = self.model_weights
        ensemble_decision['market'] = self.market
        ensemble_decision['instrument_type'] = self.instrument_type
        
        # Apply Vietnam market adjustments
        ensemble_decision = self._apply_vietnam_adjustments(ensemble_decision, df)
        
        # Cache the result
        if self.cache_enabled:
            try:
                from backend.infra.redis_cache import cache_ensemble_regime
                cache_ensemble_regime(ensemble_decision, symbol, self.ml_horizon, self.instrument_type, config.REGIME_TTL_SECONDS)
                logger.info(f"💾 [Regime] Cached result for {symbol} (T+{self.ml_horizon})")
            except Exception as e:
                logger.warning(f"⚠️ [Regime] Cache save failed: {e}")
        
        ensemble_decision['cached'] = False
        ensemble_decision['performance_mode'] = self.performance_mode
        return ensemble_decision
    
    async def calculate_ensemble_regime_async(self, df: pd.DataFrame, symbol: str = "VNINDEX") -> Dict[str, Any]:
        """Async version with parallel model execution for better performance."""
        if df.empty or len(df) < 50:
            return self._fallback_response("Insufficient data")
            
        self.model_weights = self._get_dynamic_weights(df)
        
        # Check cache first
        if self.cache_enabled:
            try:
                from backend.infra.redis_cache import get_cached_regime
                cached_result = get_cached_regime(symbol, self.ml_horizon, self.instrument_type)
                if cached_result:
                    logger.info(f"✅ [Regime-Async] Cache hit for {symbol} (T+{self.ml_horizon})")
                    cached_result['cached'] = True
                    return cached_result
            except Exception as e:
                logger.warning(f"⚠️ [Regime-Async] Cache check failed: {e}")
        
        model_predictions = {}
        
        # Run models in parallel based on performance mode
        tasks = []
        
        # Always run Creed and HMM (fast models)
        tasks.append(self._run_creed_model(df))
        tasks.append(self._run_hmm_model())
        
        # Add Kairos for HYBRID and FULL modes
        if self.performance_mode in ["HYBRID", "FULL"]:
            tasks.append(self._run_kairos_model(df))
        
        # Add XGBoost for FULL mode or when explicitly enabled
        if self.performance_mode == "FULL" and self.use_ml_forecast:
            tasks.append(self._run_ml_forecast(df, symbol))
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ [Regime-Async] Model {i} failed: {result}")
                continue
            
            if i == 0:  # Creed
                model_predictions['creed_master_grid'] = result
            elif i == 1:  # HMM
                model_predictions['hmm_4state'] = result
            elif i == 2:  # Kairos
                model_predictions['kairos_8state'] = result
            elif i == 3:  # XGBoost
                model_predictions['xgboost_forecast'] = result
        
        # Calculate ensemble decision
        ensemble_decision = self._weighted_voting(model_predictions)
        
        # Apply MTFA trend filter
        if self.use_ml_forecast and self.ml_horizon == 1:
            try:
                t5_forecast = await self._get_t5_trend_filter_async(df, symbol)
                ensemble_decision = self._apply_trend_filter(ensemble_decision, t5_forecast)
            except Exception as e:
                logger.warning(f"[WARNING] T+5 trend filter error: {e}")
        
        # Add metadata
        ensemble_decision['symbol'] = symbol
        ensemble_decision['timestamp'] = datetime.now().isoformat()
        ensemble_decision['model_breakdown'] = model_predictions
        ensemble_decision['weights_used'] = self.model_weights
        ensemble_decision['market'] = self.market
        ensemble_decision['instrument_type'] = self.instrument_type
        
        # Apply Vietnam market adjustments
        ensemble_decision = self._apply_vietnam_adjustments(ensemble_decision, df)
        
        # Cache the result
        if self.cache_enabled:
            try:
                from backend.infra.redis_cache import cache_ensemble_regime
                cache_ensemble_regime(ensemble_decision, symbol, self.ml_horizon, self.instrument_type, config.REGIME_TTL_SECONDS)
                logger.info(f"💾 [Regime-Async] Cached result for {symbol} (T+{self.ml_horizon})")
            except Exception as e:
                logger.warning(f"⚠️ [Regime-Async] Cache save failed: {e}")
        
        ensemble_decision['cached'] = False
        ensemble_decision['performance_mode'] = self.performance_mode
        ensemble_decision['async_mode'] = True
        return ensemble_decision
    
    async def _run_creed_model(self, df: pd.DataFrame) -> Dict:
        """Run Creed model in async context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_creed_model_sync, df)
    
    def _run_creed_model_sync(self, df: pd.DataFrame) -> Dict:
        """Synchronous Creed model execution."""
        try:
            from backend.modules.regime_analysis.indicators.creed_regime import calculate_creed_regime_from_df
            creed_result = calculate_creed_regime_from_df(df, trend_period=200)
            return {
                'regime': creed_result.get('regime', 'SIDEWAYS'),
                'bias': creed_result.get('bias', 'NEUTRAL'),
                'confidence': creed_result.get('confidence', 0.5),
                'raw_score': self._regime_to_score(creed_result.get('regime', 'SIDEWAYS'))
            }
        except Exception as e:
            logger.warning(f"[WARNING] Creed model error: {e}")
            return self._neutral_prediction()
    
    async def _run_hmm_model(self) -> Dict:
        """Run HMM model in async context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_hmm_model_sync)
    
    def _run_hmm_model_sync(self) -> Dict:
        """Synchronous HMM model execution."""
        try:
            from backend.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
            hmm_result = calculate_vnindex_regime(days=500)
            return {
                'regime': hmm_result.get('regime', 'BULLISH_VOL_EXPANSION'),
                'bias': hmm_result.get('bias', 'LONG_CW'),
                'confidence': hmm_result.get('confidence', 0.5),
                'raw_score': self._regime_to_score(hmm_result.get('regime', 'BULLISH_VOL_EXPANSION')),
                'hmm_probabilities': hmm_result.get('hmm_probabilities', {})
            }
        except Exception as e:
            logger.warning(f"[WARNING] HMM model error: {e}")
            return self._neutral_prediction()
    
    async def _run_kairos_model(self, df: pd.DataFrame) -> Dict:
        """Run Kairos model in async context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_kairos_model_sync, df)
    
    def _run_kairos_model_sync(self, df: pd.DataFrame) -> Dict:
        """Synchronous Kairos model execution."""
        try:
            from backend.modules.regime_analysis.indicators.regime_detection import RegimeDetector
            kairos_result = RegimeDetector.calculate_kairos_regimes(df)
            latest_kairos = kairos_result['regime'].iloc[-1]
            return {
                'regime': latest_kairos,
                'bias': self._kairos_to_bias(latest_kairos),
                'confidence': 0.7,
                'raw_score': self._kairos_to_score(latest_kairos)
            }
        except Exception as e:
            logger.warning(f"[WARNING] Kairos model error: {e}")
            return self._neutral_prediction()
    
    async def _run_ml_forecast(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Run ML forecast in async context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_ml_forecast, df, symbol)
    
    async def _get_t5_trend_filter_async(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Async version of T+5 trend filter."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_t5_trend_filter, df, symbol)
    
    def _weighted_voting(self, predictions: Dict[str, Dict]) -> Dict[str, Any]:
        """Perform weighted voting to get ensemble decision."""
        weighted_score = 0.0
        total_weight = 0.0
        bias_votes = {'LONG_CW': 0.0, 'SHORT_CW': 0.0, 'SKIP_CW': 0.0, 'CASH_ONLY': 0.0, 'NEUTRAL': 0.0}
        confidence_weighted_sum = 0.0
        
        for model_name, pred in predictions.items():
            weight = self.model_weights.get(model_name, 0.25)
            # Skip models with zero weight in current mode
            if weight == 0:
                continue
            score = pred.get('raw_score', 0.5)
            confidence = pred.get('confidence', 0.5)
            bias = pred.get('bias', 'NEUTRAL')
            
            weighted_score += score * weight
            total_weight += weight
            bias_votes[bias] += weight * confidence
            confidence_weighted_sum += confidence * weight
        
        if total_weight > 0:
            weighted_score /= total_weight
            confidence_weighted_sum /= total_weight
        
        final_bias = max(bias_votes, key=bias_votes.get)
        final_regime = self._score_to_regime(weighted_score)
        ensemble_confidence = self._calculate_ensemble_confidence(predictions, bias_votes)
        conflict_level = self._detect_conflict(predictions)
        
        return {
            'regime': final_regime,
            'bias': final_bias,
            'confidence': ensemble_confidence,
            'weighted_score': weighted_score,
            'conflict_level': conflict_level,
            'recommendation': self._generate_recommendation(final_bias, ensemble_confidence, conflict_level)
        }
    
    def _calculate_ensemble_confidence(self, predictions: Dict, bias_votes: Dict) -> float:
        """Calculate ensemble confidence based on agreement and individual confidences."""
        max_bias_votes = max(bias_votes.values())
        total_votes = sum(bias_votes.values())
        agreement_factor = max_bias_votes / total_votes if total_votes > 0 else 0.5
        individual_confidences = [p.get('confidence', 0.5) for p in predictions.values()]
        avg_confidence = np.mean(individual_confidences)
        ensemble_confidence = (agreement_factor * 0.6) + (avg_confidence * 0.4)
        return min(0.98, max(0.3, ensemble_confidence))
    
    def _detect_conflict(self, predictions: Dict) -> str:
        """Detect level of conflict between models."""
        biases = [p.get('bias', 'NEUTRAL') for p in predictions.values()]
        unique_biases = set(biases)
        
        if len(unique_biases) == 1:
            return "NONE"
        elif len(unique_biases) == 2:
            return "LOW"
        elif len(unique_biases) == 3:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def _generate_recommendation(self, bias: str, confidence: float, conflict: str) -> str:
        """Generate trading recommendation based on ensemble decision."""
        if conflict == "HIGH":
            return "HOLD - High model conflict, wait for clarity"
        if confidence < 0.5:
            return "HOLD - Low confidence, uncertain market conditions"
        
        if bias == "LONG_CW":
            return "STRONG BUY" if confidence > 0.8 else "BUY"
        elif bias == "SHORT_CW":
            return "STRONG SELL" if confidence > 0.8 else "SELL"
        elif bias == "CASH_ONLY":
            return "REDUCE EXPOSURE - High volatility bearish regime, move to cash"
        elif bias == "SKIP_CW":
            return "SKIP - Risk-off environment, avoid new positions"
        else:
            return "HOLD - Neutral market conditions"
    
    def _regime_to_score(self, regime: str) -> float:
        """Convert regime to numerical score (-1 to +1)."""
        regime = regime.upper()
        if 'BULL' in regime and 'VOL_EXPANSION' in regime:
            return 1.0
        elif 'BULL' in regime:
            return 0.7
        elif 'BEAR' in regime and 'HIGH_VOL' in regime:
            return -1.0
        elif 'BEAR' in regime:
            return -0.7
        else:
            return 0.0
    
    def _kairos_to_bias(self, kairos_regime: str) -> str:
        """Convert Kairos regime to trading bias."""
        if 'Xu_Hướng_Mạnh' in kairos_regime or 'Cao_Trào' in kairos_regime:
            return "LONG_CW"
        elif 'Đóng_Băng' in kairos_regime or 'Nhiễu_Động' in kairos_regime:
            return "SKIP_CW"
        elif 'Quét_Thanh_Khoản' in kairos_regime:
            return "SHORT_CW"
        else:
            return "NEUTRAL"
    
    def _kairos_to_score(self, kairos_regime: str) -> float:
        """Convert Kairos regime to numerical score."""
        bias = self._kairos_to_bias(kairos_regime)
        return {"LONG_CW": 0.8, "SHORT_CW": -0.8, "SKIP_CW": -0.3}.get(bias, 0.0)
    
    def _neutral_prediction(self) -> Dict:
        """Return neutral prediction for failed models."""
        return {'regime': 'SIDEWAYS', 'bias': 'NEUTRAL', 'confidence': 0.3, 'raw_score': 0.0}
    
    def _score_to_regime(self, score: float) -> str:
        """Convert numerical score back to regime."""
        if score > 0.8:
            return "BULLISH_VOL_EXPANSION"
        elif score > 0.4:
            return "BULLISH_VOL_CONTRACTION"
        elif score < -0.8:
            return "BEARISH_HIGH_VOL"
        elif score < -0.3:  # Lowered from -0.4 to avoid swallowing weak-to-moderate bearish signals
            return "BEARISH_VOL_CONTRACTION"
        else:
            return "SIDEWAYS"
    
    def _get_ml_forecast(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Get ML model forecast if available."""
        try:
            from backend.modules.regime_analysis.forecasting.xgboost_trainer import XGBoostRegimeTrainer
            trainer = XGBoostRegimeTrainer(horizon=self.ml_horizon)
            
            try:
                model = trainer.load_model(f"xgboost_regime_{symbol}_T{self.ml_horizon}.pkl")
                from backend.modules.regime_analysis.forecasting.features import RegimeFeatureEngineer
                features_df = RegimeFeatureEngineer.generate_features(df)
                
                if len(features_df) > 0:
                    latest_features = features_df.iloc[-1:]
                    # Align features to what the model was trained on (handles new columns added later)
                    if hasattr(model, 'feature_names_in_'):
                        expected = list(model.feature_names_in_)
                        missing = [c for c in expected if c not in latest_features.columns]
                        for c in missing:
                            latest_features = latest_features.copy()
                            latest_features[c] = 0.0
                        latest_features = latest_features[expected]
                    prediction = model.predict(latest_features)[0]
                    proba = model.predict_proba(latest_features)[0]
                    
                    regime_map = {0: "BULLISH_VOL_CONTRACTION", 1: "BULLISH_VOL_EXPANSION", 2: "BEARISH_VOL_CONTRACTION", 3: "BEARISH_VOL_EXPANSION"}
                    bias_map = {0: "LONG_CW", 1: "LONG_CW", 2: "SKIP_CW", 3: "CASH_ONLY"}  # class 3 = high vol bear → CASH_ONLY
                    
                    return {
                        'regime': regime_map.get(prediction, "SIDEWAYS"),
                        'bias': bias_map.get(prediction, "NEUTRAL"),
                        'confidence': float(max(proba)),
                        'raw_score': self._regime_to_score(regime_map.get(prediction, "SIDEWAYS")),
                        'forecast_horizon': f"T+{self.ml_horizon} days"
                    }
            except FileNotFoundError:
                pass
        except Exception as e:
            logger.warning(f"[WARNING] ML forecast error: {e}")
        
        return self._neutral_prediction()
    
    def _get_t5_trend_filter(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Get T+5 forecast as trend filter for T+1 signals."""
        try:
            from backend.modules.regime_analysis.forecasting.xgboost_trainer import XGBoostRegimeTrainer
            trainer = XGBoostRegimeTrainer(horizon=5)
            
            try:
                model = trainer.load_model(f"xgboost_regime_{symbol}_T5.pkl")
                from backend.modules.regime_analysis.forecasting.features import RegimeFeatureEngineer
                features_df = RegimeFeatureEngineer.generate_features(df)
                
                if len(features_df) > 0:
                    latest_features = features_df.iloc[-1:]
                    # Align features to what the model was trained on (handles new columns added later)
                    if hasattr(model, 'feature_names_in_'):
                        expected = list(model.feature_names_in_)
                        missing = [c for c in expected if c not in latest_features.columns]
                        for c in missing:
                            latest_features = latest_features.copy()
                            latest_features[c] = 0.0
                        latest_features = latest_features[expected]
                    prediction = model.predict(latest_features)[0]
                    proba = model.predict_proba(latest_features)[0]
                    
                    regime_map = {0: "BULLISH_VOL_CONTRACTION", 1: "BULLISH_VOL_EXPANSION", 2: "BEARISH_VOL_CONTRACTION", 3: "BEARISH_VOL_EXPANSION"}
                    bias_map = {0: "LONG_CW", 1: "LONG_CW", 2: "SKIP_CW", 3: "SKIP_CW"}
                    
                    return {
                        'regime': regime_map.get(prediction, "SIDEWAYS"),
                        'bias': bias_map.get(prediction, "NEUTRAL"),
                        'confidence': float(max(proba)),
                        'raw_score': self._regime_to_score(regime_map.get(prediction, "SIDEWAYS")),
                        'forecast_horizon': "T+5 days"
                    }
            except FileNotFoundError:
                pass
        except Exception as e:
            logger.warning(f"[WARNING] T+5 forecast error: {e}")
        
        return self._neutral_prediction()
    
    def _apply_trend_filter(self, t1_decision: Dict, t5_forecast: Dict) -> Dict:
        """Apply T+5 trend filter to T+1 decision."""
        t1_bias = t1_decision.get('bias', 'NEUTRAL')
        t5_bias = t5_forecast.get('bias', 'NEUTRAL')
        t1_confidence = t1_decision.get('confidence', 0.5)
        t5_confidence = t5_forecast.get('confidence', 0.5)
        
        opposing_signals = (
            (t1_bias == 'LONG_CW' and t5_bias == 'SHORT_CW') or
            (t1_bias == 'SHORT_CW' and t5_bias == 'LONG_CW') or
            (t1_bias == 'LONG_CW' and t5_bias == 'SKIP_CW') or
            (t1_bias == 'SHORT_CW' and t5_bias == 'SKIP_CW')
        )
        
        strong_agreement = (t1_bias == t5_bias) and (t1_confidence > 0.7 and t5_confidence > 0.6)
        
        if opposing_signals:
            t1_decision['confidence'] *= 0.5
            t1_decision['trend_filter'] = 'OPPOSED'
            t1_decision['t5_bias'] = t5_bias
            t1_decision['recommendation'] = f"HOLD - T+5 trend ({t5_bias}) opposes T+1 signal ({t1_bias})"
        elif strong_agreement:
            t1_decision['confidence'] = min(0.98, t1_decision['confidence'] * 1.1)
            t1_decision['trend_filter'] = 'ALIGNED'
            t1_decision['t5_bias'] = t5_bias
        else:
            t1_decision['trend_filter'] = 'NEUTRAL'
            t1_decision['t5_bias'] = t5_bias
        
        return t1_decision
    
    def _apply_vietnam_adjustments(self, decision: Dict, df: pd.DataFrame) -> Dict:
        """Apply Vietnam market specific adjustments."""
        if self.instrument_type == "STOCK":
            decision['effective_horizon'] = f"T+{self.ml_horizon + 2.5} days (with T+2.5 settlement)"
            decision['settlement_delay'] = 2.5
        elif self.instrument_type == "CW":
            decision['effective_horizon'] = f"T+{self.ml_horizon} days (T+0 settlement advantage)"
            decision['settlement_delay'] = 0
        elif self.instrument_type == "VN30F1M":
            decision['effective_horizon'] = f"T+{self.ml_horizon} days (T+0 settlement)"
            decision['settlement_delay'] = 0
            decision['volatility_multiplier'] = 1.5
        
        if self.instrument_type in ["STOCK", "CW"] and 'close' in df.columns:
            ref_price = df['close'].iloc[-20:].mean()
            current_price = df['close'].iloc[-1]
            price_band = (current_price - ref_price) / ref_price
            
            if abs(price_band) > 0.06:
                decision['confidence'] *= 0.5
                decision['price_band_warning'] = f"Near ±7% limit: {price_band:.1%}"
        
        return decision
    
    def _fallback_response(self, reason: str) -> Dict:
        """Return fallback response when data is insufficient."""
        return {
            'regime': 'UNKNOWN',
            'bias': 'NEUTRAL',
            'confidence': 0.0,
            'weighted_score': 0.0,
            'conflict_level': 'HIGH',
            'recommendation': f'HOLD - {reason}',
            'error': reason
        }
    
    def update_model_weights(self, performance_metrics: Dict[str, float]):
        """Update model weights based on recent performance."""
        for model_name, performance in performance_metrics.items():
            if model_name in self.model_weights:
                current_weight = self.model_weights[model_name]
                adjustment = (performance - 0.5) * 0.1
                new_weight = max(0.1, min(0.5, current_weight + adjustment))
                self.model_weights[model_name] = new_weight
        
        total_weight = sum(self.model_weights.values())
        for model_name in self.model_weights:
            self.model_weights[model_name] /= total_weight
    
    def forecast_regime_transition(self, df: pd.DataFrame, symbol: str = "VNINDEX", horizon: int = 5) -> Dict[str, Any]:
        """Forecast regime transition probability for given horizon.
        
        T+1..T+horizon biases are derived deterministically from:
        1. XGBoost model (if .pkl available)
        2. Falling back to confidence-decayed continuation of the HMM ensemble signal
        No random sampling — same input always yields same output.
        """
        current_regime = self.calculate_ensemble_regime(df, symbol)
        current_bias = current_regime.get('bias', 'NEUTRAL')
        current_confidence = current_regime.get('confidence', 0.5)

        ml_forecast = None
        if self.use_ml_forecast:
            try:
                ml_forecast = self._get_ml_forecast(df, symbol)
            except Exception:
                pass

        transition_probs = self._calculate_transition_probabilities(current_regime, df)

        # Bias buckets ordered by priority: continuation regime first, then most-likely transition
        BEARISH_BIASES = {'CASH_ONLY', 'SKIP_CW', 'SHORT_CW'}
        continuation_threshold = 0.55  # confidence must exceed this to keep current bias

        # Fallback bias: whichever regime is most likely from the transition matrix
        fallback_regime = max(transition_probs, key=transition_probs.get)
        _fallback_bias_map = {
            'BULLISH_VOL_EXPANSION': 'LONG_CW', 'BULLISH_VOL_CONTRACTION': 'LONG_CW',
            'BEARISH_HIGH_VOL': 'CASH_ONLY', 'BEARISH_VOL_CONTRACTION': 'CASH_ONLY',
            'SIDEWAYS': 'NEUTRAL'
        }
        fallback_bias = _fallback_bias_map.get(fallback_regime, 'NEUTRAL')

        forecasts = {}
        for day in range(1, horizon + 1):
            # Exponential confidence decay per session (3% decay per day)
            decayed_conf = current_confidence * (0.97 ** (day - 1))
            if decayed_conf >= continuation_threshold:
                forecasts[f't{day}_bias'] = current_bias
            else:
                forecasts[f't{day}_bias'] = fallback_bias

        return {
            'current_regime': current_regime['regime'],
            'current_bias': current_bias,
            'current_confidence': current_confidence,
            't2_bias': forecasts.get('t2_bias'),
            't3_bias': forecasts.get('t3_bias'),
            't4_bias': forecasts.get('t4_bias'),
            't5_bias': forecasts.get('t5_bias'),
            'forecast_horizon': f"T+{horizon} days",
            'transition_probabilities': transition_probs,
            'ml_forecast': ml_forecast,
            'most_likely_transition': fallback_regime,
            'transition_risk': self._assess_transition_risk(transition_probs),
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_transition_probabilities(self, current_regime: Dict, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate transition probabilities from actual HMM transmat_ learned on df.
        
        Uses the fitted HMM's transition matrix row for the current regime state.
        Falls back to an empirically-calibrated static matrix when HMM is unavailable.
        """
        REGIME_NAMES = [
            'BULLISH_VOL_CONTRACTION',  # state 0
            'BULLISH_VOL_EXPANSION',    # state 1
            'BEARISH_VOL_CONTRACTION',  # state 2
            'BEARISH_HIGH_VOL',         # state 3  (mapped from BEARISH_VOL_EXPANSION in HMM)
        ]
        current = current_regime.get('regime', 'SIDEWAYS')

        try:
            from backend.modules.regime_analysis.portfolio.regime_model import prepare_vnindex_features, fit_vnindex_hmm
            df_feats = prepare_vnindex_features(df)
            hmm_model, _ = fit_vnindex_hmm(df_feats)
            # transmat_ shape: (n_states, n_states) – row = from, col = to
            states = hmm_model.predict(df_feats)
            current_state = int(states[-1])
            row = hmm_model.transmat_[current_state]  # real learned probabilities
            return {REGIME_NAMES[i]: round(float(row[i]), 4) for i in range(len(REGIME_NAMES))}
        except Exception as e:
            logger.warning(f"[Regime] HMM transmat extraction failed ({e}), using calibrated fallback.")

        # Empirically-calibrated fallback (derived from VN-INDEX 2018-2024 state durations)
        STATIC_MATRIX = {
            'BULLISH_VOL_EXPANSION':    {'BULLISH_VOL_EXPANSION': 0.62, 'BULLISH_VOL_CONTRACTION': 0.20, 'BEARISH_VOL_CONTRACTION': 0.12, 'BEARISH_HIGH_VOL': 0.06},
            'BULLISH_VOL_CONTRACTION':  {'BULLISH_VOL_EXPANSION': 0.28, 'BULLISH_VOL_CONTRACTION': 0.45, 'BEARISH_VOL_CONTRACTION': 0.18, 'BEARISH_HIGH_VOL': 0.09},
            'BEARISH_HIGH_VOL':         {'BEARISH_HIGH_VOL': 0.52, 'BEARISH_VOL_CONTRACTION': 0.28, 'BULLISH_VOL_CONTRACTION': 0.14, 'BULLISH_VOL_EXPANSION': 0.06},
            'BEARISH_VOL_CONTRACTION':  {'BEARISH_VOL_CONTRACTION': 0.48, 'BEARISH_HIGH_VOL': 0.25, 'BULLISH_VOL_CONTRACTION': 0.18, 'BULLISH_VOL_EXPANSION': 0.09},
            'SIDEWAYS':                 {'SIDEWAYS': 0.38, 'BULLISH_VOL_EXPANSION': 0.28, 'BEARISH_HIGH_VOL': 0.22, 'BULLISH_VOL_CONTRACTION': 0.07, 'BEARISH_VOL_CONTRACTION': 0.05},
        }
        return STATIC_MATRIX.get(current, {'SIDEWAYS': 1.0})

    def _assess_transition_risk(self, transition_probs: Dict[str, float]) -> str:
        """Assess the risk level of regime transition."""
        max_prob = max(transition_probs.values())
        return "LOW" if max_prob > 0.7 else "MEDIUM" if max_prob > 0.5 else "HIGH"


# Singleton instance for the application
ensemble_engine = EnsembleRegimeEngine()
