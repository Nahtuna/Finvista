#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: SMC ANALYSIS TEST SCRIPT
=======================================
Test SMC analysis module for multiple stocks and VNINDEX.
Validates all SMC features and checks for errors.

Usage:
  python scripts/test_smc_analysis.py --symbols VNINDEX,VIC,VCB,VHM --days 365
  python scripts/test_smc_analysis.py --all --days 365

Author: Finvista SMC Module
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import traceback

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.smc_analysis.service import SMCAnalysisService
from backend.modules.smc_analysis.pivot_detector import PivotDetector
from backend.modules.smc_analysis.liquidity_analyzer import LiquidityAnalyzer
from backend.modules.smc_analysis.structure_analyzer import StructureAnalyzer
from backend.modules.smc_analysis.pattern_detector import PatternDetector
from backend.modules.smc_analysis.wyckoff_analyzer import WyckoffAnalyzer
from backend.core.utils import get_logger

test_logger = get_logger(__name__)


def load_stock_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Load historical stock data from existing data sources.
    
    Args:
        symbol: Stock symbol
        days: Number of days of historical data
        
    Returns:
        DataFrame with OHLCV data
    """
    # Try to load from existing CSV file first
    csv_path = os.path.join(PROJECT_ROOT, "data", "processed", f"{symbol}.csv")
    
    if os.path.exists(csv_path):
        test_logger.info(f"Loading data from existing CSV: {csv_path}")
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        
        # Filter to requested date range
        cutoff_date = datetime.now() - timedelta(days=days)
        df = df[df.index >= cutoff_date]
        
        return df
    
    # If CSV doesn't exist, try to fetch from database
    try:
        from backend.core.database import SessionLocal, StockHistoricalPrice
        
        session = SessionLocal()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        records = session.query(StockHistoricalPrice).filter(
            StockHistoricalPrice.symbol == symbol,
            StockHistoricalPrice.date >= cutoff_date
        ).all()
        
        if records:
            data = []
            for record in records:
                data.append({
                    'open': record.open,
                    'high': record.high,
                    'low': record.low,
                    'close': record.close,
                    'volume': record.volume
                })
            
            df = pd.DataFrame(data)
            df.index = pd.to_datetime([r.date for r in records])
            
            test_logger.info(f"Loaded {len(df)} records from database for {symbol}")
            session.close()
            return df
        
        session.close()
        
    except Exception as e:
        test_logger.error(f"Error loading from database: {e}")
    
    test_logger.warning(f"No data found for {symbol}")
    return pd.DataFrame()


def test_pivot_detector(df: pd.DataFrame, symbol: str) -> dict:
    """Test pivot detector."""
    test_logger.info(f"Testing PivotDetector for {symbol}")
    results = {}
    
    try:
        detector = PivotDetector(window=5)
        pivot_highs, pivot_lows = detector.detect_all_pivots(df)
        
        results['pivot_highs_count'] = int(pivot_highs.sum())
        results['pivot_lows_count'] = int(pivot_lows.sum())
        results['pivot_highs_sample'] = pivot_highs[pivot_highs].head(5).index.tolist()
        results['pivot_lows_sample'] = pivot_lows[pivot_lows].head(5).index.tolist()
        results['status'] = 'success'
        
    except Exception as e:
        test_logger.error(f"PivotDetector test failed for {symbol}: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()
    
    return results


def test_liquidity_analyzer(df: pd.DataFrame, symbol: str) -> dict:
    """Test liquidity analyzer."""
    test_logger.info(f"Testing LiquidityAnalyzer for {symbol}")
    results = {}
    
    try:
        detector = PivotDetector(window=5)
        pivot_highs, pivot_lows = detector.detect_all_pivots(df)
        
        analyzer = LiquidityAnalyzer(lookback=5)
        bsl_sweeps, ssl_sweeps = analyzer.detect_all_sweeps(df, pivot_highs, pivot_lows)
        
        results['bsl_sweeps_count'] = int(bsl_sweeps.sum())
        results['ssl_sweeps_count'] = int(ssl_sweeps.sum())
        results['bsl_sweeps_sample'] = bsl_sweeps[bsl_sweeps].head(5).index.tolist()
        results['ssl_sweeps_sample'] = ssl_sweeps[ssl_sweeps].head(5).index.tolist()
        results['status'] = 'success'
        
    except Exception as e:
        test_logger.error(f"LiquidityAnalyzer test failed for {symbol}: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()
    
    return results


def test_structure_analyzer(df: pd.DataFrame, symbol: str) -> dict:
    """Test structure analyzer."""
    test_logger.info(f"Testing StructureAnalyzer for {symbol}")
    results = {}
    
    try:
        detector = PivotDetector(window=5)
        pivot_highs, pivot_lows = detector.detect_all_pivots(df)
        
        analyzer = StructureAnalyzer()
        choch_bullish, choch_bearish, bos_bullish, bos_bearish = analyzer.distinguish_choch_bos(
            df, pivot_highs, pivot_lows
        )
        
        results['choch_bullish_count'] = int(choch_bullish.sum())
        results['choch_bearish_count'] = int(choch_bearish.sum())
        results['bos_bullish_count'] = int(bos_bullish.sum())
        results['bos_bearish_count'] = int(bos_bearish.sum())
        results['choch_bullish_sample'] = choch_bullish[choch_bullish].head(5).index.tolist()
        results['choch_bearish_sample'] = choch_bearish[choch_bearish].head(5).index.tolist()
        results['status'] = 'success'
        
    except Exception as e:
        test_logger.error(f"StructureAnalyzer test failed for {symbol}: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()
    
    return results


def test_pattern_detector(df: pd.DataFrame, symbol: str) -> dict:
    """Test pattern detector."""
    test_logger.info(f"Testing PatternDetector for {symbol}")
    results = {}
    
    try:
        detector = PivotDetector(window=5)
        pivot_highs, pivot_lows = detector.detect_all_pivots(df)
        
        pattern_detector = PatternDetector()
        
        # Test FVG detection
        fvg_list = pattern_detector.detect_fvg(df)
        fvg_list = pattern_detector.assess_fvg_quality(fvg_list, df)
        fvg_list = pattern_detector.check_fvg_fill(fvg_list, df)
        
        # Test Order Block detection
        ob_list = pattern_detector.detect_order_blocks(df, pivot_highs, pivot_lows)
        ob_list = pattern_detector.detect_ob_retest(ob_list, df)
        
        results['fvg_count'] = len(fvg_list)
        results['fvg_high_quality'] = sum(1 for fvg in fvg_list if fvg.get('quality') == 'high')
        results['fvg_filled'] = sum(1 for fvg in fvg_list if fvg.get('fill_status') == 'filled')
        results['ob_count'] = len(ob_list)
        results['ob_retested'] = sum(1 for ob in ob_list if ob.get('retest_status') == 'retested')
        results['fvg_sample'] = fvg_list[:3] if fvg_list else []
        results['ob_sample'] = ob_list[:3] if ob_list else []
        results['status'] = 'success'
        
    except Exception as e:
        test_logger.error(f"PatternDetector test failed for {symbol}: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()
    
    return results


def test_wyckoff_analyzer(df: pd.DataFrame, symbol: str) -> dict:
    """Test Wyckoff analyzer."""
    test_logger.info(f"Testing WyckoffAnalyzer for {symbol}")
    results = {}
    
    try:
        detector = PivotDetector(window=5)
        pivot_highs, pivot_lows = detector.detect_all_pivots(df)
        
        wyckoff = WyckoffAnalyzer()
        wyckoff_events = wyckoff.detect_all_wyckoff_events(df, pivot_highs, pivot_lows)
        
        results['selling_climax_count'] = int(wyckoff_events['selling_climax'].sum())
        results['spring_count'] = int(wyckoff_events['spring'].sum())
        results['utad_count'] = int(wyckoff_events['utad'].sum())
        results['sow_count'] = int(wyckoff_events['sow'].sum())
        results['selling_climax_sample'] = wyckoff_events['selling_climax'][wyckoff_events['selling_climax']].head(5).index.tolist()
        results['spring_sample'] = wyckoff_events['spring'][wyckoff_events['spring']].head(5).index.tolist()
        results['status'] = 'success'
        
    except Exception as e:
        test_logger.error(f"WyckoffAnalyzer test failed for {symbol}: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()
    
    return results


def test_full_service(df: pd.DataFrame, symbol: str) -> dict:
    """Test full SMC service integration."""
    test_logger.info(f"Testing full SMCAnalysisService for {symbol}")
    results = {}
    
    try:
        service = SMCAnalysisService()
        features = service.extract_all_features(df, symbol)
        
        results['feature_types'] = list(features.keys())
        results['pivot_highs_count'] = len(json.loads(features['pivot_highs']))
        results['pivot_lows_count'] = len(json.loads(features['pivot_lows']))
        results['bsl_sweeps_count'] = len(json.loads(features['bsl_sweeps']))
        results['ssl_sweeps_count'] = len(json.loads(features['ssl_sweeps']))
        results['fvg_count'] = len(json.loads(features['fvg']))
        results['ob_count'] = len(json.loads(features['order_blocks']))
        results['status'] = 'success'
        
    except Exception as e:
        test_logger.error(f"Full service test failed for {symbol}: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()
    
    return results


def test_symbol(symbol: str, days: int = 365) -> dict:
    """
    Run all tests for a single symbol.
    
    Args:
        symbol: Stock symbol
        days: Number of days of historical data
        
    Returns:
        Dictionary with all test results
    """
    test_logger.info(f"{'='*60}")
    test_logger.info(f"Testing SMC Analysis for {symbol}")
    test_logger.info(f"{'='*60}")
    
    # Load data
    df = load_stock_data(symbol, days)
    
    if df.empty:
        test_logger.warning(f"No data available for {symbol}, skipping tests")
        return {
            'symbol': symbol,
            'status': 'skipped',
            'reason': 'No data available'
        }
    
    # Validate data
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_columns):
        test_logger.error(f"Missing required columns for {symbol}")
        return {
            'symbol': symbol,
            'status': 'failed',
            'reason': f'Missing columns: {set(required_columns) - set(df.columns)}'
        }
    
    test_logger.info(f"Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Run all tests
    results = {
        'symbol': symbol,
        'data_points': len(df),
        'date_range': f"{df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}",
        'pivot_detector': test_pivot_detector(df, symbol),
        'liquidity_analyzer': test_liquidity_analyzer(df, symbol),
        'structure_analyzer': test_structure_analyzer(df, symbol),
        'pattern_detector': test_pattern_detector(df, symbol),
        'wyckoff_analyzer': test_wyckoff_analyzer(df, symbol),
        'full_service': test_full_service(df, symbol)
    }
    
    # Overall status
    all_passed = all(
        test.get('status') == 'success' 
        for test in results.values() 
        if isinstance(test, dict) and 'status' in test
    )
    results['overall_status'] = 'passed' if all_passed else 'failed'
    
    return results


def print_results(results: dict):
    """Print test results in a readable format."""
    print(f"\n{'='*80}")
    print(f"SMC ANALYSIS TEST RESULTS FOR {results['symbol']}")
    print(f"{'='*80}")
    print(f"Data Points: {results.get('data_points', 'N/A')}")
    print(f"Date Range: {results.get('date_range', 'N/A')}")
    print(f"Overall Status: {results.get('overall_status', 'N/A').upper()}")
    print(f"{'-'*80}")
    
    # Pivot Detector
    pivot = results.get('pivot_detector', {})
    print(f"\n📍 Pivot Detector: {pivot.get('status', 'N/A').upper()}")
    if pivot.get('status') == 'success':
        print(f"   - Pivot Highs: {pivot.get('pivot_highs_count', 0)}")
        print(f"   - Pivot Lows: {pivot.get('pivot_lows_count', 0)}")
    else:
        print(f"   - Error: {pivot.get('error', 'Unknown')}")
    
    # Liquidity Analyzer
    liq = results.get('liquidity_analyzer', {})
    print(f"\n💧 Liquidity Analyzer: {liq.get('status', 'N/A').upper()}")
    if liq.get('status') == 'success':
        print(f"   - BSL Sweeps: {liq.get('bsl_sweeps_count', 0)}")
        print(f"   - SSL Sweeps: {liq.get('ssl_sweeps_count', 0)}")
    else:
        print(f"   - Error: {liq.get('error', 'Unknown')}")
    
    # Structure Analyzer
    struct = results.get('structure_analyzer', {})
    print(f"\n📊 Structure Analyzer: {struct.get('status', 'N/A').upper()}")
    if struct.get('status') == 'success':
        print(f"   - CHoCH Bullish: {struct.get('choch_bullish_count', 0)}")
        print(f"   - CHoCH Bearish: {struct.get('choch_bearish_count', 0)}")
        print(f"   - BOS Bullish: {struct.get('bos_bullish_count', 0)}")
        print(f"   - BOS Bearish: {struct.get('bos_bearish_count', 0)}")
    else:
        print(f"   - Error: {struct.get('error', 'Unknown')}")
    
    # Pattern Detector
    pattern = results.get('pattern_detector', {})
    print(f"\n🎯 Pattern Detector: {pattern.get('status', 'N/A').upper()}")
    if pattern.get('status') == 'success':
        print(f"   - FVG Total: {pattern.get('fvg_count', 0)}")
        print(f"   - FVG High Quality: {pattern.get('fvg_high_quality', 0)}")
        print(f"   - FVG Filled: {pattern.get('fvg_filled', 0)}")
        print(f"   - Order Blocks: {pattern.get('ob_count', 0)}")
        print(f"   - OB Retested: {pattern.get('ob_retested', 0)}")
    else:
        print(f"   - Error: {pattern.get('error', 'Unknown')}")
    
    # Wyckoff Analyzer
    wyckoff = results.get('wyckoff_analyzer', {})
    print(f"\n📈 Wyckoff Analyzer: {wyckoff.get('status', 'N/A').upper()}")
    if wyckoff.get('status') == 'success':
        print(f"   - Selling Climax: {wyckoff.get('selling_climax_count', 0)}")
        print(f"   - Spring: {wyckoff.get('spring_count', 0)}")
        print(f"   - UTAD: {wyckoff.get('utad_count', 0)}")
        print(f"   - SOW: {wyckoff.get('sow_count', 0)}")
    else:
        print(f"   - Error: {wyckoff.get('error', 'Unknown')}")
    
    # Full Service
    service = results.get('full_service', {})
    print(f"\n🔧 Full Service: {service.get('status', 'N/A').upper()}")
    if service.get('status') == 'success':
        print(f"   - Feature Types: {', '.join(service.get('feature_types', []))}")
    else:
        print(f"   - Error: {service.get('error', 'Unknown')}")
    
    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description="Test SMC analysis module for multiple stocks")
    parser.add_argument('--symbols', '-s', type=str, help="Comma-separated list of symbols to test")
    parser.add_argument('--all', '-a', action='store_true', help="Test all available symbols")
    parser.add_argument('--days', '-d', type=int, default=365, help="Number of days of historical data (default: 365)")
    args = parser.parse_args()
    
    symbols = []
    
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
    elif args.all:
        processed_dir = os.path.join(PROJECT_ROOT, "data", "processed")
        if os.path.exists(processed_dir):
            csv_files = [f for f in os.listdir(processed_dir) if f.endswith('.csv')]
            symbols = [f.replace('.csv', '') for f in csv_files]
        else:
            test_logger.error("Processed data directory not found")
            sys.exit(1)
    else:
        # Default test symbols
        symbols = ['VNINDEX', 'VIC', 'VCB', 'VHM', 'MSN']
        test_logger.info(f"No symbols specified, testing default: {', '.join(symbols)}")
    
    test_logger.info(f"Testing {len(symbols)} symbols: {', '.join(symbols)}")
    
    all_results = []
    for symbol in symbols:
        results = test_symbol(symbol, args.days)
        all_results.append(results)
        print_results(results)
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    passed = sum(1 for r in all_results if r.get('overall_status') == 'passed')
    failed = sum(1 for r in all_results if r.get('overall_status') == 'failed')
    skipped = sum(1 for r in all_results if r.get('overall_status') == 'skipped')
    
    print(f"Total: {len(all_results)}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"⊘ Skipped: {skipped}")
    
    if failed > 0:
        print(f"\nFailed symbols:")
        for r in all_results:
            if r.get('overall_status') == 'failed':
                print(f"  - {r['symbol']}")
        sys.exit(1)
    else:
        print(f"\n✓ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
