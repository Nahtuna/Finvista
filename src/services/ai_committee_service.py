# -*- coding: utf-8 -*-
"""
🤖 FINVISTA: AI COMMITTEE SERVICE (MULTI-AGENT QUANT)
=====================================================
Orchestrates the 7-layer hybrid filtering process:
Quant -> Credit -> Macro -> Vision -> Option Pricing -> Debate -> PM Decision.

Author: samvo
"""

import asyncio
import base64
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import desc
from src.common.ai_client import get_ai_client
from src.common.chart_generator import generate_candlestick_base64
from src.services.warrant_service import WarrantService
from src.services.credit_risk_service import CreditRiskService
from src.common.database import SessionLocal, MarketOpportunity, AIAnalysisMemory, CorporateNews, CorporateEvent
from src.etl.extractors.orderbook_scraper import get_real_order_book, calculate_slippage

try:
    import vnstock
except ImportError:
    vnstock = None

class AICommitteeService:
    """
    Orchestrator for the AI Quant Committee.
    Implements a rigorous 7-layer filtering process for Covered Warrants.
    """

    def __init__(self):
        self.ai_client = get_ai_client()
        self.warrant_service = WarrantService()
        self.credit_service = CreditRiskService()

    async def analyze_opportunity(self, symbol: str, target_volume: int = 5000) -> Dict[str, Any]:
        """
        Run the full 7-layer AI Committee analysis for a specific warrant.
        """
        symbol = symbol.upper().strip()
        
        # 🟢 LAYER 0: EXPERIENCE MEMORY (Retrieve past mistakes/successes)
        past_experience = self._get_past_experience(symbol)
        
        # 🟢 LAYER 1: QUANT GATEKEEPER (Python)
        quant_data = self._layer1_quant_gatekeeper(symbol)
        if not quant_data:
            return {"status": "rejected", "layer": 1, "reason": "Failed Quant Gatekeeper checks (Liquidity/Greeks)"}

        underlying = quant_data.get("underlying")
        
        # 🟢 LAYER 1.5: CREDIT & FUNDAMENTAL (XGBoost)
        credit_data = self._layer1_5_credit_engine(underlying)
        if credit_data.get("credit_metrics", {}).get("bankruptcy_probability", 1.0) > 0.30:
            return {"status": "rejected", "layer": 1.5, "reason": f"Credit risk too high for underlying {underlying}"}

        # 🟢 LAYER 2, 3, 4: PARALLEL AGENT INVESTIGATION
        tasks = [
            self._layer2_macro_sentiment(symbol, underlying),
            self._layer3_vision_ta(symbol, underlying, quant_data.get("days_to_maturity", 90)),
            self._layer4_volatility_arb(symbol, quant_data),
            self._layer7_liquidity_gate(symbol, target_volume)
        ]
        layer_results = await asyncio.gather(*tasks)
        
        macro_report = layer_results[0]
        vision_report = layer_results[1]
        options_report = layer_results[2]
        liquidity_report = layer_results[3]

        # 🟢 LAYER 5: AI DEBATE PHASE (Now with Experience Memory & Real-time Liquidity)
        # Fetch upcoming events specifically for the debate phase to highlight corporate actions
        upcoming_events = self._get_upcoming_events(underlying)
        debate_result = await self._layer5_ai_debate(
            quant_data, credit_data, macro_report, vision_report, options_report, past_experience, liquidity_report, upcoming_events
        )

        # 🟢 LAYER 6: PM DECISION (Total Commander)
        final_decision = await self._layer6_pm_decision(debate_result, liquidity_report)

        # 🟢 LAYER 7: SAVE TO MEMORY
        self._save_to_memory(symbol, underlying, quant_data, final_decision)

        return {
            "symbol": symbol,
            "underlying": underlying,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "decision": final_decision,
            "past_experience": past_experience,
            "committee_reports": {
                "quant": quant_data,
                "credit": credit_data,
                "macro": macro_report,
                "vision": vision_report,
                "options": options_report,
                "liquidity": liquidity_report,
                "debate": debate_result
            }
        }

    def _get_past_experience(self, symbol: str) -> str:
        """Retrieve recent AI analysis records for this symbol to provide historical context."""
        db = SessionLocal()
        try:
            records = db.query(AIAnalysisMemory).filter(
                AIAnalysisMemory.symbol == symbol
            ).order_by(AIAnalysisMemory.timestamp.desc()).limit(3).all()
            
            if not records:
                return "Chưa có kinh nghiệm quá khứ cho mã này."
            
            exp_text = "KINH NGHIỆM QUÁ KHỨ (BÀI HỌC):\n"
            for r in records:
                status = "Đúng" if r.is_correct else "Sai/Chưa rõ"
                exp_text += f"- [{r.timestamp.strftime('%Y-%m-%d')}] Quyết định: {r.decision}, Điểm: {r.consensus_score}, Kết quả: {status}. Lý do cũ: {r.rationale_summary}\n"
            return exp_text
        finally:
            db.close()

    def _save_to_memory(self, symbol: str, underlying: str, quant: Dict[str, Any], decision: Dict[str, Any]):
        """Persist the current analysis result into the long-term memory table."""
        db = SessionLocal()
        try:
            mem = AIAnalysisMemory(
                symbol=symbol,
                underlying=underlying,
                decision=decision.get("decision"),
                consensus_score=decision.get("confidence_score", 0),
                rationale_summary=decision.get("rationale_summary"),
                price_at_analysis=quant.get("price"),
                underlying_price_at_analysis=quant.get("underlying_price"),
                iv_at_analysis=quant.get("iv"),
                delta_at_analysis=quant.get("delta"),
                days_to_maturity=quant.get("days_to_maturity")
            )
            db.add(mem)
            db.commit()
        except Exception as e:
            print(f"⚠️ Failed to save to AI memory: {e}")
        finally:
            db.close()

    def _layer1_quant_gatekeeper(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Filter by quantitative liquidity and basic Greeks."""
        db = SessionLocal()
        try:
            opp = db.query(MarketOpportunity).filter(MarketOpportunity.symbol == symbol).first()
            if not opp:
                return None
            
            # Example hard-gates:
            if opp.days_to_maturity < 14:
                return None
            
            return {
                "symbol": opp.symbol,
                "underlying": opp.underlying,
                "price": opp.price,
                "underlying_price": opp.underlying_price,
                "delta": opp.delta,
                "gearing": opp.gearing,
                "iv": opp.implied_volatility_pct,
                "hv": opp.historical_volatility_pct,
                "days_to_maturity": opp.days_to_maturity,
                "g_score": opp.score
            }
        finally:
            db.close()

    def _layer1_5_credit_engine(self, underlying: str) -> Dict[str, Any]:
        """Fetch credit health via XGBoost engine."""
        try:
            return self.credit_service.get_credit_health(underlying)
        except Exception:
            return {"credit_metrics": {"bankruptcy_probability": 1.0}}

    async def _layer2_macro_sentiment(self, symbol: str, underlying: str) -> str:
        """Agent: Macro & Market Sentiment (with RAG from database)."""
        news_context = ""
        db = SessionLocal()
        try:
            # Fetch latest news for both symbol and underlying from DB
            relevant_news = db.query(CorporateNews).filter(
                (CorporateNews.symbol == underlying) | (CorporateNews.symbol == symbol)
            ).order_by(desc(CorporateNews.date)).limit(10).all()
            
            if relevant_news:
                news_context = "\n\nCÁC TIN TỨC & SỰ KIỆN LIÊN QUAN (Vietstock):\n"
                for item in relevant_news:
                    news_context += f"- [{item.date}] {item.title} ({item.category})\n"
            
            # Fetch upcoming events
            events = db.query(CorporateEvent).filter(
                CorporateEvent.ticker == underlying
            ).order_by(desc(CorporateEvent.event_date)).limit(5).all()
            
            if events:
                news_context += "\nLỊCH SỰ KIỆN DOANH NGHIỆP:\n"
                for ev in events:
                    news_context += f"- [{ev.event_date}] {ev.event_type}: {ev.description}\n"
                    
        except Exception as e:
            print(f"⚠️ RAG News DB Error: {e}")
        finally:
            db.close()

        prompt = f"""Bạn là Macro Sentiment Agent. 
Hãy phân tích tâm lý thị trường và dòng tiền đối với cổ phiếu cơ sở {underlying}.

Tập trung vào:
1. Xu hướng mua/bán ròng của khối ngoại.
2. Trạng thái phái sinh VN30F1M (Basis dương/âm).
3. Đánh giá trạng thái thị trường: Risk-On hay Risk-Off?{news_context}

Trả lời ngắn gọn, chuyên nghiệp, dựa trên cả dữ liệu định lượng và tin tức thực tế (nếu có)."""
        
        messages = [{"role": "user", "content": prompt}]
        return self.ai_client.chat(messages, temperature=0.5)

    def _get_upcoming_events(self, underlying: str) -> str:
        """Helper to fetch events for the debate phase."""
        db = SessionLocal()
        try:
            events = db.query(CorporateEvent).filter(
                CorporateEvent.ticker == underlying
            ).order_by(desc(CorporateEvent.event_date)).limit(5).all()
            if not events: return "Không có sự kiện doanh nghiệp sắp tới."
            
            text = "SỰ KIỆN DOANH NGHIỆP SẮP TỚI:\n"
            for ev in events:
                text += f"- {ev.event_date}: {ev.event_type} ({ev.description})\n"
            return text
        finally:
            db.close()

    async def _layer3_vision_ta(self, symbol: str, underlying: str, days_to_maturity: int = 90) -> str:
        """Agent: Visual Technical Analyst (Gemini Vision)."""
        try:
            # Dynamically adjust chart timeframe based on warrant maturity
            # We want to see history roughly proportional to the warrant's remaining life, up to 2 years
            chart_days = 90
            if days_to_maturity > 360:
                chart_days = 720  # ~2 years for LEAPS
            elif days_to_maturity > 180:
                chart_days = 360  # ~1 year
            elif days_to_maturity > 90:
                chart_days = 180  # ~6 months

            chart_base64 = generate_candlestick_base64(ticker=underlying, days=chart_days)
            if not chart_base64: return f"Lỗi tạo biểu đồ cho {underlying}."
            vision_prompt = f"""Bạn là Chuyên gia Phân tích Kỹ thuật (Visual TA Agent). 
Phân tích biểu đồ kỹ thuật {chart_days} ngày gần nhất của cổ phiếu {underlying} (cơ sở của chứng quyền {symbol}, còn {days_to_maturity} ngày đáo hạn).
Nhiệm vụ:
1. Xác định xu hướng lớn (Macro Trend) và các vùng hỗ trợ/kháng cự dài hạn/ngắn hạn.
2. Tìm các mô hình nến hoặc mô hình giá (như Wyckoff, Price Action).
3. Đánh giá sức mạnh của xu hướng qua khối lượng.
4. Đưa ra nhận định phù hợp với khung thời gian còn lại của chứng quyền ({days_to_maturity} ngày).
Trả lời bằng tiếng Việt, ngắn gọn, tập trung vào tín hiệu tin cậy cao."""
            return self.ai_client.analyze_chart_vision(chart_base64, vision_prompt)
        except Exception as e:
            return f"Lỗi trong quá trình phân tích Vision: {str(e)}"

    async def _layer4_volatility_arb(self, symbol: str, quant_data: Dict[str, Any]) -> str:
        """Agent: Volatility & Greeks Specialist."""
        prompt = f"""Bạn là Volatility Arbitrageur.
Phân tích chứng quyền {symbol}:
- Delta: {quant_data.get('delta')}
- Đòn bẩy: {quant_data.get('gearing')}x
- IV: {quant_data.get('iv')}% vs HV: {quant_data.get('hv')}%
- Ngày đáo hạn: {quant_data.get('days_to_maturity')}
Đánh giá rủi ro Theta decay và Vol Crush. Có nên nắm giữ 3-5 ngày không?"""
        messages = [{"role": "user", "content": prompt}]
        return self.ai_client.chat(messages, temperature=0.4)

    async def _layer7_liquidity_gate(self, symbol: str, volume: int) -> Dict[str, Any]:
        """Perform a real-time order book depth check."""
        ob = get_real_order_book(symbol)
        if not ob:
            return {"status": "unknown", "reason": "Could not fetch real-time L2 data (Market closed or blocked)."}
        analysis = calculate_slippage(ob, "BUY", volume)
        return analysis

    async def _layer5_ai_debate(self, quant, credit, macro, vision, options, past_experience, liquidity, upcoming_events) -> str:
        """Phase 5: The Multi-Round AI Debate Phase."""
        critique_prompt = f"""HỘI ĐỒNG AI FINVISTA - PHIÊN TRANH LUẬN VÒNG 2 (PHẢN BIỆN CHÉO)
{past_experience}
{upcoming_events}
DỮ LIỆU GỐC:
- Mã CW: {quant.get('symbol')} | Cơ sở: {quant.get('underlying')}
- Định lượng: G-Score {quant.get('g_score')}, Delta {quant.get('delta')}, IV {quant.get('iv')}%
- Tín dụng (ML): Xác suất rủi ro {credit.get('credit_metrics', {}).get('bankruptcy_probability', 0)*100:.1f}%
- THANH KHOẢN THỰC TẾ (Sổ lệnh): {json.dumps(liquidity)}
LUẬN ĐIỂM CỦA CÁC AGENT (VÒNG 1):
1. Agent Vĩ mô: {macro}
2. Agent Thị giác (Vision): {vision}
3. Agent Quyền chọn: {options}
NHIỆM VỤ PHẢN BIỆN (CRITIQUE):
Bạn hãy đóng vai 'Người phản biện sắc sảo' (Skeptic). Hãy tìm ra các mâu thuẫn hoặc rủi ro bị bỏ sót.
ĐẶC BIỆT: 
- Đối chiếu với KINH NGHIỆM QUÁ KHỨ và SỰ KIỆN DOANH NGHIỆP sắp tới (như ngày chốt quyền cổ tức có thể làm thay đổi giá cơ sở và định giá CW).
- Kiểm tra tính khả thi dựa trên THANH KHOẢN THỰC TẾ (Nếu trượt giá cao hoặc không đủ lệnh bán, hãy cảnh báo cực mạnh).
HÃY XUẤT KẾT QUẢ THEO ĐỊNH DẠNG BẢNG SAU:
| Khía cạnh | Luận điểm chính | Điểm yếu/Rủi ro | Hệ số tin tưởng (0-100) |
| :--- | :--- | :--- | :--- |
| Vĩ mô & Sự kiện | ... | ... | ... |
| Kỹ thuật | ... | ... | ... |
| Định giá | ... | ... | ... |
| Khả thi (L2) | ... | ... | ... |
KẾT LUẬN CUỐI: Đưa ra ĐIỂM ĐỒNG THUẬN (Consensus Score) trung bình."""
        messages = [{"role": "user", "content": critique_prompt}]
        return self.ai_client.chat(messages, temperature=0.6)

    async def _layer6_pm_decision(self, debate_result: str, liquidity: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 6: The Portfolio Manager (PM) Decision."""
        pm_prompt = f"""Bạn là Portfolio Manager (Tổng Tư Lệnh).
Dựa trên kết quả tranh luận sau:
{debate_result}
BỐI CẢNH THANH KHOẢN THỰC TẾ:
{json.dumps(liquidity)}
Hãy đưa ra quyết định cuối cùng.
LƯU Ý: Nếu thanh khoản không đủ cho khối lượng mục tiêu hoặc trượt giá quá cao, phải hạ bậc quyết định.
Yêu cầu trả về định dạng JSON nghiêm ngặt:
{{
  "decision": "STRONG BUY" | "BUY" | "HOLD" | "SELL" | "SKIP",
  "confidence_score": 0-100,
  "allocation_pct": 0-10,
  "rationale_summary": "Tóm tắt lý do bằng tiếng Việt (1 câu)",
  "risk_warnings": ["Cảnh báo 1", "Cảnh báo 2"]
}}"""
        messages = [{"role": "user", "content": pm_prompt}]
        response = self.ai_client.chat(messages, temperature=0.2)
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            return json.loads(response[start:end])
        except:
            return {"decision": "SKIP", "confidence_score": 0, "rationale_summary": "Lỗi xử lý quyết định AI.", "response_raw": response}
