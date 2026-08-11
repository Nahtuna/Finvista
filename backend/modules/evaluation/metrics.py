"""
Signal Quality Metrics - Performance Assessment for Trading Signals
Implements various metrics to evaluate indicator performance.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from backend.core.utils import get_logger

metrics_logger = get_logger(__name__)


class SignalQualityMetrics:
    """
    Comprehensive signal quality metrics for indicator evaluation.
    
    Metrics include:
    - Signal-to-Noise Ratio (SNR)
    - Precision/Recall/F1-Score
    - Sharpe Ratio
    - Maximum Drawdown
    - Win Rate
    - Profit Factor
    """
    
    def __init__(self):
        """Initialize SignalQualityMetrics."""
        metrics_logger.info("Initialized SignalQualityMetrics")
    
    def calculate_signal_to_noise_ratio(self, signals: pd.Series, price: pd.Series) -> float:
        """
        Calculate Signal-to-Noise Ratio.
        
        SNR measures the strength of signals relative to noise (random fluctuations).
        Higher SNR indicates more reliable signals.
        
        Args:
            signals: Series of trading signals (1=buy, -1=sell, 0=hold)
            price: Series of prices
            
        Returns:
            SNR value
        """
        # Calculate signal power (variance of non-zero signals)
        signal_mask = signals != 0
        if signal_mask.sum() == 0:
            return 0.0
        
        signal_power = price[signal_mask].var()
        
        # Calculate noise power (variance of price changes during hold periods)
        hold_mask = signals == 0
        if hold_mask.sum() == 0:
            noise_power = price.var()
        else:
            noise_power = price[hold_mask].var()
        
        if noise_power == 0:
            return float('inf')
        
        snr = 10 * np.log10(signal_power / noise_power)
        
        metrics_logger.info(f"Signal-to-Noise Ratio: {snr:.3f} dB")
        return snr
    
    def calculate_precision_recall(self, signals: pd.Series, actual_changes: pd.Series) -> Dict[str, float]:
        """
        Calculate precision, recall, and F1-score for signal accuracy.
        
        Precision: How many predicted signals were correct
        Recall: How many actual changes were detected
        F1-Score: Harmonic mean of precision and recall
        
        Args:
            signals: Series of predicted signals
            actual_changes: Series of actual direction changes (1=up, -1=down, 0=no change)
            
        Returns:
            Dictionary with precision, recall, f1_score
        """
        # Real Directional Precision & Recall (Matching signal direction with price outcome)
        # True Positive (TP): BUY signal when price rose (>0) OR SELL signal when price fell (<0)
        tp = int(((signals > 0) & (actual_changes > 0)).sum() + ((signals < 0) & (actual_changes < 0)).sum())
        # False Positive (FP): BUY signal when price fell/flat (<=0) OR SELL signal when price rose/flat (>=0)
        fp = int(((signals > 0) & (actual_changes <= 0)).sum() + ((signals < 0) & (actual_changes >= 0)).sum())
        # False Negative (FN): Neutral signal (0) during significant price movement (> 0.5 * std)
        change_std = actual_changes.std() if len(actual_changes) > 0 else 0.01
        fn = int(((signals == 0) & (actual_changes.abs() > 0.5 * change_std)).sum())
        
        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics_logger.info(f"Directional Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {f1_score:.3f}")
        
        return {
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1_score)
        }
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe Ratio.
        
        Sharpe Ratio measures risk-adjusted returns.
        Higher values indicate better risk-adjusted performance.
        
        Args:
            returns: Series of returns
            risk_free_rate: Annual risk-free rate (default 2%)
            
        Returns:
            Sharpe Ratio value
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        # Daily risk-free rate
        daily_rf = risk_free_rate / 252
        
        # Excess returns
        excess_returns = returns - daily_rf
        
        # Sharpe ratio (annualized)
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        
        metrics_logger.info(f"Sharpe Ratio: {sharpe:.3f}")
        return sharpe
    
    def calculate_max_drawdown(self, equity_curve: pd.Series) -> Dict[str, float]:
        """
        Calculate Maximum Drawdown.
        
        Maximum drawdown measures the largest peak-to-trough decline.
        Lower values indicate better risk management.
        
        Args:
            equity_curve: Series of equity values
            
        Returns:
            Dictionary with max_drawdown and drawdown_duration
        """
        if len(equity_curve) == 0:
            return {'max_drawdown': 0.0, 'drawdown_duration': 0}
        
        # Calculate running maximum
        running_max = equity_curve.cummax()
        
        # Calculate drawdown
        drawdown = (equity_curve - running_max) / running_max
        
        # Maximum drawdown
        max_dd = drawdown.min()
        
        # Find drawdown duration (in bars)
        max_dd_idx = drawdown.idxmin()
        peak_idx = equity_curve[:max_dd_idx].idxmax()
        duration = (max_dd_idx - peak_idx).days if hasattr(max_dd_idx - peak_idx, 'days') else (max_dd_idx - peak_idx)
        
        metrics_logger.info(f"Max Drawdown: {max_dd:.3f}, Duration: {duration}")
        
        return {
            'max_drawdown': float(max_dd),
            'drawdown_duration': int(duration)
        }
    
    def calculate_win_rate(self, returns: pd.Series) -> Dict[str, float]:
        """
        Calculate Win Rate and related statistics.
        
        Args:
            returns: Series of returns
            
        Returns:
            Dictionary with win_rate, avg_win, avg_loss
        """
        if len(returns) == 0:
            return {'win_rate': 0.0, 'avg_win': 0.0, 'avg_loss': 0.0}
        
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        
        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.0
        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = losses.mean() if len(losses) > 0 else 0.0
        
        metrics_logger.info(f"Win Rate: {win_rate:.3f}, Avg Win: {avg_win:.3f}, Avg Loss: {avg_loss:.3f}")
        
        return {
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss)
        }
    
    def calculate_profit_factor(self, returns: pd.Series) -> float:
        """
        Calculate Profit Factor.
        
        Profit Factor = Gross Profit / Gross Loss
        Values > 1 indicate profitable strategy.
        
        Args:
            returns: Series of returns
            
        Returns:
            Profit Factor value
        """
        if len(returns) == 0:
            return 0.0
        
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        profit_factor = gross_profit / gross_loss
        
        metrics_logger.info(f"Profit Factor: {profit_factor:.3f}")
        return profit_factor
    
    def calculate_indicator_lag(self, indicator: pd.Series, price: pd.Series) -> float:
        """
        Calculate indicator lag (response time).
        
        Measures how quickly the indicator responds to price changes.
        Lower lag indicates more responsive indicator.
        
        Args:
            indicator: Series of indicator values
            price: Series of prices
            
        Returns:
            Average lag in bars
        """
        # Calculate cross-correlation to find optimal lag
        price_norm = (price - price.mean()) / price.std()
        indicator_norm = (indicator - indicator.mean()) / indicator.std()
        
        max_lag = min(20, len(price) // 4)
        correlations = []
        
        for lag in range(max_lag + 1):
            if lag < len(price_norm) and lag < len(indicator_norm):
                corr = price_norm[lag:].corr(indicator_norm[:-lag] if lag > 0 else indicator_norm)
                correlations.append((lag, corr))
        
        if not correlations:
            return 0.0
        
        # Find lag with maximum correlation
        best_lag = max(correlations, key=lambda x: abs(x[1]))[0]
        
        metrics_logger.info(f"Indicator Lag: {best_lag} bars")
        return float(best_lag)
    
    def calculate_stability(self, indicator: pd.Series, window: int = 20) -> float:
        """
        Calculate indicator stability (whipsaw resistance).
        
        Measures how frequently the indicator changes direction.
        Lower values indicate more stable indicator.
        
        Args:
            indicator: Series of indicator values
            window: Window for stability calculation
            
        Returns:
            Stability score (0-1, higher is more stable)
        """
        if len(indicator) < window:
            return 0.0
        
        # Count direction changes
        diff = indicator.diff()
        direction_changes = ((diff.shift(1) * diff) < 0).sum()
        
        # Normalize by length
        stability = 1 - (direction_changes / len(indicator))
        
        metrics_logger.info(f"Indicator Stability: {stability:.3f}")
        return float(stability)
    
    def comprehensive_evaluation(self, signals: pd.Series, price: pd.Series, returns: pd.Series) -> Dict[str, Any]:
        """
        Perform comprehensive signal quality evaluation.
        
        Args:
            signals: Series of trading signals
            price: Series of prices
            returns: Series of returns
            
        Returns:
            Dictionary with all evaluation metrics
        """
        metrics_logger.info("Starting comprehensive signal evaluation")
        
        # Calculate actual price changes for precision/recall
        price_changes = price.pct_change()
        actual_direction = (price_changes > 0).astype(int) - (price_changes < 0).astype(int)
        
        # Calculate all metrics
        snr = self.calculate_signal_to_noise_ratio(signals, price)
        precision_recall = self.calculate_precision_recall(signals, actual_direction)
        sharpe = self.calculate_sharpe_ratio(returns)
        max_dd = self.calculate_max_drawdown(returns.cumsum())
        win_rate = self.calculate_win_rate(returns)
        profit_factor = self.calculate_profit_factor(returns)
        
        # Calculate equity curve for additional metrics
        equity_curve = (1 + returns).cumprod()
        
        evaluation = {
            'signal_to_noise_ratio': snr,
            'precision': precision_recall['precision'],
            'recall': precision_recall['recall'],
            'f1_score': precision_recall['f1_score'],
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd['max_drawdown'],
            'drawdown_duration': max_dd['drawdown_duration'],
            'win_rate': win_rate['win_rate'],
            'avg_win': win_rate['avg_win'],
            'avg_loss': win_rate['avg_loss'],
            'profit_factor': profit_factor,
            'total_return': float(returns.sum()),
            'final_equity': float(equity_curve.iloc[-1]),
            'num_signals': int((signals != 0).sum())
        }
        
        metrics_logger.info(f"Comprehensive evaluation completed: {len(evaluation)} metrics")
        return evaluation
