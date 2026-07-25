# -*- coding: utf-8 -*-
"""
🕒 FINVISTA: TIERED BACKGROUND SCHEDULER
=========================================
Smart tiered scheduling strategy:
  - IN-SESSION  (09:00-15:00): CW pricing scan mỗi 15 phút + giá live
  - END-OF-DAY  (15:05): OHLCV đóng phiên incremental toàn thị trường
  - NIGHTLY     (02:00 Chủ nhật): BCTC incremental (by quarter)
  - MONTHLY     (01:00 ngày 1): FA full refresh để detect revision

Author: samvo
"""

import asyncio
import threading
import time
from datetime import datetime


def _is_weekday() -> bool:
    return datetime.now().weekday() < 5


def _hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def _run_async(coro):
    """Chạy coroutine async trong context đồng bộ (thread-safe)."""
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except Exception as e:
        print(f"⚠️ [Scheduler] Async task error: {e}")
    finally:
        if loop is not None:
            loop.close()


# ─── Job Runners ──────────────────────────────────────────────────────────────

def _job_intraday_cw_scan():
    """Job trong phiên: chạy quét định giá CW (BSM, Greeks, G-Score)."""
    try:
        from src.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
        run_quant_pipeline_programmatic(strategy="balanced")
        print("✅ [Scheduler] Intraday CW scan completed.")
    except Exception as e:
        print(f"⚠️ [Scheduler] Intraday CW scan error: {e}")


def _job_eod_ohlcv():
    """Job cuối phiên: cào OHLCV đóng phiên hôm nay (incremental)."""
    try:
        from src.infra.scraper_engine import ScraperEngine
        engine = ScraperEngine(semaphore_limit=10)
        print("📥 [Scheduler] EOD OHLCV incremental scrape starting...")
        result = _run_async(engine.run_ohlcv_incremental(is_cw=False))
        print(f"✅ [Scheduler] EOD OHLCV done: {result.get('records_new_total', 0)} new records")
        # Cào CW history cũng cuối phiên
        result_cw = _run_async(engine.run_ohlcv_incremental(is_cw=True))
        print(f"✅ [Scheduler] EOD CW OHLCV done: {result_cw.get('records_new_total', 0)} new records")
        
        # Chạy quét định giá cuối phiên để cập nhật giá khớp ATC mới nhất
        print("📊 [Scheduler] Running post-market quant pipeline scan...")
        from src.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
        run_quant_pipeline_programmatic(strategy="balanced")
        print("✅ [Scheduler] Post-market quant pipeline scan completed.")
    except Exception as e:
        print(f"⚠️ [Scheduler] EOD OHLCV error: {e}")


def _job_weekly_news():
    """Job tuần: cào tin tức incremental toàn thị trường."""
    try:
        from src.infra.scraper_engine import ScraperEngine
        engine = ScraperEngine(semaphore_limit=6)
        print("📰 [Scheduler] Weekly news incremental scrape starting...")
        result = _run_async(engine.run_news_incremental(max_per_ticker=50))
        print(f"✅ [Scheduler] Weekly news done: {result.get('records_new_total', 0)} new articles")
    except Exception as e:
        print(f"⚠️ [Scheduler] Weekly news error: {e}")


# ─── Main scheduler loop ──────────────────────────────────────────────────────

def _scheduler_loop():
    time.sleep(15)  # Warm-up delay
    print("🕒 [Scheduler] Tiered background scheduler started.")

    _eod_done_today: str = ""         # Ngày đã chạy EOD job
    _weekly_done_week: str = ""       # Tuần đã chạy weekly job

    while True:
        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            week = now.strftime("%Y-W%W")
            hm = _hhmm()
            weekday = now.weekday()  # 0=Mon, 6=Sun

            # ── TRONG PHIÊN: CW scan mỗi 15 phút (09:00 – 14:45) ──────────
            if _is_weekday() and "09:00" <= hm <= "14:45":
                _job_intraday_cw_scan()
                time.sleep(900)  # 15 phút
                continue

            # ── CUỐI PHIÊN: OHLCV incremental một lần sau 15:05 ────────────
            if _is_weekday() and "15:05" <= hm <= "15:30" and _eod_done_today != today:
                _eod_done_today = today
                _job_eod_ohlcv()
                time.sleep(300)
                continue

            # ── TUẦN: News incremental Chủ nhật 02:00 ──────────────────────
            if weekday == 6 and "02:00" <= hm <= "02:30" and _weekly_done_week != week:
                _weekly_done_week = week
                _job_weekly_news()
                time.sleep(1800)
                continue

            # ── IDLE: poll mỗi 5 phút ngoài giờ ───────────────────────────
            time.sleep(300)

        except Exception as e:
            print(f"⚠️ [Scheduler] Unexpected error: {e}")
            time.sleep(60)


def start_periodic_scheduler() -> None:
    """Khởi động background scheduler thread — chỉ chạy ở 1 worker process duy nhất."""
    import os, tempfile
    lock_path = os.path.join(tempfile.gettempdir(), "finvista_scheduler.lock")

    # Clean stale lock from previous container/process that no longer exists
    if os.path.exists(lock_path):
        try:
            with open(lock_path) as f:
                old_pid = int(f.read().strip())
            # Check if that PID is still alive
            os.kill(old_pid, 0)   # raises OSError if dead
        except (OSError, ValueError):
            # Stale lock — remove it so this worker can take over
            try:
                os.remove(lock_path)
            except OSError:
                pass

    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except OSError:
        return  # Another live worker already owns the scheduler

    t = threading.Thread(target=_scheduler_loop, daemon=True, name="FinvistaScheduler")
    t.start()
    print(f"🕒 [Scheduler] Background thread started (PID {os.getpid()} owns lock).")

