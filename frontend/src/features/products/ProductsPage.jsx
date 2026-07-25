import React from "react";
import { Check, ShieldCheck, Zap, Star } from "lucide-react";

export function ProductsPage({ language = "vi" }) {
  const isEnglish = language === "en";

  const tiers = [
    {
      name: "Bản dùng thử (Free)",
      price: "0đ",
      desc: "Bộ công cụ cơ bản đánh giá định giá chứng quyền",
      features: [
        "Định giá chứng quyền (trễ 15 phút)",
        "Bộ quét cơ hội cơ bản",
        "Tài khoản giả lập mặc định",
        "Trợ lý AI hỗ trợ cơ bản"
      ],
      current: false,
      actionText: "Dùng thử ngay"
    },
    {
      name: "Gói Chuyên Nghiệp (PRO)",
      price: "299,000đ / tháng",
      desc: "Dữ liệu thời gian thực và Greeks nâng cao",
      features: [
        "Dữ liệu thời gian thực không trễ",
        "Bộ quét Greeks nâng cao (Delta/Gamma/Theta/Vega)",
        "Bộ phân tích tín dụng Altman Z-Score",
        "Không giới hạn tài khoản giả lập",
        "Cảnh báo qua Email và Webhook riêng"
      ],
      current: true,
      actionText: "Đang sử dụng",
      popular: true
    },
    {
      name: "Gói Cao Cấp (PREMIUM)",
      price: "799,000đ / tháng",
      desc: "Các mô hình định lượng cấp doanh nghiệp",
      features: [
        "Hệ thống dự báo Creed Market Regime",
        "Thuật toán XGBoost tác động giá",
        "Cung cấp API để Backtest định lượng",
        "Hỗ trợ ưu tiên từ kỹ sư định lượng",
        "Hỗ trợ tích hợp mô hình ML riêng biệt"
      ],
      current: false,
      actionText: "Liên hệ nâng cấp"
    }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: "#fff", background: "#0b0f19" }}>
      
      {/* HEADER BAR (PDF Page 13) */}
      <div style={{ background: "#131b2e", border: "1px solid #1e293b", borderRadius: "0.75rem", padding: "1.25rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: "900", margin: 0, letterSpacing: "0.5px" }}>
          10. SẢN PHẨM & DỊCH VỤ FINVISTA
        </h2>
        <p style={{ fontSize: "0.82rem", color: "#94a3b8", margin: "0.25rem 0 0 0" }}>
          Nâng cấp tài khoản để mở khóa toàn bộ dữ liệu định lượng real-time, Greeks và API backtest.
        </p>
      </div>

      {/* PRICING CARDS (PDF Page 13) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1.25rem" }}>
        {tiers.map(tier => (
          <div
            key={tier.name}
            style={{
              background: "#131b2e",
              border: tier.popular ? "2px solid #ef4444" : "1px solid #1e293b",
              borderRadius: "0.75rem",
              padding: "1.5rem",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              position: "relative",
              gap: "1.25rem"
            }}
          >
            {tier.popular && (
              <span style={{
                position: "absolute",
                top: "-12px",
                right: "20px",
                background: "#ef4444",
                color: "#fff",
                fontSize: "0.7rem",
                fontWeight: "800",
                padding: "0.2rem 0.75rem",
                borderRadius: "999px",
                boxShadow: "0 0 10px rgba(239, 68, 68, 0.5)"
              }}>
                NỔI BẬT NHẤT
              </span>
            )}

            <div>
              <h3 style={{ fontSize: "1.15rem", fontWeight: "800", margin: 0 }}>{tier.name}</h3>
              <p style={{ fontSize: "0.78rem", color: "#94a3b8", margin: "0.35rem 0 1rem 0" }}>{tier.desc}</p>
              <strong style={{ fontSize: "1.6rem", fontWeight: "900", color: "#10b981" }}>{tier.price}</strong>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.8rem", borderTop: "1px solid #1e293b", paddingTop: "1rem" }}>
              {tier.features.map(f => (
                <div key={f} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ color: "#10b981", fontWeight: "800" }}>✓</span>
                  <span>{f}</span>
                </div>
              ))}
            </div>

            <button
              style={{
                width: "100%",
                background: tier.popular ? "#ef4444" : "#1e293b",
                color: "#fff",
                border: "none",
                padding: "0.6rem",
                borderRadius: "0.375rem",
                fontSize: "0.85rem",
                fontWeight: "800",
                cursor: "pointer"
              }}
            >
              {tier.actionText}
            </button>
          </div>
        ))}
      </div>

    </div>
  );
}
