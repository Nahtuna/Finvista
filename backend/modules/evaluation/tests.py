"""
Tests for Evaluation Module
"""

import os
import sys
import pandas as pd
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.evaluation.metrics import SignalQualityMetrics
from backend.modules.evaluation.backtester import Backtester
from backend.modules.evaluation.advanced_backtester import AdvancedBacktester
from backend.modules.evaluation.visualizer import IndicatorVisualizer
from backend.modules.evaluation.benchmark import BenchmarkComparator


def create_test_data(n=100):
    """Create test data for evaluation."""
    np.random.seed(42)
    
    dates = pd.date_range(start='2024-01-01', periods=n, freq='D')
    
    # Generate synthetic price data
    close = np.cumsum(np.random.randn(n) * 0.02) + 100
    high = close + np.random.rand(n) * 2
    low = close - np.random.rand(n) * 2
    open_price = close + np.random.randn(n) * 0.5
    volume = np.random.randint(1000000, 5000000, n)
    
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)
    
    return df


def test_signal_quality_metrics():
    """Test signal quality metrics calculation."""
    print("Testing SignalQualityMetrics...")
    
    df = create_test_data(100)
    metrics = SignalQualityMetrics()
    
    # Create test signals
    signals = pd.Series(0, index=df.index)
    signals.iloc[10] = 1
    signals.iloc[30] = -1
    signals.iloc[50] = 1
    signals.iloc[70] = -1
    
    # Calculate returns
    returns = df['close'].pct_change().fillna(0)
    
    # Test comprehensive evaluation
    evaluation = metrics.comprehensive_evaluation(signals, df['close'], returns)
    
    print(f"  SNR: {evaluation['signal_to_noise_ratio']:.3f}")
    print(f"  Precision: {evaluation['precision']:.3f}")
    print(f"  Sharpe Ratio: {evaluation['sharpe_ratio']:.3f}")
    print(f"  Win Rate: {evaluation['win_rate']:.3f}")
    
    assert 'signal_to_noise_ratio' in evaluation
    assert 'sharpe_ratio' in evaluation
    assert 'win_rate' in evaluation
    
    print("  ✓ SignalQualityMetrics test passed")


def test_backtester():
    """Test backtesting framework."""
    print("Testing Backtester...")
    
    df = create_test_data(100)
    backtester = Backtester()
    
    # Create test signals
    signals = pd.Series(0, index=df.index)
    signals.iloc[10] = 1
    signals.iloc[30] = -1
    signals.iloc[50] = 1
    signals.iloc[70] = -1
    
    # Run backtest
    results = backtester.run_backtest(df, signals)
    
    print(f"  Final Capital: {results['final_capital']:.2f}")
    print(f"  Total Return: {results['total_return_pct']:.2f}%")
    print(f"  Number of Trades: {results['num_trades']}")
    print(f"  Win Rate: {results['win_rate']:.3f}")
    
    assert 'final_capital' in results
    assert 'total_return_pct' in results
    assert 'num_trades' in results
    
    # Test risk metrics
    risk_metrics = backtester.calculate_risk_metrics(results)
    print(f"  Max Drawdown: {risk_metrics['max_drawdown']:.3f}")
    print(f"  Sortino Ratio: {risk_metrics['sortino_ratio']:.3f}")
    
    assert 'max_drawdown' in risk_metrics
    assert 'sortino_ratio' in risk_metrics
    
    print("  ✓ Backtester test passed")


def test_visualizer():
    """Test visualization data preparation."""
    print("Testing IndicatorVisualizer...")
    
    df = create_test_data(100)
    visualizer = IndicatorVisualizer()
    
    # Test indicator plot data
    indicator_values = pd.Series(np.random.randn(100), index=df.index)
    plot_data = visualizer.prepare_indicator_plot_data(df, "Test Indicator", indicator_values)
    
    print(f"  Plot data prepared: {len(plot_data['dates'])} data points")
    
    assert 'dates' in plot_data
    assert 'price' in plot_data
    assert 'indicator_values' in plot_data
    
    # Test signal plot data
    signals = pd.Series(0, index=df.index)
    signals.iloc[10] = 1
    signals.iloc[30] = -1
    
    signal_data = visualizer.prepare_signal_plot_data(df, signals)
    print(f"  Signal data: {len(signal_data['buy_dates'])} buys, {len(signal_data['sell_dates'])} sells")
    
    assert 'buy_dates' in signal_data
    assert 'sell_dates' in signal_data
    
    # Test text report generation
    evaluation_results = {
        'signal_to_noise_ratio': 5.2,
        'precision': 0.75,
        'recall': 0.80,
        'f1_score': 0.77,
        'total_return': 0.15,
        'sharpe_ratio': 1.2,
        'max_drawdown': -0.10,
        'win_rate': 0.60,
        'num_signals': 20,
        'profit_factor': 1.5,
        'avg_win': 0.02,
        'avg_loss': -0.015
    }
    
    report = visualizer.generate_text_report(evaluation_results)
    print(f"  Report generated: {len(report)} characters")
    
    assert "INDICATOR EVALUATION REPORT" in report
    
    print("  ✓ IndicatorVisualizer test passed")


def test_benchmark_comparator():
    """Test benchmark comparison."""
    print("Testing BenchmarkComparator...")
    
    df = create_test_data(100)
    comparator = BenchmarkComparator()
    
    # Test standard indicators
    sma_20 = comparator.calculate_sma(df['close'], 20)
    rsi = comparator.calculate_rsi(df['close'])
    macd = comparator.calculate_macd(df['close'])
    bb = comparator.calculate_bollinger_bands(df['close'])
    
    print(f"  SMA calculated: {sma_20.iloc[-1]:.2f}")
    print(f"  RSI calculated: {rsi.iloc[-1]:.2f}")
    print(f"  MACD calculated: {macd['macd'].iloc[-1]:.4f}")
    print(f"  Bollinger Bands calculated")
    
    # Test signal generation
    sma_signals = comparator.generate_sma_signals(df['close'])
    rsi_signals = comparator.generate_rsi_signals(rsi)
    macd_signals = comparator.generate_macd_signals(macd)
    
    print(f"  SMA signals: {(sma_signals != 0).sum()}")
    print(f"  RSI signals: {(rsi_signals != 0).sum()}")
    print(f"  MACD signals: {(macd_signals != 0).sum()}")
    
    # Test comparison
    custom_signals = pd.Series(0, index=df.index)
    custom_signals.iloc[10] = 1
    custom_signals.iloc[30] = -1
    
    comparison = comparator.compare_indicators(df, custom_signals, "Test Custom")
    print(f"  Comparison completed: {len(comparison)} indicators")
    
    assert 'custom_name' in comparison
    assert 'benchmarks' in comparison
    
    # Test Buy & Hold
    buy_hold_perf = comparator.calculate_buy_hold_performance(df)
    print(f"  Buy & Hold return: {buy_hold_perf['total_return_pct']:.2f}%")
    
    assert 'total_return' in buy_hold_perf
    assert 'final_capital' in buy_hold_perf
    
    print("  ✓ BenchmarkComparator test passed")


def run_all_tests():
    """Run all evaluation module tests."""
    print("=" * 50)
    print("Running Evaluation Module Tests")
    print("=" * 50)
    
    try:
        test_signal_quality_metrics()
        test_backtester()
        test_visualizer()
        test_benchmark_comparator()
        
        print("=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
