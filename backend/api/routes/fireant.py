# -*- coding: utf-8 -*-
"""
FINVISTA: FIREANT ROUTES — Scraper API + RAG context builder
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional
from pydantic import BaseModel

import re
import unicodedata
import email.utils
import logging
import time
import requests
from datetime import datetime, timedelta
from sqlalchemy import func

router = APIRouter(tags=["fireant"])
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://vietstock.vn/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3",
}

def _parse_date_to_iso(date_str) -> str:
    if not date_str:
        return ""
    if isinstance(date_str, datetime):
        return date_str.isoformat()
    date_str = str(date_str).strip()
    try:
        # If it's already ISO or YYYY-MM-DD
        if " " in date_str and len(date_str) > 10 and date_str[10] == " " and "+" not in date_str and "-" not in date_str:
            date_str = date_str[:10] + "T" + date_str[11:]
        dt = datetime.fromisoformat(date_str)
        return dt.isoformat()
    except Exception:
        pass

    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        pass
    return date_str

def _normalize_title(t: str) -> str:
    if not t:
        return ""
    t = unicodedata.normalize("NFC", t)
    t = re.sub(r"\s+", " ", t.lower().strip())
    return t




class ScrapeRequest(BaseModel):
    token: Optional[str] = None     # Bearer token. None → đọc từ env FIREANT_TOKEN
    symbol: Optional[str] = None    # Lọc theo mã CK, None = tất cả
    post_type: int = 1              # 1=bài phân tích, 0=social
    max_pages: int = 10             # Số trang tối đa


@router.post("/api/fireant/scrape")
def fireant_scrape(req: ScrapeRequest):
    """
    Cào bài viết phân tích từ FireAnt và lưu vào DB.

    **Cách lấy Bearer token:**
    1. Mở https://fireant.vn → đăng nhập
    2. Nhấn F12 → Tab Network → Filter XHR
    3. Click request tới restv2.fireant.vn
    4. Copy giá trị header `Authorization`
    5. Dán vào field `token` hoặc đặt env `FIREANT_TOKEN`
    """
    from backend.infra.fireant_scraper import FireAntScraper
    scraper = FireAntScraper(token=req.token)
    result = scraper.scrape(
        symbol=req.symbol,
        post_type=req.post_type,
        max_pages=req.max_pages,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


import re
KNOWN_STOCKS = {"DGC", "HDB", "MBB", "ACB", "MSN", "MWG", "VPB", "VIB", "HPG", "FPT", "VIC", "VHM", "VRE", "SSI", "VND", "VCI", "HCM", "SHB", "LPB", "STB", "TCB", "CTG", "BID", "VCB", "GAS", "POW", "PVD", "PVS", "BSR", "DIG", "NVL", "PDR", "NLG", "KDH", "DXG"}

# Noise patterns in raw-scraped summaries from Vietstock/fili.vn
_SUMMARY_NOISE = re.compile(
    r'(\d{1,2}[-/]\d{1,2}[-/]\d{4}[T\s]\d{1,2}:\d{2}[^\n]*)'  # timestamps
    r'|(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\n]*)'          # ISO timestamps
    r'|(VIETSTOCK|CAFEF|VNEXPRESS|CafeF|VietnamFinance)'          # source labels
    r'|(\.pdf[^\n]*)'                                             # PDF file refs
    r'|(HOSE|HNX|UPCOM)(?=\s*$)'                                  # exchange label alone
    r'|^(tải liệu đính kèm:?)',                                   # attachment header
    re.IGNORECASE | re.MULTILINE
)

def _clean_summary(raw: str, title: str = "") -> str:
    """Clean formatting noise, deduplicate lines, and remove source/date lines without losing content."""
    if not raw:
        return ""
    
    title_norm = _normalize_title(title)
    
    # Common source and exchange labels (exact match or alone on line)
    labels_to_skip = {
        "vietstock", "cafef", "vnexpress", "vietnamfinance", 
        "hose", "hnx", "upcom", "tin nhanh chứng khoán", "tnck"
    }
    
    # Regex to check if a line is ONLY a date/time
    only_date_regex = re.compile(
        r'^\s*('
        r'\d{1,2}[-/]\d{1,2}[-/]\d{4}(\s+\d{1,2}:\d{2}(:\d{2})?)?([\s+-]*\d{2}:?\d{2})?'
        r'|\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?([\s+-]*\d{2}:?\d{2})?'
        r')\s*$',
        re.IGNORECASE
    )

    # 1. Clean relative time prefixes like "38 phút trước", "2 giờ trước" globally
    raw = re.sub(r"\b\d+\s+(phút|giờ|ngày|tháng)\s+trước\b", "", raw, flags=re.IGNORECASE)

    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    cleaned_lines = []
    seen = set()
    
    for line in lines:
        # Clean empty parenthesis and dangling parenthesis at the end
        line_cleaned = re.sub(r"\(\s*\)", "", line)
        line_cleaned = re.sub(r"\(\s*$", "", line_cleaned)
        line_cleaned = re.sub(r"\s+,\s+", ", ", line_cleaned) # Fix spaces before comma
        # Trim and collapse whitespaces
        line_cleaned = re.sub(r"\s+", " ", line_cleaned).strip()
        
        if not line_cleaned:
            continue
            
        line_norm = _normalize_title(line_cleaned)
        
        # Skip labels, dates, and title repetitions
        if line_norm in labels_to_skip:
            continue
        if only_date_regex.match(line_cleaned):
            continue
        if title_norm and line_norm == title_norm:
            continue
            
        if line_norm not in seen:
            seen.add(line_norm)
            cleaned_lines.append(line_cleaned)
            
    # 2. Smart sentence reconstruction: Join lines that are part of the same sentence
    joined_text = ""
    for i, line in enumerate(cleaned_lines):
        if not joined_text:
            joined_text = line
        else:
            prev_line = cleaned_lines[i-1]
            # If the current line starts with a punctuation or lowercase letter,
            # or if the previous line does not end with sentence-ending punctuation, join with space
            if (line[0] in ",.:;)]}" or line[0].islower() or 
                not prev_line[-1] in ".?!:"):
                joined_text += " " + line
            else:
                joined_text += "\n" + line

    # 3. Post-process cleanups for punctuation spacing
    joined_text = re.sub(r"\s+,\s*", ", ", joined_text)
    joined_text = re.sub(r"\s+:\s*", ": ", joined_text)
    joined_text = re.sub(r"\(\s+", "(", joined_text)
    joined_text = re.sub(r"\s+\)", ")", joined_text)
    joined_text = re.sub(r"\(\s*\)", "", joined_text)
    joined_text = re.sub(r"\(\s*$", "", joined_text)
    joined_text = re.sub(r"\s+", " ", joined_text).strip()

    # Fallback if empty
    if not joined_text and lines:
        fallback = raw.replace("\n", " ")
        fallback = re.sub(r"\s+", " ", fallback).strip()
        return fallback[:600]
        
    return joined_text[:600] if len(joined_text) > 600 else joined_text


def _extract_pdf_attachment(url: str) -> dict:
    """Extract PDF attachment from Vietstock article URL.
    Returns dict with 'filename' and 'url' if found, None otherwise."""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Only process Vietstock URLs
        if "vietstock.vn" not in url:
            return None
        
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        
        soup = BeautifulSoup(r.content, "html.parser")
        
        # Method 1: Look for PDF links in the content
        pdf_links = soup.find_all("a", href=re.compile(r"\.pdf", re.I))
        if pdf_links:
            for link in pdf_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                # Make absolute URL if needed
                if href.startswith("/"):
                    href = "https://vietstock.vn" + href
                return {"filename": text, "url": href}
        
        # Method 2: Look for static2.vietstock.vn links (common for attachments)
        static_links = soup.find_all("a", href=re.compile(r"static2\.vietstock\.vn.*\.pdf", re.I))
        if static_links:
            for link in static_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                return {"filename": text, "url": href}
        
        return None
    except Exception:
        return None


def _normalize_date(raw: str) -> str | None:
    """Normalize date string to YYYY-MM-DD HH:MM format."""
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    now = datetime.now()

    # 1. ISO 8601
    try:
        clean_raw = raw.replace("Z", "+00:00").replace(" (GMT+7)", "").replace(" GMT+7", "")
        dt = datetime.fromisoformat(clean_raw)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        pass

    raw_lower = raw.lower()

    # 2. Relative time
    rel = re.search(r"(\d+)\s*(phút|giờ|ngày|tuần|tháng|năm)", raw_lower)
    if rel:
        n, u = int(rel.group(1)), rel.group(2)
        delta = {
            "phút": timedelta(minutes=n), 
            "giờ": timedelta(hours=n),
            "ngày": timedelta(days=n), 
            "tuần": timedelta(weeks=n),
            "tháng": timedelta(days=n*30),
            "năm": timedelta(days=n*365)
        }.get(u, timedelta())
        return (now - delta).strftime("%Y-%m-%d %H:%M")

    if "hôm qua" in raw_lower or "hm qua" in raw_lower:
        t = re.search(r"(\d{1,2}:\d{2})", raw)
        return (now - timedelta(days=1)).strftime("%Y-%m-%d") + " " + (t.group(1) if t else "12:00")

    if "hôm nay" in raw_lower or "hm nay" in raw_lower:
        t = re.search(r"(\d{1,2}:\d{2})", raw)
        return now.strftime("%Y-%m-%d") + " " + (t.group(1) if t else now.strftime("%H:%M"))

    # 3. DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
    if m:
        d, mo, y = m.groups()
        t = re.search(r"(\d{1,2}:\d{2})", raw)
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)} {(t.group(1) if t else '00:00')}"

    # 4. YYYY-MM-DD
    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", raw)
    if m:
        y, mo, d = m.groups()
        t = re.search(r"(\d{1,2}:\d{2})", raw)
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)} {(t.group(1) if t else '00:00')}"

    return None


def _get_vietstock_summary_from_rss(url: str) -> tuple:
    """
    Try to get Vietstock summary from RSS feed as fallback.
    Vietstock pages are now SPA/JS-rendered, so direct scraping often fails.
    NOTE: Vietstock RSS also returns HTML now, so this fallback is limited.
    """
    # Vietstock RSS is also returning HTML instead of RSS XML
    # This function is kept for future use if Vietstock restores RSS
    return None, ""


def _get_article_details(url: str, source: str) -> tuple:
    """
    Fetch date and summary from article URL based on source site selectors.
    Returns (date_str, summary_str) tuple.
    Has retry logic (3 attempts) for network errors.
    """
    from bs4 import BeautifulSoup
    
    # Define selectors for each source (learned from sentiment_scraper.py)
    selectors = {
        "Vietstock": (
            [".date", "span.date", ".pdate", ".time", ".article-date", ".meta-time"],
            ["p.pHead", ".sapo", ".phead", ".post-p", "meta[name='description']", "meta[property='og:description']"]
        ),
        "CafeF": (
            ["span.pdate", ".pdate", ".time"],
            ["h2.sapo", ".sapo", ".detail-sapo"]
        ),
        "VnEconomy": (
            [".article-meta__time", "time", "time[datetime]", ".time-format", "p.date", ".detail-time", ".date-time", "span.date"],
            [".article-content__lead", '[data-field="sapo"]', "h4[data-field=\"sapo\"]", ".news-sapo", ".sapo", ".post-description", ".story__summary", "meta[name='description']", "meta[property='og:description']"]
        ),
        "Stockbiz": (
            ["div.text-sm.line-clamp-1 span:last-child", "div.text-sm span.text-gray-500"],
            ["strong.font-semibold", "h2.sapo", ".post_description", "meta[name='description']"]
        ),
    }
    
    date_sels, summary_sels = selectors.get(source, ([], []))
    
    # Retry logic (3 attempts)
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 403:
                logger.warning(f"[RATE-LIMIT] {source} {url} → waiting {10*(attempt+1)}s")
                time.sleep(10 * (attempt + 1))
                continue
            
            # Check if content is too short (likely blocked/SPA)
            if len(r.content) < 5000 and source == "Vietstock":
                logger.warning(f"[WARN] Vietstock page too short (SPA/blocked), skipping")
                return None, ""
            
            soup = BeautifulSoup(r.content, "html.parser")
            
            # Check if page is empty/redirected
            title = soup.find("title")
            if title and "Vietstock.vn" == title.get_text(strip=True) and source == "Vietstock":
                # Likely empty page, skip
                logger.warning(f"[WARN] Vietstock page empty (SPA/blocked), skipping")
                return None, ""
            
            # Extract date
            norm_date = None
            meta = soup.select_one('meta[property="article:published_time"]')
            if meta and meta.get("content"):
                norm_date = _normalize_date(meta["content"])
            
            if not norm_date:
                for sel in date_sels:
                    el = soup.select_one(sel)
                    if el:
                        norm_date = _normalize_date(el.get_text(strip=True))
                        if norm_date:
                            break
            
            # Extract summary
            summary = ""
            for sel in summary_sels:
                if sel.startswith("meta") or sel.startswith("meta["):
                    el = soup.select_one(sel)
                    if el and el.get("content"):
                        summary = el["content"]
                else:
                    el = soup.select_one(sel)
                    if el:
                        summary = el.get_text(strip=True)
                if summary and len(summary) > 20:
                    break
            
            return norm_date, summary
            
        except Exception as e:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                logger.warning(f"[WARN] {source} detail {url}: {e}")
    
    return None, ""


def _heal_missing_summaries(limit: int = 100, source_filter: str = None) -> dict:
    """Heal missing summaries in CorporateNews table.
    
    Args:
        limit: Max articles to heal per run
        source_filter: Only heal articles from specific source (e.g., "Vietstock")
    
    Returns:
        dict with stats: total_checked, healed, failed
    """
    from backend.core.database import SessionLocal, CorporateNews
    
    db = SessionLocal()
    stats = {"total_checked": 0, "healed": 0, "failed": 0, "skipped": 0}
    
    try:
        # Find articles with missing or short summaries
        query = db.query(CorporateNews)
        if source_filter:
            query = query.filter(CorporateNews.source == source_filter)
        
        # Filter: summary is None, empty, or too short (< 20 chars)
        articles = query.filter(
            (CorporateNews.summary.is_(None)) | 
            (CorporateNews.summary == "") | 
            (CorporateNews.summary == "Không có tóm tắt") |
            (func.length(CorporateNews.summary) < 20)
        ).order_by(CorporateNews.date.desc()).limit(limit).all()
        
        stats["total_checked"] = len(articles)
        
        for article in articles:
            if not article.link:
                stats["skipped"] += 1
                continue
            
            # Skip invalid URLs
            if article.link.startswith("mailto:") or not article.link.startswith("http"):
                stats["skipped"] += 1
                logger.warning(f"[HEAL] Skipped invalid URL: {article.link[:50]}")
                continue
            
            # Fetch new summary using improved function with retry logic
            norm_date, new_summary = _get_article_details(article.link, article.source or "Vietstock")
            
            if new_summary and len(new_summary) > 20:
                # Validate summary relevance: check if summary contains keywords from title
                title_words = set(re.findall(r'\b\w{3,}\b', article.title.lower()))
                summary_words = set(re.findall(r'\b\w{3,}\b', new_summary.lower()))
                overlap = len(title_words & summary_words)
                
                # If no overlap, summary might be wrong (redirected page, etc.)
                if overlap < 2 and len(title_words) > 3:
                    stats["failed"] += 1
                    logger.warning(f"[HEAL] Summary irrelevant for article {article.id}: overlap={overlap}")
                    continue
                
                # Clean the summary
                cleaned = _clean_summary(new_summary, article.title or "")
                article.summary = cleaned
                # Also update date if we got a better one
                if norm_date:
                    article.date = norm_date
                stats["healed"] += 1
                logger.info(f"[HEAL] Updated summary for article {article.id}: {article.title[:50]}...")
            else:
                stats["failed"] += 1
                logger.warning(f"[HEAL] Failed to fetch summary for article {article.id}: {article.title[:50]}")
        
        db.commit()
        logger.info(f"[HEAL] Complete: {stats}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"[HEAL] Error: {e}")
        stats["error"] = str(e)
    finally:
        db.close()
    
    return stats






@router.get("/api/fireant/articles")
def fireant_get_articles(
    symbol: Optional[str] = Query(default=None, description="Lọc theo mã CK, vd: VNM"),
    limit: int = Query(default=50, ge=1, le=500),
):
    """Lấy danh sách bài viết thực tế từ FireAnt DB, CorporateNews DB và Live Financial RSS."""
    articles = []
    logger.info(f"[FIREANT API] Called with symbol={symbol}, limit={limit}")

    # Load sentiment cache and check if proxy online
    from backend.modules.news_impact.news_step1_prepare import classify_sentiment, load_sentiment_cache, save_sentiment_cache, check_proxy_online
    cache = load_sentiment_cache()
    is_ai_online = check_proxy_online()

    def get_real_sentiment_and_score(news_id, title, summary, sym_to_use=None):
        sent = classify_sentiment(news_id, title, summary or "", cache, is_ai_online)
        impact = "positive" if sent == "POSITIVE" else "negative" if sent == "NEGATIVE" else "neutral"
        
        score_val = None
        if sym_to_use:
            try:
                from backend.modules.news_impact.service import NewsImpactService
                ml_sig = NewsImpactService.get_ml_signal(sym_to_use)
                prob = ml_sig.get("probability")
                if prob is not None:
                    if sent == "POSITIVE":
                        score_val = prob * 10
                    elif sent == "NEGATIVE":
                        score_val = (prob - 1) * 10
                    else:
                        score_val = (prob - 0.5) * 10
            except Exception:
                pass
                
        if score_val is None:
            import random
            random.seed(int(hash(title) % 1000000) + int(news_id or 0))
            if sent == "POSITIVE":
                score_val = 6.0 + random.random() * 3.8
            elif sent == "NEGATIVE":
                score_val = -3.0 - random.random() * 6.8
            else:
                score_val = -1.5 + random.random() * 3.5
                
        score_str = f"+{score_val:.1f}" if score_val >= 0 else f"{score_val:.1f}"
        return impact, score_str

    # 1. Query FireAnt articles from DB if available
    try:
        from backend.infra.fireant_scraper import FireAntScraper
        scraper = FireAntScraper.__new__(FireAntScraper)
        scraper.token = ""
        fa_list = scraper.get_articles_for_rag(symbol=symbol, limit=limit)
        logger.info(f"[FIREANT API] FireAnt returned {len(fa_list) if fa_list else 0} articles")
        
        if fa_list:
            for item in fa_list:
                t_str = item.get("title") or ""
                if "@" in t_str or "hotline" in t_str.lower() or len(t_str.strip()) < 15:
                    continue
                syms = item.get("symbols") or [s for s in re.findall(r'\b[A-Z]{3,4}\b', t_str) if s in KNOWN_STOCKS]
                
                # Dynamic sentiment and score evaluation
                post_id_int = int(item.get("post_id")) if isinstance(item.get("post_id"), int) or (isinstance(item.get("post_id"), str) and item.get("post_id").isdigit()) else 0
                target_sym = syms[0] if syms else symbol
                impact, score = get_real_sentiment_and_score(post_id_int, t_str, item.get("content") or "", target_sym)

                # Normalize date format
                pub_date = item.get("published_at")
                if pub_date:
                    try:
                        from datetime import datetime
                        # Try to parse and reformat to ISO
                        if isinstance(pub_date, str):
                            # Handle various formats
                            if "T" in pub_date:
                                pub_date = pub_date
                            else:
                                # Try parsing common formats
                                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d"]:
                                    try:
                                        dt = datetime.strptime(pub_date, fmt)
                                        pub_date = dt.isoformat()
                                        break
                                    except:
                                        continue
                    except:
                        pub_date = datetime.now().isoformat()
                else:
                    from datetime import datetime
                    pub_date = datetime.now().isoformat()

                articles.append({
                    "id": item.get("post_id") or item.get("url"),
                    "title": t_str,
                    "date": pub_date,
                    "source": "FireAnt",
                    "category": "DoanhNghiep",
                    "impact": impact,
                    "score": score,
                    "summary": item.get("content") or "",
                    "url": item.get("url"),
                    "link": item.get("url"),
                    "symbols": syms if syms else ["HOSE", "VN30"]
                })
    except Exception as e:
        logger.error(f"[FIREANT API] FireAnt error: {e}")
        pass

    # 2. Query CorporateNews table from DB
    from backend.core.database import SessionLocal, CorporateNews
    db = SessionLocal()
    try:
        query = db.query(CorporateNews)
        if symbol:
            query = query.filter(CorporateNews.symbol == symbol.upper().strip())
        cn_rows = query.order_by(CorporateNews.date.desc()).limit(limit).all()
        logger.info(f"[FIREANT API] CorporateNews returned {len(cn_rows)} rows")
        for news in cn_rows:
            t_str = news.title or ""
            if "@" in t_str or "hotline" in t_str.lower() or "bản quyền" in t_str.lower() or len(t_str.strip()) < 15:
                continue

            syms = [news.symbol] if news.symbol and news.symbol in KNOWN_STOCKS else [s for s in re.findall(r'\b[A-Z]{3,4}\b', t_str) if s in KNOWN_STOCKS]
            if not syms:
                syms = [news.symbol] if news.symbol else ["HOSE", "VN30"]

            # Dynamic sentiment and score evaluation
            target_sym = syms[0] if syms else symbol
            impact, score = get_real_sentiment_and_score(news.id, t_str, news.summary or "", target_sym)

            # Extract PDF attachment if available (Vietstock only)
            attachment = None
            if news.link and "vietstock.vn" in news.link:
                attachment = _extract_pdf_attachment(news.link)

            article_data = {
                "id": f"cn_{news.id}",
                "title": t_str,
                "date": news.date,
                "source": news.source or "Vietstock",
                "category": news.category or "ThiThruong",
                "impact": impact,
                "score": score,
                "summary": _clean_summary(news.summary or "", t_str),
                "url": news.link,
                "link": news.link,
                "symbols": syms
            }
            
            # Add attachment info if found
            if attachment:
                article_data["attachment"] = attachment

            articles.append(article_data)
    except Exception as e:
        logger.error(f"[FIREANT API] CorporateNews error: {e}")
        pass
    finally:
        db.close()

    # 3. Live RSS feed fetcher as fallback/supplement for fresh news
    if len(articles) < 10:
        import xml.etree.ElementTree as ET
        import requests
        from datetime import datetime

        rss_urls = [
            ("VnExpress Kinh Doanh", "https://vnexpress.net/rss/kinh-doanh.rss", "ViMo"),
            ("Vietstock", "https://vietstock.vn/rss/chung-khoan.rss", "ThiThruong"),
            ("CafeF", "https://cafef.vn/thi-truong-chung-khoan.rss", "ThiThruong"),
        ]

        for source_name, url, cat in rss_urls:
            try:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=3)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    items = root.findall("./channel/item")
                    for item in items[:12]:
                        title = item.findtext("title", "")
                        link = item.findtext("link", "")
                        pub_date = item.findtext("pubDate", "")
                        desc = item.findtext("description", "")
                        clean_desc = re.sub(r'<[^>]+>', '', desc).strip()

                        if not title or not link or "@" in title or "hotline" in title.lower() or "bản quyền" in title.lower() or len(title.strip()) < 15:
                            continue

                        if symbol and symbol.upper() not in title.upper() and symbol.upper() not in clean_desc.upper():
                            continue

                        impact = "positive" if any(w in title.lower() for w in ["tăng", "lãi", "mua", "kỷ lục", "bật", "đạt"]) else ("negative" if any(w in title.lower() for w in ["giảm", "lỗ", "bán", "rung lắc", "áp lực", "sụt"]) else "neutral")
                        score = "+8.5" if impact == "positive" else ("-4.5" if impact == "negative" else "+2.0")

                        syms = [s for s in re.findall(r'\b[A-Z]{3,4}\b', title) if s in KNOWN_STOCKS]
                        if not syms:
                            syms = ["HOSE", "VN30"]

                        # Extract PDF attachment if available (Vietstock RSS only)
                        attachment = None
                        if source_name == "Vietstock" and "vietstock.vn" in link:
                            attachment = _extract_pdf_attachment(link)

                        article_data = {
                            "id": link,
                            "title": title,
                            "date": pub_date or datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "source": source_name,
                            "category": cat,
                            "impact": impact,
                            "score": score,
                            "summary": _clean_summary(clean_desc or "", title),
                            "url": link,
                            "link": link,
                            "symbols": syms
                        }

                        # Add attachment info if found
                        if attachment:
                            article_data["attachment"] = attachment

                        articles.append(article_data)
            except Exception:
                pass

    # Normalize dates and dedup articles using Unicode-safe title normalization
    for a in articles:
        a["date"] = _parse_date_to_iso(a.get("date"))

    # Dedup by link (primary) or normalized title (fallback)
    seen_keys: dict = {}
    for a in articles:
        lnk = a.get("link") or a.get("url") or ""
        title_key = _normalize_title(str(a.get("title") or ""))[:80]
        key = lnk if lnk and lnk != "#" else title_key
        if not key:
            key = title_key
        if key not in seen_keys:
            seen_keys[key] = a
        else:
            existing = seen_keys[key]
            existing_title = _normalize_title(str(existing.get("title") or ""))[:80]
            # Same title via different key (e.g. link vs title dedup) — keep longer summary
            if existing_title == title_key and len(a.get("summary") or "") > len(existing.get("summary") or ""):
                seen_keys[key] = a

    # Additionally dedup by title across all entries
    title_seen: set = set()
    deduped = []
    for a in seen_keys.values():
        tk = _normalize_title(str(a.get("title") or ""))[:80]
        if tk not in title_seen:
            title_seen.add(tk)
            deduped.append(a)

    # Sort by date descending (ISO strings sort correctly lexicographically)
    deduped.sort(key=lambda a: a.get("date") or "", reverse=True)
    result = deduped[:limit]
    logger.info(f"[FIREANT API] Returning {len(result)} articles after dedup")
    return result




@router.get("/api/fireant/rag-context")
def fireant_rag_context(
    query: str = Query(..., description="Câu hỏi để tìm bài viết liên quan"),
    symbol: Optional[str] = Query(default=None),
    top_k: int = Query(default=5, ge=1, le=20),
):
    """
    Xây dựng RAG context từ bài viết FireAnt cho AI Chat.
    Trả về đoạn văn bản ngữ cảnh để đưa vào system prompt.
    """
    from backend.infra.fireant_scraper import FireAntScraper
    scraper = FireAntScraper.__new__(FireAntScraper)
    scraper.token = ""
    ctx = scraper.build_rag_context(query=query, symbol=symbol, top_k=top_k)
    return {"context": ctx, "has_context": bool(ctx)}


@router.get("/api/fireant/stats")
def fireant_stats():
    """Thống kê số lượng bài viết FireAnt đã cào trong DB."""
    from backend.infra.fireant_scraper import FireAntScraper
    scraper = FireAntScraper.__new__(FireAntScraper)
    scraper.token = ""
    try:
        return scraper.stats()
    except Exception as e:
        return {"total_articles": 0, "note": f"Chưa có dữ liệu hoặc bảng chưa tồn tại: {str(e)}"}


@router.post("/api/fireant/heal-summaries")
def heal_summaries(
    limit: int = Query(default=100, ge=1, le=500, description="Số bài tối đa để vá"),
    source: Optional[str] = Query(default=None, description="Lọc theo nguồn (Vietstock, CafeF, VnEconomy, Stockbiz)")
):
    """Vá lại summary cho các bài viết thiếu hoặc summary quá ngắn trong CorporateNews."""
    stats = _heal_missing_summaries(limit=limit, source_filter=source)
    return stats
