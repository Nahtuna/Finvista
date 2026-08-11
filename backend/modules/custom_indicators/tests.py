"""
Tests for Custom Indicators Module
"""

import os
import sys
import pandas as pd
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.custom_indicators.mk_indicator import MKIndicator
from backend.modules.custom_indicators.sl_indicator import SLIndicator
from backend.modules.custom_indicators.sc_indicator import SCIndicator
from backend.modules.custom_indicators.service import CustomIndicatorService


def create_sample_data(n=100):
    """Create sample OHLCV data for testing."""
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


def test_mk_indicator():
    """Test MK indicator."""
    print("Testing MKIndicator...")
    
    df = create_sample_data(100)
    indicator = MKIndicator()
    
    mk_values = indicator.compute(df)
    
    print(f"  MK indicator range: [{mk_values.min():.3f}, {mk_values.max():.3f}]")
    print(f"  MK indicator mean: {mk_values.mean():.3f}")
    
    assert mk_values.min() >= -1, "MK values should be >= -1"
    assert mk_values.max() <= 1, "MK values should be <= 1"
    
    print("  ✓ MKIndicator test passed")


def test_sl_indicator():
    """Test SL indicator."""
    print("Testing SLIndicator...")
    
    df = create_sample_data(100)
    indicator = SLIndicator()
    
    sl_system = indicator.compute(df)
    
    print(f"  SL bands computed: upper and lower")
    print(f"  Compression detected: {sl_system['compression'].sum()} bars")
    print(f"  Expansion detected: {sl_system['expansion'].sum()} bars")
    print(f"  Reversals detected: {(sl_system['reversals'] != 0).sum()} bars")
    
    assert 'upper_band' in sl_system, "Should have upper_band"
    assert 'lower_band' in sl_system, "Should have lower_band"
    
    print("  ✓ SLIndicator test passed")


def test_sc_indicator():
    """Test SC indicator."""
    print("Testing SCIndicator...")
    
    df = create_sample_data(100)
    indicator = SCIndicator()
    
    sc_system = indicator.compute(df)
    
    print(f"  Extreme selling detected: {sc_system['extreme_selling'].sum()} bars")
    print(f"  Support breaches: {sc_system['support_breach'].sum()} bars")
    print(f"  SC signals: {(sc_system['signals'] != 0).sum()} bars")
    print(f"  SC intensity mean: {sc_system['intensity'].mean():.3f}")
    
    assert 'extreme_selling' in sc_system, "Should have extreme_selling"
    assert 'signals' in sc_system, "Should have signals"
    
    print("  ✓ SCIndicator test passed")


def test_custom_indicator_service():
    """Test unified custom indicator service."""
    print("Testing CustomIndicatorService...")
    
    df = create_sample_data(100)
    service = CustomIndicatorService()
    
    indicators = service.compute_all_indicators(df)
    
    print(f"  Indicator types computed: {len(indicators)}")
    print(f"  Indicator types: {list(indicators.keys())}")
    
    assert 'mk_indicator' in indicators, "Should have mk_indicator"
    assert 'sl_upper_band' in indicators, "Should have sl_upper_band"
    assert 'sc_extreme_selling' in indicators, "Should have sc_extreme_selling"
    
    print("  ✓ CustomIndicatorService test passed")


def test_combined_signals():
    """Test combined signal generation."""
    print("Testing combined signal generation...")
    
    df = create_sample_data(100)
    service = CustomIndicatorService()
    
    combined_signals = service.generate_combined_signals(df)
    
    buy_count = (combined_signals == 1).sum()
    sell_count = (combined_signals == -1).sum()
    
    print(f"  Combined signals: {buy_count} buy, {sell_count} sell")
    
    print("  ✓ Combined signals test passed")


def test_divergence_analysis():
    """Test divergence analysis."""
    print("Testing divergence analysis...")
    
    df = create_sample_data(100)
    service = CustomIndicatorService()
    
    mk_values = service.mk_indicator.compute(df)
    divergence = service.analyze_divergence(df, mk_values)
    
    print(f"  Bullish divergence: {sum(divergence['bullish_divergence'].values())}")
    print(f"  Bearish divergence: {sum(divergence['bearish_divergence'].values())}")
    
    print("  ✓ Divergence analysis test passed")


def run_all_tests():
    """Run all custom indicator tests."""
    print("=" * 50)
    print("Running Custom Indicators Module Tests")
    print("=" * 50)
    
    try:
        test_mk_indicator()
        test_sl_indicator()
        test_sc_indicator()
        test_custom_indicator_service()
        test_combined_signals()
        test_divergence_analysis()
        
        print("=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
