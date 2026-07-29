# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: ATC (END-OF-SESSION CLOSE PRICE) API ROUTES
=========================================================
API endpoints để quản lý & kiểm tra trạng thái dữ liệu giá chốt phiên ATC.

Author: samvo
Version: 1.0
"""

import os
import sys
import threading
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.modules.atc_manager.service import (
    sync_atc_data,
    check_data_freshness,
    get_last_trading_day,
    get_atc_sync_status,
    run_startup_atc_check_and_sync,
)


router = APIRouter(tags=["atc — end-of-session close price"])


@router.get("/api/atc/status")
def atc_get_status(limit_logs: int = Query(10, ge=1, le=50)):
    """
    Kiểm tra trạng thái độ tươi mới của dữ liệu ATC.
    Trả về:
      - expected_trading_day: ngày giao dịch gần nhất cần có dữ liệu
      - atc_stock / atc_cw: latest_in_db, is_ok
      - is_up_to_date: True nếu cả stock & cw đều đã đủ data
      - recent_sync_logs: 10 log sync gần nhất
      - freshness_states: tổng số record & ngày mới nhất theo DataFreshnessState
    """
    try:
        result = get_atc_sync_status(limit=limit_logs)
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ATC status: {str(e)}",
        )


@router.get("/api/atc/last-trading-day")
def atc_get_last_trading_day():
    """
    Trả về ngày giao dịch gần nhất (bỏ qua T7, Chủ Nhật, ngày lễ VN).
    Useful để debug / verify logic tính ngày.
    """
    last_day = get_last_trading_day()
    return {"status": "ok", "last_trading_day": last_day}


@router.get("/api/atc/quick-status")
def atc_get_quick_status():
    """
    Endpoint NHANH cho FRONTEND dashboard badge.
    Trả về thông tin ngắn gọn: ngày STOCK/CW mới nhất trong DB, ngày kỳ vọng,
    bool is_up_to_date, số ngày trễ, màu badge, text hiển thị.
    Được gọi mỗi 60s từ trang chủ + sidebar để cảnh báo data outdated.
    """
    from datetime import datetime

    try:
        # Lấy freshness check
        fresh = check_data_freshness()
        expected = fresh["expected_trading_day"]

        # Tính số ngày trễ (so với expected)
        def _days_diff(actual_str: Optional[str]) -> Optional[int]:
            if not actual_str:
                return None
            try:
                a_dt = datetime.strptime(actual_str, "%Y-%m-%d")
                e_dt = datetime.strptime(expected, "%Y-%m-%d")
                return max(0, (e_dt - a_dt).days)
            except Exception:
                return None

        stock_latest = fresh["atc_stock"]["latest_in_db"]
        cw_latest = fresh["atc_cw"]["latest_in_db"]
        stock_behind = _days_diff(stock_latest)
        cw_behind = _days_diff(cw_latest)

        # Overall status
        is_up_to_date = fresh["is_up_to_date"]

        # Định dạng ngày Việt Nam DD/MM cho frontend hiển thị gọn
        def _fmt_ddmm(s: Optional[str]) -> str:
            if not s:
                return "N/A"
            try:
                return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m")
            except Exception:
                return s

        stock_fmt = _fmt_ddmm(stock_latest)
        cw_fmt = _fmt_ddmm(cw_latest)
        expected_fmt = _fmt_ddmm(expected)

        # Badge color & display text (frontend vẫn có thể override)
        if is_up_to_date:
            severity = "ok"
            badge_color = "#10b981"  # green
            short_text = f"Data {expected_fmt} · Mới nhất"
            long_text = f"Dữ liệu đến {expected_fmt} · Mới nhất"
            suggest_sync = False
        else:
            # Severity = warning nếu ít ngày, danger nếu nhiều ngày
            max_behind = max([d for d in [stock_behind, cw_behind] if d is not None] or [0])
            if max_behind >= 3:
                severity = "danger"
                badge_color = "#ef4444"  # red
            else:
                severity = "warning"
                badge_color = "#f59e0b"  # amber
            short_text_parts = []
            if stock_behind and stock_behind > 0:
                short_text_parts.append(f"CK {stock_fmt}(-{stock_behind}d)")
            if cw_behind and cw_behind > 0:
                short_text_parts.append(f"CW {cw_fmt}(-{cw_behind}d)")
            short_text = " | ".join(short_text_parts) if short_text_parts else "Dữ liệu cũ"
            long_text = (
                f"Dữ liệu đang cũ · Cần đến ngày {expected_fmt} · "
                f"Cổ phiếu: {stock_fmt} ({stock_behind}d) · "
                f"Chứng quyền: {cw_fmt} ({cw_behind}d)"
            )
            suggest_sync = True

        return {
            "status": "ok",
            "is_up_to_date": is_up_to_date,
            "severity": severity,          # "ok" | "warning" | "danger"
            "badge_color": badge_color,
            "expected_trading_day": expected,
            "expected_trading_day_fmt": expected_fmt,
            "stock_latest": stock_latest,
            "stock_latest_fmt": stock_fmt,
            "stock_days_behind": stock_behind,
            "cw_latest": cw_latest,
            "cw_latest_fmt": cw_fmt,
            "cw_days_behind": cw_behind,
            "short_text": short_text,
            "long_text": long_text,
            "suggest_sync": suggest_sync,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quick ATC status: {str(e)}",
        )


@router.post("/api/atc/sync")
def atc_trigger_sync(
    background_tasks: BackgroundTasks,
    sync_type: str = Query("ALL", enum=["STOCK", "CW", "ALL"], description="Kiểu dữ liệu cần sync"),
    target_date: Optional[str] = Query(None, description="Ngày phiên cần sync (YYYY-MM-DD). Mặc định = ngày giao dịch gần nhất."),
    force: bool = Query(False, description="Bỏ qua freshness check & sync lại ngay cả khi data đã up-to-date."),
    blocking: bool = Query(False, description="True = response trả về sau khi sync xong; False = chạy background (default)."),
):
    """
    Trigger thủ công việc sync dữ liệu ATC (giá chốt phiên).
    Sử dụng khi:
      - Muốn cập nhật lại dữ liệu thủ công
      - Test chức năng sync
      - Bổ sung dữ liệu thiếu cho 1 ngày cụ thể
    """
    trigger_source = "MANUAL_API"

    # Validate target_date
    if target_date:
        try:
            from datetime import datetime
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_date không hợp lệ. Phải theo format YYYY-MM-DD.",
            )

    if blocking:
        # Đợi sync xong rồi mới trả response
        try:
            result = sync_atc_data(
                sync_type=sync_type,
                trigger_source=trigger_source,
                target_date=target_date,
                force=force,
            )
            return {"status": "completed", "result": result}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ATC sync failed: {str(e)}",
            )
    else:
        # Chạy background task
        def _bg_sync():
            try:
                sync_atc_data(
                    sync_type=sync_type,
                    trigger_source=trigger_source,
                    target_date=target_date,
                    force=force,
                )
            except Exception as exc:
                print(f"⚠️ [ATC API] Background sync error: {exc}")

        background_tasks.add_task(_bg_sync)
        return {
            "status": "started_in_background",
            "message": f"Background ATC sync started. Check /api/atc/status để xem log trạng thái.",
            "params": {"sync_type": sync_type, "target_date": target_date, "force": force},
        }


@router.post("/api/atc/startup-check")
def atc_run_startup_check(blocking: bool = Query(True)):
    """
    Chạy lại thủ công logic Startup Check.
    Giống như lúc app vừa khởi động: check freshness + trigger sync nếu cần.
    """
    try:
        result = run_startup_atc_check_and_sync(blocking=blocking)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Startup check error: {str(e)}",
        )


@router.get("/api/atc/freshness-check")
def atc_freshness_check(expected_date: Optional[str] = Query(None, description="YYYY-MM-DD. Mặc định = ngày giao dịch gần nhất.")):
    """
    Endpoint nhanh để kiểm tra độ tươi dữ liệu (không trigger sync).
    """
    try:
        result = check_data_freshness(expected_date=expected_date)
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Freshness check failed: {str(e)}",
        )


@router.get("/api/atc/scheduler-status")
def atc_get_scheduler_status():
    """
    KIỂM TRA LUỒNG 3: Xác nhận Background Scheduler đang chạy đúng lịch 15:15 T2-T6.
    Trả về:
      - now_vietnam_time: thời gian hiện tại theo giờ VN (đối chiếu với next_run_time)
      - engine.apscheduler.running / engine.fallback_thread_loop.running (engine nào hoạt động)
      - List jobs (có job id=atc_eod_sync không? next_run_time có đúng 15:15 ngày T2-T6 tiếp theo không?)
    """
    try:
        from src.api.scheduler import get_scheduler_status
        return {"status": "ok", **get_scheduler_status()}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}",
        )
