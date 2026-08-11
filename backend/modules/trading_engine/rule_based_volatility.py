# -*- coding: utf-8 -*-
"""
Rule-based Volatility Analysis cho AI Committee
Thay thế AI để giảm phụ thuộc
"""

from typing import Dict, Any

class RuleBasedVolatilityAnalyzer:
    """Phân tích volatility bằng rule-based thay vì AI"""
    
    def analyze_volatility(self, symbol: str, quant_data: Dict[str, Any]) -> str:
        """
        Phân tích volatility và định giá chứng quyền
        
        Args:
            symbol: Mã chứng quyền
            quant_data: Dict chứa delta, gearing, iv, hv, days_to_maturity
            
        Returns:
            String commentary về volatility
        """
        delta = quant_data.get('delta', 0.5)
        gearing = quant_data.get('gearing', 1.0)
        iv = quant_data.get('iv', 30.0)
        hv = quant_data.get('hv', 25.0)
        days_to_maturity = quant_data.get('days_to_maturity', 90)
        
        commentary = []
        
        # 1. Volatility Risk
        iv_hv_ratio = iv / hv if hv > 0 else 1.0
        if iv_hv_ratio > 1.3:
            commentary.append(f"Volatility Risk: IV ({iv}%) đang cao hơn HV ({hv}%) {iv_hv_ratio:.1f}x, chứng quyền có thể đang overpriced.")
        elif iv_hv_ratio < 0.8:
            commentary.append(f"Volatility Risk: IV ({iv}%) thấp hơn HV ({hv}%) {iv_hv_ratio:.1f}x, có thể là cơ hội giá rẻ.")
        else:
            commentary.append(f"Volatility Risk: IV ({iv}%) và HV ({hv}%) tương đương, định giá hợp lý.")
        
        # 2. Theta Burn
        if days_to_maturity <= 30:
            commentary.append(f"Theta Burn: Còn {days_to_maturity} ngày, bào mòn vốn hàng ngày rất nhanh (high theta risk).")
        elif days_to_maturity <= 60:
            commentary.append(f"Theta Burn: Còn {days_to_maturity} ngày, bào mòn vốn ở mức trung bình.")
        else:
            commentary.append(f"Theta Burn: Còn {days_to_maturity} ngày, áp lực theta burn thấp.")
        
        # 3. Gamma Risk
        if delta > 0.7:
            commentary.append(f"Gamma Risk: Delta cao ({delta:.2f}), nếu giá cơ sở biến động mạnh, CW có thể bùng nổ lợi nhuận.")
        elif delta < 0.3:
            commentary.append(f"Gamma Risk: Delta thấp ({delta:.2f}), cần biến động lớn để có lợi nhuận đáng kể.")
        else:
            commentary.append(f"Gamma Risk: Delta ở mức trung bình ({delta:.2f}), phản ứng cân đối với biến động giá.")
        
        # 4. Gearing Assessment
        if gearing > 2.0:
            commentary.append(f"Gearing: Đòn bẩy cao ({gearing:.1f}x), rủi ro tăng nhưng lợi nhuận tiềm năng lớn.")
        elif gearing < 1.0:
            commentary.append(f"Gearing: Đòn bẩy thấp ({gearing:.1f}x), rủi ro thấp nhưng lợi nhuận hạn chế.")
        else:
            commentary.append(f"Gearing: Đòn bẩy trung bình ({gearing:.1f}x), cân bằng rủi ro/lợi nhuận.")
        
        # 5. Overall Recommendation
        if iv_hv_ratio > 1.3 and days_to_maturity <= 30:
            commentary.append("Recommendation: KHÔNG KHUYẾN NGHỊ - Overpriced và thời gian quá ngắn.")
        elif iv_hv_ratio < 0.8 and delta > 0.5 and days_to_maturity > 60:
            commentary.append("Recommendation: CÓ LỢI THẾ MATH - Giá rẻ, delta tốt, thời gian đủ.")
        else:
            commentary.append("Recommendation: CÂN NHẮC - Cần phân tích thêm các yếu tố khác.")
        
        return "\n".join(commentary)

# Singleton instance
_volatility_analyzer = None

def get_volatility_analyzer() -> RuleBasedVolatilityAnalyzer:
    """Get singleton volatility analyzer instance"""
    global _volatility_analyzer
    if _volatility_analyzer is None:
        _volatility_analyzer = RuleBasedVolatilityAnalyzer()
    return _volatility_analyzer
