# -*- coding: utf-8 -*-
"""
Integration giữa AI Committee và Chat Assistant
Cho phép người dùng phân tích CW qua chat thay vì committee riêng biệt
"""

from typing import Dict, Any, List
from backend.core.database import SessionLocal, MarketOpportunity
from backend.modules.credit_risk.service import CreditRiskService
from backend.modules.regime_analysis.service import GlobalAlphaEngine

class CommitteeChatIntegration:
    """Tích hợp AI Committee vào Chat Assistant"""
    
    def __init__(self):
        self.credit_service = CreditRiskService()
        self.regime_engine = GlobalAlphaEngine(use_ai=False)  # Rule-based regime
    
    def analyze_cw_via_chat(self, symbol: str) -> str:
        """
        Phân tích chứng quyền qua chat (không cần committee riêng)
        
        Args:
            symbol: Mã chứng quyền
            
        Returns:
            String analysis summary
        """
        symbol = symbol.upper().strip()
        
        try:
            # 1. Lấy quant data từ database
            db = SessionLocal()
            try:
                cw_data = db.query(MarketOpportunity).filter(
                    MarketOpportunity.symbol == symbol
                ).first()
                
                if not cw_data:
                    return f"Không tìm thấy dữ liệu cho mã chứng quyền {symbol}"
                
                # 2. Rule-based analysis
                analysis_parts = [
                    f"PHÂN TÍCH CHỨNG QUYỀN {symbol}",
                    f"Cơ sở: {cw_data.underlying}",
                    f"Giá hiện tại: {cw_data.price:.2f} VND",
                    f"Đòn bẩy: {cw_data.gearing:.1f}x",
                    f"Delta: {cw_data.delta:.2f}",
                    f"IV: {cw_data.implied_volatility_pct:.1f}% vs HV: {cw_data.historical_volatility_pct:.1f}%",
                    f"Còn lại: {cw_data.days_to_maturity} ngày",
                    f"Score: {cw_data.score:.1f}",
                    f"Signal: {cw_data.decision_signal}"
                ]
                
                # 3. Credit risk analysis
                try:
                    credit_health = self.credit_service.get_credit_health(cw_data.underlying)
                    z_score = credit_health.get('altman_z_score', 0)
                    distress_prob = credit_health.get('bankruptcy_probability', 0)
                    
                    analysis_parts.append(f"\nRỦI RO TÍN DỤNG CƠ SỞ {cw_data.underlying}:")
                    analysis_parts.append(f"Altman Z-Score: {z_score:.2f}")
                    analysis_parts.append(f"Xác suất kiệt quệ: {distress_prob*100:.1f}%")
                    
                    if z_score < 1.1:
                        analysis_parts.append("⚠️ Cơ sở nằm trong vùng nguy hiểm")
                    elif z_score > 2.6:
                        analysis_parts.append("✅ Cơ sở có nền tảng tài chính lành mạnh")
                    else:
                        analysis_parts.append("⚠️ Cơ sở nằm trong vùng cảnh báo")
                except Exception as e:
                    analysis_parts.append(f"\nKhông thể phân tích rủi ro tín dụng: {e}")
                
                # 4. Market regime
                try:
                    regime_data = self.regime_engine.get_current_regime()
                    analysis_parts.append(f"\nCHẾ THỊ HIỆN TẠI: {regime_data.get('regime', 'Unknown')}")
                    
                    if 'BULLISH' in regime_data.get('regime', ''):
                        analysis_parts.append("Thị trường tăng giá - Có lợi cho CW")
                    elif 'BEARISH' in regime_data.get('regime', ''):
                        analysis_parts.append("Thị trường giảm giá - Cần thận trọng với CW")
                except Exception as e:
                    analysis_parts.append(f"\nKhông thể xác định regime: {e}")
                
                # 5. Simple recommendation
                iv_hv_ratio = cw_data.implied_volatility_pct / cw_data.historical_volatility_pct if cw_data.historical_volatility_pct > 0 else 1.0
                
                if cw_data.score > 7.0 and iv_hv_ratio < 1.2 and cw_data.days_to_maturity > 30:
                    analysis_parts.append(f"\n💡 KHUYẾN NGHỊ: CÂN NHẮC MUA - Score cao, định giá hợp lý, thời gian đủ")
                elif cw_data.score < 4.0 or iv_hv_ratio > 1.5 or cw_data.days_to_maturity < 15:
                    analysis_parts.append(f"\n⚠️ KHUYẾN NGHỊ: TRÁNH - Score thấp hoặc overpriced hoặc thời gian quá ngắn")
                else:
                    analysis_parts.append(f"\n💡 KHUYẾN NGHỊ: CÂN NHẮC - Cần phân tích thêm")
                
                return "\n".join(analysis_parts)
                
            finally:
                db.close()
                
        except Exception as e:
            return f"Lỗi khi phân tích {symbol}: {e}"
    
    def get_top_cw_recommendations(self, limit: int = 5) -> str:
        """
        Lấy top CW recommendation nhanh
        """
        try:
            db = SessionLocal()
            try:
                top_cws = db.query(MarketOpportunity).order_by(
                    MarketOpportunity.score.desc()
                ).limit(limit).all()
                
                if not top_cws:
                    return "Không có dữ liệu CW"
                
                recommendations = ["TOP CHỨNG QUYỀN KHUYẾN NGHỊ:"]
                for cw in top_cws:
                    recommendations.append(
                        f"- {cw.symbol} ({cw.underlying}): Score {cw.score:.1f}, "
                        f"Đòn bẩy {cw.gearing:.1f}x, Signal {cw.decision_signal}"
                    )
                
                return "\n".join(recommendations)
            finally:
                db.close()
        except Exception as e:
            return f"Lỗi khi lấy top CW: {e}"

# Singleton instance
_committee_chat = None

def get_committee_chat() -> CommitteeChatIntegration:
    """Get singleton committee chat integration"""
    global _committee_chat
    if _committee_chat is None:
        _committee_chat = CommitteeChatIntegration()
    return _committee_chat
