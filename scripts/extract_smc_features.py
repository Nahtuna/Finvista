#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: SMC FEATURE EXTRACTION SCRIPT
============================================
Extracts Smart Money Concepts features from historical stock data
and stores them in the database for enhanced trading signals.

Usage:
  python scripts/extract_smc_features.py --symbol VNINDEX --days 365
  python scripts/extract_smc_features.py --all --days 365

Author: Finvista SMC Module
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

from backend.modules.smc_analysis.service import SMCAnalysisService
from backend.core.utils import get_logger

smc_logger = get_logger(__name__)


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
        smc_logger.info(f"Loading data from existing CSV: {csv_path}")
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
            
            smc_logger.info(f"Loaded {len(df)} records from database for {symbol}")
            session.close()
            return df
        
        session.close()
        
    except Exception as e:
        smc_logger.error(f"Error loading from database: {e}")
    
    smc_logger.warning(f"No data found for {symbol}")
    return pd.DataFrame()


def extract_smc_for_symbol(symbol: str, days: int = 365) -> bool:
    """
    Extract SMC features for a single symbol.
    
    Args:
        symbol: Stock symbol
        days: Number of days of historical data
        
    Returns:
        True if successful, False otherwise
    """
    smc_logger.info(f"Extracting SMC features for {symbol} ({days} days)")
    
    try:
        # Load data
        df = load_stock_data(symbol, days)
        
        if df.empty:
            smc_logger.warning(f"No data available for {symbol}")
            return False
        
        # Validate data
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            smc_logger.error(f"Missing required columns for {symbol}")
            return False
        
        # Extract SMC features
        service = SMCAnalysisService()
        features = service.extract_all_features(df, symbol)
        
        # Save to database
        latest_date = df.index[-1].strftime('%Y-%m-%d')
        success = service.save_features_to_db(symbol, latest_date, features)
        
        if success:
            smc_logger.info(f"✓ Successfully extracted and saved SMC features for {symbol}")
            return True
        else:
            smc_logger.error(f"✗ Failed to save SMC features for {symbol}")
            return False
            
    except Exception as e:
        smc_logger.error(f"Error extracting SMC features for {symbol}: {e}")
        return False


def extract_smc_for_all_symbols(days: int = 365) -> int:
    """
    Extract SMC features for all available symbols.
    
    Args:
        days: Number of days of historical data
        
    Returns:
        Number of successfully processed symbols
    """
    smc_logger.info(f"Extracting SMC features for all symbols ({days} days)")
    
    # Get list of symbols from existing data
    processed_dir = os.path.join(PROJECT_ROOT, "data", "processed")
    
    if not os.path.exists(processed_dir):
        smc_logger.warning(f"Processed data directory not found: {processed_dir}")
        return 0
    
    # Get all CSV files
    csv_files = [f for f in os.listdir(processed_dir) if f.endswith('.csv')]
    symbols = [f.replace('.csv', '') for f in csv_files]
    
    smc_logger.info(f"Found {len(symbols)} symbols to process")
    
    success_count = 0
    for symbol in symbols:
        if extract_smc_for_symbol(symbol, days):
            success_count += 1
    
    smc_logger.info(f"Successfully processed {success_count}/{len(symbols)} symbols")
    return success_count


def main():
    parser = argparse.ArgumentParser(description="Extract SMC features from historical stock data")
    parser.add_argument('--symbol', '-s', type=str, help="Single symbol to process")
    parser.add_argument('--all', '-a', action='store_true', help="Process all available symbols")
    parser.add_argument('--days', '-d', type=int, default=365, help="Number of days of historical data (default: 365)")
    args = parser.parse_args()
    
    if args.symbol:
        # Process single symbol
        success = extract_smc_for_symbol(args.symbol, args.days)
        sys.exit(0 if success else 1)
        
    elif args.all:
        # Process all symbols
        success_count = extract_smc_for_all_symbols(args.days)
        sys.exit(0 if success_count > 0 else 1)
        
    else:
        smc_logger.error("Please specify either --symbol or --all")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
