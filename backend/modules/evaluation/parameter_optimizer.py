"""
Parameter Optimizer - Walk-Forward Validation for Parameter Optimization
Implements walk-forward validation to optimize indicator parameters.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from backend.core.utils import get_logger

optimizer_logger = get_logger(__name__)


class ParameterOptimizer:
    """
    Parameter optimizer using walk-forward validation.
    
    Walk-forward validation:
    1. Split data into train/validation/test periods
    2. Optimize parameters on training data
    3. Validate on validation data
    4. Test on out-of-sample data
    5. Roll forward and repeat
    """
    
    def __init__(self, train_pct: float = 0.6, val_pct: float = 0.2, test_pct: float = 0.2):
        """
        Initialize Parameter Optimizer.
        
        Args:
            train_pct: Percentage of data for training
            val_pct: Percentage of data for validation
            test_pct: Percentage of data for testing
        """
        self.train_pct = train_pct
        self.val_pct = val_pct
        self.test_pct = test_pct
        optimizer_logger.info(f"Initialized ParameterOptimizer with train={train_pct}, val={val_pct}, test={test_pct}")
    
    def split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split data into train, validation, and test sets.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        n = len(df)
        train_end = int(n * self.train_pct)
        val_end = int(n * (self.train_pct + self.val_pct))
        
        train_df = df.iloc[:train_end]
        val_df = df.iloc[train_end:val_end]
        test_df = df.iloc[val_end:]
        
        optimizer_logger.info(f"Data split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")
        return train_df, val_df, test_df
    
    def optimize_smc_parameters(self, train_df: pd.DataFrame, val_df: pd.DataFrame, 
                                param_grid: Dict[str, List]) -> Dict[str, Any]:
        """
        Optimize SMC parameters using grid search.
        
        Args:
            train_df: Training data
            val_df: Validation data
            param_grid: Dictionary of parameter ranges
            
        Returns:
            Dictionary with best parameters and performance
        """
        from backend.modules.smc_analysis.service import SMCAnalysisService
        from backend.modules.evaluation.signal_generator import AdvancedSignalGenerator
        from backend.modules.evaluation.advanced_backtester import AdvancedBacktester
        
        best_params = {}
        best_score = -np.inf
        best_performance = {}
        
        # Generate parameter combinations
        pivot_windows = param_grid.get('pivot_window', [3, 5, 7, 10])
        liquidity_lookbacks = param_grid.get('liquidity_lookback', [3, 5, 7, 10])
        
        optimizer_logger.info(f"Optimizing SMC parameters: {len(pivot_windows) * len(liquidity_lookbacks)} combinations")
        
        for pivot_window in pivot_windows:
            for liquidity_lookback in liquidity_lookbacks:
                try:
                    # Train on training data
                    smc_service = SMCAnalysisService(pivot_window=pivot_window, liquidity_lookback=liquidity_lookback)
                    signal_generator = AdvancedSignalGenerator()
                    
                    features = smc_service.extract_all_features(train_df, 'TRAIN')
                    signals = signal_generator.generate_smc_signals(train_df, features)
                    
                    # Validate on validation data
                    val_features = smc_service.extract_all_features(val_df, 'VAL')
                    val_signals = signal_generator.generate_smc_signals(val_df, val_features)
                    
                    # Calculate performance
                    if (val_signals != 0).sum() > 0:
                        backtester = AdvancedBacktester()
                        backtest_results = backtester.run_backtest(val_df, val_signals)
                        
                        # Score based on Sharpe ratio and win rate
                        score = backtest_results['win_rate'] * 0.5 + (backtest_results['total_return'] + 1) * 0.5
                        
                        if score > best_score:
                            best_score = score
                            best_params = {
                                'pivot_window': pivot_window,
                                'liquidity_lookback': liquidity_lookback
                            }
                            best_performance = backtest_results
                            
                            optimizer_logger.info(f"New best params: pivot_window={pivot_window}, liquidity_lookback={liquidity_lookback}, score={score:.3f}")
                
                except Exception as e:
                    optimizer_logger.warning(f"Error optimizing params: {e}")
                    continue
        
        optimizer_logger.info(f"Best SMC parameters: {best_params}, score: {best_score:.3f}")
        return {
            'best_params': best_params,
            'best_score': best_score,
            'performance': best_performance
        }
    
    def optimize_custom_parameters(self, train_df: pd.DataFrame, val_df: pd.DataFrame,
                                  param_grid: Dict[str, List]) -> Dict[str, Any]:
        """
        Optimize Custom Indicator parameters using grid search.
        
        Args:
            train_df: Training data
            val_df: Validation data
            param_grid: Dictionary of parameter ranges
            
        Returns:
            Dictionary with best parameters and performance
        """
        from backend.modules.custom_indicators.service import CustomIndicatorService
        from backend.modules.evaluation.signal_generator import AdvancedSignalGenerator
        from backend.modules.evaluation.advanced_backtester import AdvancedBacktester
        
        best_params = {}
        best_score = -np.inf
        best_performance = {}
        
        # Generate parameter combinations
        atr_periods = param_grid.get('atr_period', [7, 14, 21, 28])
        volume_periods = param_grid.get('volume_period', [10, 20, 30, 40])
        
        optimizer_logger.info(f"Optimizing Custom parameters: {len(atr_periods) * len(volume_periods)} combinations")
        
        for atr_period in atr_periods:
            for volume_period in volume_periods:
                try:
                    # Train on training data
                    indicator_service = CustomIndicatorService(
                        mk_atr_period=atr_period,
                        mk_volume_period=volume_period
                    )
                    signal_generator = AdvancedSignalGenerator()
                    
                    indicators = indicator_service.compute_all_indicators(train_df)
                    signals = signal_generator.generate_custom_signals(train_df, indicators)
                    
                    # Validate on validation data
                    val_indicators = indicator_service.compute_all_indicators(val_df)
                    val_signals = signal_generator.generate_custom_signals(val_df, val_indicators)
                    
                    # Calculate performance
                    if (val_signals != 0).sum() > 0:
                        backtester = AdvancedBacktester()
                        backtest_results = backtester.run_backtest(val_df, val_signals)
                        
                        # Score based on Sharpe ratio and win rate
                        score = backtest_results['win_rate'] * 0.5 + (backtest_results['total_return'] + 1) * 0.5
                        
                        if score > best_score:
                            best_score = score
                            best_params = {
                                'atr_period': atr_period,
                                'volume_period': volume_period
                            }
                            best_performance = backtest_results
                            
                            optimizer_logger.info(f"New best params: atr_period={atr_period}, volume_period={volume_period}, score={score:.3f}")
                
                except Exception as e:
                    optimizer_logger.warning(f"Error optimizing params: {e}")
                    continue
        
        optimizer_logger.info(f"Best Custom parameters: {best_params}, score: {best_score:.3f}")
        return {
            'best_params': best_params,
            'best_score': best_score,
            'performance': best_performance
        }
    
    def walk_forward_validation(self, df: pd.DataFrame, num_windows: int = 5,
                                param_grid: Dict[str, List] = None) -> Dict[str, Any]:
        """
        Perform walk-forward validation.
        
        Args:
            df: DataFrame with OHLCV data
            num_windows: Number of walk-forward windows
            param_grid: Parameter grid for optimization
            
        Returns:
            Dictionary with walk-forward validation results
        """
        if param_grid is None:
            param_grid = {
                'pivot_window': [3, 5, 7, 10],
                'liquidity_lookback': [3, 5, 7, 10],
                'atr_period': [7, 14, 21, 28],
                'volume_period': [10, 20, 30, 40]
            }
        
        optimizer_logger.info(f"Starting walk-forward validation with {num_windows} windows")
        
        results = {
            'smc_results': [],
            'custom_results': [],
            'window_performance': []
        }
        
        window_size = len(df) // num_windows
        
        for i in range(num_windows):
            start_idx = i * window_size
            end_idx = min((i + 1) * window_size, len(df))
            
            if end_idx - start_idx < 50:  # Skip small windows
                continue
            
            window_df = df.iloc[start_idx:end_idx]
            
            optimizer_logger.info(f"Processing window {i+1}/{num_windows}: {len(window_df)} bars")
            
            # Split window into train/val/test
            train_df, val_df, test_df = self.split_data(window_df)
            
            # Optimize SMC parameters
            smc_opt = self.optimize_smc_parameters(train_df, val_df, param_grid)
            
            # Optimize Custom parameters
            custom_opt = self.optimize_custom_parameters(train_df, val_df, param_grid)
            
            # Test on test data
            from backend.modules.smc_analysis.service import SMCAnalysisService
            from backend.modules.custom_indicators.service import CustomIndicatorService
            from backend.modules.evaluation.signal_generator import AdvancedSignalGenerator
            from backend.modules.evaluation.advanced_backtester import AdvancedBacktester
            
            # Test SMC
            smc_service = SMCAnalysisService(**smc_opt['best_params'])
            signal_generator = AdvancedSignalGenerator()
            test_features = smc_service.extract_all_features(test_df, 'TEST')
            test_signals = signal_generator.generate_smc_signals(test_df, test_features)
            
            if (test_signals != 0).sum() > 0:
                backtester = AdvancedBacktester()
                smc_test_perf = backtester.run_backtest(test_df, test_signals)
            else:
                smc_test_perf = {'total_return': 0, 'win_rate': 0}
            
            # Test Custom
            indicator_service = CustomIndicatorService(**custom_opt['best_params'])
            test_indicators = indicator_service.compute_all_indicators(test_df)
            test_custom_signals = signal_generator.generate_custom_signals(test_df, test_indicators)
            
            if (test_custom_signals != 0).sum() > 0:
                custom_test_perf = backtester.run_backtest(test_df, test_custom_signals)
            else:
                custom_test_perf = {'total_return': 0, 'win_rate': 0}
            
            results['smc_results'].append({
                'window': i + 1,
                'best_params': smc_opt['best_params'],
                'validation_score': smc_opt['best_score'],
                'test_performance': smc_test_perf
            })
            
            results['custom_results'].append({
                'window': i + 1,
                'best_params': custom_opt['best_params'],
                'validation_score': custom_opt['best_score'],
                'test_performance': custom_test_perf
            })
            
            results['window_performance'].append({
                'window': i + 1,
                'smc_return': smc_test_perf.get('total_return', 0),
                'custom_return': custom_test_perf.get('total_return', 0)
            })
        
        # Calculate aggregate performance
        smc_returns = [r['test_performance'].get('total_return', 0) for r in results['smc_results']]
        custom_returns = [r['test_performance'].get('total_return', 0) for r in results['custom_results']]
        
        results['aggregate'] = {
            'smc_avg_return': np.mean(smc_returns) if smc_returns else 0,
            'custom_avg_return': np.mean(custom_returns) if custom_returns else 0,
            'smc_std_return': np.std(smc_returns) if smc_returns else 0,
            'custom_std_return': np.std(custom_returns) if custom_returns else 0
        }
        
        optimizer_logger.info(f"Walk-forward validation completed: SMC avg={results['aggregate']['smc_avg_return']:.3f}, Custom avg={results['aggregate']['custom_avg_return']:.3f}")
        return results
