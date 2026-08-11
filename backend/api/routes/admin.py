# -*- coding: utf-8 -*-
"""
🛡️ FINVISTA: ADMIN API ROUTES
================================
Internal admin endpoints for monitoring scraper status,
triggering manual incremental scrapes, and system diagnostics.

Author: samvo
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/scraper/status")
def scraper_status(
    scraper_type: Optional[str] = Query(None, description="Filter by type: ohlcv_stock, ohlcv_cw, news, financials"),
    limit: int = Query(200, ge=1, le=1000),
):
    """
    📊 Scraper State Dashboard.
    Trả về trạng thái cào incremental cho từng ticker:
    - Lần cào cuối, ngày record cuối, số records mới, error count.
    """
    try:
        from backend.infra.scraper_engine import get_scraper_engine
        engine = get_scraper_engine()
        report = engine.get_status_report(scraper_type=scraper_type, limit=limit)
        return {
            "status": "ok",
            "data": report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraper status error: {str(e)}")


@router.post("/scraper/run/ohlcv")
async def trigger_ohlcv_incremental(
    tickers: Optional[str] = Query(None, description="Comma-separated tickers. Leave empty for all."),
    is_cw: bool = Query(False, description="True to scrape CW price history instead of stock"),
    semaphore: int = Query(8, ge=1, le=20, description="Max concurrent requests"),
):
    """
    ⚡ Trigger incremental OHLCV scraper manually.
    Chỉ cào dữ liệu giá mới hơn ngày cuối đã có trong DB.
    """
    try:
        from backend.infra.scraper_engine import ScraperEngine
        engine = ScraperEngine(semaphore_limit=semaphore)
        ticker_list = [t.strip().upper() for t in tickers.split(",")] if tickers else None
        summary = await engine.run_ohlcv_incremental(tickers=ticker_list, is_cw=is_cw)
        return {
            "status": "completed",
            "message": f"OHLCV incremental scrape finished: {summary['records_new_total']} new records",
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OHLCV scraper error: {str(e)}")


@router.post("/scraper/run/news")
async def trigger_news_incremental(
    tickers: Optional[str] = Query(None, description="Comma-separated tickers. Leave empty for all."),
    max_per_ticker: int = Query(30, ge=1, le=100),
):
    """
    📰 Trigger incremental news scraper manually.
    Chỉ cào tin tức mới (dedup bằng unique link).
    """
    try:
        from backend.infra.scraper_engine import ScraperEngine
        engine = ScraperEngine()
        ticker_list = [t.strip().upper() for t in tickers.split(",")] if tickers else None
        summary = await engine.run_news_incremental(tickers=ticker_list, max_per_ticker=max_per_ticker)
        return {
            "status": "completed",
            "message": f"News incremental scrape finished: {summary.get('records_new_total', 0)} new articles",
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"News scraper error: {str(e)}")


@router.get("/scraper/reset-errors")
def reset_error_ticker(
    ticker: str = Query(..., description="Ticker to reset error count"),
    scraper_type: str = Query("ohlcv_stock", description="Scraper type"),
):
    """
    🔄 Reset error_count về 0 cho 1 ticker cụ thể.
    Cho phép re-scrape các ticker bị skip do lỗi.
    """
    try:
        from backend.core.database import SessionLocal, ScraperState
        db = SessionLocal()
        try:
            state = db.query(ScraperState).filter_by(
                ticker=ticker.upper(), scraper_type=scraper_type
            ).first()
            if not state:
                return {"status": "not_found", "message": f"No state found for {ticker} / {scraper_type}"}
            state.error_count = 0
            state.last_error = None
            db.commit()
            return {"status": "ok", "message": f"Error count reset for {ticker} ({scraper_type})"}
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
