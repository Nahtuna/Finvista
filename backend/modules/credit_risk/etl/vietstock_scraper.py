# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: VIETSTOCK CORPORATE EVENTS & NEWS SCRAPER
=====================================================
Crawls Vietstock for Covered Warrant specific news and underlying stock dividend schedules.
Optimized to avoid redundant crawls for CWs sharing the same underlying security.

Author: samvo
"""

import os
import sys
import requests
import time
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy.orm import Session

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.core.database import SessionLocal, CorporateNews, CorporateEvent
from backend.modules.cw_pricing.backtest.fetcher import fetch_market_cw_data
# from backend.core.utils import logger, random_sleep  # Removed to avoid I/O errors
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

def normalize_date(raw: str) -> str:
    """Standardize date strings to YYYY-MM-DD HH:MM."""
    if not raw:
        return ""
    raw = raw.strip()
    # Try ISO format like 2026-07-29T11:47:11+07:00
    try:
        if 'T' in raw:
            dt = datetime.fromisoformat(raw)
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    # Try dd/mm/yyyy hh:mm
    try:
        match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}:\d{2}(?::\d{2})?))?", raw)
        if match:
            d, m, y, t = match.groups()
            if t:
                t = t[:5]
            else:
                t = "00:00"
            return f"{y}-{m.zfill(2)}-{d.zfill(2)} {t}"
    except Exception:
        pass
    return raw

class VietstockScraper:
    def __init__(self):
        self.db = SessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def get_cw_list(self):
        """Fetch unique underlying symbols and one representative CW for each."""
        try:
            df = fetch_market_cw_data()
            if df.empty:
                return {}
            # Group by underlying and pick the first CW symbol
            mapping = df.groupby('B_MaCPCS')['A_MaCW'].first().to_dict()
            return mapping
        except Exception as e:
            # Silent error handling to avoid I/O errors
            try:
                print(f"[ERROR] Error fetching CW list: {e}")
            except Exception:
                pass
            return {}

    def scrape_cw_page(self, cw_symbol, underlying_symbol, max_pages=2):
        """Scrape news and events for a specific CW/Underlying pair with fast pagination."""
        try:
            print(f"Scraping Vietstock for {underlying_symbol} (via {cw_symbol}) - Fast Crawl ({max_pages} pages)...")
        except Exception:
            pass
        
        # 1. Scrape News (Underlying Stock)
        self._scrape_paged_content(
            url="https://finance.vietstock.vn/View/StockNewsContentPage",
            code=underlying_symbol,
            category="Cổ phiếu cơ sở",
            target_symbol=underlying_symbol,
            max_pages=max_pages
        )

        # 2. Scrape News (Warrant)
        self._scrape_paged_content(
            url="https://finance.vietstock.vn/View/StockNewsContentPage",
            code=cw_symbol,
            category="Chứng quyền",
            target_symbol=cw_symbol,
            max_pages=max_pages
        )

        # 3. Scrape Events (Underlying Stock)
        self._scrape_paged_events(
            url="https://finance.vietstock.vn/View/StockEventContentPage",
            code=underlying_symbol,
            max_pages=max_pages
        )

    def _scrape_paged_content(self, url, code, category, target_symbol, max_pages):
        """Generic handler for paged news content via POST."""
        for page in range(1, max_pages + 1):
            payload = {
                "code": code,
                "channelID": -1,
                "page": page,
                "pageSize": 10
            }
            try:
                resp = None
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = requests.post(url, headers=HEADERS, data=payload, timeout=25)
                        break
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as req_err:
                        if attempt == max_retries - 1:
                            raise req_err
                        time.sleep(attempt * 2 + 2)
                
                if not resp or resp.status_code != 200 or not resp.text.strip():
                    break
                
                soup = BeautifulSoup(resp.content, "html.parser")
                rows = soup.select("table tr")
                if not rows: break
                
                added_in_page = 0
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        date_raw = cols[0].get_text(strip=True)
                        link_el = cols[1].find("a")
                        if link_el:
                            title = link_el.get_text(strip=True)
                            raw_href = link_el['href'] or ""
                            if raw_href.startswith("//"):
                                link = "https:" + raw_href
                            elif raw_href.startswith("/vietstock.vn"):
                                link = "https:/" + raw_href
                            elif raw_href.startswith("/"):
                                link = "https://finance.vietstock.vn" + raw_href
                            else:
                                link = raw_href
                            if self._save_news(target_symbol, title, link, normalize_date(date_raw), category):
                                added_in_page += 1
                
                if added_in_page == 0: # No new items found (all already in DB)
                    break
                    
                random.uniform(1, 2)
            except Exception as e:
                try:
                    print(f"[ERROR] Error scraping news page {page} for {code}: {e}")
                except Exception:
                    pass
                break

    def _scrape_paged_events(self, url, code, max_pages):
        """Generic handler for paged event content via POST."""
        for page in range(1, max_pages + 1):
            payload = {
                "code": code,
                "channelID": 0, # 0 usually covers all events
                "page": page,
                "pageSize": 10,
                "orderBy": "Date1",
                "orderDir": "DESC"
            }
            try:
                resp = None
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = requests.post(url, headers=HEADERS, data=payload, timeout=25)
                        break
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as req_err:
                        if attempt == max_retries - 1:
                            raise req_err
                        time.sleep(attempt * 2 + 2)
                
                if not resp or resp.status_code != 200 or not resp.text.strip():
                    break
                
                soup = BeautifulSoup(resp.content, "html.parser")
                rows = soup.select("table tr")
                if not rows: break
                
                added_in_page = 0
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        date_raw = cols[0].get_text(strip=True)
                        event_desc = cols[1].get_text(strip=True)
                        
                        event_type = "Sự kiện doanh nghiệp"
                        if "cổ tức" in event_desc.lower():
                            event_type = "Cổ tức tiền mặt" if "tiền" in event_desc.lower() else "Cổ tức cổ phiếu"
                        elif "họp" in event_desc.lower():
                            event_type = "Đại hội cổ đông"
                        
                        if self._save_event(code, normalize_date(date_raw).split(" ")[0], event_type, event_desc):
                            added_in_page += 1
                
                if added_in_page == 0:
                    break
                    
                random.uniform(1, 2)
            except Exception as e:
                try:
                    print(f"[ERROR] Error scraping event page {page} for {code}: {e}")
                except Exception:
                    pass
                break

    def _extract_news_content(self, link):
        """Fetch and extract content (summary) and precise publish time from news link."""
        summary = ""
        publish_time = None
        try:
            resp = requests.get(link, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return "", None
            
            soup = BeautifulSoup(resp.content, "html.parser")
            
            # 1. Try to find explicit summary/lead paragraphs (like p.pHead in Vietstock, p.sapo, etc.)
            lead_el = soup.select_one("p.pHead, p.sapo, div.sapo, .lead")
            if lead_el:
                summary = lead_el.get_text(strip=True)

            # 2. Try to find summary from meta tags if not found on page
            if not summary:
                meta_desc = (
                    soup.find("meta", attrs={"property": "og:description"}) or 
                    soup.find("meta", attrs={"name": "description"}) or 
                    soup.find("meta", attrs={"name": "DESCRIPTION"})
                )
                if meta_desc:
                    val = meta_desc.get("content")
                    if isinstance(val, str):
                        summary = val.strip()

            # 3. Try to get precise publish date from meta tags
            pub_meta = (
                soup.find("meta", attrs={"property": "article:published_time"}) or 
                soup.find("meta", attrs={"name": "pubdate"}) or 
                soup.find("meta", attrs={"name": "publish-date"}) or
                soup.find("meta", attrs={"property": "og:pubdate"})
            )
            if pub_meta:
                val = pub_meta.get("content")
                if isinstance(val, str):
                    publish_time = val.strip()
            
            # If summary still not found, fallback to body selectors
            if not summary:
                content_selectors = [
                    "div.blog_postcontent",
                    "div.news-content",
                    "div.content-detail",
                    "div.article-content",
                    "div.detail-content",
                    "div.fck_detail",
                    "div.content",
                    "article",
                ]
                for selector in content_selectors:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(separator="\n", strip=True)
                        lines = [line.strip() for line in text.split("\n") if line.strip()]
                        summary = "\n".join(lines[:20])
                        if len(summary) > 500:
                            break
            
            return summary, publish_time
        except Exception as e:
            try:
                logger.warning(f"⚠️ Could not extract content from {link}: {e}")
            except Exception:
                pass
            return "", None

    def _save_news(self, symbol, title, link, date, category):
        # Check if news exists
        existing = self.db.query(CorporateNews).filter(CorporateNews.link == link).first()
        if not existing:
            # Fetch content from link to extract summary
            summary, publish_time = self._extract_news_content(link)
            
            saved_date = date
            if publish_time:
                normalized_pub_time = normalize_date(publish_time)
                if normalized_pub_time:
                    saved_date = normalized_pub_time
            
            news = CorporateNews(
                symbol=symbol,
                title=title,
                link=link,
                date=saved_date,
                category=category,
                source="Vietstock",
                summary=summary
            )
            self.db.add(news)
            try:
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
        return False

    def _save_event(self, ticker, event_date, event_type, description):
        # Check if event exists
        existing = self.db.query(CorporateEvent).filter(
            CorporateEvent.ticker == ticker,
            CorporateEvent.event_date == event_date,
            CorporateEvent.description == description
        ).first()
        
        if not existing:
            event = CorporateEvent(
                ticker=ticker,
                event_date=event_date,
                event_type=event_type,
                description=description
            )
            self.db.add(event)
            try:
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
        return False

    def run(self, limit=None):
        try:
            print("Starting Vietstock Corporate Events & News Scraper...")
        except Exception:
            pass  # Ignore logging errors in background tasks
        
        mapping = self.get_cw_list()
        if not mapping:
            try:
                print("[WARNING] No CW symbols found to process.")
            except Exception:
                pass
            return

        count = 0
        for underlying, cw in mapping.items():
            if limit and count >= limit:
                break
            
            self.scrape_cw_page(cw, underlying)
            count += 1
            random.uniform(2, 4)

        try:
            print(f"Finished scraping events for {count} underlying assets.")
        except Exception:
            pass

if __name__ == "__main__":
    scraper = VietstockScraper()
    scraper.run()
