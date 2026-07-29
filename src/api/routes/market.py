# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: MARKET DATA ROUTES
================================
FastAPI routes for market metadata and underlying stock data.
"""

import requests as _req
from fastapi import APIRouter, Query, BackgroundTasks
from src.modules.cw_pricing.service import WarrantService

router = APIRouter(tags=["market"])


def run_news_scraper_bg():
    try:
        from src.modules.credit_risk.etl.vietstock_scraper import VietstockScraper
        scraper = VietstockScraper()
        # Fetch news for the top 10 underlyings to be fast and avoid rate-limiting
        scraper.run(limit=10)
    except Exception as e:
        import logging
        logging.error(f"Error running background news scraper: {e}")


@router.get("/api/market/metadata")
def get_market_metadata(force_refresh: bool = Query(False)):
    """
    Retrieve market metadata including available underlyings, sectors, and market status.
    """
    try:
        metadata = WarrantService.get_market_metadata(force_refresh=force_refresh)
        return metadata
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve market metadata: {str(e)}"
        }


@router.get("/api/market/underlyings")
def get_underlyings(
    background_tasks: BackgroundTasks,
    news_limit: int = Query(20, ge=1, le=100),
    language: str = Query("en"),
    force_refresh: bool = Query(False)
):
    """
    Retrieve underlying stock data with optional news information.
    """
    if force_refresh:
        background_tasks.add_task(run_news_scraper_bg)
    try:
        data = WarrantService.get_underlyings(
            news_limit=news_limit,
            language=language,
            force_refresh=force_refresh
        )
        return data
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve underlyings: {str(e)}",
            "underlyings": []
        }


@router.get("/api/market/macro")
def get_macro_data():
    """
    Lấy dữ liệu vĩ mô thực: USD/VND, Vàng SJC, Dầu Brent.
    Ưu tiên: Entrade → fallback giá trị gần nhất từ các nguồn công khai.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    result = {}

    # ── 1. USD/VND — Yahoo Finance VND=X ────────────────────────────────────
    try:
        yf_usd = _req.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/VND=X?interval=1d&range=1d",
            headers=headers, timeout=4
        ).json()
        meta = yf_usd["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        if price and price > 0:
            result["usd_vnd"] = {
                "sell": price,
                "buy": price,
                "mid": price,
                "source": "Yahoo Finance"
            }
    except Exception:
        pass

    # ── 2. Vàng SJC — vang.today API ─────────────────────────────────────────
    try:
        vt = _req.get(
            "https://www.vang.today/api/prices",
            headers=headers, timeout=4
        ).json()
        sjc_data = vt.get("prices", {}).get("SJL1L10") or vt.get("prices", {}).get("VNGSJC")
        if sjc_data:
            buy = float(sjc_data.get("buy") or 0) / 1e6
            sell = float(sjc_data.get("sell") or 0) / 1e6
            if sell > 0:
                result["gold_sjc"] = {
                    "sell_m": round(sell, 2),
                    "buy_m":  round(buy, 2),
                    "source": "Vang.today"
                }
    except Exception:
        pass

    # ── 3. Dầu Brent — giá USD/thùng từ Yahoo Finance hoặc Entrade ───────────
    try:
        # Yahoo Finance realtime quote for Brent crude (BZ=F)
        yf = _req.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF"
            "?interval=1d&range=2d",
            headers={**headers, "Accept": "application/json"}, timeout=5
        ).json()
        meta = yf["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
        prev  = meta.get("previousClose") or price
        chg   = round(price - prev, 2)
        pct   = round(chg / prev * 100, 2) if prev else 0
        if price > 0:
            result["brent_oil"] = {
                "price": round(price, 2),
                "change": chg,
                "change_pct": pct,
                "source": "Yahoo Finance"
            }
    except Exception:
        pass

    return {"status": "ok", "data": result}


@router.post("/api/market/refresh-all")
def refresh_all_data(background_tasks: BackgroundTasks):
    """
    Trigger full data refresh including market data, indices, and models.
    Runs in background to avoid blocking the response.
    """
    def run_refresh():
        try:
            from scripts.data_pipelines.refresh_all_realtime import main
            main()
        except Exception as e:
            import logging
            logging.error(f"Error running refresh_all_realtime: {e}")
    
    background_tasks.add_task(run_refresh)
    return {
        "status": "ok",
        "message": "Data refresh started in background",
        "note": "This may take several minutes to complete"
    }

