#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: INDICATOR EVALUATION SCRIPT
========================================
Comprehensive evaluation of SMC and Custom Indicators performance.
Includes metrics calculation, backtesting, and benchmark comparison.

Usage:
  python scripts/evaluate_indicators.py --symbol VNINDEX --days 365
  python scripts/evaluate_indicators.py --all --days 365

Author: Finvista Evaluation Module
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.evaluation.metrics import SignalQualityMetrics
from backend.modules.evaluation.backtester import Backtester
from backend.modules.evaluation.advanced_backtester import AdvancedBacktester
from backend.modules.evaluation.visualizer import IndicatorVisualizer
from backend.modules.evaluation.benchmark import BenchmarkComparator
from backend.modules.evaluation.signal_generator import AdvancedSignalGenerator
from backend.modules.evaluation.regime_filter import RegimeSignalFilter
from backend.modules.smc_analysis.service import SMCAnalysisService
from backend.modules.custom_indicators.service import CustomIndicatorService
from backend.core.utils import get_logger

eval_logger = get_logger(__name__)


def load_test_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Load test data for evaluation from database.
    
    Args:
        symbol: Symbol name
        days: Number of days of historical data
        
    Returns:
        DataFrame with OHLCV data
    """
    # Try to load from database
    try:
        from backend.core.database import engine
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = f"""
            SELECT date, open, high, low, close, volume 
            FROM stock_history 
            WHERE symbol = '{symbol}' 
            AND date >= '{start_date.strftime('%Y-%m-%d')}' 
            AND date <= '{end_date.strftime('%Y-%m-%d')}'
            ORDER BY date
        """
        
        eval_logger.info(f"Loading data from database for {symbol}")
        df = pd.read_sql(query, engine)
        
        if df.empty:
            eval_logger.warning(f"No data found for {symbol} in database")
            return generate_synthetic_data(days)
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        return df
        
    except Exception as e:
        eval_logger.error(f"Failed to load data from database: {e}")
        # Generate synthetic data for testing
        eval_logger.warning(f"Generating synthetic data for {symbol}")
        return generate_synthetic_data(days)


def generate_synthetic_data(days: int) -> pd.DataFrame:
    """Generate synthetic data for testing."""
    np.random.seed(42)
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')
    
    # Generate synthetic price data
    close = np.cumsum(np.random.randn(days) * 0.02) + 100
    high = close + np.random.rand(days) * 2
    low = close - np.random.rand(days) * 2
    open_price = close + np.random.randn(days) * 0.5
    volume = np.random.randint(1000000, 5000000, days)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)
    
    return df


def evaluate_smc_indicators(df: pd.DataFrame, symbol: str) -> dict:
    """
    Evaluate SMC indicators with optimized parameters.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol name
        
    Returns:
        Dictionary with SMC evaluation results
    """
    eval_logger.info(f"Evaluating SMC indicators for {symbol}")
    
    # Extract SMC features with optimized parameters
    smc_service = SMCAnalysisService(pivot_window=5, liquidity_lookback=5)
    features = smc_service.extract_all_features(df, symbol)
    
    # Generate improved SMC signals
    signal_generator = AdvancedSignalGenerator()
    signals = signal_generator.generate_smc_signals(df, features)
    
    return {
        'name': 'SMC Indicators',
        'signals': signals,
        'features': features
    }


def evaluate_custom_indicators(df: pd.DataFrame, symbol: str) -> dict:
    """
    Evaluate Custom Indicators (MK-SL-SC) with optimized parameters.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol name
        
    Returns:
        Dictionary with custom indicator evaluation results
    """
    eval_logger.info(f"Evaluating custom indicators for {symbol}")
    
    # Compute custom indicators with optimized parameters
    indicator_service = CustomIndicatorService(
        mk_atr_period=21,
        mk_volume_period=20
    )
    indicators = indicator_service.compute_all_indicators(df)
    
    # Generate improved custom signals
    signal_generator = AdvancedSignalGenerator()
    combined_signals = signal_generator.generate_custom_signals(df, indicators)
    
    return {
        'name': 'Custom Indicators (MK-SL-SC)',
        'signals': combined_signals,
        'indicators': indicators
    }


def run_comprehensive_evaluation(df: pd.DataFrame, symbol: str) -> dict:
    """
    Run comprehensive evaluation of all indicators.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol name
        
    Returns:
        Dictionary with comprehensive evaluation results
    """
    eval_logger.info(f"Running comprehensive evaluation for {symbol}")
    
    # Evaluate indicators
    smc_results = evaluate_smc_indicators(df, symbol)
    custom_results = evaluate_custom_indicators(df, symbol)
    
    # Initialize evaluation components
    metrics_calculator = SignalQualityMetrics()
    backtester = AdvancedBacktester()
    visualizer = IndicatorVisualizer()
    benchmark_comparator = BenchmarkComparator()
    regime_filter = RegimeSignalFilter()
    
    # Detect market regime
    regimes = regime_filter.detect_regime(df)
    
    # Calculate returns for evaluation
    price_changes = df['close'].pct_change().fillna(0)
    
    results = {}
    
    # Evaluate SMC indicators
    eval_logger.info("Evaluating SMC indicators...")
    smc_evaluation = metrics_calculator.comprehensive_evaluation(
        smc_results['signals'],
        df['close'],
        price_changes
    )
    
    # Apply regime filtering
    smc_filtered_signals = regime_filter.filter_signals(smc_results['signals'], regimes)
    
    smc_backtest = backtester.run_backtest(df, smc_filtered_signals)
    smc_risk = backtester.calculate_advanced_risk_metrics(smc_backtest)
    
    results['smc'] = {
        'evaluation': smc_evaluation,
        'backtest': smc_backtest,
        'risk': smc_risk
    }
    
    # Evaluate Custom indicators
    eval_logger.info("Evaluating custom indicators...")
    custom_evaluation = metrics_calculator.comprehensive_evaluation(
        custom_results['signals'],
        df['close'],
        price_changes
    )
    
    # Apply regime filtering
    custom_filtered_signals = regime_filter.filter_signals(custom_results['signals'], regimes)
    
    custom_backtest = backtester.run_backtest(df, custom_filtered_signals)
    custom_risk = backtester.calculate_advanced_risk_metrics(custom_backtest)
    
    results['custom'] = {
        'evaluation': custom_evaluation,
        'backtest': custom_backtest,
        'risk': custom_risk
    }
    
    # Benchmark comparison
    eval_logger.info("Running benchmark comparison...")
    
    # Buy & Hold benchmark
    buy_hold_perf = benchmark_comparator.calculate_buy_hold_performance(df)
    results['buy_hold'] = buy_hold_perf
    
    # Standard indicators benchmark
    benchmark_results = benchmark_comparator.compare_indicators(
        df,
        custom_results['signals'],
        "Custom MK-SL-SC"
    )
    
    results['benchmark'] = benchmark_results
    
    # Generate reports
    eval_logger.info("Generating evaluation reports...")
    
    smc_report = visualizer.generate_text_report(smc_evaluation, smc_backtest)
    custom_report = visualizer.generate_text_report(custom_evaluation, custom_backtest)
    
    results['reports'] = {
        'smc': smc_report,
        'custom': custom_report
    }
    
    eval_logger.info("Comprehensive evaluation completed")
    return results


def print_evaluation_summary(results: dict):
    """Print evaluation summary to console."""
    print("\n" + "=" * 70)
    print("INDICATOR EVALUATION SUMMARY")
    print("=" * 70)
    
    # SMC Results
    print("\nSMC INDICATORS (Optimized)")
    print("-" * 50)
    smc_eval = results['smc']['evaluation']
    smc_bt = results['smc']['backtest']
    print(f"Total Return: {smc_eval['total_return']:.3f}")
    print(f"Sharpe Ratio: {smc_eval['sharpe_ratio']:.3f}")
    print(f"Max Drawdown: {smc_eval['max_drawdown']:.3f}")
    print(f"Win Rate: {smc_eval['win_rate']:.3f}")
    print(f"Number of Signals: {smc_eval['num_signals']}")
    
    # Custom Indicators Results
    print("\nCUSTOM INDICATORS (MK-SL-SC) (Optimized)")
    print("-" * 50)
    custom_eval = results['custom']['evaluation']
    custom_bt = results['custom']['backtest']
    print(f"Total Return: {custom_eval['total_return']:.3f}")
    print(f"Sharpe Ratio: {custom_eval['sharpe_ratio']:.3f}")
    print(f"Max Drawdown: {custom_eval['max_drawdown']:.3f}")
    print(f"Win Rate: {custom_eval['win_rate']:.3f}")
    print(f"Number of Signals: {custom_eval['num_signals']}")
    
    # Buy & Hold Benchmark
    print("\nBUY & HOLD BENCHMARK")
    print("-" * 50)
    buy_hold = results.get('buy_hold', {})
    print(f"Total Return: {buy_hold.get('total_return', 0):.3f}")
    print(f"Total Return %: {buy_hold.get('total_return_pct', 0):.2f}%")
    print(f"Final Capital: {buy_hold.get('final_capital', 0):.2f}")
    
    # Comparison
    print("\nCOMPARISON")
    print("-" * 50)
    smc_return = smc_eval['total_return']
    custom_return = custom_eval['total_return']
    buy_hold_return = buy_hold.get('total_return', 0)
    
    smc_vs_bh = ((smc_return - buy_hold_return) / abs(buy_hold_return) * 100) if buy_hold_return != 0 else 0
    custom_vs_bh = ((custom_return - buy_hold_return) / abs(buy_hold_return) * 100) if buy_hold_return != 0 else 0
    
    print(f"SMC vs Buy & Hold: {smc_vs_bh:.2f}%")
    print(f"Custom vs Buy & Hold: {custom_vs_bh:.2f}%")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Evaluate SMC and Custom Indicators performance")
    parser.add_argument('--symbol', '-s', type=str, help="Single symbol to evaluate")
    parser.add_argument('--all', '-a', action='store_true', help="Evaluate all available symbols")
    parser.add_argument('--days', '-d', type=int, default=365, help="Number of days of historical data (default: 365)")
    args = parser.parse_args()
    
    if args.symbol:
        # Evaluate single symbol
        eval_logger.info(f"Evaluating indicator for {args.symbol}")
        df = load_test_data(args.symbol, args.days)
        results = run_comprehensive_evaluation(df, args.symbol)
        print_evaluation_summary(results)
        
        # Save detailed reports
        with open(f"evaluation_report_{args.symbol}.txt", "w", encoding='utf-8') as f:
            f.write(results['reports']['smc'])
            f.write("\n\n")
            f.write(results['reports']['custom'])
        
        print(f"\n📄 Detailed reports saved to evaluation_report_{args.symbol}.txt")
        
    elif args.all:
        # Evaluate all symbols
        processed_dir = os.path.join(PROJECT_ROOT, "data", "processed")
        
        if not os.path.exists(processed_dir):
            eval_logger.warning(f"Processed data directory not found: {processed_dir}")
            return
        
        csv_files = [f for f in os.listdir(processed_dir) if f.endswith('.csv')]
        symbols = [f.replace('.csv', '') for f in csv_files]
        
        eval_logger.info(f"Evaluating {len(symbols)} symbols")
        
        for symbol in symbols:
            df = load_test_data(symbol, args.days)
            results = run_comprehensive_evaluation(df, symbol)
            print_evaluation_summary(results)
        
    else:
        eval_logger.error("Please specify either --symbol or --all")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
