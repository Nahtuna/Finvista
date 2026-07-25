# -*- coding: utf-8 -*-
"""
FINVISTA: FIREANT ROUTES — Scraper API + RAG context builder
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional
from pydantic import BaseModel

router = APIRouter(tags=["fireant"])


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


@router.get("/api/fireant/articles")
def fireant_get_articles(
    symbol: Optional[str] = Query(default=None, description="Lọc theo mã CK, vd: VNM"),
    limit: int = Query(default=50, ge=1, le=500),
):
    """Lấy danh sách bài viết thực tế từ FireAnt DB, CorporateNews DB và Live Financial RSS."""
    import re
    KNOWN_STOCKS = {"DGC", "HDB", "MBB", "ACB", "MSN", "MWG", "VPB", "VIB", "HPG", "FPT", "VIC", "VHM", "VRE", "SSI", "VND", "VCI", "HCM", "SHB", "LPB", "STB", "TCB", "CTG", "BID", "VCB", "GAS", "POW", "PVD", "PVS", "BSR", "DIG", "NVL", "PDR", "NLG", "KDH", "DXG"}
    articles = []
    
    # 1. Query FireAnt articles from DB if available
    try:
        from src.infra.fireant_scraper import FireAntScraper
        scraper = FireAntScraper.__new__(FireAntScraper)
        scraper.token = ""
        fa_list = scraper.get_articles_for_rag(symbol=symbol, limit=limit)
        if fa_list:
            for item in fa_list:
                t_str = item.get("title") or ""
                if "@" in t_str or "hotline" in t_str.lower() or len(t_str.strip()) < 15:
                    continue
                syms = item.get("symbols") or [s for s in re.findall(r'\b[A-Z]{3,4}\b', t_str) if s in KNOWN_STOCKS]
                articles.append({
                    "id": item.get("post_id") or item.get("url"),
                    "title": t_str,
                    "date": item.get("published_at"),
                    "source": "FireAnt",
                    "category": "DoanhNghiep",
                    "impact": "positive" if any(w in t_str.lower() for w in ["tăng", "lãi", "mua", "kỷ lục", "đạt"]) else "neutral",
                    "score": "+6.5",
                    "summary": (item.get("content") or "")[:200],
                    "url": item.get("url"),
                    "link": item.get("url"),
                    "symbols": syms if syms else ["HOSE", "VN30"]
                })
    except Exception:
        pass

    # 2. Query CorporateNews table from DB
    from src.core.database import SessionLocal, CorporateNews
    db = SessionLocal()
    try:
        query = db.query(CorporateNews)
        if symbol:
            query = query.filter(CorporateNews.symbol == symbol.upper().strip())
        cn_rows = query.order_by(CorporateNews.date.desc()).limit(limit).all()
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
                "summary": news.summary or t_str,
                "url": news.link,
                "link": news.link,
                "symbols": syms
            })
    except Exception:
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
                        
                        # Filter out junk titles or contact info
                        if not title or not link or "@" in title or "hotline" in title.lower() or "bản quyền" in title.lower() or len(title.strip()) < 15:
                            continue

                        # Filter by symbol if specified
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
                            "summary": clean_desc[:250] if clean_desc else title,
                            "url": link,
                            "link": link,
                            "symbols": syms
                        })
            except Exception:
                pass

    return articles[:limit]


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
