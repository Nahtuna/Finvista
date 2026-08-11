# -*- coding: utf-8 -*-
"""
FINVISTA: NEWS IMPACT ROUTES — dual-layer pipeline API
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging
from backend.modules.news_impact.service import NewsImpactService
from backend.core.database import SessionLocal, CorporateNews

router = APIRouter(tags=["news-impact"])
logger = logging.getLogger(__name__)


@router.get("/api/news-impact/daily-brief")
def get_daily_brief(date: Optional[str] = Query(default=None)):
    """Tổng hợp tin tức vĩ mô và doanh nghiệp nổi bật trong ngày dạng bản tin vắn tắt AI (SSI Style)."""
    db = SessionLocal()
    try:
        # Get latest news, filtering out corrupt entries containing email or hotline keywords
        records = (
            db.query(CorporateNews)
            .filter(
                CorporateNews.title.notlike("%@%"),
                CorporateNews.date.notlike("%Hotline%"),
                CorporateNews.date.notlike("%@%")
            )
            .order_by(CorporateNews.date.desc())
            .limit(40)
            .all()
        )
        if not records:
            return {"macro_brief": [], "corp_brief": []}
            
        from backend.modules.news_impact.news_step1_prepare import check_proxy_online
        is_ai_online = check_proxy_online()
        
        if is_ai_online:
            # Rule-based news grouping (không phụ thuộc AI)
            try:
                # Dedup before grouping
                seen_titles = set()
                deduped_records = []
                for r in records:
                    norm_title = r.title.strip().lower().replace(" ", "")
                    if norm_title not in seen_titles:
                        seen_titles.add(norm_title)
                        deduped_records.append(r)
                
                # Group news into macro vs corporate using keywords
                macro_keywords = ["tỷ giá", "lãi suất", "chính sách", "thế giới", "kinh tế", "vĩ mô", "usd", "vnd", "chỉ số", "thị trường", "fed", "ngân hàng trung ương"]
                macro_brief = []
                corp_brief = []
                
                for r in deduped_records[:20]:
                    title = r.title or ""
                    summary = r.summary or ""
                    symbol = r.symbol or ""
                    
                    # Determine if macro or corporate
                    is_macro = any(kw in title.lower() or kw in summary.lower() for kw in macro_keywords)
                    
                    if is_macro:
                        macro_brief.append(f"- {title}")
                    else:
                        if symbol:
                            corp_brief.append(f"- [{symbol}](detail:{symbol}) {title}")
                        else:
                            corp_brief.append(f"- {title}")
                
                # Limit to 3-5 items per group
                macro_brief = macro_brief[:5]
                corp_brief = corp_brief[:5]
                
                return {
                    "macro_brief": macro_brief,
                    "corp_brief": corp_brief
                }
            except Exception as e:
                logger.error(f"Failed to generate daily brief with rule-based: {e}")
                
        # Fallback manual extraction if rule-based fails (with title deduplication)
        macro = []
        corp = []
        seen_titles = set()
        for r in records:
            title_clean = r.title.strip()
            norm_title = title_clean.lower().replace(" ", "")
            if norm_title in seen_titles:
                continue
            seen_titles.add(norm_title)
            
            if not r.symbol or r.symbol in ["HOSE", "VN30", "MARKET", "VNINDEX"]:
                macro.append(title_clean)
            else:
                corp.append(f"[{r.symbol}](detail:{r.symbol}): {title_clean}")
        return {"macro_brief": macro[:5], "corp_brief": corp[:5]}
    finally:
        db.close()


@router.get("/api/news-impact/sector-brief")
def get_sector_brief():
    """Tính toán chỉ số cảm xúc nhóm ngành (Sector Sentiment Index) từ tin tức thực tế."""
    db = SessionLocal()
    try:
        from backend.core.database import CompanyDistressAnalysis
        records = db.query(CorporateNews).order_by(CorporateNews.date.desc()).limit(40).all()
        if not records:
            return {"sectors": []}
            
        # Get sectors for tickers
        ticker_sectors = {}
        tickers = {r.symbol for r in records if r.symbol and isinstance(r.symbol, str) and len(r.symbol) in [3, 4]}
        if tickers:
            analyses = db.query(CompanyDistressAnalysis).filter(CompanyDistressAnalysis.ticker.in_(list(tickers))).all()
            for a in analyses:
                if a.industry:
                    ticker_sectors[a.ticker] = a.industry
                    
        from backend.modules.news_impact.news_step1_prepare import load_sentiment_cache
        cache = load_sentiment_cache()
        
        sector_stats = {}
        for r in records:
            sec = ticker_sectors.get(r.symbol, "Khác")
            if sec == "Khác" and r.symbol in ["HOSE", "VN30", "MARKET", "VNINDEX"]:
                sec = "Tài chính & Thị trường"
            
            sent = cache.get(str(r.id), "NEUTRAL")
            if sec not in sector_stats:
                sector_stats[sec] = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
            sector_stats[sec]["total"] += 1
            sector_stats[sec][sent.lower()] += 1
            
        sectors_res = []
        for sec, stats in sector_stats.items():
            total = max(stats["total"], 1)
            pos_ratio = round(stats["positive"] / total * 100)
            neg_ratio = round(stats["negative"] / total * 100)
            
            desc = f"Nhóm ngành {sec} đang có tin tức giao dịch ổn định."
            if pos_ratio > 50:
                desc = f"Nhóm ngành {sec} đón nhận nhiều luồng thông tin tích cực."
            elif neg_ratio > 50:
                desc = f"Nhóm ngành {sec} chịu áp lực điều chỉnh ngắn hạn."
                
            sectors_res.append({
                "sector": sec,
                "positive_pct": pos_ratio,
                "negative_pct": neg_ratio,
                "neutral_pct": 100 - pos_ratio - neg_ratio,
                "brief": desc
            })
            
        # Return top 4 sectors
        sectors_res.sort(key=lambda x: x["positive_pct"] + x["negative_pct"], reverse=True)
        return {"sectors": sectors_res[:4]}
    finally:
        db.close()


@router.get("/api/news-impact/{ticker}")
def get_news_impact(
    ticker: str,
    days: int = Query(default=90, ge=7, le=365),
    full_pipeline: bool = Query(default=False, description="Chạy pipeline CAR + CW (nặng hơn)"),
):
    return NewsImpactService.get_news_impact(
        ticker=ticker, days=days, run_pipeline=full_pipeline
    )


@router.get("/api/news-impact/{ticker}/pipeline")
def run_pipeline(
    ticker: str,
    event_date: str = Query(default=None, description="YYYY-MM-DD — lọc case study"),
    keyword: str = Query(default=None),
    train_ml: bool = Query(default=False),
):
    """Chạy full dual-layer pipeline B1→B2→B3 cho một mã CPCS."""
    if event_date:
        return NewsImpactService.run_event_study(
            symbol=ticker, event_date=event_date, keyword=keyword
        )
    return NewsImpactService.run_full_pipeline(
        symbol=ticker, keyword=keyword, min_events=1, train_ml=train_ml, skip_report=True
    )


@router.get("/api/news-impact/{ticker}/ml-signal")
def get_news_ml_signal(ticker: str):
    return NewsImpactService.get_ml_signal(ticker=ticker)


@router.get("/api/news-impact/{ticker}/sentiment")
def get_news_sentiment_score(
    ticker: str,
    days: int = Query(default=30, ge=7, le=180),
):
    score = NewsImpactService.get_ticker_sentiment_score(ticker=ticker, days=days)
    label = "BULLISH" if score > 0.1 else "BEARISH" if score < -0.1 else "NEUTRAL"
    return {
        "ticker": ticker.upper().strip(),
        "period_days": days,
        "sentiment_score": score,
        "sentiment_label": label,
    }
