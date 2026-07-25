import React from "react";
import { ArrowUpRight, ArrowDownRight, Globe, Coins, Flame, DollarSign } from "lucide-react";
import { useThemeTokens } from "../../../app/useThemeTokens.js";

export function MacroBar({ preferences = {} }) {
  const { cardBg, borderColor, textColor, mutedText } = useThemeTokens(preferences);

  // Fallback / mock real-time data for VN Macro indicators
  const macroItems = [
    { label: "VN-INDEX", val: "1,284.50", change: "+5.20", percent: "+0.41%", isUp: true },
    { label: "VN30", val: "1,312.80", change: "+6.10", percent: "+0.47%", isUp: true },
    { label: "VN30F1M", val: "1,314.50", change: "+7.00", percent: "+0.54%", isUp: true, sub: "Basis: +1.70" },
    { label: "USD/VND", val: "25,450", change: "+15.00", percent: "+0.06%", isUp: true, icon: DollarSign },
    { label: "VÀNG SJC", val: "88.50M", change: "-0.50M", percent: "-0.56%", isUp: false, icon: Coins },
    { label: "DẦU BRENT", val: "$82.40", change: "+0.85", percent: "+1.04%", isUp: true, icon: Flame }
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
        gap: "0.75rem",
        width: "100%"
      }}
    >
      {macroItems.map((item, idx) => {
        const IconComponent = item.isUp ? ArrowUpRight : ArrowDownRight;
        const color = item.isUp ? "#10b981" : "#ef4444";

        return (
          <div
            key={idx}
            style={{
              background: cardBg,
              border: `1px solid ${borderColor}`,
              borderRadius: "0.5rem",
              padding: "0.65rem 0.85rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.15rem"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "0.7rem", fontWeight: "800", color: mutedText, letterSpacing: "0.5px" }}>
                {item.label}
              </span>
              {item.icon ? (
                <item.icon size={12} style={{ color: mutedText }} />
              ) : (
                <Globe size={12} style={{ color: mutedText }} />
              )}
            </div>

            <div style={{ display: "flex", alignItems: "baseline", gap: "0.4rem" }}>
              <span style={{ fontSize: "1.05rem", fontWeight: "900", color: textColor }}>
                {item.val}
              </span>
              <span
                style={{
                  fontSize: "0.72rem",
                  fontWeight: "700",
                  color: color,
                  display: "flex",
                  alignItems: "center"
                }}
              >
                <IconComponent size={12} /> {item.percent}
              </span>
            </div>

            {item.sub && (
              <span style={{ fontSize: "0.65rem", color: "#3b82f6", fontWeight: "600" }}>
                {item.sub}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
