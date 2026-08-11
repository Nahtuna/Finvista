# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: AI CHAT ENDPOINT V2 - OPTIMIZED
===========================================
AI-powered financial chat assistant with parallel async context gathering.
Performance optimized for production scale.

Author: samvo
Version: 2.0
"""

import re
import asyncio
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
        from backend.api.dependencies import get_current_user
        return get_current_user(token)
    except Exception:
        return None


# === ASYNC CONTEXT GATHERING FUNCTIONS ===
async def fetch_regime_context(is_asking_market: bool) -> str:
    """Async fetch regime context when needed."""
    if not is_asking_market:
        return ""
    try:
        from backend.modules.regime_analysis.indicators.hmm_regime import calculate_vnindex_regime
        loop = asyncio.get_event_loop()
        regime = await loop.run_in_executor(None, calculate_vnindex_regime, 1250, True)
        return (
            f"TRẠNG THÁI THỊ TRƯỜNG HIỆN TẠI (HMM Model):\n"
            f"- Regime: {regime.get('regime', 'UNKNOWN')}\n"
            f"- Bias: {regime.get('bias', 'NEUTRAL')}\n"
            f"- Confidence: {regime.get('confidence', 0.0) * 100:.1f}%\n"
            f"- Mô tả: {regime.get('description', '')}\n"
        )
    except Exception:
        return ""

async def fetch_portfolio_context(username: str) -> str:
    """Async fetch portfolio context."""
    try:
        from backend.modules.trading_engine.portfolio_service import PortfolioService
        loop = asyncio.get_event_loop()
        port = await loop.run_in_executor(None, PortfolioService.get_portfolio, username)
        if port and port.get("status") == "success":
            assets = port.get("assets", [])
            asset_str = ""
            for a in assets:
                asset_str += f"  + {a['symbol']}: Số lượng {a['qty']}, Giá vốn {a['avg_price']:,} VNĐ, Giá hiện tại {a['market_price']:,} VNĐ, Lãi/Lỗ: {a['pnl_pct']:.2f}%\n"
            return (
                f"DANH MỤC ĐẦU TƯ ĐANG THEO DÕI (User: {username}):\n"
                f"- Số dư tiền mặt: {port.get('cash', 0):,} VNĐ\n"
                f"- Tổng giá trị tài sản (NAV): {port.get('total_value', 0):,} VNĐ\n"
                f"- Các vị thế đang nắm giữ:\n{asset_str if asset_str else '  (Chưa nắm giữ tài sản nào)'}\n"
            )
    except Exception:
        return ""
    return ""

async def fetch_ticker_news_context(symbols: List[str]) -> str:
    """Async fetch news for symbols."""
    ticker_info = ""
    for sym in set(symbols):
        try:
            from backend.modules.cw_pricing.service import WarrantService
            loop = asyncio.get_event_loop()
            news_res = await loop.run_in_executor(None, WarrantService.get_news, sym, 3)
            news_list = news_res.get("news", [])
            if news_list:
                ticker_info += f"Tin tức gần đây của {sym}:\n"
                for n in news_list:
                    ticker_info += f"  - [{n['date']}] {n['title']}: {n['summary'] or ''}\n"
        except Exception:
            pass
    return ticker_info

async def fetch_ticker_events_context(symbols: List[str]) -> str:
    """Async fetch events for symbols."""
    ticker_info = ""
    for sym in set(symbols):
        try:
            from backend.modules.cw_pricing.service import WarrantService
            loop = asyncio.get_event_loop()
            event_res = await loop.run_in_executor(None, WarrantService.get_events, sym, 2)
            events = event_res.get("events", [])
            if events:
                ticker_info += f"Sự kiện sắp tới của {sym}:\n"
                for ev in events:
                    ticker_info += f"  - [{ev['event_date']}] {ev['event_type']}: {ev['description']}\n"
        except Exception:
            pass
    return ticker_info

async def fetch_financial_context(symbols: List[str]) -> str:
    """Async fetch financial data for symbols."""
    ticker_info = ""
    for sym in set(symbols):
        try:
            from backend.core.database import SessionLocal, CompanyFinancial, CompanyDistressAnalysis
            loop = asyncio.get_event_loop()
            
            def fetch_financials():
                db_sess = SessionLocal()
                try:
                    fins = db_sess.query(CompanyFinancial).filter(CompanyFinancial.ticker == sym).order_by(CompanyFinancial.year.desc()).all()
                    distress = db_sess.query(CompanyDistressAnalysis).filter(CompanyDistressAnalysis.ticker == sym).order_by(CompanyDistressAnalysis.year.desc()).all()
                    return fins, distress
                finally:
                    db_sess.close()
            
            fins, distress = await loop.run_in_executor(None, fetch_financials)
            
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
        except Exception:
            pass
    return ticker_info

async def fetch_cw_opportunities_context() -> str:
    """Async fetch CW opportunities."""
    try:
        from backend.modules.cw_pricing.service import WarrantService
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, WarrantService.get_opportunities, 5)
        opps_list = opps.get("recommendations", [])
        if opps_list:
            opps_str = ""
            for o in opps_list:
                opps_str += f"  - {o['warrant_symbol']} (Cơ sở: {o['underlying_symbol']}): Tín hiệu {o['recommendation_signal']}, G-Score {o['composite_g_score']}, Greeks Delta {o['delta']}, Giá {o['market_price']} VNĐ\n"
            return f"TOP CƠ HỘI ĐẦU TƯ CHỨNG QUYỀN (G-Score cao nhất):\n{opps_str}"
    except Exception:
        return ""
    return ""

async def fetch_peer_comparison_context(symbols: List[str]) -> str:
    """Async fetch peer comparison data."""
    peer_info = ""
    for sym in set(symbols):
        try:
            from backend.core.database import CompanyDistressAnalysis
            loop = asyncio.get_event_loop()
            
            def fetch_peer_data():
                db_sess = SessionLocal()
                try:
                    dist_latest = (
                        db_sess.query(CompanyDistressAnalysis)
                        .filter(CompanyDistressAnalysis.ticker == sym)
                        .order_by(CompanyDistressAnalysis.year.desc())
                        .first()
                    )
                    return dist_latest
                finally:
                    db_sess.close()
            
            dist_latest = await loop.run_in_executor(None, fetch_peer_data)
            if dist_latest:
                industry_str = dist_latest.industry or "Không xác định"
                roae_pct = dist_latest.roae * 100 if dist_latest.roae else None
                roaa_pct = dist_latest.roaa * 100 if dist_latest.roae else None
                debt_ratio = dist_latest.debt_ratio
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
                    )
                if len(peer_lines) > 1:
                    peer_info += "SO SÁNH NGÀNH (PEER COMPARISON):\n" + "\n".join(peer_lines) + "\n"
        except Exception:
            pass
    return peer_info


@router.get("/context-summary")
async def get_context_summary():
    """
    Returns a simple AI introduction.
    Called once when the chat widget opens.
    """
    import datetime
    now = datetime.datetime.now()
    
    greeting = (
        "Chào bạn! Tôi là **Finvista Quant AI** — Chuyên gia Phân tích Tài chính & "
        "Cố vấn Đầu tư Chứng quyền/Cổ phiếu của bạn.\n\n"
        "Hỏi tôi bất cứ điều gì về thị trường, chứng quyền hoặc cổ phiếu nhé!"
    )

    return {"greeting": greeting, "timestamp": now.isoformat()}


@router.post("/", response_model=ChatResponse)
async def chat_completion(request: ChatRequest, req_raw: Request):
    """
    AI-powered financial chat assistant with optimized parallel async context gathering.
    """
    try:
        from backend.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client(module_name="chat", auto_start_proxy=False)
        
        # Check if AI client is properly configured
        if ai_client.use_web_api and not ai_client._is_port_open(ai_client.port):
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
                from backend.core.database import SessionLocal, StockHistoricalPrice, CompanyFinancial
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
        
        # 3. Check if user is asking about market or CW
        last_message_lower = last_message.lower()
        market_keywords = ["thị trường", "thị trường hôm nay", "vnindex", "chỉ số", "trend", "xu hướng", "regime"]
        cw_keywords = ["chứng quyền", "cw", "khuyến nghị", "gợi ý", "top", "mua", "bán"]
        is_asking_market = any(kw in last_message_lower for kw in market_keywords)
        is_asking_cw = any(kw in last_message_lower for kw in cw_keywords)
        
        # 4. PARALLEL CONTEXT GATHERING
        system_context = []
        
        # Create parallel tasks for context gathering
        tasks = []
        
        # Always fetch portfolio if user is logged in
        active_username = current_user["username"] if current_user else "demo"
        if current_user:
            tasks.append(fetch_portfolio_context(active_username))
        
        # Fetch regime only if asking about market
        if is_asking_market:
            tasks.append(fetch_regime_context(is_asking_market))
        
        # Fetch symbol-specific data if symbols mentioned
        if symbols:
            tasks.append(fetch_ticker_news_context(symbols))
            tasks.append(fetch_ticker_events_context(symbols))
            tasks.append(fetch_financial_context(symbols))
            tasks.append(fetch_peer_comparison_context(symbols))
            
            # Check if asking about CW analysis
            if is_asking_cw:
                try:
                    from backend.modules.trading_engine.committee_chat_integration import get_committee_chat
                    committee_chat = get_committee_chat()
                    
                    # If user mentioned specific CW symbol
                    cw_symbols = [s for s in symbols if len(s) <= 5 and s.isalpha()]
                    if cw_symbols:
                        cw_analysis = committee_chat.analyze_cw_via_chat(cw_symbols[0])
                        system_context.append(cw_analysis)
                    else:
                        # Show top recommendations
                        top_cw = committee_chat.get_top_cw_recommendations(limit=3)
                        system_context.append(top_cw)
                except Exception as e:
                    print(f"⚠️ [AI Chat] CW analysis error: {e}")
        
        # Always fetch CW opportunities
        tasks.append(fetch_cw_opportunities_context())
        
        # Execute all tasks in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, str) and result.strip():
                    system_context.append(result)
                elif isinstance(result, Exception):
                    print(f"⚠️ [AI Chat] Context gathering error: {result}")
        
        # 5. RAG BCTC Query (conditional)
        try:
            years_mentioned = [int(y) for y in re.findall(r'\b(20\d{2})\b', last_message)]
            report_keywords = ["bctc", "báo cáo tài chính", "báo cáo thường niên", "báo cáo", "annual report", "năm", "vòng quay", "số liệu", "data"]
            is_asking_about_reports = any(kw in last_message_lower for kw in report_keywords)
            
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
                    from backend.modules.annual_reports.manager import AnnualReportManager
                    report_mgr = AnnualReportManager()
                    loop = asyncio.get_event_loop()
                    rag_answer = await loop.run_in_executor(
                        None, 
                        report_mgr.query_report,
                        sym, query_year, 5, last_message
                    )
                    if rag_answer and not rag_answer.startswith("❌"):
                        report_rag_context += f"  - Kết quả RAG từ BCTC {sym} năm {query_year}: {rag_answer}\n"
                
                if report_rag_context:
                    system_context.append(f"KẾT QUẢ TRUY VẤN RAG BCTC DÀNH CHO CÂU HỎI HIỆN TẠI:\n{report_rag_context}")
        except Exception:
            pass

        # 6. Build system prompt
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
            "2. TRẢI LỜI NGẮN GỌN, VÀO TRỌNG TÂM: Tối đa 3-5 câu cho mỗi câu trả lời. Không giải thích quá dài dòng, không có lý thuyết chung chung. Đi thẳng vào kết luận và số liệu quan trọng.\n"
            "3. Khi chào hỏi hoặc trả lời, hãy trả lời tự nhiên, thân thiện và đi thẳng vào phân tích tài chính/chứng khoán. Không được nói 'tôi không có thông tin định danh cá nhân của bạn'.\n"
            "4. Khi người dùng hỏi về danh mục hoặc vị thế, hãy chủ động phân tích các mã chứng quyền/cổ phiếu trong danh mục đang theo dõi (NAV, Lãi/Lỗ, tỷ trọng).\n"
            "5. Khi context có 'MỐC GIÁ HÀNH ĐỘNG', BẮT BUỘC trình bày đầy đủ các mốc Entry / Cắt lỗ (SL) / Chốt lời (TP) / Tỷ lệ R:R và rủi ro thời gian Theta decay.\n"
            "6. Kết luận phân tích PHẢI DỨT KHOÁT: MUA (BUY) / CHỜ (WATCH) / ĐỨNG NGOÀI (NEUTRAL). Tránh dùng các từ chung chung mơ hồ.\n"
            "7. Khi user hỏi về thị trường hôm nay, PHẢI tham chiếu dữ liệu 'TỔNG QUAN THỊ TRƯỜNG PHIÊN HÔM NAY' bên dưới.\n"
            "8. Khi user hỏi về mùa vụ hoặc tháng nào nên mua, PHẢI tham chiếu 'PHÂN TÍCH MÙA VỤ VNINDEX' từ dữ liệu lịch sử thực.\n"
            "9. Khi user hỏi tổng quan CW hoặc mã nào tốt, PHẢI tham chiếu 'TỔNG QUAN THỊ TRƯỜNG CHỨNG QUYỀN' với phân phối tín hiệu thực tế.\n\n"
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
    """
    try:
        from backend.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client(module_name="chat", auto_start_proxy=False)
        
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
    """
    try:
        from backend.infra.ai_client import get_ai_client
        
        ai_client = get_ai_client(module_name="chat", auto_start_proxy=False)
        
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
