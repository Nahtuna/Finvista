"""
Tests for SMC Analysis Module
"""

import os
import sys
import pandas as pd
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.smc_analysis.pivot_detector import PivotDetector
from backend.modules.smc_analysis.liquidity_analyzer import LiquidityAnalyzer
from backend.modules.smc_analysis.structure_analyzer import StructureAnalyzer
from backend.modules.smc_analysis.service import SMCAnalysisService
from backend.modules.smc_analysis.pattern_detector import PatternDetector
from backend.modules.smc_analysis.wyckoff_analyzer import WyckoffAnalyzer


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


def test_pivot_detector():
    """Test pivot detection."""
    print("Testing PivotDetector...")
    
    df = create_sample_data(100)
    detector = PivotDetector(window=5)
    
    pivot_highs = detector.detect_pivot_highs(df)
    pivot_lows = detector.detect_pivot_lows(df)
    
    print(f"  Pivot highs detected: {pivot_highs.sum()}")
    print(f"  Pivot lows detected: {pivot_lows.sum()}")
    
    assert pivot_highs.sum() > 0, "Should detect some pivot highs"
    assert pivot_lows.sum() > 0, "Should detect some pivot lows"
    
    print("  ✓ PivotDetector test passed")


def test_liquidity_analyzer():
    """Test liquidity analysis."""
    print("Testing LiquidityAnalyzer...")
    
    df = create_sample_data(100)
    detector = PivotDetector(window=5)
    pivot_highs, pivot_lows = detector.detect_all_pivots(df)
    
    analyzer = LiquidityAnalyzer(lookback=5)
    bsl_sweeps = analyzer.detect_bsl_sweeps(df, pivot_highs)
    ssl_sweeps = analyzer.detect_ssl_sweeps(df, pivot_lows)
    
    print(f"  BSL sweeps detected: {bsl_sweeps.sum()}")
    print(f"  SSL sweeps detected: {ssl_sweeps.sum()}")
    
    print("  ✓ LiquidityAnalyzer test passed")


def test_structure_analyzer():
    """Test structure analysis."""
    print("Testing StructureAnalyzer...")
    
    df = create_sample_data(100)
    detector = PivotDetector(window=5)
    pivot_highs, pivot_lows = detector.detect_all_pivots(df)
    
    analyzer = StructureAnalyzer()
    choch_bullish, choch_bearish, bos_bullish, bos_bearish = analyzer.distinguish_choch_bos(
        df, pivot_highs, pivot_lows
    )
    
    print(f"  Bullish CHoCH: {choch_bullish.sum()}")
    print(f"  Bearish CHoCH: {choch_bearish.sum()}")
    print(f"  Bullish BOS: {bos_bullish.sum()}")
    print(f"  Bearish BOS: {bos_bearish.sum()}")
    
    print("  ✓ StructureAnalyzer test passed")


def test_smc_service():
    """Test SMC service integration."""
    print("Testing SMCAnalysisService...")
    
    df = create_sample_data(100)
    service = SMCAnalysisService()
    
    features = service.extract_all_features(df, 'TEST')
    
    print(f"  Features extracted: {len(features)}")
    print(f"  Feature types: {list(features.keys())}")
    
    assert 'pivot_highs' in features, "Should have pivot_highs"
    assert 'pivot_lows' in features, "Should have pivot_lows"
    assert 'bsl_sweeps' in features, "Should have bsl_sweeps"
    assert 'ssl_sweeps' in features, "Should have ssl_sweeps"
    assert 'fvg' in features, "Should have fvg"
    assert 'order_blocks' in features, "Should have order_blocks"
    assert 'wyckoff_events' in features, "Should have wyckoff_events"
    
    print("  ✓ SMCAnalysisService test passed")


def test_pattern_detector():
    """Test pattern detection (FVG and Order Blocks)."""
    print("Testing PatternDetector...")
    
    df = create_sample_data(100)
    detector = PivotDetector(window=5)
    pivot_highs, pivot_lows = detector.detect_all_pivots(df)
    
    pattern_detector = PatternDetector()
    fvg_list = pattern_detector.detect_fvg(df)
    ob_list = pattern_detector.detect_order_blocks(df, pivot_highs, pivot_lows)
    
    print(f"  FVG events detected: {len(fvg_list)}")
    print(f"  Order Blocks detected: {len(ob_list)}")
    
    print("  ✓ PatternDetector test passed")


def test_wyckoff_analyzer():
    """Test Wyckoff event detection."""
    print("Testing WyckoffAnalyzer...")
    
    df = create_sample_data(100)
    detector = PivotDetector(window=5)
    pivot_highs, pivot_lows = detector.detect_all_pivots(df)
    
    wyckoff = WyckoffAnalyzer()
    events = wyckoff.detect_all_wyckoff_events(df, pivot_highs, pivot_lows)
    
    print(f"  Selling Climax: {events['selling_climax'].sum()}")
    print(f"  Spring: {events['spring'].sum()}")
    print(f"  UTAD: {events['utad'].sum()}")
    print(f"  SOW: {events['sow'].sum()}")
    
    print("  ✓ WyckoffAnalyzer test passed")


def run_all_tests():
    """Run all SMC module tests."""
    print("=" * 50)
    print("Running SMC Analysis Module Tests")
    print("=" * 50)
    
    try:
        test_pivot_detector()
        test_liquidity_analyzer()
        test_structure_analyzer()
        test_smc_service()
        test_pattern_detector()
        test_wyckoff_analyzer()
        
        print("=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
