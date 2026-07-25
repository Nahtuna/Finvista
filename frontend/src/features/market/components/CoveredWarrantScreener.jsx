import React from "react";
import { Award, TrendingUp, Flame, ArrowRight } from "lucide-react";
import { useThemeTokens } from "../../../app/useThemeTokens.js";
import { formatNumber } from "../../../lib/formatters.js";

export function CoveredWarrantScreener({ warrants = [], onSelectWarrant, setPage, preferences = {} }) {
  const { cardBg, subBg, borderColor, textColor, mutedText } = useThemeTokens(preferences);

  // Top 5 Volume CWs
  const topVolume = [...warrants]
    .sort((a, b) => (b.volume || 0) - (a.volume || 0))
    .slice(0, 5);

  // Top 5 Highest G-Score CWs
  const topScore = [...warrants]
    .sort((a, b) => (b.composite_g_score || b.score || 0) - (a.composite_g_score || a.score || 0))
    .slice(0, 5);

  return (
    <div
      style={{
        background: cardBg,
        border: `1px solid ${borderColor}`,
        borderRadius: "0.75rem",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem"
      }}
    >
      {/* Title Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "900", margin: 0, color: textColor, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Award size={18} style={{ color: "#eab308" }} /> TỔNG QUAN CHỨNG QUYỀN NỔI BẬT THỊ TRƯỜNG
          </h3>
          <p style={{ fontSize: "0.75rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
            Bức tranh tổng quan các mã CW sôi động nhất & có tín hiệu định lượng hàng đầu
          </p>
        </div>

        {setPage && (
          <button
            onClick={() => setPage("cw")}
            style={{
              background: "#2563eb",
              color: "#fff",
              border: "none",
              padding: "0.45rem 0.9rem",
              borderRadius: "0.375rem",
              fontSize: "0.78rem",
              fontWeight: "700",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.35rem"
            }}
          >
            Mở Scanner chuyên sâu <ArrowRight size={14} />
          </button>
        )}
      </div>

      {/* 2-Column Overview Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        {/* Top Volume */}
        <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem" }}>
          <h4 style={{ fontSize: "0.88rem", fontWeight: "800", color: "#60a5fa", margin: "0 0 0.75rem 0", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <Flame size={15} color="#60a5fa" /> Top CW Thanh khoản Cao nhất
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {topVolume.map((item, idx) => {
              const sym = item.warrant_symbol || item.symbol || "";
              const price = item.market_price || item.price || 0;
              const chg = item.price_change_pct ?? 0;
              return (
                <div
                  key={sym + idx}
                  onClick={() => onSelectWarrant && onSelectWarrant(sym)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "0.45rem 0.6rem",
                    background: cardBg,
                    borderRadius: "0.375rem",
                    border: `1px solid ${borderColor}`,
                    cursor: "pointer",
                    fontSize: "0.78rem"
                  }}
                >
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <strong style={{ color: "#60a5fa" }}>{sym}</strong>
                    <span style={{ color: mutedText, fontSize: "0.72rem" }}>({item.underlying_symbol || item.underlying})</span>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span style={{ fontWeight: "700", color: textColor, marginRight: "0.5rem" }}>{formatNumber(price, 0)} đ</span>
                    <span style={{ color: chg >= 0 ? "#10b981" : "#ef4444", fontWeight: "700" }}>
                      {chg >= 0 ? "+" : ""}{formatNumber(chg, 2)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Top G-Score */}
        <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem" }}>
          <h4 style={{ fontSize: "0.88rem", fontWeight: "800", color: "#10b981", margin: "0 0 0.75rem 0", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <TrendingUp size={15} color="#10b981" /> Top CW G-Score Cao nhất
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {topScore.map((item, idx) => {
              const sym = item.warrant_symbol || item.symbol || "";
              const price = item.market_price || item.price || 0;
              const score = Math.round(item.composite_g_score || item.score || 0);
              const signal = item.recommendation_signal || item.decision_signal || "BUY";
              return (
                <div
                  key={sym + idx}
                  onClick={() => onSelectWarrant && onSelectWarrant(sym)}
                  style={{
                    display: "flex",
                    justify: "space-between",
                    alignItems: "center",
                    padding: "0.45rem 0.6rem",
                    background: cardBg,
                    borderRadius: "0.375rem",
                    border: `1px solid ${borderColor}`,
                    cursor: "pointer",
                    fontSize: "0.78rem"
                  }}
                >
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <strong style={{ color: "#60a5fa" }}>{sym}</strong>
                    <span style={{ background: "rgba(16,185,129,0.15)", color: "#10b981", padding: "0.1rem 0.35rem", borderRadius: "0.2rem", fontSize: "0.68rem", fontWeight: "800" }}>
                      Score: {score}
                    </span>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span style={{ fontWeight: "700", color: textColor, marginRight: "0.5rem" }}>{formatNumber(price, 0)} đ</span>
                    <span style={{ color: "#10b981", fontWeight: "800", fontSize: "0.7rem" }}>{signal}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
