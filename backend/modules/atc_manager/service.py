# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: ATC DATA MANAGER SERVICE
=====================================
Xử lý các nghiệp vụ quản lý dữ liệu giá chốt phiên ATC:
  1. Xác định ngày giao dịch gần nhất (bỏ qua T7, CN, ngày lễ VN)
  2. Sync / crawl dữ liệu ATC (giá đóng phiên) cho STOCK và CW
  3. Kiểm tra độ tươi mới của dữ liệu (data freshness check)
  4. Tự động trigger sync khi dữ liệu cũ/thiếu (startup check)

Author: samvo
Version: 1.0
"""

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any

# === Fix Windows CP1252 console UnicodeEncodeError for emoji prints ===
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Python 3.7+
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    try:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.core.database import (
    SessionLocal,
    ATCSyncLog,
    DataFreshnessState,
    StockHistoricalPrice,
    CWHistoricalPrice,
)
from sqlalchemy import func


# ============================================================
# 1. NGÀY GIAO DỊCH GẦN NHẤT (skip T7, CN, lễ VN)
# ============================================================

_VN_TZ = timezone(timedelta(hours=7))


def _now_vn() -> datetime:
    """Lấy thời gian hiện tại ở múi giờ Việt Nam (UTC+7)."""
    return datetime.now(_VN_TZ)


def get_vn_holidays_set(year: Optional[int] = None) -> set:
    """
    Trả về set gồm các ngày lễ Việt Nam (YYYY-MM-DD string).
    Ưu tiên dùng thư viện `holidays` nếu có sẵn; fallback sang hard-code Tết + ngày lễ cố định.
    """
    target_year = year or _now_vn().year
    holiday_set = set()

    # --- Thử dùng thư viện holidays (chính xác hơn) ---
    try:
        import holidays  # type: ignore
        vn_holidays = holidays.country_holidays("VN", years=target_year)
        for d in vn_holidays.keys():
            holiday_set.add(d.strftime("%Y-%m-%d"))
    except Exception:
        # Fallback: hard-code ngày lễ cố định + Tết (xấp xỉ, đủ để skip weekend & lễ lớn)
        fixed = [
            f"{target_year}-01-01",  # Tết Dương lịch
            f"{target_year}-04-30",  # Giải phóng Miền Nam
            f"{target_year}-05-01",  # Quốc tế Lao động
            f"{target_year}-09-02",  # Quốc khánh
        ]
        holiday_set.update(fixed)
        # Tết Nguyên Đán (ước lượng ~7 ngày quanh tháng 1-2 âm lịch → hard-code khoảng từ Tết đến Hàn)
        # Lưu ý: Thực tế nên dùng thư viện holidays cho chính xác
        # Đoạn này đủ dùng để tránh false-negative nghiêm trọng trong weekend check
        tet_range = [
            # 2025 Tết: 29/01 - 04/02
            "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
            "2025-02-03", "2025-02-04", "2025-02-05", "2025-02-06",
            # 2026 Tết: 17/02 - 23/02
            "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19",
            "2026-02-20", "2026-02-23", "2026-02-24",
            # 2027 Tết: 06/02 - 12/02
            "2027-02-05", "2027-02-08", "2027-02-09", "2027-02-10",
            "2027-02-11", "2027-02-12",
        ]
        holiday_set.update(tet_range)

    return holiday_set


def is_trading_day(date_str: str, holiday_set: Optional[set] = None) -> bool:
    """
    Kiểm tra 1 ngày có phải ngày giao dịch bình thường không.
    Trả về False nếu là Thứ 7 (5), Chủ Nhật (6) hoặc nằm trong danh sách lễ VN.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False

    # Weekend check
    if dt.weekday() >= 5:
        return False

    # Holiday check
    if holiday_set is None:
        holiday_set = get_vn_holidays_set(dt.year)
    return date_str not in holiday_set


def get_last_trading_day(reference: Optional[datetime] = None) -> str:
    """
    Trả về ngày giao dịch HOẶT ĐỘNG GẦN NHẤT so với thời điểm reference.
    Logic: trừ dần 1 ngày cho đến khi gặp thứ 2-6 không phải lễ.
    """
    if reference is None:
        reference = _now_vn()
    ref_date = reference.strftime("%Y-%m-%d")
    current_dt = datetime.strptime(ref_date, "%Y-%m-%d")
    holiday_set = get_vn_holidays_set(current_dt.year)

    # Dò lùi tối đa 14 ngày để tránh vòng lặp vô hạn
    for _ in range(14):
        date_str = current_dt.strftime("%Y-%m-%d")
        if is_trading_day(date_str, holiday_set):
            return date_str
        # Lùi 1 ngày, qua năm mới thì refresh holiday set
        current_dt -= timedelta(days=1)
        if current_dt.year != (current_dt + timedelta(days=1)).year:
            holiday_set = get_vn_holidays_set(current_dt.year)

    # Fallback: trả về ngày gốc nếu có vấn đề
    return ref_date


def get_next_trading_day(reference: Optional[datetime] = None) -> str:
    """
    Trả về ngày giao dịch hoạt động TIẾP THEO (dùng để xác định sau 15h hôm nay => cần check ngày hôm nay).
    """
    if reference is None:
        reference = _now_vn()
    ref_date = reference.strftime("%Y-%m-%d")
    current_dt = datetime.strptime(ref_date, "%Y-%m-%d")
    holiday_set = get_vn_holidays_set(current_dt.year)

    for _ in range(14):
        date_str = current_dt.strftime("%Y-%m-%d")
        if is_trading_day(date_str, holiday_set):
            return date_str
        current_dt += timedelta(days=1)
        if current_dt.year != (current_dt - timedelta(days=1)).year:
            holiday_set = get_vn_holidays_set(current_dt.year)
    return ref_date


# ============================================================
# 2. KIỂM TRA ĐỘ TƯƠI MỚI DỮ LIỆU (FRESHNESS CHECK)
# ============================================================

def _get_max_date_in_table(TableModel, symbol_col: str = "symbol", date_col: str = "date", exclude_indices: bool = False) -> Optional[str]:
    """Lấy giá trị MAX(date) trong bảng lịch sử giá (stock_history hoặc cw_history)."""
    db = SessionLocal()
    try:
        query = db.query(func.max(getattr(TableModel, date_col)))
        if exclude_indices:
            indices = ["VNINDEX", "VN30", "HNXINDEX", "UPCOM", "SPX", "NDX"]
            query = query.filter(~getattr(TableModel, symbol_col).in_(indices))
        max_date = query.scalar()
        return max_date
    finally:
        db.close()


def check_data_freshness(expected_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Kiểm tra xem dữ liệu giá trong DB đã là dữ liệu mới nhất của ngày giao dịch gần nhất chưa.

    Trả về dict:
      {
        "is_up_to_date": bool,
        "expected_trading_day": "YYYY-MM-DD",
        "atc_stock": {"latest_in_db": "YYYY-MM-DD" | None, "is_ok": bool},
        "atc_cw":    {"latest_in_db": "YYYY-MM-DD" | None, "is_ok": bool},
        "message": "Tin nhắn log status"
      }
    """
    if expected_date is None:
        expected_date = get_last_trading_day()

    stock_latest = _get_max_date_in_table(StockHistoricalPrice, exclude_indices=True)
    cw_latest = _get_max_date_in_table(CWHistoricalPrice)

    # Ưu tiên đọc từ DataFreshnessState nếu có (nhanh hơn, và cho biết trạng thái đã được xác nhận chưa)
    db = SessionLocal()
    try:
        for dtype, latest_in_db in [("ATC_STOCK", stock_latest), ("ATC_CW", cw_latest)]:
            row = db.query(DataFreshnessState).filter(DataFreshnessState.data_type == dtype).first()
            if row and row.latest_trading_day:
                # Dùng giá trị trong state, đảm bảo consistency
                if dtype == "ATC_STOCK":
                    stock_latest = row.latest_trading_day
                else:
                    cw_latest = row.latest_trading_day
    finally:
        db.close()

    stock_ok = stock_latest is not None and stock_latest >= expected_date
    cw_ok = cw_latest is not None and cw_latest >= expected_date
    is_up_to_date = stock_ok and cw_ok

    if is_up_to_date:
        message = f"✅ [ATC Manager] Data is up-to-date [{expected_date}]"
    else:
        missing_parts = []
        if not stock_ok:
            missing_parts.append(f"STOCK(expected={expected_date}, got={stock_latest})")
        if not cw_ok:
            missing_parts.append(f"CW(expected={expected_date}, got={cw_latest})")
        message = f"⚠️ [ATC Manager] Data outdated! Triggering auto-fetch — missing: " + " | ".join(missing_parts)

    return {
        "is_up_to_date": is_up_to_date,
        "expected_trading_day": expected_date,
        "atc_stock": {"latest_in_db": stock_latest, "is_ok": stock_ok},
        "atc_cw": {"latest_in_db": cw_latest, "is_ok": cw_ok},
        "message": message,
    }


# ============================================================
# 3. CÔNG CỤ UPDATE STATE / LOGS
# ============================================================

def _create_sync_log(db, sync_date: str, sync_type: str, trigger_source: str) -> ATCSyncLog:
    log = ATCSyncLog(
        sync_date=sync_date,
        sync_type=sync_type,
        trigger_source=trigger_source,
        status="RUNNING",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _update_sync_log(db, log: ATCSyncLog, status: str, records_new: int = 0,
                     total_tickers: int = 0, error_message: Optional[str] = None) -> None:
    log.status = status
    log.records_new = records_new
    log.total_tickers = total_tickers
    log.error_message = error_message[:1000] if error_message else None
    log.finished_at = datetime.now(timezone.utc)
    db.commit()


def _update_freshness_state(log_id: int, stock_ok_date: Optional[str], cw_ok_date: Optional[str]) -> None:
    db = SessionLocal()
    try:
        # Stock
        state_stock = db.query(DataFreshnessState).filter(DataFreshnessState.data_type == "ATC_STOCK").first()
        if state_stock is None:
            state_stock = DataFreshnessState(data_type="ATC_STOCK", latest_trading_day="1970-01-01")
            db.add(state_stock)
        if stock_ok_date and (stock_ok_date >= state_stock.latest_trading_day):
            state_stock.latest_trading_day = stock_ok_date
            state_stock.last_sync_log_id = log_id
        state_stock.total_records = db.query(StockHistoricalPrice).count()

        # CW
        state_cw = db.query(DataFreshnessState).filter(DataFreshnessState.data_type == "ATC_CW").first()
        if state_cw is None:
            state_cw = DataFreshnessState(data_type="ATC_CW", latest_trading_day="1970-01-01")
            db.add(state_cw)
        if cw_ok_date and (cw_ok_date >= state_cw.latest_trading_day):
            state_cw.latest_trading_day = cw_ok_date
            state_cw.last_sync_log_id = log_id
        state_cw.total_records = db.query(CWHistoricalPrice).count()

        db.commit()
    except Exception as e:
        print(f"⚠️ [ATC Manager] Update freshness state error: {e}")
        db.rollback()
    finally:
        db.close()


# ============================================================
# 4. HÀM SYNC DỮ LIỆU ATC CHÍNH
# ============================================================

def sync_atc_data(
    sync_type: str = "ALL",
    trigger_source: str = "MANUAL",
    target_date: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Đồng bộ dữ liệu ATC (giá chốt phiên) từ nguồn dữ liệu về DB.

    Tham số:
      - sync_type      : 'STOCK' | 'CW' | 'ALL'
      - trigger_source : 'SCHEDULER' | 'STARTUP_CHECK' | 'MANUAL'
      - target_date    : ngày phiên cần sync (None = tự động tính ngày giao dịch gần nhất)
      - force          : bỏ qua freshness check, sync luôn

    Trả về dict summary kết quả.
    """
    sync_date = target_date or get_last_trading_day()
    print(f"🔄 [ATC Manager] Starting ATC sync — date={sync_date}, type={sync_type}, source={trigger_source}")

    # Freshness check (nếu không force)
    if not force:
        fresh = check_data_freshness(expected_date=sync_date)
        if sync_type == "STOCK" and fresh["atc_stock"]["is_ok"]:
            print(f"ℹ️ [ATC Manager] STOCK data already up-to-date [{sync_date}]. Skip.")
            return {"status": "skipped_stock_already_up_to_date", "sync_date": sync_date}
        if sync_type == "CW" and fresh["atc_cw"]["is_ok"]:
            print(f"ℹ️ [ATC Manager] CW data already up-to-date [{sync_date}]. Skip.")
            return {"status": "skipped_cw_already_up_to_date", "sync_date": sync_date}
        if sync_type == "ALL" and fresh["is_up_to_date"]:
            print(fresh["message"])
            return {"status": "up_to_date", "sync_date": sync_date}

    # Tạo log entry
    db = SessionLocal()
    log = None
    try:
        log = _create_sync_log(db, sync_date, sync_type, trigger_source)
        log_id = log.id
    finally:
        db.close()

    start_ts = datetime.now()
    results = {"status": "SUCCESS", "sync_date": sync_date, "stock": None, "cw": None}
    stock_new = 0
    cw_new = 0
    total_tickers = 0

    try:
        # Tạo ScraperEngine & chạy async sync
        from backend.infra.scraper_engine import ScraperEngine, DEFAULT_SEMAPHORE
        engine = ScraperEngine(semaphore_limit=DEFAULT_SEMAPHORE)

        def _run_coro(coro):
            """Chạy coroutine async đồng bộ với event loop riêng hoặc loop đang chạy."""
            try:
                # Check if there's already a running loop (FastAPI context)
                loop = asyncio.get_running_loop()
                # If loop is running, use nest_asyncio to allow nested loops
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                except ImportError:
                    # Fallback: run in thread executor if nest_asyncio not available
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, coro)
                        return future.result()
                return asyncio.run(coro)
            except RuntimeError:
                # No running loop, create new one
                loop = None
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(coro)
                finally:
                    if loop is not None:
                        loop.close()

        # === Stock ATC sync ===
        if sync_type in ("STOCK", "ALL"):
            print("📈 [ATC Manager] Syncing STOCK ATC (end-of-session close prices)...")
            r_stock = _run_coro(engine.run_ohlcv_incremental(is_cw=False))
            results["stock"] = r_stock
            stock_new = r_stock.get("records_new_total", 0)
            total_tickers += r_stock.get("total", 0)
            print(f"📈 [ATC Manager] STOCK ATC sync done — new records: {stock_new}")

        # === CW ATC sync ===
        if sync_type in ("CW", "ALL"):
            print("📊 [ATC Manager] Syncing CW ATC (end-of-session close prices)...")
            r_cw = _run_coro(engine.run_ohlcv_incremental(is_cw=True))
            results["cw"] = r_cw
            cw_new = r_cw.get("records_new_total", 0)
            total_tickers += r_cw.get("total", 0)
            print(f"📊 [ATC Manager] CW ATC sync done — new records: {cw_new}")

        # Chạy quant pipeline sau khi có ATC mới (để cập nhật market_opportunities)
        if sync_type in ("ALL", "STOCK", "CW") and (stock_new > 0 or cw_new > 0):
            print("🧮 [ATC Manager] Refreshing quant pipeline with latest ATC prices...")
            try:
                # Run ML credit distress evaluation
                print("🧠 [ATC Manager] Evaluating ML Credit Distress Model...")
                from backend.modules.credit_risk.models.credit_step7_evaluate_market import evaluate_market_health
                evaluate_market_health()
                
                # Run systemic risk contagion model
                print("🕸️ [ATC Manager] Simulating Systematic Risk Contagion (DebtRank)...")
                from backend.modules.credit_risk.models.credit_step8_contagion_model import evaluate_systemic_risk
                evaluate_systemic_risk()
                
                # Run final CW valuation pipeline
                from backend.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
                run_quant_pipeline_programmatic(strategy="balanced")
                print("✅ [ATC Manager] All ML models and quant calculations refreshed successfully.")
            except Exception as qe:
                print(f"⚠️ [ATC Manager] ML model / Quant pipeline refresh warning: {qe}")

        duration = (datetime.now() - start_ts).total_seconds()
        records_new_total = stock_new + cw_new

        # Cập nhật log SUCCESS
        db = SessionLocal()
        try:
            if log:
                log2 = db.query(ATCSyncLog).filter(ATCSyncLog.id == log.id).first()
                if log2:
                    _update_sync_log(db, log2, "SUCCESS", records_new=records_new_total, total_tickers=total_tickers)
                    log_id = log2.id
        finally:
            db.close()

        # Cập nhật freshness state
        stock_latest = sync_date if (sync_type in ("STOCK", "ALL")) else None
        cw_latest = sync_date if (sync_type in ("CW", "ALL")) else None
        if log_id:
            _update_freshness_state(log_id, stock_latest, cw_latest)

        print(f"✅ [ATC Manager] ATC sync done in {duration:.1f}s — total new records: {records_new_total}")
        print(f"✅ [ATC Manager] Data up-to-date [{sync_date}]")
        results.update({
            "duration_seconds": round(duration, 2),
            "records_new_total": records_new_total,
            "total_tickers_processed": total_tickers,
        })

    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        print(f"❌ [ATC Manager] ATC sync FAILED: {err}")
        # Update log FAILED
        db = SessionLocal()
        try:
            if log:
                log2 = db.query(ATCSyncLog).filter(ATCSyncLog.id == log.id).first()
                if log2:
                    _update_sync_log(db, log2, "FAILED", records_new=stock_new + cw_new,
                                     total_tickers=total_tickers, error_message=err)
        finally:
            db.close()
        results["status"] = "FAILED"
        results["error"] = err

    return results


# ============================================================
# 5. STARTUP CHECK — TỰ ĐỘNG KIỂM TRA + SYNC KHI APP BẮT ĐẦU
# ============================================================

def run_startup_atc_check_and_sync(blocking: bool = True) -> Dict[str, Any]:
    """
    Kiểm tra độ tươi dữ liệu lúc App khởi động. Nếu cũ/thiếu thì trigger sync ngay lập tức.

    Tham số:
      - blocking = True (chạy đồng bộ, đợi xong mới tiếp tục) | False (background thread)
    Được gọi từ FastAPI @app.on_event("startup") / lifespan.
    """
    print("\n" + "=" * 88)
    print("🔍 [ATC Manager] RUNNING STARTUP DATA FRESHNESS CHECK...")
    print("=" * 88)

    now = _now_vn()
    hm_str = now.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")

    # Nếu hôm nay là ngày giao dịch & giờ đã >= 15:15 → ngày kỳ vọng là hôm nay
    # Ngược lại → kỳ vọng là ngày giao dịch gần nhất (hôm qua hoặc hiệu chỉnh lễ/T7/CN)
    if is_trading_day(today_str) and hm_str >= "15:15":
        expected_day = today_str
        scenario = f"POST-MARKET [hôm nay {today_str} {hm_str}]"
    else:
        expected_day = get_last_trading_day(now)
        scenario = f"PRE-MARKET / NON-TRADING [ref={today_str} {hm_str}]"

    print(f"ℹ️  [ATC Manager] Scenario: {scenario}")
    print(f"ℹ️  [ATC Manager] Expected latest trading day: {expected_day}")

    # Check freshness
    fresh_result = check_data_freshness(expected_date=expected_day)
    print(fresh_result["message"])
    print("-" * 88)

    # Nếu đã up-to-date → return
    if fresh_result["is_up_to_date"]:
        print("✅ [ATC Manager] STARTUP CHECK PASSED — No sync needed.\n")
        return {
            "action": "none",
            "reason": "up_to_date",
            "expected_day": expected_day,
            "check": fresh_result,
        }

    # Ngược lại → trigger sync ngay
    if blocking:
        print("🚨 [ATC Manager] DATA OUTDATED! Triggering auto-fetch immediately (blocking=True)...")
        print("   Server will accept requests only after sync completes to avoid stale reads.\n")
    else:
        print("🚨 [ATC Manager] DATA OUTDATED! Triggering auto-fetch in background (blocking=False)...")
        print("   Server will start immediately, sync runs in background.\n")

    if not blocking:
        import threading
        t = threading.Thread(
            target=sync_atc_data,
            kwargs={"sync_type": "ALL", "trigger_source": "STARTUP_CHECK", "target_date": expected_day, "force": False},
            daemon=True,
            name="ATCStartupSync",
        )
        t.start()
        return {
            "action": "background_sync_started",
            "expected_day": expected_day,
            "check": fresh_result,
        }

    # Blocking sync (mặc định) — đảm bảo server sẵn sàng với data mới
    sync_result = sync_atc_data(
        sync_type="ALL",
        trigger_source="STARTUP_CHECK",
        target_date=expected_day,
        force=True,  # force vì đã check tươi rồi, tránh check lại lần 2
    )

    # Verify lại sau khi sync xong
    final_check = check_data_freshness(expected_date=expected_day)
    print("=" * 88)
    print(final_check["message"])
    if final_check["is_up_to_date"]:
        print("✅ [ATC Manager] STARTUP SYNC SUCCESSFUL — App is now ready with latest ATC data.")
    else:
        print("⚠️  [ATC Manager] STARTUP SYNC INCOMPLETE — Some data may still be outdated (see logs above).")
    print("=" * 88 + "\n")

    return {
        "action": "blocking_sync_completed",
        "expected_day": expected_day,
        "sync_result": sync_result,
        "final_check": final_check,
    }


# ============================================================
# 6. UTILS: TRẠNG THÁI SYNC GẦN NHẤT (dùng cho API/debug)
# ============================================================

def get_atc_sync_status(limit: int = 10) -> Dict[str, Any]:
    """Trả về trạng thái độ tươi dữ liệu + log sync gần nhất (để API / health check)."""
    db = SessionLocal()
    try:
        fresh = check_data_freshness()
        recent_logs = (
            db.query(ATCSyncLog)
            .order_by(ATCSyncLog.id.desc())
            .limit(limit)
            .all()
        )
        logs_out = []
        for log in recent_logs:
            logs_out.append({
                "id": log.id,
                "sync_date": log.sync_date,
                "sync_type": log.sync_type,
                "trigger_source": log.trigger_source,
                "status": log.status,
                "records_new": log.records_new,
                "total_tickers": log.total_tickers,
                "error_message": log.error_message,
                "started_at": log.started_at.strftime("%Y-%m-%d %H:%M:%S") if log.started_at else None,
                "finished_at": log.finished_at.strftime("%Y-%m-%d %H:%M:%S") if log.finished_at else None,
            })

        # Độ tươi state từ DataFreshnessState
        states = {}
        for row in db.query(DataFreshnessState).all():
            states[row.data_type] = {
                "latest_trading_day": row.latest_trading_day,
                "last_synced_at": row.last_synced_at.strftime("%Y-%m-%d %H:%M:%S") if row.last_synced_at else None,
                "total_records": row.total_records,
            }

        return {
            "freshness": fresh,
            "recent_sync_logs": logs_out,
            "freshness_states": states,
        }
    finally:
        db.close()
