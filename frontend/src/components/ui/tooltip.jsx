import React, { useState } from "react";
import { HelpCircle } from "lucide-react";

export const GLOSSARY_HINTS = {
  "G-Score": "Điểm số định lượng tổng hợp từ 0-100 đánh giá mức độ hấp dẫn của chứng quyền dựa trên định giá, đòn bẩy và thanh khoản.",
  "Delta": "Mức độ thay đổi giá CW khi cổ phiếu cơ sở tăng 1,000đ. Ví dụ Delta = 0.5 nghĩa là CPCS tăng 1,000đ thì CW tăng ~500đ.",
  "Gamma": "Tốc độ thay đổi của chỉ số Delta khi giá cổ phiếu cơ sở thay đổi 1 đơn vị.",
  "Vega": "Độ nhạy của giá CW khi biến động ngầm định (Implied Volatility) thay đổi 1%.",
  "Theta": "Mức độ giảm giá trị của CW sau mỗi ngày trôi qua (Hao mòn thời gian).",
  "Rho": "Độ nhạy của giá chứng quyền đối với sự thay đổi của lãi suất phi rủi ro.",
  "Implied Volatility": "Biến động ngầm định (IV) phản ánh kỳ vọng của nhà tạo lập thị trường về biến động CPCS trong tương lai.",
  "Moneyness": "Trạng thái giá chứng quyền: ITM (Trong thế tiền - có giá trị nội tại), ATM (Ngang giá), OTM (Ngoài thế tiền)."
};

export function InfoTooltip({ term, text }) {
  const [visible, setVisible] = useState(false);
  const hintText = text || GLOSSARY_HINTS[term] || term;

  return (
    <span
      className="info-tooltip-wrapper"
      style={{ position: "relative", display: "inline-flex", alignItems: "center", cursor: "help", marginLeft: "0.25rem" }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <HelpCircle size={13} style={{ opacity: 0.6 }} />
      {visible && (
        <span
          className="tooltip-box"
          style={{
            position: "absolute",
            bottom: "125%",
            left: "50%",
            transform: "translateX(-50%)",
            background: "#0f172a",
            border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: "0.375rem",
            padding: "0.5rem 0.75rem",
            color: "#e2e8f0",
            fontSize: "0.75rem",
            lineHeight: "1.35",
            width: "220px",
            zIndex: 1000,
            boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
            pointerEvents: "none",
            textAlign: "left",
            fontWeight: "normal"
          }}
        >
          {hintText}
        </span>
      )}
    </span>
  );
}
