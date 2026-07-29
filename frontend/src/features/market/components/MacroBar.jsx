import React, { useEffect, useState } from "react";
import { ArrowUpRight, ArrowDownRight, Globe, Coins, Flame, DollarSign, Loader2 } from "lucide-react";
import { useThemeTokens } from "../../../app/useThemeTokens.js";
import { getMacroData } from "../../../api/market.js";

export function MacroBar({ marketData, preferences = {} }) {
  const { cardBg, borderColor, textColor, mutedText } = useThemeTokens(preferences);
  const [macro, setMacro] = useState(null);

  useEffect(() => {
    getMacroData()
      .then(res => { if (res?.data) setMacro(res.data); })
      .catch(() => {});
  }, []);

  if (!marketData) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "65px",
          background: cardBg,
          border: `1px solid ${borderColor}`,
          borderRadius: "0.5rem",
          width: "100%"
        }}
      >
        <Loader2 size={20} className="animate-spin" style={{ color: "#3b82f6" }} />
        <span style={{ fontSize: "0.85rem", color: mutedText, marginLeft: "0.5rem", fontWeight: "600" }}>Đang tải dữ liệu vĩ mô...</span>
      </div>
    );
  }

  // ── VN Indices from marketData ──────────────────────────────────────────────
  const vnindexData = marketData?.indices?.VNINDEX;
  const vn30Data    = marketData?.indices?.VN30;

  const fmt = (v, digits = 2) => v != null ? Number(v).toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "—";
  const signStr = (v) => v >= 0 ? `+${Number(v).toFixed(2)}` : Number(v).toFixed(2);
  const pctStr  = (v) => v >= 0 ? `+${Number(v).toFixed(2)}%` : `${Number(v).toFixed(2)}%`;

  // ── USD/VND ─────────────────────────────────────────────────────────────────
  const usd = macro?.usd_vnd;
  const usdVal     = usd ? fmt(usd.sell, 0) : "—";
  const usdPrev    = usd ? (usd.sell * 0.9994) : null; // no prev available from VCB, show neutral
  const usdChg     = 0;
  const usdPct     = 0;

  // ── Vàng SJC ────────────────────────────────────────────────────────────────
  const gold = macro?.gold_sjc;
  const goldVal = gold ? `${fmt(gold.sell_m, 2)}M` : "—";

  // ── Dầu Brent ───────────────────────────────────────────────────────────────
  const oil = macro?.brent_oil;
  const oilVal = oil ? `$${oil.price.toFixed(2)}` : "—";
  const oilChg = oil?.change ?? 0;
  const oilPct = oil?.change_pct ?? 0;

  const BASIS = 1.70;
  const vn30f1mVal = vn30Data ? (vn30Data.close + BASIS).toLocaleString("vi-VN", { minimumFractionDigits: 2 }) : "—";

  const macroItems = [
    {
      label: "VN-INDEX",
      val: vnindexData ? fmt(vnindexData.close) : "—",
      change: vnindexData ? signStr(vnindexData.change) : "—",
      percent: vnindexData ? pctStr(vnindexData.pct) : "—",
      isUp: vnindexData ? vnindexData.change >= 0 : true,
      icon: Globe
    },
    {
      label: "VN30",
      val: vn30Data ? fmt(vn30Data.close) : "—",
      change: vn30Data ? signStr(vn30Data.change) : "—",
      percent: vn30Data ? pctStr(vn30Data.pct) : "—",
      isUp: vn30Data ? vn30Data.change >= 0 : true,
      icon: Globe
    },
    {
      label: "VN30F1M",
      val: vn30f1mVal,
      change: vn30Data ? signStr(vn30Data.change) : "—",
      percent: vn30Data ? pctStr(vn30Data.pct) : "—",
      isUp: vn30Data ? vn30Data.change >= 0 : true,
      sub: `Basis: +${BASIS.toFixed(2)}`,
      icon: Globe
    },
    {
      label: "USD/VND",
      val: usdVal,
      change: usd ? signStr(usdChg) : "—",
      percent: usd ? `${pctStr(usdPct)}` : "—",
      isUp: usdChg >= 0,
      sub: usd ? `Nguồn: ${usd.source}` : null,
      icon: DollarSign
    },
    {
      label: "VÀNG SJC",
      val: goldVal,
      change: "—",
      percent: "—",
      isUp: true,
      sub: gold ? `Mua: ${fmt(gold.buy_m, 2)}M · ${gold.source}` : null,
      icon: Coins
    },
    {
      label: "DẦU BRENT",
      val: oilVal,
      change: oil ? (oilChg >= 0 ? `+${oilChg.toFixed(2)}` : oilChg.toFixed(2)) : "—",
      percent: oil ? pctStr(oilPct) : "—",
      isUp: oilChg >= 0,
      sub: oil ? `Nguồn: ${oil.source}` : null,
      icon: Flame
    }
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
        const isNeutral = item.change === "—" || item.change === "+0.00";
        const color = isNeutral ? mutedText : (item.isUp ? "#10b981" : "#ef4444");
        const IconComponent = isNeutral ? item.icon : (item.isUp ? ArrowUpRight : ArrowDownRight);

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
              <item.icon size={12} style={{ color: mutedText }} />
            </div>

            <div style={{ display: "flex", alignItems: "baseline", gap: "0.4rem" }}>
              <span style={{ fontSize: "1.05rem", fontWeight: "900", color: textColor }}>
                {item.val}
              </span>
              {item.percent !== "—" && (
                <span style={{ fontSize: "0.72rem", fontWeight: "700", color, display: "flex", alignItems: "center" }}>
                  <IconComponent size={12} /> {item.percent}
                </span>
              )}
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
