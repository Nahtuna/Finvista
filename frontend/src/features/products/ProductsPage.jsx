import React from "react";
import { Check, ShieldCheck, Zap, Star } from "lucide-react";
import { useThemeTokens } from "../../app/useThemeTokens.js";

export function ProductsPage({ language = "vi", preferences = {} }) {
  const isEnglish = language === "en";
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const tiers = isEnglish ? [
    {
      name: "Free Trial",
      price: "0đ / month",
      desc: "Basic warrant valuation tools",
      features: [
        "Warrant valuation (15-min delay)",
        "Basic opportunity scanner",
        "Default simulation account",
        "Basic AI assistant support"
      ],
      current: false,
      actionText: "Try Now"
    },
    {
      name: "Professional (PRO)",
      price: "299,000đ / month",
      desc: "Real-time data and advanced Greeks",
      features: [
        "Real-time data without delay",
        "Advanced Greeks scanner (Delta/Gamma/Theta/Vega)",
        "Altman Z-Score credit analysis",
        "Unlimited simulation accounts",
        "Email and Webhook alerts"
      ],
      current: true,
      actionText: "Current Plan",
      popular: true
    },
    {
      name: "Premium (PREMIUM)",
      price: "799,000đ / month",
      desc: "Enterprise-level quantitative models",
      features: [
        "Creed Market Regime forecasting system",
        "XGBoost price impact algorithm",
        "API for quantitative backtesting",
        "Priority support from quantitative engineers",
        "Custom ML model integration support"
      ],
      current: false,
      actionText: "Contact for Upgrade"
    }
  ] : [
    {
      name: "Bản dùng thử (Free)",
      price: "0đ / tháng",
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
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>
      
      {/* HEADER BAR (PDF Page 13) */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: "900", margin: 0, letterSpacing: "0.5px", color: textColor }}>
          {isEnglish ? "FINVISTA PRODUCTS & SERVICES" : "SẢN PHẨM & DỊCH VỤ FINVISTA"}
        </h2>
        <p style={{ fontSize: "0.82rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
          {isEnglish ? "Upgrade your account to unlock full real-time quantitative data, Greeks and backtest API" : "Nâng cấp tài khoản để mở khóa toàn bộ dữ liệu định lượng real-time, Greeks và API backtest"}
        </p>
      </div>

      {/* PRICING CARDS (PDF Page 13) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1.25rem" }}>
        {tiers.map(tier => (
          <div
            key={tier.name}
            style={{
              background: cardBg,
              border: tier.popular ? "2px solid #ef4444" : `1px solid ${borderColor}`,
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
                {isEnglish ? "MOST POPULAR" : "NỔI BẬT NHẤT"}
              </span>
            )}

            <div>
              <h3 style={{ fontSize: "1.15rem", fontWeight: "800", margin: 0, color: textColor }}>{tier.name}</h3>
              <p style={{ fontSize: "0.78rem", color: mutedText, margin: "0.35rem 0 1rem 0" }}>{tier.desc}</p>
              <strong style={{ fontSize: "1.6rem", fontWeight: "900", color: "#10b981" }}>{tier.price}</strong>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.8rem", borderTop: `1px solid ${borderColor}`, paddingTop: "1rem" }}>
              {tier.features.map(f => (
                <div key={f} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ color: "#10b981", fontWeight: "800" }}>✓</span>
                  <span style={{ color: textColor }}>{f}</span>
                </div>
              ))}
            </div>

            <button
              style={{
                width: "100%",
                background: tier.popular ? "#ef4444" : subBg,
                color: textColor,
                border: tier.popular ? "none" : `1px solid ${borderColor}`,
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
