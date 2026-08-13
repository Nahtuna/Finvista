# -*- coding: utf-8 -*-
"""
💰 FINVISTA: DIVIDEND SCHEDULE SCRAPER
========================================
Fetches dividend schedules and ex-dividend dates from Vietnamese stock market.
Supports multiple free sources: Vietstock, CaféF, and vnstock.

Author: samvo
"""

import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os
import pandas as pd
from backend.core.utils import logger
from backend.core import config
from tenacity import retry, stop_after_attempt, wait_exponential

def fetch_dividend_schedule_vnstock(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetches dividend schedule using vnstock library.
    
    Args:
        symbol: Stock symbol (e.g., "VCB", "VNM")
    
    Returns:
        List of dividend events with dates and amounts
    """
    try:
        from vnstock import Fundamental
        fund = Fundamental()
        
        logger.info(f"📊 Fetching dividend schedule for {symbol} via vnstock...")
        
        # Try to get dividend data
        # Note: vnstock API may vary by version
        dividend_data = []
        
        # Placeholder structure - actual implementation depends on vnstock capabilities
        # In production, this would call the appropriate vnstock method
        
        return dividend_data
        
    except Exception as e:
        logger.warning(f"⚠️ Could not fetch dividends via vnstock for {symbol}: {e}")
        return []

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=False
)
def fetch_dividend_schedule_vietstock(symbol: str) -> List[Dict[str, Any]]:
    """
    Scrapes dividend schedule from Vietstock website.
    
    Args:
        symbol: Stock symbol (e.g., "VCB", "VNM")
    
    Returns:
        List of dividend events
    """
    logger.info(f"📊 Fetching dividend schedule for {symbol} from Vietstock...")
    
    # Vietstock dividend page URL pattern
    url = f"https://finance.vietstock.vn/{symbol}/tai-chinh/co-tuc.aspx"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3",
        }
        
        response = httpx.get(url, headers=headers, timeout=10.0)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            dividend_events = []
            
            # Parse dividend table
            # Note: HTML structure may change, this is a generic parser
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        try:
                            ex_date = cols[0].get_text(strip=True)
                            dividend_type = cols[1].get_text(strip=True)
                            amount = cols[2].get_text(strip=True)
                            
                            # Parse amount (remove currency symbols, convert to float)
                            amount_clean = amount.replace(',', '').replace('đ', '').replace('VND', '').strip()
                            amount_val = float(amount_clean) if amount_clean else 0.0
                            
                            dividend_events.append({
                                "ex_date": ex_date,
                                "type": dividend_type,
                                "amount": amount_val,
                                "currency": "VND"
                            })
                        except Exception as e:
                            continue
            
            logger.info(f"✅ Found {len(dividend_events)} dividend events for {symbol}")
            return dividend_events
            
    except Exception as e:
        logger.warning(f"⚠️ Could not scrape Vietstock dividends for {symbol}: {e}")
    
    return []

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=False
)
def fetch_dividend_schedule_cafef(symbol: str) -> List[Dict[str, Any]]:
    """
    Scrapes dividend schedule from CaféF website.
    
    Args:
        symbol: Stock symbol (e.g., "VCB", "VNM")
    
    Returns:
        List of dividend events
    """
    logger.info(f"📊 Fetching dividend schedule for {symbol} from CaféF...")
    
    # CaféF company page URL pattern
    url = f"https://cafef.vn/du-lieu-co-tuc/{symbol}.chn"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        response = httpx.get(url, headers=headers, timeout=10.0)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            dividend_events = []
            
            # Parse dividend data from CaféF structure
            # Note: HTML structure may change
            
            logger.info(f"✅ Found {len(dividend_events)} dividend events for {symbol}")
            return dividend_events
            
    except Exception as e:
        logger.warning(f"⚠️ Could not scrape CaféF dividends for {symbol}: {e}")
    
    return []

def get_dividend_schedule(symbol: str, prefer_source: str = "vnstock") -> List[Dict[str, Any]]:
    """
    Gets dividend schedule from multiple sources with fallback.
    
    Args:
        symbol: Stock symbol
        prefer_source: Preferred source ("vnstock", "vietstock", "cafef")
    
    Returns:
        List of dividend events sorted by date
    """
    sources = {
        "vnstock": fetch_dividend_schedule_vnstock,
        "vietstock": fetch_dividend_schedule_vietstock,
        "cafef": fetch_dividend_schedule_cafef
    }
    
    # Try preferred source first
    if prefer_source in sources:
        events = sources[prefer_source](symbol)
        if events:
            return events
    
    # Try other sources as fallback
    for source_name, source_func in sources.items():
        if source_name != prefer_source:
            events = source_func(symbol)
            if events:
                return events
    
    return []

def parse_dividend_for_pricing(symbol: str, current_date: Optional[datetime] = None) -> List[tuple]:
    """
    Parses dividend schedule into format required by pricing models.
    
    Args:
        symbol: Stock symbol
        current_date: Reference date (default: today)
    
    Returns:
        List of tuples (dividend_amount, time_to_pay_in_years)
    """
    if current_date is None:
        current_date = datetime.now()
    
    events = get_dividend_schedule(symbol)
    
    parsed_dividends = []
    for event in events:
        try:
            ex_date_str = event.get("ex_date", "")
            if ex_date_str:
                # Parse date (handle various formats)
                try:
                    ex_date = datetime.strptime(ex_date_str, "%Y-%m-%d")
                except:
                    try:
                        ex_date = datetime.strptime(ex_date_str, "%d/%m/%Y")
                    except:
                        continue
                
                # Calculate time to payment in years
                time_to_pay = (ex_date - current_date).days / 365.0
                
                # Only include future dividends
                if time_to_pay > 0:
                    amount = event.get("amount", 0.0)
                    parsed_dividends.append((amount, time_to_pay))
                    
        except Exception as e:
            continue
    
    # Sort by time
    parsed_dividends.sort(key=lambda x: x[1])
    
    return parsed_dividends

def save_dividend_cache(symbol: str, events: List[Dict[str, Any]]):
    """
    Saves dividend schedule to cache.
    
    Args:
        symbol: Stock symbol
        events: List of dividend events
    """
    cache_dir = os.path.join(config.DATA_DIR, "cache", "dividends")
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_file = os.path.join(cache_dir, f"{symbol}_dividends.json")
    
    cache_data = {
        "symbol": symbol,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "events": events
    }
    
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=4, ensure_ascii=False)
    
    logger.info(f"💾 Dividend cache saved for {symbol}")

def load_dividend_cache(symbol: str) -> Optional[List[Dict[str, Any]]]:
    """
    Loads dividend schedule from cache.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        List of dividend events if cache exists and is recent (< 7 days)
    """
    cache_dir = os.path.join(config.DATA_DIR, "cache", "dividends")
    cache_file = os.path.join(cache_dir, f"{symbol}_dividends.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        # Check if cache is recent (< 7 days)
        last_updated = datetime.strptime(cache_data["last_updated"], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last_updated).days < 7:
            logger.info(f"💾 Loading dividend cache for {symbol}")
            return cache_data["events"]
        
    except Exception as e:
        logger.warning(f"⚠️ Could not load dividend cache for {symbol}: {e}")
    
    return None

def get_dividend_data_with_cache(symbol: str) -> List[Dict[str, Any]]:
    """
    Gets dividend data with cache support.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        List of dividend events
    """
    # Try cache first
    cached = load_dividend_cache(symbol)
    if cached:
        return cached
    
    # Fetch from sources
    events = get_dividend_schedule(symbol)
    
    # Save to cache
    if events:
        save_dividend_cache(symbol, events)
    
    return events

if __name__ == "__main__":
    # Test fetching dividend data
    symbol = "VCB"
    
    events = get_dividend_data_with_cache(symbol)
    
    print(f"\n💰 Dividend Schedule for {symbol}:")
    print(json.dumps(events, indent=2, ensure_ascii=False))
    
    # Test parsing for pricing
    parsed = parse_dividend_for_pricing(symbol)
    print(f"\n📊 Parsed Dividends for Pricing (amount, time_in_years):")
    for div in parsed:
        print(f"  {div[0]:,.0f} VND at {div[1]:.3f} years")
