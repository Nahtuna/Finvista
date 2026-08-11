#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: PARAMETER OPTIMIZATION SCRIPT
=========================================
Optimize indicator parameters using walk-forward validation.

Usage:
  python scripts/optimize_parameters.py --symbol ACB --days 365
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.evaluation.parameter_optimizer import ParameterOptimizer
from backend.core.utils import get_logger

opt_logger = get_logger(__name__)


def load_test_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """Load test data for optimization from database."""
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
        
        opt_logger.info(f"Loading data from database for {symbol}")
        df = pd.read_sql(query, engine)
        
        if df.empty:
            opt_logger.warning(f"No data found for {symbol} in database")
            return None
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        return df
        
    except Exception as e:
        opt_logger.error(f"Failed to load data from database: {e}")
        return None


def optimize_smc_parameters(df: pd.DataFrame, symbol: str):
    """Optimize SMC parameters."""
    opt_logger.info(f"Optimizing SMC parameters for {symbol}")
    
    optimizer = ParameterOptimizer(train_pct=0.6, val_pct=0.2, test_pct=0.2)
    
    param_grid = {
        'pivot_window': [3, 5, 7, 10],
        'liquidity_lookback': [3, 5, 7, 10]
    }
    
    results = optimizer.optimize_smc_parameters(df, df, param_grid)
    
    print(f"\nSMC Parameter Optimization Results for {symbol}:")
    print(f"  Best Parameters: {results['best_params']}")
    print(f"  Validation Score: {results['best_score']:.3f}")
    print(f"  Test Performance: {results['performance']}")
    
    return results


def optimize_custom_parameters(df: pd.DataFrame, symbol: str):
    """Optimize Custom Indicator parameters."""
    opt_logger.info(f"Optimizing Custom parameters for {symbol}")
    
    optimizer = ParameterOptimizer(train_pct=0.6, val_pct=0.2, test_pct=0.2)
    
    param_grid = {
        'atr_period': [7, 14, 21, 28],
        'volume_period': [10, 20, 30, 40]
    }
    
    results = optimizer.optimize_custom_parameters(df, df, param_grid)
    
    print(f"\nCustom Indicator Parameter Optimization Results for {symbol}:")
    print(f"  Best Parameters: {results['best_params']}")
    print(f"  Validation Score: {results['best_score']:.3f}")
    print(f"  Test Performance: {results['performance']}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Optimize indicator parameters")
    parser.add_argument('--symbol', '-s', type=str, help="Symbol to optimize")
    parser.add_argument('--days', '-d', type=int, default=365, help="Number of days of data")
    parser.add_argument('--walk-forward', '-w', action='store_true', help="Run walk-forward validation")
    args = parser.parse_args()
    
    if args.symbol:
        df = load_test_data(args.symbol, args.days)
        
        if df is None or df.empty:
            opt_logger.error(f"Could not load data for {args.symbol}")
            sys.exit(1)
        
        if args.walk_forward:
            optimizer = ParameterOptimizer()
            param_grid = {
                'pivot_window': [3, 5, 7],
                'liquidity_lookback': [3, 5, 7],
                'atr_period': [7, 14, 21],
                'volume_period': [10, 20, 30]
            }
            
            results = optimizer.walk_forward_validation(df, num_windows=3, param_grid=param_grid)
            
            print(f"\nWalk-Forward Validation Results for {args.symbol}:")
            print(f"  SMC Average Return: {results['aggregate']['smc_avg_return']:.3f}")
            print(f"  Custom Average Return: {results['aggregate']['custom_avg_return']:.3f}")
            print(f"  SMC Std Return: {results['aggregate']['smc_std_return']:.3f}")
            print(f"  Custom Std Return: {results['aggregate']['custom_std_return']:.3f}")
        else:
            smc_results = optimize_smc_parameters(df, args.symbol)
            custom_results = optimize_custom_parameters(df, args.symbol)
    else:
        opt_logger.error("Please specify --symbol")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
