# -*- coding: utf-8 -*-
"""
🕒 FINVISTA: TIERED BACKGROUND SCHEDULER v2
============================================
Hỗ trợ 2 engine scheduler (điều phối qua start_periodic_scheduler):
  A) APScheduler (BackgroundScheduler) — CHÍNH, chính xác theo cron/giờ Việt Nam
  B) Custom thread loop — FALLBACK nếu APScheduler chưa cài đặt

Jobs được lên lịch (theo giờ Việt Nam / Asia/Ho_Chi_Minh / UTC+7):
  ┌──────────────┬────────────────┬─────────────────────────────────────────────┐
  │ Time (VN)    │ Days           │ Job                                         │
  ├──────────────┼────────────────┼─────────────────────────────────────────────┤
  │ 09:00-14:45  │ T2 - T6        │ Intraday CW scan mỗi 15 phút                │
  │ 15:15        │ T2 - T6        │ ATC / EOD OHLCV sync (giá chốt phiên)       │
  │ 02:00        │ Chủ Nhật       │ Weekly news incremental                     │
  └──────────────┴────────────────┴─────────────────────────────────────────────┘

Author: samvo
Version: 2.0 (APScheduler + ATF fallback)
"""

import os
import sys
import asyncio
import threading
import time
from datetime import datetime

# Event loop reference — set by main.py on_startup so background threads
# can safely schedule coroutines into FastAPI's running event loop.
_event_loop = None


def set_event_loop(loop) -> None:
    """Called once from FastAPI startup to register the running event loop."""
    global _event_loop
    _event_loop = loop


def _broadcast_from_thread(data: dict) -> None:
    """Thread-safe WebSocket broadcast. Silently skips if loop not registered."""
    if _event_loop is None or not _event_loop.is_running():
        return
    try:
        from backend.api.websocket import manager
        asyncio.run_coroutine_threadsafe(manager.broadcast(data), _event_loop)
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] WebSocket broadcast failed: {e}")

# === Fix Windows CP1252 console UnicodeEncodeError ===
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Python 3.7+
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    try:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    except Exception:
        pass

# Safe print function for background threads
def safe_print(*args, **kwargs):
    """Thread-safe print that handles closed file handles."""
    try:
        print(*args, **kwargs)
    except (ValueError, OSError):
        pass  # Silently ignore print errors in background threads

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ============================================================
# 0. TIMEZONE & UTILS
# ============================================================

_VN_TZ_NAME = "Asia/Ho_Chi_Minh"


def _try_get_vn_tz():
    """Lấy timezone object cho Việt Nam. Ưu tiên zoneinfo (Python 3.9+) rồi pytz, cuối cùng fallback timedelta(+7)."""
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
        return ZoneInfo(_VN_TZ_NAME)
    except Exception:
        try:
            import pytz  # type: ignore
            return pytz.timezone(_VN_TZ_NAME)
        except Exception:
            from datetime import timezone, timedelta
            return timezone(timedelta(hours=7))


# ============================================================
# 1. JOB RUNNERS (shared cho cả 2 engine)
# ============================================================

def _job_intraday_cw_scan():
    """Job trong phiên: chạy quét định giá CW (BSM, Greeks, G-Score)."""
    try:
        from backend.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
        from backend.infra.redis_cache import invalidate_warrant_cache
        run_quant_pipeline_programmatic(strategy="balanced")
        
        # Invalidate warrant cache after scan
        invalidated = invalidate_warrant_cache()
        safe_print(f"✅ [Scheduler] Intraday CW scan completed. Invalidated {invalidated} cache entries.")
        
        # Broadcast WebSocket notification (thread-safe)
        _broadcast_from_thread({
            "event": "cw_scan_completed",
            "timestamp": datetime.now(_try_get_vn_tz()).isoformat(),
            "cache_invalidated": invalidated,
        })
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Intraday CW scan error: {e}")


def _job_eod_ohlcv_atc():
    """
    Job cuối phiên: sync dữ liệu ATC / giá chốt phiên cho toàn bộ STOCK + CW.
    Chạy lúc 15:15 T2-T6 (giờ VN) — thời điểm giá ATC đã ổn định sau khi đóng phiên.
    """
    try:
        from backend.modules.atc_manager.service import sync_atc_data, get_last_trading_day
        from backend.infra.redis_cache import invalidate_atc_cache
        today_vn_str = datetime.now(_try_get_vn_tz()).strftime("%Y-%m-%d")
        expected_trading_day = get_last_trading_day()

        safe_print(f"\n🔔 [Scheduler] ===========================================")
        safe_print(f"🔔 [Scheduler] TRIGGERING ATC / EOD SYNC (post-market)")
        safe_print(f"🔔 [Scheduler]   Today (VN)      : {today_vn_str}")
        safe_print(f"🔔 [Scheduler]   Expected trading : {expected_trading_day}")
        safe_print(f"🔔 [Scheduler] ===========================================\n")

        sync_atc_data(
            sync_type="ALL",
            trigger_source="SCHEDULER",
            target_date=expected_trading_day,
            force=False,
        )
        
        # Invalidate ATC cache after sync
        invalidated = invalidate_atc_cache()
        safe_print(f"🗑️ [Scheduler] Invalidated {invalidated} ATC cache entries")
        
        # Broadcast WebSocket notification (thread-safe)
        _broadcast_from_thread({
            "event": "atc_sync_completed",
            "timestamp": datetime.now(_try_get_vn_tz()).isoformat(),
            "trading_day": expected_trading_day,
            "cache_invalidated": invalidated,
        })
        
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] ATC / EOD sync error: {e}")


def _job_daily_stock_history_update():
    """
    Job ngày: cập nhật stock history (dữ liệu giá cổ phiếu cơ sở) cho volatility calculation.
    Chạy lúc 15:30 T2-T6 (sau ATC sync 15:15) — đảm bảo data mới nhất cho HV calculation.
    """
    try:
        from backend.modules.atc_manager.service import sync_atc_data, get_last_trading_day
        from backend.infra.redis_cache import invalidate_stock_cache
        expected_trading_day = get_last_trading_day()

        safe_print(f"\n📈 [Scheduler] ===========================================")
        safe_print(f"📈 [Scheduler] TRIGGERING STOCK HISTORY UPDATE")
        safe_print(f"📈 [Scheduler]   Expected trading : {expected_trading_day}")
        safe_print(f"📈 [Scheduler] ===========================================\n")

        sync_atc_data(
            sync_type="STOCK",
            trigger_source="SCHEDULER",
            target_date=expected_trading_day,
            force=False,
        )
        
        # Invalidate stock cache after sync
        try:
            invalidated = invalidate_stock_cache()
            safe_print(f"🗑️ [Scheduler] Invalidated {invalidated} stock cache entries")
        except Exception as cache_err:
            safe_print(f"⚠️ [Scheduler] Stock cache invalidation skipped: {cache_err}")
        
        # Broadcast WebSocket notification (thread-safe)
        _broadcast_from_thread({
            "event": "stock_history_updated",
            "timestamp": datetime.now(_try_get_vn_tz()).isoformat(),
            "trading_day": expected_trading_day,
        })
        
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Stock history update error: {e}")


def _job_weekly_news():
    """Job tuần: cào tin tức incremental toàn thị trường (Chủ Nhật 02:00)."""
    try:
        from backend.infra.scraper_engine import ScraperEngine
        engine = ScraperEngine(semaphore_limit=6)
        import asyncio

        safe_print("📰 [Scheduler] Weekly news incremental scrape starting...")

        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(engine.run_news_incremental(max_per_ticker=50))
        finally:
            if loop:
                loop.close()

        safe_print(f"✅ [Scheduler] Weekly news done: {result.get('records_new_total', 0)} new articles")
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Weekly news error: {e}")


def _job_daily_indices_update():
    """Job ngày: cập nhật market indices (VNINDEX, VN30, HNXINDEX, UPCOM, SPX) hàng ngày."""
    try:
        from scripts.data_pipelines.backfill_indices import backfill_index_vps, backfill_spx_index
        safe_print("📊 [Scheduler] Daily market indices update starting...")
        
        # Vietnam indices via VPS
        backfill_index_vps("VNINDEX")
        backfill_index_vps("VN30")
        try:
            backfill_index_vps("HNXINDEX")
        except Exception as hnx_err:
            safe_print(f"⚠️ [Scheduler] HNXINDEX update skipped: {hnx_err}")
        try:
            backfill_index_vps("UPCOM")
        except Exception as upcom_err:
            safe_print(f"⚠️ [Scheduler] UPCOM update skipped: {upcom_err}")
        
        # International indices
        try:
            backfill_spx_index(start_year=2020)
        except Exception as spx_err:
            safe_print(f"⚠️ [Scheduler] SPX update skipped: {spx_err}")
            
        safe_print("✅ [Scheduler] Daily indices update completed")
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Daily indices update error: {e}")


def run_startup_indices_and_regime_check_and_sync() -> None:
    """
    Kiểm tra dữ liệu VNINDEX lúc App khởi động.
    Nếu thiếu dữ liệu EOD của ngày giao dịch gần nhất (kể cả sau 15:30 hôm nay),
    tự động chạy cập nhật chỉ số (vps) + chạy tính toán quant/G-score ngay lập tức.
    """
    try:
        from datetime import datetime, timedelta
        from backend.core.database import SessionLocal, StockHistoricalPrice
        from backend.modules.cw_pricing.backtest.run_analysis import run_quant_pipeline_programmatic
        from scripts.data_pipelines.backfill_indices import backfill_index_vps
        
        safe_print("\n📊 [Startup Sync] Checking Market Indices & G-Scores freshness...")
        
        # 1. Determine expected day
        now = datetime.now(_try_get_vn_tz())
        hm_str = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")
        
        # Helper to check if weekend (weekday: 0-4 = Mon-Fri, 5 = Sat, 6 = Sun)
        weekday = now.weekday()
        
        # Determine expected date:
        # Nếu là T7/CN: expected_day là thứ 6 gần nhất
        if weekday == 5: # Saturday
            expected_day_dt = now - timedelta(days=1)
        elif weekday == 6: # Sunday
            expected_day_dt = now - timedelta(days=2)
        else: # T2-T6
            # Nếu trong phiên hoặc trước 15:30 -> expected_day là ngày giao dịch trước đó
            if hm_str < "15:30":
                offset = 3 if weekday == 0 else 1 # nếu Thứ Hai, quay về Thứ Sáu
                expected_day_dt = now - timedelta(days=offset)
            else:
                expected_day_dt = now
                
        expected_day = expected_day_dt.strftime("%Y-%m-%d")
        safe_print(f"   Expected latest trading day: {expected_day}")
        
        # 2. Query database for latest VNINDEX date
        db = SessionLocal()
        try:
            latest = db.query(StockHistoricalPrice).filter(StockHistoricalPrice.symbol == "VNINDEX").order_by(StockHistoricalPrice.date.desc()).first()
            
            latest_db_date = None
            if latest:
                if isinstance(latest.date, datetime):
                    latest_db_date = latest.date.strftime("%Y-%m-%d")
                else:
                    latest_db_date = str(latest.date)
            
            safe_print(f"   Database latest VNINDEX date: {latest_db_date}")
            
            if not latest_db_date or latest_db_date < expected_day:
                safe_print(f"🚨 [Startup Sync] Data is outdated (DB: {latest_db_date} vs Expected: {expected_day}). Starting sync...")
                
                # Fetch indices via VPS datafeed
                try:
                    backfill_index_vps("VNINDEX")
                    backfill_index_vps("VN30")
                    backfill_index_vps("UPCOM")
                    backfill_index_vps("HNXINDEX")
                except Exception as e:
                    safe_print(f"⚠️ [Startup Sync] Error backfilling indices: {e}")
                
                # Run the quant pipeline G-score recalculation
                try:
                    safe_print("⚙️ [Startup Sync] Recalculating Covered Warrants G-scores and regimes...")
                    run_quant_pipeline_programmatic(strategy="delta_adaptive")
                    safe_print("✅ [Startup Sync] Quantitative scoring update completed.")
                except Exception as e:
                    safe_print(f"⚠️ [Startup Sync] Error running quant pipeline: {e}")
            else:
                safe_print("✅ [Startup Sync] Indices and G-Scores are up to date. No sync needed.\n")
        finally:
            db.close()
    except Exception as e:
        safe_print(f"⚠️ [Startup Sync] Unexpected error: {e}")


def _job_daily_macro_update():
    """Job ngày: cập nhật macro data (USD/VND, Vàng, VIX, Oil) hàng ngày."""
    try:
        from backend.modules.regime_analysis.etl.macro_scraper import fetch_macro_indicators
        safe_print("💰 [Scheduler] Daily macro data update starting...")
        fetch_macro_indicators()
        safe_print("✅ [Scheduler] Daily macro update completed")
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Daily macro update error: {e}")


def _job_daily_derivatives_update():
    """Job ngày: cập nhật phái sinh VN30F1M (basis, OI, flow) hàng ngày."""
    try:
        from backend.modules.cw_pricing.backtest.fetcher import fetch_derivatives_sentiment
        safe_print("📈 [Scheduler] Daily derivatives data update starting...")
        fetch_derivatives_sentiment()
        safe_print("✅ [Scheduler] Daily derivatives update completed")
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Daily derivatives update error: {e}")


def _job_daily_us_indices_update():
    """Job ngày: cập nhật US indices (S&P 500, NASDAQ) hàng ngày và lưu vào DB."""
    try:
        import yfinance as yf
        import pandas as pd
        from datetime import datetime, timedelta
        from backend.core.database import SessionLocal, StockHistoricalPrice
        safe_print("🇺🇸 [Scheduler] Daily US indices update starting...")
        
        db = SessionLocal()
        try:
            # Fetch S&P 500 and NASDAQ
            symbols = [
                ("^GSPC", "SPX"),  # S&P 500
                ("^NDX", "NDX")    # NASDAQ 100
            ]
            
            for yf_symbol, db_symbol in symbols:
                try:
                    # Fetch last 5 days to get latest data
                    df = yf.download(yf_symbol, period="5d", progress=False)
                    if df.empty:
                        safe_print(f"   {yf_symbol}: No data")
                        continue
                        
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    # Get latest row
                    latest = df['Close'].dropna().iloc[-1]
                    latest_date = df.index[-1]
                    
                    # Format date
                    date_str = latest_date.strftime('%Y-%m-%d')
                    
                    # Check if exists
                    existing = db.query(StockHistoricalPrice).filter(
                        StockHistoricalPrice.symbol == db_symbol,
                        StockHistoricalPrice.date == date_str
                    ).first()
                    
                    if existing:
                        # Update
                        existing.close = float(latest)
                        existing.open = float(df['Open'].dropna().iloc[-1]) if not df['Open'].dropna().empty else float(latest)
                        existing.high = float(df['High'].dropna().iloc[-1]) if not df['High'].dropna().empty else float(latest)
                        existing.low = float(df['Low'].dropna().iloc[-1]) if not df['Low'].dropna().empty else float(latest)
                        existing.volume = float(df['Volume'].dropna().iloc[-1]) if not df['Volume'].dropna().empty else 0.0
                        existing.ref_price = float(latest)
                    else:
                        # Insert
                        new_record = StockHistoricalPrice(
                            symbol=db_symbol,
                            date=date_str,
                            open=float(df['Open'].dropna().iloc[-1]) if not df['Open'].dropna().empty else float(latest),
                            high=float(df['High'].dropna().iloc[-1]) if not df['High'].dropna().empty else float(latest),
                            low=float(df['Low'].dropna().iloc[-1]) if not df['Low'].dropna().empty else float(latest),
                            close=float(latest),
                            volume=float(df['Volume'].dropna().iloc[-1]) if not df['Volume'].dropna().empty else 0.0,
                            ref_price=float(latest)
                        )
                        db.add(new_record)
                    
                    db.commit()
                    safe_print(f"   {db_symbol}: {latest:.2f} ({date_str})")
                    
                except Exception as e:
                    safe_print(f"   Error fetching {yf_symbol}: {e}")
                    db.rollback()
                    
        finally:
            db.close()
        
        safe_print("✅ [Scheduler] Daily US indices update completed")
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Daily US indices update error: {e}")


def _job_weekly_regime_retraining():
    """Job tuần: retrain ML regime models để duy trì accuracy."""
    try:
        safe_print("🤖 [Scheduler] Weekly ML regime model retraining starting...")
        
        # Import training script
        import subprocess
        import sys
        
        # Train on multiple symbols for robustness
        symbols = ['SPY', 'QQQ', 'IWM']  # Major US ETFs as proxies
        
        for symbol in symbols:
            try:
                safe_print(f"   Training model for {symbol}...")
                result = subprocess.run(
                    [sys.executable, "scripts/model_training/train_ml_regime.py", "--symbol", symbol, "--horizon", "5"],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout per symbol
                )
                
                if result.returncode == 0:
                    safe_print(f"   ✅ {symbol} model retrained successfully")
                else:
                    safe_print(f"   ⚠️ {symbol} retraining failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                safe_print(f"   ⚠️ {symbol} retraining timed out")
            except Exception as e:
                safe_print(f"   ⚠️ {symbol} retraining error: {e}")
        
        safe_print("✅ [Scheduler] Weekly ML regime retraining completed")
        
        # Broadcast WebSocket notification
        _broadcast_from_thread({
            "event": "regime_models_retrained",
            "timestamp": datetime.now(_try_get_vn_tz()).isoformat(),
            "symbols": symbols
        })
        
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Weekly ML regime retraining error: {e}")


def _job_daily_latex_report():
    """Job ngày: sinh báo cáo thị trường PDF/HTML hàng ngày lúc 18:00."""
    try:
        from scripts.data_pipelines.generate_daily_latex_report import generate_report
        safe_print("📊 [Scheduler] Starting automated daily market HTML/PDF report generation...")
        generate_report()
        safe_print("✅ [Scheduler] Automated daily market HTML/PDF report generated successfully.")
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Automated daily market HTML/PDF report generation error: {e}")


def _job_daily_regime_evaluation_precompute():
    """Job ngày lúc 17:30: Pre-compute Regime Backtest Evaluation để API trả về < 5ms."""
    try:
        safe_print("🏆 [Scheduler] Starting daily EOD Regime Evaluation pre-computation...")
        from backend.api.routes.regime import get_regime_evaluation
        quick_symbols = ["VNINDEX", "VN30", "ACB", "FPT", "HPG", "MWG", "VHM"]
        regime_types = ["kairos", "hmm", "creed"]
        for sym in quick_symbols:
            for r_type in regime_types:
                try:
                    get_regime_evaluation(ticker=sym, days=500, regime_type=r_type)
                except Exception:
                    pass
        safe_print("✅ [Scheduler] Daily EOD Regime Evaluation pre-computation completed successfully.")
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Daily EOD Regime Evaluation error: {e}")


# ============================================================
# 2. ENGINE A — APSCHEDULER (CHÍNH)
# ============================================================

_scheduler_instance = None  # type: ignore  # giữ ref để avoid GC


def _try_start_apscheduler() -> bool:
    """
    Khởi động APScheduler BackgroundScheduler.
    Trả về True nếu thành công, False nếu APScheduler không có/khởi động được.
    """
    global _scheduler_instance
    try:
        from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
    except Exception:
        safe_print("ℹ️  [Scheduler] APScheduler not installed — falling back to custom thread loop.")
        safe_print("   → (Install: pip install APScheduler>=3.10.4)")
        return False

    vn_tz = _try_get_vn_tz()
    scheduler = BackgroundScheduler(timezone=vn_tz, daemon=True)

    # ------------------------------------------------------------------
    # JOB 1: Intraday CW scan — mỗi 15 phút trong giờ giao dịch (T2-T6 09:00-14:45)
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_intraday_cw_scan,
        trigger="cron",
        day_of_week="mon-fri",
        hour="9-14",
        minute="*/15",
        id="intraday_cw_scan",
        name="Intraday CW Quant Scan (every 15m)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )

    # ------------------------------------------------------------------
    # JOB 2: ATC / EOD OHLCV sync — lúc 15:15 T2-T6 (chỉ chạy 1 lần mỗi ngày)
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_eod_ohlcv_atc,
        trigger="cron",
        day_of_week="mon-fri",
        hour=15,
        minute=15,
        id="atc_eod_sync",
        name="ATC End-of-Session Close Price Sync (15:15 VN)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=900,  # 15 phút miss vẫn chạy bù
    )

    # ------------------------------------------------------------------
    # JOB 2.5: Daily Stock History Update — lúc 15:30 T2-T6 (sau ATC sync)
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_daily_stock_history_update,
        trigger="cron",
        day_of_week="mon-fri",
        hour=15,
        minute=30,
        id="daily_stock_history_update",
        name="Daily Stock History Update (15:30 VN)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=900,
    )

    # ------------------------------------------------------------------
    # JOB 2.6: Daily EOD Regime Evaluation Pre-compute — lúc 17:30 T2-T6
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_daily_regime_evaluation_precompute,
        trigger="cron",
        day_of_week="mon-fri",
        hour=17,
        minute=30,
        id="eod_regime_evaluation_precompute",
        name="Daily EOD Regime Evaluation Pre-compute (17:30 VN)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )

    # ------------------------------------------------------------------
    # JOB 3: Weekly news — Chủ Nhật 02:00
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_weekly_news,
        trigger="cron",
        day_of_week="sun",
        hour=2,
        minute=0,
        id="weekly_news",
        name="Weekly News Incremental Scrape (Sunday 02:00)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    # ------------------------------------------------------------------
    # JOB 3.5: Weekly ML regime retraining — Chủ Nhật 03:00 (sau news)
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_weekly_regime_retraining,
        trigger="cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        id="weekly_regime_retraining",
        name="Weekly ML Regime Model Retraining (Sunday 03:00)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=7200,  # 2 hours grace time
    )

    # ------------------------------------------------------------------
    # JOB 4: Daily indices update — 16:00 T2-T6 (sau ATC sync)
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_daily_indices_update,
        trigger="cron",
        day_of_week="mon-fri",
        hour=16,
        minute=0,
        id="daily_indices_update",
        name="Daily Market Indices Update (VNINDEX, VN30, HNX, UPCOM)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )

    # ------------------------------------------------------------------
    # JOB 5: Daily macro update — 16:30 T2-T6 (sau indices update)
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_daily_macro_update,
        trigger="cron",
        day_of_week="mon-fri",
        hour=16,
        minute=30,
        id="daily_macro_update",
        name="Daily Macro Data Update (USD/VND, Gold, VIX, Oil)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )

    # ------------------------------------------------------------------
    # JOB 6: Daily derivatives update — 17:00 T2-T6 (sau macro update)
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_daily_derivatives_update,
        trigger="cron",
        day_of_week="mon-fri",
        hour=17,
        minute=0,
        id="daily_derivatives_update",
        name="Daily Derivatives Update (VN30F1M Basis, OI, Flow)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )

    # ------------------------------------------------------------------
    # JOB 7: Daily US indices update — 17:30 T2-T6 (sau derivatives update)
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_daily_us_indices_update,
        trigger="cron",
        day_of_week="mon-fri",
        hour=17,
        minute=30,
        id="daily_us_indices_update",
        name="Daily US Indices Update (S&P 500, NASDAQ)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )

    # ------------------------------------------------------------------
    # JOB 8: Daily market PDF/HTML report — 18:00 T2-T6
    # ------------------------------------------------------------------
    scheduler.add_job(
        _job_daily_latex_report,
        trigger="cron",
        day_of_week="mon-fri",
        hour=18,
        minute=0,
        id="daily_market_report",
        name="Daily Market HTML/PDF Report (18:00 VN)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )


    try:
        scheduler.start()
        _scheduler_instance = scheduler
        safe_print("🕒 [Scheduler] APScheduler started (BackgroundScheduler).")
        safe_print(f"   • Timezone        : {_VN_TZ_NAME} (UTC+7)")
        safe_print(f"   • intraday_cw_scan: every 15 min 09:00-14:45 (Mon-Fri)")
        safe_print(f"   • atc_eod_sync    : 15:15 (Mon-Fri) — ATC close price sync")
        safe_print(f"   • stock_history   : 15:30 (Mon-Fri) — Stock history for HV calc")
        safe_print(f"   • daily_indices   : 16:00 (Mon-Fri) — VNINDEX, VN30, HNX, UPCOM")
        safe_print(f"   • daily_macro     : 16:30 (Mon-Fri) — USD/VND, Gold, VIX, Oil")
        safe_print(f"   • daily_derivatives: 17:00 (Mon-Fri) — VN30F1M Basis, OI, Flow")
        safe_print(f"   • daily_us_indices: 17:30 (Mon-Fri) — S&P 500, NASDAQ")
        safe_print(f"   • daily_market_report: 18:00 (Mon-Fri) — Daily Market PDF/HTML Report")
        safe_print(f"   • weekly_news     : Sunday 02:00")

        # In lan luot next_run_time cho tung job (de kiem tra lich trinh de dang)
        for job in scheduler.get_jobs():
            try:
                nrt = job.next_run_time
                if nrt:
                    try:
                        nrt_vn = nrt.astimezone(vn_tz).strftime("%Y-%m-%d %H:%M:%S %Z")
                    except Exception:
                        nrt_vn = str(nrt)
                    safe_print(f"       → job[{job.id:18s}] next_run = {nrt_vn}")
            except Exception:
                pass
        return True
    except Exception as e:
        safe_print(f"⚠️ [Scheduler] Failed to start APScheduler: {e}")
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass
        return False


def get_scheduler_status() -> dict:
    """
    Trả về trạng thái scheduler + list jobs (cho API /api/atc/scheduler-status).
    Giúp kiểm tra luồng 3 (scheduler 15:15) hoạt động đúng chưa.
    """
    from datetime import datetime
    vn_tz = _try_get_vn_tz()
    now_vn = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S %Z")

    # APScheduler running?
    aps = {
        "running": False,
        "jobs": [],
    }
    if _scheduler_instance is not None:
        try:
            if _scheduler_instance.running:
                aps["running"] = True
            for job in _scheduler_instance.get_jobs():
                nrt = job.next_run_time
                nrt_str = None
                if nrt:
                    try:
                        nrt_str = nrt.astimezone(vn_tz).strftime("%Y-%m-%d %H:%M:%S %Z")
                    except Exception:
                        nrt_str = str(nrt)
                aps["jobs"].append({
                    "id": job.id,
                    "name": job.name,
                    "trigger": str(job.trigger),
                    "next_run_time": nrt_str,
                    "max_instances": job.max_instances,
                })
        except Exception:
            pass

    fallback = {"running": False, "note": "Runs as daemon thread 'FinvistaSchedulerFallback' when APScheduler unavailable (self-managed)."}
    import threading
    for t in threading.enumerate():
        if t.name == "FinvistaSchedulerFallback":
            fallback["running"] = True and t.is_alive()
            break

    return {
        "now_vietnam_time": now_vn,
        "engine": {
            "apscheduler": aps,
            "fallback_thread_loop": fallback,
        },
        "atc_job_expected_spec": {
            "schedule": "Cron: 15:15 every Monday-Friday (Asia/Ho_Chi_Minh)",
            "job_id": "atc_eod_sync",
            "description": "Sync ATC end-of-session close prices for STOCK + CW, then refresh quant pipeline.",
            "misfire_grace_time": "900s (15 min — runs catch-up if server was down briefly at 15:15)",
            "coalesce": True,
        },
    }


# ============================================================
# 3. ENGINE B — CUSTOM THREAD LOOP (FALLBACK)
# ============================================================

def _is_weekday_vn() -> bool:
    now = datetime.now(_try_get_vn_tz())
    return now.weekday() < 5


def _hhmm_vn() -> str:
    return datetime.now(_try_get_vn_tz()).strftime("%H:%M")


def _scheduler_loop_fallback():
    """Thread loop fallback (chạy khi APScheduler không có)."""
    time.sleep(15)  # Warm-up delay
    safe_print("🕒 [Scheduler] Fallback custom thread scheduler started.")

    _eod_done_today: str = ""
    _weekly_done_week: str = ""
    _stock_history_done_today: str = ""
    _indices_done_today: str = ""
    _macro_done_today: str = ""
    _derivatives_done_today: str = ""
    _us_indices_done_today: str = ""
    _market_report_done_today: str = ""
    _intraday_last_run_epoch: float = 0.0
    _INTRADAY_INTERVAL = 900  # 15 phút

    while True:
        try:
            now = datetime.now(_try_get_vn_tz())
            today = now.strftime("%Y-%m-%d")
            week = now.strftime("%Y-W%W")
            hm = _hhmm_vn()
            weekday = now.weekday()
            epoch = time.time()

            # ── TRONG PHIÊN: CW scan mỗi 15 phút (09:00 – 14:45) ──────
            if _is_weekday_vn() and "09:00" <= hm <= "14:45" and (epoch - _intraday_last_run_epoch >= _INTRADAY_INTERVAL):
                _job_intraday_cw_scan()
                _intraday_last_run_epoch = epoch
                time.sleep(60)
                continue

            # ── CUỐI PHIÊN: ATC / EOD sync 15:15-15:30 (mỗi ngày 1 lần) ─
            if _is_weekday_vn() and "15:15" <= hm <= "15:30" and _eod_done_today != today:
                _eod_done_today = today
                _job_eod_ohlcv_atc()
                time.sleep(300)
                continue

            # ── SAU PHIÊN: Stock history update 15:30-16:00 (mỗi ngày 1 lần) ──
            if _is_weekday_vn() and "15:30" <= hm <= "16:00" and _stock_history_done_today != today:
                _stock_history_done_today = today
                _job_daily_stock_history_update()
                time.sleep(300)
                continue

            # ── SAU PHIÊN: Indices update 16:00-16:30 (mỗi ngày 1 lần) ──
            if _is_weekday_vn() and "16:00" <= hm <= "16:30" and _indices_done_today != today:
                _indices_done_today = today
                _job_daily_indices_update()
                time.sleep(300)
                continue

            # ── SAU PHIÊN: Macro update 16:30-17:00 (mỗi ngày 1 lần) ──
            if _is_weekday_vn() and "16:30" <= hm <= "17:00" and _macro_done_today != today:
                _macro_done_today = today
                _job_daily_macro_update()
                time.sleep(300)
                continue

            # ── SAU PHIÊN: Derivatives update 17:00-17:30 (mỗi ngày 1 lần) ──
            if _is_weekday_vn() and "17:00" <= hm <= "17:30" and _derivatives_done_today != today:
                _derivatives_done_today = today
                _job_daily_derivatives_update()
                time.sleep(300)
                continue

            # ── SAU PHIÊN: US indices update 17:30-18:00 (mỗi ngày 1 lần) ──
            if _is_weekday_vn() and "17:30" <= hm <= "18:00" and _us_indices_done_today != today:
                _us_indices_done_today = today
                _job_daily_us_indices_update()
                time.sleep(300)
                continue

            # ── SAU PHIÊN: EOD Regime Evaluation pre-compute 17:30-18:00 ──
            if _is_weekday_vn() and "17:30" <= hm <= "18:00" and _regime_eval_done_today != today:
                _regime_eval_done_today = today
                _job_daily_regime_evaluation_precompute()
                time.sleep(120)
                continue

            # ── SAU PHIÊN: Daily market report 18:00-18:15 (mỗi ngày 1 lần) ──
            if _is_weekday_vn() and "18:00" <= hm <= "18:15" and _market_report_done_today != today:
                _market_report_done_today = today
                _job_daily_latex_report()
                time.sleep(300)
                continue

            # ── TUẦN: News incremental Chủ nhật 02:00 ────────────────────
            if weekday == 6 and "02:00" <= hm <= "02:30" and _weekly_done_week != week:
                _weekly_done_week = week
                _job_weekly_news()
                time.sleep(1800)
                continue

            # ── IDLE: poll mỗi 5 phút ngoài giờ ─────────────────────────
            time.sleep(300)

        except Exception as e:
            safe_print(f"⚠️ [Scheduler] Unexpected error in fallback loop: {e}")
            time.sleep(60)


# ============================================================
# 4. ENTRYPOINT — DUY NHẤT 1 PROCESS CHẠY SCHEDULER
# ============================================================

def _is_pid_alive(pid: int) -> bool:
    """
    Kiểm tra process PID còn sống không (cross-platform: Windows + Unix).
    Ưu tiên psutil nếu có, fallback:
      - Windows: OpenProcess + GetExitCodeProcess (ctypes)
      - Unix: os.kill(pid, 0) signal=0 existence test
    """
    if not isinstance(pid, int) or pid <= 0:
        return False
    # 1) psutil (có sẵn trong nhiều môi trường data science)
    try:
        import psutil  # type: ignore
        return bool(psutil.pid_exists(pid))
    except Exception:
        pass
    # 2) Platform-specific fallback
    try:
        if sys.platform.startswith("win"):
            import ctypes
            PROCESS_QUERY_INFORMATION = 0x0400
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            proc_handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if not proc_handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                ok = kernel32.GetExitCodeProcess(proc_handle, ctypes.byref(exit_code))
                if not ok:
                    return False
                return bool(exit_code.value == STILL_ACTIVE)
            finally:
                kernel32.CloseHandle(proc_handle)
        else:
            # Unix / macOS: kill(pid, 0) sends no signal, just checks existence.
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def _lock_age_seconds(lock_path: str) -> float:
    """Số giây kể từ khi file lock được tạo/sửa đổi lần cuối (stale check dự phòng)."""
    try:
        return time.time() - os.path.getmtime(lock_path)
    except OSError:
        return 0.0


def start_periodic_scheduler() -> None:
    """
    Khởi động background scheduler (thread hoặc process) — đảm bảo chỉ có 1 worker chạy.
    Dùng lock file để phòng trường hợp multi-worker uvicorn/gunicorn.
      - Ưu tiên kiểm tra PID còn sống (psutil / OpenProcess)
      - Nếu PID chết HOẶC lock file quá stale (> 2 tiếng) → xóa file và lấy lock mới
    Ưu tiên APScheduler, nếu không có sẽ tự động fallback sang custom thread loop.
    """
    import tempfile
    lock_path = os.path.join(tempfile.gettempdir(), "finvista_scheduler.lock")
    STALE_LOCK_SECONDS = 7200  # 2 tiếng => xác định lock chết nếu quá lâu không update

    # Clean stale lock
    if os.path.exists(lock_path):
        should_remove = False
        try:
            with open(lock_path) as f:
                old_pid = int(f.read().strip())
            if old_pid == os.getpid():
                should_remove = True
            elif not _is_pid_alive(old_pid):
                should_remove = True
            elif _lock_age_seconds(lock_path) > STALE_LOCK_SECONDS:
                should_remove = True
        except (ValueError, OSError):
            should_remove = True
        if should_remove:
            try:
                os.remove(lock_path)
            except OSError:
                pass

    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except OSError:
        safe_print("ℹ️  [Scheduler] Another worker already owns scheduler lock — skip starting scheduler.")
        return

    # Step 1: thử APScheduler trước
    aps_ok = _try_start_apscheduler()
    if aps_ok:
        safe_print(f"🕒 [Scheduler] Engine: APScheduler (PID {os.getpid()} owns lock).\n")
        return

    # Step 2: fallback custom thread loop
    safe_print("🕒 [Scheduler] Engine: Custom thread loop (fallback).")
    t = threading.Thread(target=_scheduler_loop_fallback, daemon=True, name="FinvistaSchedulerFallback")
    t.start()
    safe_print(f"🕒 [Scheduler] Fallback thread started (PID {os.getpid()} owns lock).\n")
