#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
📊 FINVISTA: VNSE DATA COLLECTOR
==================================
Download real historical data from Vietnam Stock Exchange (VNSE).

Usage:
  python scripts/collect_vnse_data.py --symbols VCB,VNM,FPT,MWG --years 3
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.core.utils import get_logger

data_logger = get_logger(__name__)


# Popular VNSE symbols (VN30 + Blue Chips)
POPULAR_SYMBOLS = [
    'VCB',  # Vietcombank
    'VNM',  # Vinamilk
    'FPT',  # FPT Corporation
    'MWG',  # Mobile World Group
    'VIC',  # Vingroup
    'HPG',  # Hoa Phat Group
    'MSN',  # Masan Group
    'HDB',  # HDBank
    'TCB',  # Techcombank
    'MBB',  # Military Bank
    'SSB',  # Saigon Securities
    'SSI',  # SSI Securities
    'VRE',  # Vincom Retail
    'PLX',  # Petrovietnam
    'GVR',  # Vinhomes
    'STB',  # Sacombank
    'ACB',  # Asia Commercial Bank
    'CTG',  # VietinBank
    'BID',  # BIDV
    'VPB',  # VPBank
]


def download_stock_data(symbol: str, years: int = 3) -> pd.DataFrame:
    """
    Download historical data for a single stock.
    
    Args:
        symbol: Stock symbol (e.g., 'VCB.VN' for Yahoo Finance)
        years: Number of years of historical data
        
    Returns:
        DataFrame with OHLCV data
    """
    try:
        # Yahoo Finance format for Vietnam stocks
        ticker = f"{symbol}.VN"
        
        data_logger.info(f"Downloading data for {symbol}...")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        # Download data
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            data_logger.warning(f"No data found for {symbol}")
            return None
        
        # Reset index to make date a column
        df.reset_index(inplace=True)
        
        # Rename columns to match our format
        df.rename(columns={
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }, inplace=True)
        
        # Add symbol column
        df['symbol'] = symbol
        
        # Select only needed columns
        df = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']]
        
        # Sort by date
        df.sort_values('date', inplace=True)
        
        data_logger.info(f"Downloaded {len(df)} bars for {symbol}")
        return df
    
    except Exception as e:
        data_logger.error(f"Error downloading data for {symbol}: {e}")
        return None


def download_multiple_stocks(symbols: list, years: int = 3) -> pd.DataFrame:
    """
    Download historical data for multiple stocks.
    
    Args:
        symbols: List of stock symbols
        years: Number of years of historical data
        
    Returns:
        DataFrame with all stocks data
    """
    all_data = []
    
    for symbol in symbols:
        df = download_stock_data(symbol, years)
        if df is not None and not df.empty:
            all_data.append(df)
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        data_logger.info(f"Total downloaded: {len(combined_df)} bars across {len(symbols)} symbols")
        return combined_df
    else:
        data_logger.error("No data downloaded for any symbol")
        return None


def save_data(df: pd.DataFrame, output_path: str):
    """
    Save data to CSV file.
    
    Args:
        df: DataFrame with stock data
        output_path: Path to save the CSV file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        data_logger.info(f"Data saved to {output_path}")
        
        # Print summary
        print(f"\n" + "=" * 60)
        print("DATA COLLECTION SUMMARY")
        print("=" * 60)
        print(f"Total bars: {len(df)}")
        print(f"Symbols: {df['symbol'].nunique()}")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"Data saved to: {output_path}")
        print("=" * 60)
        
    except Exception as e:
        data_logger.error(f"Error saving data: {e}")


def validate_data(df: pd.DataFrame) -> dict:
    """
    Validate data quality.
    
    Args:
        df: DataFrame with stock data
        
    Returns:
        Dictionary with validation results
    """
    validation = {
        'total_bars': len(df),
        'symbols': df['symbol'].nunique(),
        'date_range': f"{df['date'].min()} to {df['date'].max()}",
        'missing_values': df.isnull().sum().sum(),
        'completeness': (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100,
        'issues': []
    }
    
    # Check for missing values
    if validation['missing_values'] > 0:
        validation['issues'].append(f"Missing values: {validation['missing_values']}")
    
    # Check for zero volume
    zero_volume = (df['volume'] == 0).sum()
    if zero_volume > 0:
        validation['issues'].append(f"Zero volume bars: {zero_volume}")
    
    # Check for negative prices
    negative_prices = (df[['open', 'high', 'low', 'close']] < 0).sum().sum()
    if negative_prices > 0:
        validation['issues'].append(f"Negative prices: {negative_prices}")
    
    # Check for high > low
    invalid_ohlc = (df['high'] < df['low']).sum()
    if invalid_ohlc > 0:
        validation['issues'].append(f"High < Low: {invalid_ohlc}")
    
    return validation


def main():
    parser = argparse.ArgumentParser(description="Download VNSE historical data")
    parser.add_argument('--symbols', '-s', type=str, 
                       help="Comma-separated symbols (e.g., VCB,VNM,FPT)")
    parser.add_argument('--years', '-y', type=int, default=3,
                       help="Number of years of historical data (default: 3)")
    parser.add_argument('--output', '-o', type=str, 
                       default="data/processed/vnse_historical_prices.csv",
                       help="Output CSV file path")
    parser.add_argument('--popular', '-p', action='store_true',
                       help="Download popular VNSE symbols (VN30 + Blue Chips)")
    
    args = parser.parse_args()
    
    # Determine symbols to download
    if args.popular:
        symbols = POPULAR_SYMBOLS
        data_logger.info(f"Downloading {len(symbols)} popular VNSE symbols")
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
        data_logger.info(f"Downloading {len(symbols)} symbols: {symbols}")
    else:
        data_logger.error("Please specify --symbols or --popular")
        parser.print_help()
        sys.exit(1)
    
    # Download data
    df = download_multiple_stocks(symbols, args.years)
    
    if df is None or df.empty:
        data_logger.error("Failed to download data")
        sys.exit(1)
    
    # Validate data
    validation = validate_data(df)
    print(f"\nData Validation:")
    print(f"  Total bars: {validation['total_bars']}")
    print(f"  Symbols: {validation['symbols']}")
    print(f"  Date range: {validation['date_range']}")
    print(f"  Completeness: {validation['completeness']:.2f}%")
    
    if validation['issues']:
        print(f"  Issues:")
        for issue in validation['issues']:
            print(f"    - {issue}")
    else:
        print(f"  No issues detected!")
    
    # Save data
    save_data(df, args.output)
    
    data_logger.info("Data collection completed successfully")


if __name__ == "__main__":
    main()
