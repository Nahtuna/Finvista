# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: AI CHAT ENDPOINT
==============================
AI-powered financial chat assistant using Gemini integration.

Author: samvo
"""

import re
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


class ChatMessage(BaseModel):
    role: str
    content: str
    image_base64: Optional[str] = None   # base64-encoded image for Vision requests
    image_media_type: Optional[str] = "image/png"


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict] = None


async def get_optional_current_user(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        from src.api.dependencies import get_current_user
        return get_current_user(token)
    except Exception:
        return None



@router.get("/context-summary")
async def get_context_summary():
    """
    Returns a dynamic AI-generated welcome greeting with live market data.
    Called once when the chat widget opens, to show fresh regime + top CW.
    """
    import datetime
    now = datetime.datetime.now()
    lines = []

    # Market regime
    try:
        from src.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
        regime = calculate_vnindex_regime(days=1250)
        regime_name = regime.get("regime", "UNKNOWN")
        bias = regime.get("bias", "NEUTRAL")
        confidence = regime.get("confidence", 0.0) * 100
        desc = regime.get("description", "")
        lines.append(
            f"Hệ thống Finvista ghi nhận thị trường đang ở trạng thái **{regime_name}** "
            f"({desc}), với xu hướng ưu tiên là **{bias}** (Độ tin cậy: {confidence:.1f}%)."
        )
    except Exception:
        lines.append("Hệ thống đang cập nhật trạng thái thị trường...")

    # Top CW opportunities
    try:
        from src.modules.cw_pricing.service import WarrantService
        opps_res = WarrantService.get_opportunities(limit=3)
        opps_list = opps_res.get("recommendations", [])
        total_count = opps_res.get("total_count", len(opps_list))

        buy_opps = [o for o in opps_list if "BUY" in (o.get("recommendation_signal") or "").upper()]
        if buy_opps:
            top = buy_opps[0]
            sym = top["warrant_symbol"]
            und = top["underlying_symbol"]
            gscore = top.get("composite_g_score", 0)
            delta = top.get("delta", 0)
            dtm = top.get("days_to_maturity", "?")
            price = top.get("market_price", 0)
            signal = top.get("recommendation_signal", "BUY")
            lines.append(
                f"\n📊 **Top tín hiệu {signal}: {sym}** (CPCS: {und})\n"
                f"G-Score: {gscore:.1f} | Δ Delta: {delta:.3f} | "
                f"Còn {dtm} ngày | Giá: {price:,} VNĐ"
            )
        elif opps_list:
            lines.append(f"\n📊 Đang theo dõi {len(opps_list)} mã chứng quyền — chưa có tín hiệu MUA rõ ràng phiên này.")
    except Exception:
        pass

    # Market snapshot
    try:
        from src.modules.cw_pricing.service import WarrantService
        mkt = WarrantService.get_underlying_market()
        indices = mkt.get("indices", {})
        snap_parts = []
        for idx_name in ["VNINDEX", "VN30", "HNXINDEX"]:
            idx = indices.get(idx_name) or {}
            if idx.get("close"):
                chg = idx.get("change_pct", 0) or 0
                arrow = "▲" if chg >= 0 else "▼"
                snap_parts.append(f"{idx_name} {idx['close']:,.2f} {arrow}{abs(chg):.2f}%")
        if snap_parts:
            lines.append("\n📈 " + "  |  ".join(snap_parts))
    except Exception:
        pass

    time_str = now.strftime("%H:%M ngày %d/%m/%Y")
    greeting = (
        f"Chào bạn! Tôi là **Finvista Quant AI** — Chuyên gia Phân tích Tài chính & "
        f"Cố vấn Đầu tư Chứng quyền/Cổ phiếu của bạn.\n\n"
        + "\n".join(lines)
        + f"\n\n_Dữ liệu cập nhật lúc {time_str}. Hỏi tôi bất cứ điều gì về thị trường, chứng quyền hoặc cổ phiếu nhé!_"
    )

    return {"greeting": greeting, "timestamp": now.isoformat()}


@router.post("/", response_model=ChatResponse)
async def chat_completion(request: ChatRequest, req_raw: Request):
    """
    AI-powered financial chat assistant with personalized context integration.
    """
    try:
        from src.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        # Check if AI client is properly configured
        if ai_client.use_web_api and not ai_client._is_port_open(8081):
            raise HTTPException(
                status_code=503,
                detail="AI service unavailable. Please configure OPENROUTER_API_KEY in environment variables."
            )
        
        # 1. Resolve optional logged-in user
        current_user = await get_optional_current_user(req_raw)
        
        # 2. Extract mentioned symbols from conversation history
        last_message = request.messages[-1].content if request.messages else ""
        candidate_symbols = []
        for msg in request.messages:
            candidate_symbols.extend(re.findall(r'\b[A-Z]{3,4}\b', msg.content))
        
        # Verify which ones are actual stock symbols in database
        symbols = []
        if candidate_symbols:
            try:
                from src.core.database import SessionLocal, StockHistoricalPrice, CompanyFinancial
                db_sess = SessionLocal()
                try:
                    valid_stock_symbols = {s[0].upper() for s in db_sess.query(StockHistoricalPrice.symbol).distinct().all()}
                    valid_company_tickers = {c[0].upper() for c in db_sess.query(CompanyFinancial.ticker).distinct().all()}
                    all_valid_symbols = valid_stock_symbols.union(valid_company_tickers)
                    for sym in set(candidate_symbols):
                        if sym.upper() in all_valid_symbols:
                            symbols.append(sym.upper())
                finally:
                    db_sess.close()
            except Exception:
                # Fallback to simple filtering if db query fails
                EXCLUDE_KEYWORDS = {"ICR", "OCF", "ROA", "ROE", "HMM", "QUY", "MUA", "SAI", "EBIT", "SHAP", "NAV"}
                for sym in set(candidate_symbols):
                    if sym.upper() not in EXCLUDE_KEYWORDS:
                        symbols.append(sym.upper())
        
        # 3. Gather quantitative contexts
        system_context = []
        
        # 3.1 Market Regime
        try:
            from src.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
            regime = calculate_vnindex_regime(days=1250)
            system_context.append(
                f"TRẠNG THÁI THỊ TRƯỜNG HIỆN TẠI (HMM Model):\n"
                f"- Regime: {regime.get('regime', 'UNKNOWN')}\n"
                f"- Bias: {regime.get('bias', 'NEUTRAL')}\n"
                f"- Confidence: {regime.get('confidence', 0.0) * 100:.1f}%\n"
                f"- Mô tả: {regime.get('description', '')}\n"
            )
        except Exception:
            pass
            
        # 3.2 User's Portfolio (Fallback to demo user if not logged in)
        active_username = current_user["username"] if current_user else "demo"
        try:
            from src.modules.trading_engine.portfolio_service import PortfolioService
            port = PortfolioService.get_portfolio(username=active_username)
            if port and port.get("status") == "success":
                assets = port.get("assets", [])
                asset_str = ""
                for a in assets:
                    asset_str += f"  + {a['symbol']}: Số lượng {a['qty']}, Giá vốn {a['avg_price']:,} VNĐ, Giá hiện tại {a['market_price']:,} VNĐ, Lãi/Lỗ: {a['pnl_pct']:.2f}%\n"
                system_context.append(
                    f"DANH MỤC ĐẦU TƯ ĐANG THEO DÕI (User: {active_username}):\n"
                    f"- Số dư tiền mặt: {port.get('cash', 0):,} VNĐ\n"
                    f"- Tổng giá trị tài sản (NAV): {port.get('total_value', 0):,} VNĐ\n"
                    f"- Các vị thế đang nắm giữ:\n{asset_str if asset_str else '  (Chưa nắm giữ tài sản nào)'}\n"
                )
        except Exception:
            pass
                
        # 3.3 Ticker Specific Data (News & Events)
        ticker_info = ""
        for sym in set(symbols):
            try:
                from src.modules.cw_pricing.service import WarrantService
                news_res = WarrantService.get_news(symbol=sym, limit=3)
                news_list = news_res.get("news", [])
                if news_list:
                    ticker_info += f"Tin tức gần đây của {sym}:\n"
                    for n in news_list:
                        ticker_info += f"  - [{n['date']}] {n['title']}: {n['summary'] or ''}\n"
            except Exception:
                pass
                
            try:
                from src.modules.cw_pricing.service import WarrantService
                event_res = WarrantService.get_events(ticker=sym, limit=2)
                events = event_res.get("events", [])
                if events:
                    ticker_info += f"Sự kiện sắp tới của {sym}:\n"
                    for ev in events:
                        ticker_info += f"  - [{ev['event_date']}] {ev['event_type']}: {ev['description']}\n"
            except Exception:
                pass

            # Query financials & credit risk from SQLite
            try:
                from src.core.database import SessionLocal, CompanyFinancial, CompanyDistressAnalysis
                db_sess = SessionLocal()
                try:
                    fins = db_sess.query(CompanyFinancial).filter(CompanyFinancial.ticker == sym).order_by(CompanyFinancial.year.desc()).all()
                    distress = db_sess.query(CompanyDistressAnalysis).filter(CompanyDistressAnalysis.ticker == sym).order_by(CompanyDistressAnalysis.year.desc()).all()
                    
                    if fins:
                        ticker_info += f"Dữ liệu BCTC thực tế của {sym} trong hệ thống:\n"
                        for f in fins:
                            ticker_info += (
                                f"  - Năm {f.year}: Doanh thu {f.net_revenue:,.0f} VND, LNST {f.profit_after_tax:,.0f} VND, "
                                f"Tổng tài sản {f.total_assets:,.0f} VND, Tổng nợ {f.total_liabilities:,.0f} VND, "
                                f"Vốn chủ sở hữu {f.total_equity:,.0f} VND, Dòng tiền HĐKD {f.operating_cash_flow:,.0f} VND\n"
                            )
                    if distress:
                        ticker_info += f"Chỉ số tài chính & Phân tích rủi ro của {sym} trong hệ thống:\n"
                        for d in distress:
                            ticker_info += (
                                f"  - Năm {d.year}: Tỷ số thanh toán hiện hành {d.current_ratio:.2f}, "
                                f"Tỷ lệ nợ/tài sản {d.debt_ratio:.2f}, ROAA {d.roaa*100:.2f}%, ROAE {d.roae*100:.2f}%, "
                                f"Altman Z-Score {d.altman_z_score:.2f}, Merton Probability of Default {d.merton_pd*100:.2f}%\n"
                            )
                finally:
                    db_sess.close()
            except Exception:
                pass
                
        if ticker_info:
            system_context.append(f"THÔNG TIN DOANH NGHIỆP TRUY VẤN:\n{ticker_info}")
            
        # 3.4 Ranked Opportunities
        try:
            from src.modules.cw_pricing.service import WarrantService
            opps = WarrantService.get_opportunities(limit=5)
            opps_list = opps.get("recommendations", [])
            if opps_list:
                opps_str = ""
                for o in opps_list:
                    opps_str += f"  - {o['warrant_symbol']} (Cơ sở: {o['underlying_symbol']}): Tín hiệu {o['recommendation_signal']}, G-Score {o['composite_g_score']}, Greeks Delta {o['delta']}, Giá {o['market_price']} VNĐ\n"
                system_context.append(f"TOP CƠ HỘI ĐẦU TƯ CHỨNG QUYỀN (G-Score cao nhất):\n{opps_str}")
        except Exception:
            pass

        # 3.5 Query BCTC/Annual Report via RAG if the user asks about financial reports
        try:
            years_mentioned = [int(y) for y in re.findall(r'\b(20\d{2})\b', last_message)]
            report_keywords = ["bctc", "báo cáo tài chính", "báo cáo thường niên", "báo cáo", "annual report", "năm", "vòng quay", "số liệu", "data"]
            is_asking_about_reports = any(kw in last_message.lower() for kw in report_keywords)
            
            if is_asking_about_reports and symbols:
                if not years_mentioned:
                    for msg in reversed(request.messages[:-1]):
                        years = [int(y) for y in re.findall(r'\b(20\d{2})\b', msg.content)]
                        if years:
                            years_mentioned = years
                            break
                
                query_year = years_mentioned[0] if years_mentioned else 2025
                report_rag_context = ""
                for sym in set(symbols):
                    from src.modules.annual_reports.manager import AnnualReportManager
                    report_mgr = AnnualReportManager()
                    rag_answer = report_mgr.query_report(
                        ticker=sym,
                        year=query_year,
                        quarter=5,
                        question=last_message
                    )
                    if rag_answer and not rag_answer.startswith("❌"):
                        report_rag_context += f"  - Kết quả RAG từ BCTC {sym} năm {query_year}: {rag_answer}\n"
                
                if report_rag_context:
                    system_context.append(f"KẾT QUẢ TRUY VẤN RAG BCTC DÀNH CHO CÂU HỎI HIỆN TẠI:\n{report_rag_context}")
        except Exception:
            pass
            
        # 3.5 Peer Comparison (Industry Benchmark) — inject percentile vs. industry
        try:
            from src.core.database import CompanyDistressAnalysis
            for sym in set(symbols):
                db_sess = SessionLocal()
                try:
                    # Get the most recent distress record for this ticker
                    dist_latest = (
                        db_sess.query(CompanyDistressAnalysis)
                        .filter(CompanyDistressAnalysis.ticker == sym)
                        .order_by(CompanyDistressAnalysis.year.desc())
                        .first()
                    )
                    if dist_latest:
                        industry_str = dist_latest.industry or "Không xác định"
                        roae_pct = dist_latest.roae * 100 if dist_latest.roae else None
                        roaa_pct = dist_latest.roaa * 100 if dist_latest.roaa else None
                        debt_ratio = dist_latest.debt_ratio

                        # Percentile positions in industry
                        roae_pctile = dist_latest.industry_roae_percentile
                        roaa_pctile = dist_latest.industry_roaa_percentile
                        debt_pctile = dist_latest.industry_debt_ratio_percentile

                        peer_lines = [f"So sánh ngành của {sym} (Ngành: {industry_str}, Năm {dist_latest.year}):"]
                        if roae_pct is not None and roae_pctile is not None:
                            peer_lines.append(
                                f"  - ROAE: {roae_pct:.2f}% — vượt {roae_pctile*100:.0f}% doanh nghiệp cùng ngành"
                            )
                        if roaa_pct is not None and roaa_pctile is not None:
                            peer_lines.append(
                                f"  - ROAA: {roaa_pct:.2f}% — vượt {roaa_pctile*100:.0f}% doanh nghiệp cùng ngành"
                            )
                        if debt_ratio is not None and debt_pctile is not None:
                            peer_lines.append(
                                f"  - Tỷ lệ nợ/tài sản: {debt_ratio:.2f} — cao hơn {debt_pctile*100:.0f}% ngành"
                                f" ({'Thận trọng' if debt_ratio > 0.7 else 'Bình thường'})"
                            )
                        if dist_latest.altman_z_score is not None:
                            z = dist_latest.altman_z_score
                            z_label = (
                                "AN TOÀN" if z > 2.99
                                else "VÙNG XÁM" if z > 1.81
                                else "CÓ RỦI RO"
                            )
                            peer_lines.append(f"  - Altman Z-Score: {z:.2f} ({z_label})")
                        if dist_latest.merton_pd is not None:
                            pd_pct = dist_latest.merton_pd * 100
                            peer_lines.append(
                                f"  - Xác suất vỡ nợ Merton: {pd_pct:.3f}%"
                                f" ({'Rủi ro cao' if pd_pct > 5 else 'Bình thường'})"
                            )
                        if len(peer_lines) > 1:
                            system_context.append("SO SÁNH NGÀNH (PEER COMPARISON):\n" + "\n".join(peer_lines))
                finally:
                    db_sess.close()
        except Exception:
            pass

        # 3.6 CAGR & Growth Trend — multi-year revenue & profit growth
        try:
            from src.core.database import CompanyFinancial
            for sym in set(symbols):
                db_sess = SessionLocal()
                try:
                    fins_all = (
                        db_sess.query(CompanyFinancial)
                        .filter(CompanyFinancial.ticker == sym)
                        .order_by(CompanyFinancial.year.asc())
                        .all()
                    )
                    if len(fins_all) >= 2:
                        oldest = fins_all[0]
                        latest = fins_all[-1]
                        n_years = latest.year - oldest.year
                        if n_years > 0:
                            growth_lines = [f"Xu hướng tăng trưởng {n_years} năm của {sym} ({oldest.year}–{latest.year}):"]

                            # Revenue CAGR
                            if oldest.net_revenue and latest.net_revenue and oldest.net_revenue > 0:
                                rev_cagr = (latest.net_revenue / oldest.net_revenue) ** (1 / n_years) - 1
                                growth_lines.append(
                                    f"  - CAGR Doanh thu: {rev_cagr*100:.1f}%/năm "
                                    f"({oldest.net_revenue/1e9:.0f} tỷ → {latest.net_revenue/1e9:.0f} tỷ VND)"
                                )

                            # PAT CAGR
                            if (oldest.profit_after_tax and latest.profit_after_tax
                                    and oldest.profit_after_tax > 0 and latest.profit_after_tax > 0):
                                pat_cagr = (latest.profit_after_tax / oldest.profit_after_tax) ** (1 / n_years) - 1
                                growth_lines.append(
                                    f"  - CAGR Lợi nhuận sau thuế: {pat_cagr*100:.1f}%/năm "
                                    f"({oldest.profit_after_tax/1e9:.0f} tỷ → {latest.profit_after_tax/1e9:.0f} tỷ VND)"
                                )

                            # Asset growth
                            if oldest.total_assets and latest.total_assets and oldest.total_assets > 0:
                                asset_cagr = (latest.total_assets / oldest.total_assets) ** (1 / n_years) - 1
                                growth_lines.append(
                                    f"  - CAGR Tổng tài sản: {asset_cagr*100:.1f}%/năm"
                                )

                            # Operating cash flow trend (latest only)
                            if latest.operating_cash_flow:
                                ocf_sign = "Dương ✅" if latest.operating_cash_flow > 0 else "Âm ⚠️"
                                growth_lines.append(
                                    f"  - Dòng tiền HĐKD năm {latest.year}: "
                                    f"{latest.operating_cash_flow/1e9:.0f} tỷ VND ({ocf_sign})"
                                )

                            if len(growth_lines) > 1:
                                system_context.append("PHÂN TÍCH XU HƯỚNG TĂNG TRƯỞNG:\n" + "\n".join(growth_lines))
                finally:
                    db_sess.close()
        except Exception:
            pass

        # 3.7 Actionable Levels — Entry/SL/TP/R:R/Theta for BUY or WATCH CWs
        try:
            from src.modules.cw_pricing.service import WarrantService as WS
            # Get the CW opportunities already fetched (reuse from 3.4)
            opps_for_levels = WS.get_opportunities(limit=10)
            target_cws = [
                o for o in opps_for_levels.get("recommendations", [])
                if o.get("recommendation_signal") and
                any(kw in (o.get("recommendation_signal") or "").upper()
                    for kw in ["BUY", "WATCH"])
            ]
            if target_cws:
                levels_str = "MỐC GIÁ HÀNH ĐỘNG (Entry/SL/TP/R:R) — Tính từ dữ liệu BSM:\n"
                for opp in target_cws[:3]:  # max 3 mã
                    cw_sym = opp["warrant_symbol"]
                    lvl = WS.get_actionable_levels(cw_sym)
                    if lvl.get("status") == "ok":
                        cl = lvl["cw_levels"]
                        thr = lvl["theta_risk"]
                        ul = lvl["underlying_levels"]
                        time_warn = lvl.get("time_warning", "")
                        levels_str += (
                            f"\nMã {cw_sym} (CPCS: {lvl['underlying_symbol']}) — {lvl['signal']}\n"
                            f"  Chứng quyền CW:\n"
                            f"    Entry       : {cl['entry']:,} VNĐ\n"
                            f"    Cắt lỗ (SL) : {cl['stop_loss']:,} VNĐ ({cl['stop_loss_pct']:.0f}%)\n"
                            f"    Mục tiêu 1  : {cl['take_profit_1']:,} VNĐ (+{cl['take_profit_1_pct']:.1f}%) ← CPCS +5%\n"
                            f"    Mục tiêu 2  : {cl['take_profit_2']:,} VNĐ (+{cl['take_profit_2_pct']:.1f}%) ← CPCS +10%\n"
                            f"    R:R Ratio   : 1:{cl['risk_reward_ratio']} {cl['rr_quality']}\n"
                            f"    Theta burn  : -{thr['theta_pct_daily']:.2f}%/ngày "
                            f"(cầm 5 ngày ≈ -{thr['cost_5_days_pct']:.1f}%)\n"
                            f"  Cổ phiếu cơ sở {lvl['underlying_symbol']}:\n"
                            f"    Vùng gom    : {ul['entry_zone_low']:,} – {ul['entry_zone_high']:,} VNĐ\n"
                            f"    Mục tiêu 1  : {ul['target_5pct']:,} VNĐ (+5%)\n"
                            f"    Mục tiêu 2  : {ul['target_10pct']:,} VNĐ (+10%)\n"
                            f"    Cắt lỗ     : {ul['stop_loss']:,} VNĐ (-7%)\n"
                            f"    Break-even  : {ul['break_even_price']:,.0f} VNĐ\n"
                            f"  ⏱️ {time_warn}\n"
                        )
                system_context.append(levels_str)
        except Exception:
            pass

        # 3.8 Live Market Snapshot — VNINDEX, VN30, top gainers/losers
        try:
            from src.modules.cw_pricing.service import WarrantService
            mkt = WarrantService.get_underlying_market()
            indices = mkt.get("indices", {})
            underlyings = mkt.get("underlyings", [])

            snap_lines = ["TỔNG QUAN THỊ TRƯỜNG PHIÊN HÔM NAY:"]
            for idx_name in ["VNINDEX", "VN30", "HNXINDEX"]:
                idx = indices.get(idx_name) or {}
                if idx.get("close"):
                    chg = idx.get("change_pct", 0) or 0
                    arrow = "▲" if chg >= 0 else "▼"
                    snap_lines.append(
                        f"  - {idx_name}: {idx['close']:,.2f} điểm  {arrow}{abs(chg):.2f}%  "
                        f"Khớp lệnh: {idx.get('total_volume', 0):,} CP"
                    )

            if underlyings:
                sorted_u = sorted(underlyings, key=lambda x: x.get("change_pct") or 0, reverse=True)
                gainers = [u for u in sorted_u if (u.get("change_pct") or 0) > 0][:3]
                losers  = [u for u in sorted_u if (u.get("change_pct") or 0) < 0][-3:]
                if gainers:
                    snap_lines.append("  Tăng mạnh nhất: " + " | ".join(
                        f"{u['symbol']} +{u.get('change_pct',0):.2f}%" for u in gainers
                    ))
                if losers:
                    snap_lines.append("  Giảm mạnh nhất: " + " | ".join(
                        f"{u['symbol']} {u.get('change_pct',0):.2f}%" for u in reversed(losers)
                    ))

            if len(snap_lines) > 1:
                system_context.append("\n".join(snap_lines))
        except Exception:
            pass

        # 3.9 Seasonal Intelligence — monthly win-rate from DB historical prices
        try:
            import datetime as _dt
            from src.core.database import SessionLocal, StockHistoricalPrice
            current_month = _dt.datetime.now().month
            month_names_vi = ["", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
                              "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
                              "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]

            db_s = SessionLocal()
            try:
                rows = (
                    db_s.query(StockHistoricalPrice.date, StockHistoricalPrice.close)
                    .filter(StockHistoricalPrice.symbol == "VNINDEX")
                    .order_by(StockHistoricalPrice.date.asc())
                    .all()
                )
            finally:
                db_s.close()

            if rows:
                # Compute monthly return for VNINDEX for each calendar month
                monthly_returns = {m: [] for m in range(1, 13)}
                prev_close = None
                prev_mo = None
                mo_start = None
                for r in rows:
                    try:
                        dt = _dt.datetime.strptime(r.date, "%Y-%m-%d")
                        mo = dt.month
                        c = float(r.close)
                        if c > 10000:
                            c /= 1000.0
                        if prev_mo is not None and mo != prev_mo and mo_start is not None and mo_start > 0:
                            monthly_returns[prev_mo].append((c - mo_start) / mo_start * 100)
                        if mo != prev_mo:
                            mo_start = c
                        prev_mo = mo
                    except Exception:
                        continue

                # Build win-rate for each month
                cur_mo_data = monthly_returns.get(current_month, [])
                wins = sum(1 for x in cur_mo_data if x > 0)
                total = len(cur_mo_data)
                win_rate = round(wins / total * 100) if total > 0 else None
                avg_ret = round(sum(cur_mo_data) / total, 2) if total > 0 else None

                # Find best and worst months overall
                best_mo = max(range(1, 13), key=lambda m: (
                    sum(1 for x in monthly_returns[m] if x > 0) / len(monthly_returns[m])
                    if monthly_returns[m] else 0
                ))
                worst_mo = min(range(1, 13), key=lambda m: (
                    sum(1 for x in monthly_returns[m] if x > 0) / len(monthly_returns[m])
                    if monthly_returns[m] else 1
                ))

                season_lines = [
                    f"PHÂN TÍCH MÙA VỤ VNINDEX (dữ liệu lịch sử {len(rows)} phiên):",
                    f"  - {month_names_vi[current_month]} (tháng hiện tại): "
                    + (f"Tỷ lệ thắng {win_rate}% / {total} năm, TB {avg_ret:+.2f}%/tháng"
                       if win_rate is not None else "Chưa đủ dữ liệu"),
                    f"  - Tháng tốt nhất lịch sử: {month_names_vi[best_mo]}",
                    f"  - Tháng rủi ro nhất lịch sử: {month_names_vi[worst_mo]}",
                ]
                system_context.append("\n".join(season_lines))
        except Exception:
            pass

        # 3.10 CW Screener Summary — signal distribution + expiring soon
        try:
            from src.modules.cw_pricing.service import WarrantService as _WS
            all_opps = _WS.get_opportunities(limit=500)
            all_recs = all_opps.get("recommendations", [])
            if all_recs:
                buy_cnt = sum(1 for r in all_recs if "BUY" in (r.get("recommendation_signal") or "").upper())
                sell_cnt = sum(1 for r in all_recs if "SELL" in (r.get("recommendation_signal") or "").upper())
                neutral_cnt = len(all_recs) - buy_cnt - sell_cnt

                top3 = sorted(all_recs, key=lambda r: r.get("composite_g_score") or 0, reverse=True)[:3]
                expiring = sorted(
                    [r for r in all_recs if (r.get("days_to_maturity") or 999) <= 30],
                    key=lambda r: r.get("days_to_maturity") or 999
                )[:3]

                cw_sum_lines = [
                    f"TỔNG QUAN THỊ TRƯỜNG CHỨNG QUYỀN ({len(all_recs)} mã đang lưu hành):",
                    f"  Tín hiệu: 🟢 MUA {buy_cnt} | 🔴 BÁN {sell_cnt} | ⚪ TRUNG TÍNH {neutral_cnt}",
                ]
                if top3:
                    cw_sum_lines.append("  Top G-Score cao nhất: " + " | ".join(
                        f"{r['warrant_symbol']} (G={r.get('composite_g_score',0):.1f}, "
                        f"Δ={r.get('delta',0):.2f}, DTM={r.get('days_to_maturity','?')}d)"
                        for r in top3
                    ))
                if expiring:
                    cw_sum_lines.append("  Sắp đáo hạn (≤30 ngày): " + " | ".join(
                        f"{r['warrant_symbol']} còn {r.get('days_to_maturity','?')} ngày"
                        for r in expiring
                    ))
                system_context.append("\n".join(cw_sum_lines))
        except Exception:
            pass

        import datetime
        current_time_dt = datetime.datetime.now()
        current_time_str = current_time_dt.strftime("%d/%m/%Y %H:%M:%S")
        current_date_vn = current_time_dt.strftime("%d/%m/%Y")
        current_month_name = ["", "Tháng Một", "Tháng Hai", "Tháng Ba", "Tháng Tư",
                              "Tháng Năm", "Tháng Sáu", "Tháng Bảy", "Tháng Tám",
                              "Tháng Chín", "Tháng Mười", "Tháng Mười Một", "Tháng Mười Hai"][current_time_dt.month]
        system_prompt = (
            "Bạn là Finvista Quant AI — Chuyên gia Phân tích Tài chính & Cố vấn Đầu tư Chứng quyền/Cổ phiếu cấp cao của hệ thống Finvista.\n"
            f"Thời gian hiện tại của hệ thống: Ngày {current_date_vn} ({current_time_str}), {current_month_name}.\n\n"
            "## CHỈ THỊ & PHONG CÁCH TRẢ LỜI (PROMPT CHUYÊN SÂU):\n"
            f"1. Bạn ĐÃ ĐƯỢC CẤP QUYỀN TRUY CẬP TRỰC TIẾP vào toàn bộ dữ liệu định lượng, danh mục đầu tư (NAV, vị thế), tín hiệu chứng quyền BSM/Greeks, điểm G-Score, báo cáo BCTC, phân tích mùa vụ, và tổng quan thị trường phiên hôm nay trong hệ thống Finvista.\n"
            "2. Khi chào hỏi hoặc trả lời, hãy trả lời tự nhiên, thân thiện và đi thẳng vào phân tích tài chính/chứng khoán. Không được nói 'tôi không có thông tin định danh cá nhân của bạn'.\n"
            "3. Khi người dùng hỏi về danh mục hoặc vị thế, hãy chủ động phân tích các mã chứng quyền/cổ phiếu trong danh mục đang theo dõi (NAV, Lãi/Lỗ, tỷ trọng).\n"
            "4. Khi context có 'MỐC GIÁ HÀNH ĐỘNG', BẮT BUỘC trình bày đầy đủ các mốc Entry / Cắt lỗ (SL) / Chốt lời (TP) / Tỷ lệ R:R và rủi ro thời gian Theta decay.\n"
            "5. Kết luận phân tích PHẢI DỨT KHOÁT: MUA (BUY) / CHỜ (WATCH) / ĐỨNG NGOÀI (NEUTRAL). Tránh dùng các từ chung chung mơ hồ.\n"
            "6. Khi user hỏi về thị trường hôm nay, PHẢI tham chiếu dữ liệu 'TỔNG QUAN THỊ TRƯỜNG PHIÊN HÔM NAY' bên dưới.\n"
            "7. Khi user hỏi về mùa vụ hoặc tháng nào nên mua, PHẢI tham chiếu 'PHÂN TÍCH MÙA VỤ VNINDEX' từ dữ liệu lịch sử thực.\n"
            "8. Khi user hỏi tổng quan CW hoặc mã nào tốt, PHẢI tham chiếu 'TỔNG QUAN THỊ TRƯỜNG CHỨNG QUYỀN' với phân phối tín hiệu thực tế.\n\n"
            "## DỮ LIỆU ĐỊNH LƯỢNG THỜI GIAN THỰC TỪ FINVISTA SYSTEM:\n"
        )
        system_prompt += "\n\n".join(system_context)
        
        # Extract image from the last user message (if any)
        last_user_msg = next(
            (m for m in reversed(request.messages) if m.role == "user"),
            None
        )
        image_b64 = last_user_msg.image_base64 if last_user_msg else None
        image_mime = (last_user_msg.image_media_type or "image/png") if last_user_msg else "image/png"
        
        # Convert Pydantic models to dicts and prepend system message
        messages_dict = [{"role": "system", "content": system_prompt}] + [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        response = ai_client.chat(
            messages=messages_dict,
            image_base64=image_b64,
            image_media_type=image_mime,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not response:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty response"
            )
        
        return ChatResponse(
            response=response,
            model=request.model or ai_client.default_model
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat completion failed: {str(e)}"
        )


@router.post("/financial-commentary")
async def generate_financial_commentary(
    ticker: str,
    current_ratio: float,
    debt_ratio: float,
    altman_z_score: float,
    profit_after_tax: float = 0.0,
    operating_cash_flow: float = 0.0,
    ebit_to_interest: float = 9999.0
):
    """
    Generate AI-powered financial commentary for distressed companies.
    
    This endpoint provides the same functionality used in Telegram alerts
    but accessible via REST API.
    """
    try:
        from src.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        commentary = ai_client.generate_financial_commentary(
            ticker=ticker,
            current_ratio=current_ratio,
            debt_ratio=debt_ratio,
            altman_z_score=altman_z_score,
            profit_after_tax=profit_after_tax,
            operating_cash_flow=operating_cash_flow,
            ebit_to_interest=ebit_to_interest
        )
        
        if not commentary:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty commentary"
            )
        
        return {
            "ticker": ticker,
            "commentary": commentary,
            "model": ai_client.default_model
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Financial commentary generation failed: {str(e)}"
        )


@router.post("/trading-signal-commentary")
async def generate_trading_signal_commentary(
    cw_code: str,
    signal: str,
    g_score: float,
    price: float,
    leverage: float,
    days_to_expiry: int,
    price_change_pct: float
):
    """
    Generate AI-powered commentary for CW trading signals.
    
    This endpoint provides AI analysis for trading signals
    used in the quantitative trading system.
    """
    try:
        from src.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client()
        
        commentary = ai_client.generate_trading_signal_commentary(
            cw_code=cw_code,
            signal=signal,
            g_score=g_score,
            price=price,
            leverage=leverage,
            days_to_expiry=days_to_expiry,
            price_change_pct=price_change_pct
        )
        
        if not commentary:
            raise HTTPException(
                status_code=500,
                detail="AI service returned empty commentary"
            )
        
        return {
            "cw_code": cw_code,
            "signal": signal,
            "commentary": commentary,
            "model": ai_client.default_model
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Trading signal commentary generation failed: {str(e)}"
        )
