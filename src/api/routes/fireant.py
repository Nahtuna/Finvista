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
from datetime import datetime

router = APIRouter(tags=["fireant"])

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
    from src.infra.fireant_scraper import FireAntScraper
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






@router.get("/api/fireant/articles")
def fireant_get_articles(
    symbol: Optional[str] = Query(default=None, description="Lọc theo mã CK, vd: VNM"),
    limit: int = Query(default=50, ge=1, le=500),
):
    """Lấy danh sách bài viết thực tế từ FireAnt DB, CorporateNews DB và Live Financial RSS."""
    articles = []
    print(f"[FIREANT API] Called with symbol={symbol}, limit={limit}")

    # 1. Query FireAnt articles from DB if available
    try:
        from src.infra.fireant_scraper import FireAntScraper
        scraper = FireAntScraper.__new__(FireAntScraper)
        scraper.token = ""
        fa_list = scraper.get_articles_for_rag(symbol=symbol, limit=limit)
        print(f"[FIREANT API] FireAnt returned {len(fa_list) if fa_list else 0} articles")
        if fa_list:
            for item in fa_list:
                t_str = item.get("title") or ""
                if "@" in t_str or "hotline" in t_str.lower() or len(t_str.strip()) < 15:
                    continue
                syms = item.get("symbols") or [s for s in re.findall(r'\b[A-Z]{3,4}\b', t_str) if s in KNOWN_STOCKS]
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
                    "impact": "positive" if any(w in t_str.lower() for w in ["tăng", "lãi", "mua", "kỷ lục", "đạt"]) else "neutral",
                    "score": "+6.5",
                    "summary": item.get("content") or "",
                    "url": item.get("url"),
                    "link": item.get("url"),
                    "symbols": syms if syms else ["HOSE", "VN30"]
                })
    except Exception as e:
        print(f"[FIREANT API] FireAnt error: {e}")
        pass

    # 2. Query CorporateNews table from DB
    from src.core.database import SessionLocal, CorporateNews
    db = SessionLocal()
    try:
        query = db.query(CorporateNews)
        if symbol:
            query = query.filter(CorporateNews.symbol == symbol.upper().strip())
        cn_rows = query.order_by(CorporateNews.date.desc()).limit(limit).all()
        print(f"[FIREANT API] CorporateNews returned {len(cn_rows)} rows")
        for news in cn_rows:
            t_str = news.title or ""
            if "@" in t_str or "hotline" in t_str.lower() or "bản quyền" in t_str.lower() or len(t_str.strip()) < 15:
                continue

            impact = "positive" if any(w in t_str.lower() for w in ["tăng", "lãi", "mua", "kỷ lục", "vượt", "chấp thuận"]) else ("negative" if any(w in t_str.lower() for w in ["giảm", "lỗ", "khởi tố", "bán", "rung lắc", "áp lực"]) else "neutral")
            score = "+8.5" if impact == "positive" else ("-4.5" if impact == "negative" else "+2.0")

            syms = [news.symbol] if news.symbol and news.symbol in KNOWN_STOCKS else [s for s in re.findall(r'\b[A-Z]{3,4}\b', t_str) if s in KNOWN_STOCKS]
            if not syms:
                syms = [news.symbol] if news.symbol else ["HOSE", "VN30"]

            articles.append({
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
            })
    except Exception as e:
        print(f"[FIREANT API] CorporateNews error: {e}")
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

                        articles.append({
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
                        })
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
    print(f"[FIREANT API] Returning {len(result)} articles after dedup")
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
    from src.infra.fireant_scraper import FireAntScraper
    scraper = FireAntScraper.__new__(FireAntScraper)
    scraper.token = ""
    ctx = scraper.build_rag_context(query=query, symbol=symbol, top_k=top_k)
    return {"context": ctx, "has_context": bool(ctx)}


@router.get("/api/fireant/stats")
def fireant_stats():
    """Thống kê số lượng bài viết FireAnt đã cào trong DB."""
    from src.infra.fireant_scraper import FireAntScraper
    scraper = FireAntScraper.__new__(FireAntScraper)
    scraper.token = ""
    try:
        return scraper.stats()
    except Exception as e:
        return {"total_articles": 0, "note": f"Chưa có dữ liệu hoặc bảng chưa tồn tại: {str(e)}"}
