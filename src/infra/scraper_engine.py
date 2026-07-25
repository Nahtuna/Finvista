# -*- coding: utf-8 -*-
"""
⚡ FINVISTA: INCREMENTAL SCRAPER ENGINE
========================================
Async parallel data scraper with:
  - Incremental fetching (only new data since last run)
  - SQLAlchemy Upsert (on_conflict_do_update) for dedup safety
  - asyncio.Semaphore for rate-limit-safe parallel fetching
  - ScraperState tracking (hash, last_date, error_count)
  - Change detection: skip if data hash unchanged

Usage:
    from src.infra.scraper_engine import ScraperEngine
    engine = ScraperEngine()
    asyncio.run(engine.run_ohlcv_incremental(tickers=["VNM", "HPG"]))

Author: samvo
"""

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ─── Concurrency config ───────────────────────────────────────────────────────
DEFAULT_SEMAPHORE  = 8   # Số request đồng thời tối đa (tránh bị ban)
RETRY_MAX          = 3   # Số lần retry khi gặp lỗi
RETRY_BACKOFF_BASE = 2.0 # Exponential backoff base (seconds)


class ScraperEngine:
    """
    Incremental async scraper engine.
    Quản lý trạng thái cào qua bảng `scraper_state` trong SQLite.
    """

    def __init__(self, semaphore_limit: int = DEFAULT_SEMAPHORE):
        self.sem = asyncio.Semaphore(semaphore_limit)

    # ──────────────────────────────────────────────────────────────────────────
    # STATE HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _get_state(self, db, ticker: str, scraper_type: str):
        """Lấy hoặc tạo ScraperState record cho ticker + type."""
        from src.core.database import ScraperState
        state = db.query(ScraperState).filter_by(
            ticker=ticker, scraper_type=scraper_type
        ).first()
        if not state:
            state = ScraperState(ticker=ticker, scraper_type=scraper_type)
            db.add(state)
            db.flush()
        return state

    def _compute_hash(self, data: Any) -> str:
        """MD5 hash của data để phát hiện thay đổi."""
        raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        return hashlib.md5(raw).hexdigest()

    def _update_state_success(
        self, db, state, records_new: int, last_date: Optional[str] = None,
        data_hash: Optional[str] = None, records_total: Optional[int] = None
    ):
        """Cập nhật ScraperState sau khi cào thành công."""
        state.last_scraped_at = datetime.now(timezone.utc)
        state.records_new_last_run = records_new
        state.error_count = 0
        state.last_error = None
        if last_date:
            state.last_record_date = last_date
        if data_hash:
            state.data_hash = data_hash
        if records_total is not None:
            state.records_total = records_total
        db.commit()

    def _update_state_error(self, db, state, error_msg: str):
        """Cập nhật ScraperState khi gặp lỗi."""
        state.error_count = (state.error_count or 0) + 1
        state.last_error = str(error_msg)[:500]
        db.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # OHLCV INCREMENTAL SCRAPER (Giá lịch sử Cổ phiếu / CW)
    # ──────────────────────────────────────────────────────────────────────────

    async def scrape_ohlcv_one(
        self, ticker: str, is_cw: bool = False
    ) -> Dict[str, Any]:
        """
        Cào OHLCV incremental cho 1 ticker.
        Chỉ fetch từ (last_record_date + 1 ngày) đến hôm nay.
        """
        async with self.sem:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._scrape_ohlcv_sync, ticker, is_cw
            )

    def _scrape_ohlcv_sync(self, ticker: str, is_cw: bool) -> Dict[str, Any]:
        """Sync implementation chạy trong thread executor."""
        from src.core.database import SessionLocal, StockHistoricalPrice, CWHistoricalPrice
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        from sqlalchemy import func

        db = SessionLocal()
        try:
            scraper_type = "ohlcv_cw" if is_cw else "ohlcv_stock"
            TableModel = CWHistoricalPrice if is_cw else StockHistoricalPrice
            state = self._get_state(db, ticker, scraper_type)

            # Xác định start_date: từ last_record_date + 1 ngày
            if state.last_record_date:
                try:
                    last_dt = datetime.strptime(state.last_record_date, "%Y-%m-%d")
                    start_date = (last_dt + timedelta(days=1)).strftime("%Y-%m-%d")
                except ValueError:
                    start_date = "2020-01-01"
            else:
                # Không có data nào → query DB để lấy MAX(date)
                max_date = db.query(func.max(TableModel.date)).filter(
                    TableModel.symbol == ticker
                ).scalar()
                if max_date:
                    try:
                        last_dt = datetime.strptime(max_date, "%Y-%m-%d")
                        start_date = (last_dt + timedelta(days=1)).strftime("%Y-%m-%d")
                    except ValueError:
                        start_date = "2020-01-01"
                else:
                    start_date = "2020-01-01"

            end_date = datetime.now().strftime("%Y-%m-%d")

            # Skip nếu đã up-to-date
            if start_date > end_date:
                return {"ticker": ticker, "status": "up_to_date", "records_new": 0}

            # Fetch data từ vnstock
            records = self._fetch_ohlcv_vnstock(ticker, start_date, end_date, is_cw)
            if not records:
                return {"ticker": ticker, "status": "no_new_data", "records_new": 0}

            # Change detection: skip nếu hash không đổi
            new_hash = self._compute_hash(records)
            if new_hash == state.data_hash and len(records) == 0:
                return {"ticker": ticker, "status": "unchanged", "records_new": 0}

            # Upsert records (safe khi chạy song song)
            inserted = 0
            for rec in records:
                stmt = sqlite_insert(TableModel).values(
                    symbol=ticker,
                    date=rec["date"],
                    open=rec.get("open"),
                    high=rec.get("high"),
                    low=rec.get("low"),
                    close=rec.get("close"),
                    volume=rec.get("volume"),
                    ref_price=rec.get("ref_price"),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "date"] if hasattr(TableModel, "symbol") else ["id"],
                    set_={
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                    }
                )
                db.execute(stmt)
                inserted += 1
            db.commit()

            # Cập nhật state
            last_date_inserted = records[-1]["date"] if records else end_date
            total = db.query(TableModel).filter(TableModel.symbol == ticker).count()
            self._update_state_success(
                db, state,
                records_new=inserted,
                last_date=last_date_inserted,
                data_hash=new_hash,
                records_total=total
            )
            return {"ticker": ticker, "status": "success", "records_new": inserted}

        except Exception as e:
            state = self._get_state(db, ticker, "ohlcv_cw" if is_cw else "ohlcv_stock")
            self._update_state_error(db, state, str(e))
            return {"ticker": ticker, "status": "error", "error": str(e)}
        finally:
            db.close()

    def _fetch_ohlcv_vnstock(
        self, ticker: str, start_date: str, end_date: str, is_cw: bool
    ) -> List[Dict]:
        """Fetch OHLCV từ vnstock (sync). Trả về list of dicts."""
        try:
            from vnstock import Vnstock
            stock = Vnstock().stock(symbol=ticker, source="VCI")
            df = stock.quote.history(
                start=start_date,
                end=end_date,
                interval="1D"
            )
            if df is None or df.empty:
                return []
            records = []
            for _, row in df.iterrows():
                try:
                    records.append({
                        "date": str(row.get("time", row.get("date", "")))[:10],
                        "open": float(row.get("open", 0) or 0),
                        "high": float(row.get("high", 0) or 0),
                        "low": float(row.get("low", 0) or 0),
                        "close": float(row.get("close", 0) or 0),
                        "volume": float(row.get("volume", 0) or 0),
                        "ref_price": float(row.get("reference", row.get("ref", 0)) or 0),
                    })
                except Exception:
                    continue
            return records
        except Exception as e:
            print(f"   [ScraperEngine] OHLCV fetch error for {ticker}: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # BATCH RUNNER
    # ──────────────────────────────────────────────────────────────────────────

    async def run_ohlcv_incremental(
        self,
        tickers: Optional[List[str]] = None,
        is_cw: bool = False,
        max_error_skip: int = 5,
    ) -> Dict[str, Any]:
        """
        Chạy incremental OHLCV cho danh sách ticker (async parallel).
        Tự động bỏ qua ticker có error_count > max_error_skip.
        """
        if tickers is None:
            tickers = self._get_all_tickers(is_cw)

        # Lọc bỏ ticker bị lỗi nhiều lần liên tiếp
        filtered = self._filter_error_tickers(tickers, "ohlcv_cw" if is_cw else "ohlcv_stock", max_error_skip)
        skipped = len(tickers) - len(filtered)

        print(f"⚡ [ScraperEngine] OHLCV Incremental: {len(filtered)} tickers "
              f"({skipped} skipped due to repeated errors)")

        start_time = datetime.now()
        tasks = [self.scrape_ohlcv_one(ticker, is_cw) for ticker in filtered]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        summary = {
            "total": len(filtered),
            "success": 0,
            "up_to_date": 0,
            "no_new_data": 0,
            "unchanged": 0,
            "error": 0,
            "records_new_total": 0,
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "skipped_error_tickers": skipped,
        }
        for r in results:
            if isinstance(r, Exception):
                summary["error"] += 1
            else:
                status = r.get("status", "error")
                summary[status] = summary.get(status, 0) + 1
                summary["records_new_total"] += r.get("records_new", 0)

        print(f"✅ [ScraperEngine] Done in {summary['duration_seconds']:.1f}s — "
              f"Success: {summary['success']}, New records: {summary['records_new_total']}, "
              f"Up-to-date: {summary['up_to_date']}, Errors: {summary['error']}")
        return summary

    # ──────────────────────────────────────────────────────────────────────────
    # NEWS INCREMENTAL SCRAPER
    # ──────────────────────────────────────────────────────────────────────────

    async def run_news_incremental(
        self, tickers: Optional[List[str]] = None, max_per_ticker: int = 30
    ) -> Dict[str, Any]:
        """
        Cào tin tức incremental: chỉ fetch tin mới hơn tin cuối đã có trong DB.
        Sử dụng CorporateNews.link (unique) làm dedup key.
        """
        if tickers is None:
            tickers = self._get_all_tickers(is_cw=False)

        print(f"📰 [ScraperEngine] News Incremental: {len(tickers)} tickers")
        start_time = datetime.now()
        tasks = [self._scrape_news_one(ticker, max_per_ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        summary = {"total": len(tickers), "success": 0, "error": 0,
                   "records_new_total": 0,
                   "duration_seconds": (datetime.now() - start_time).total_seconds()}
        for r in results:
            if isinstance(r, Exception):
                summary["error"] += 1
            else:
                summary[r.get("status", "error")] = summary.get(r.get("status", "error"), 0) + 1
                summary["records_new_total"] += r.get("records_new", 0)
        return summary

    async def _scrape_news_one(self, ticker: str, max_per_ticker: int) -> Dict:
        async with self.sem:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._scrape_news_sync, ticker, max_per_ticker
            )

    def _scrape_news_sync(self, ticker: str, max_per_ticker: int) -> Dict:
        from src.core.database import SessionLocal, CorporateNews
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        db = SessionLocal()
        try:
            state = self._get_state(db, ticker, "news")
            # Lấy tập link đã có để dedup
            existing_links = {
                r[0] for r in db.query(CorporateNews.link).filter(
                    CorporateNews.symbol == ticker
                ).all()
            }
            # Fetch news (dùng WarrantService nếu có)
            new_items = self._fetch_news_for_ticker(ticker, max_per_ticker)
            inserted = 0
            for item in new_items:
                if item.get("link") in existing_links:
                    continue
                try:
                    stmt = sqlite_insert(CorporateNews).values(
                        symbol=ticker,
                        title=item.get("title", ""),
                        link=item.get("link", ""),
                        date=item.get("date", ""),
                        source=item.get("source", "Vietstock"),
                        summary=item.get("summary", ""),
                        category=item.get("category", ""),
                    ).on_conflict_do_nothing(index_elements=["link"])
                    db.execute(stmt)
                    inserted += 1
                except Exception:
                    continue
            db.commit()
            self._update_state_success(db, state, records_new=inserted)
            return {"ticker": ticker, "status": "success", "records_new": inserted}
        except Exception as e:
            state = self._get_state(db, ticker, "news")
            self._update_state_error(db, state, str(e))
            return {"ticker": ticker, "status": "error", "error": str(e)}
        finally:
            db.close()

    def _fetch_news_for_ticker(self, ticker: str, limit: int) -> List[Dict]:
        """Fetch news từ WarrantService nếu có, fallback trả về []."""
        try:
            from src.modules.cw_pricing.service import WarrantService
            res = WarrantService.get_news(symbol=ticker, limit=limit)
            return res.get("news", [])
        except Exception:
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # STATUS DASHBOARD
    # ──────────────────────────────────────────────────────────────────────────

    def get_status_report(
        self, scraper_type: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Trả về báo cáo trạng thái cào cho /api/admin/scraper/status.
        """
        from src.core.database import SessionLocal, ScraperState

        db = SessionLocal()
        try:
            query = db.query(ScraperState)
            if scraper_type:
                query = query.filter(ScraperState.scraper_type == scraper_type)
            states = query.order_by(
                ScraperState.scraper_type,
                ScraperState.updated_at.desc()
            ).limit(limit).all()

            rows = []
            for s in states:
                rows.append({
                    "ticker": s.ticker,
                    "scraper_type": s.scraper_type,
                    "last_scraped_at": s.last_scraped_at.isoformat() if s.last_scraped_at else None,
                    "last_record_date": s.last_record_date,
                    "records_total": s.records_total,
                    "records_new_last_run": s.records_new_last_run,
                    "error_count": s.error_count,
                    "last_error": s.last_error,
                    "status": "ERROR" if (s.error_count or 0) >= 3 else
                              ("WARNING" if (s.error_count or 0) >= 1 else "OK"),
                })

            summary = {
                "total_tickers": len(rows),
                "ok": sum(1 for r in rows if r["status"] == "OK"),
                "warning": sum(1 for r in rows if r["status"] == "WARNING"),
                "error": sum(1 for r in rows if r["status"] == "ERROR"),
                "total_records_new_last_run": sum(r["records_new_last_run"] or 0 for r in rows),
            }
            return {"summary": summary, "states": rows}
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # UTILITY HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _get_all_tickers(self, is_cw: bool = False) -> List[str]:
        """Lấy danh sách tất cả ticker từ DB."""
        from src.core.database import SessionLocal, StockHistoricalPrice, MarketOpportunity
        db = SessionLocal()
        try:
            if is_cw:
                results = db.query(MarketOpportunity.symbol).distinct().all()
            else:
                results = db.query(StockHistoricalPrice.symbol).distinct().all()
            return [r[0] for r in results if r[0]]
        except Exception:
            return []
        finally:
            db.close()

    def _filter_error_tickers(
        self, tickers: List[str], scraper_type: str, max_errors: int
    ) -> List[str]:
        """Lọc bỏ ticker bị lỗi quá nhiều lần."""
        from src.core.database import SessionLocal, ScraperState
        db = SessionLocal()
        try:
            error_tickers = {
                r[0] for r in db.query(ScraperState.ticker).filter(
                    ScraperState.scraper_type == scraper_type,
                    ScraperState.error_count >= max_errors
                ).all()
            }
            return [t for t in tickers if t not in error_tickers]
        except Exception:
            return tickers
        finally:
            db.close()


# ─── Singleton ────────────────────────────────────────────────────────────────
_engine: Optional[ScraperEngine] = None

def get_scraper_engine() -> ScraperEngine:
    global _engine
    if _engine is None:
        _engine = ScraperEngine()
    return _engine
