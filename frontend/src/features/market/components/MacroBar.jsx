import React, { useEffect, useState } from "react";
import { ArrowUpRight, ArrowDownRight, Globe, Coins, Flame, DollarSign, Loader2, TrendingUp } from "lucide-react";
import { useThemeTokens } from "../../../app/useThemeTokens.js";
import { getMacroData } from "../../../api/market.js";

// Sleek unified sparkline component using real historical data points
function Sparkline({ data, color = "#2563eb", height = 28, width = 90 }) {
  if (!data || data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 6) - 3;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} fill="none" style={{ overflow: "visible" }}>
      <polyline points={pts} stroke={color} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={`${pts} ${width},${height} 0,${height}`} fill={`${color}10`} stroke="none" />
    </svg>
  );
}

export function MacroBar({ marketData, preferences = {}, language = "vi" }) {
  const { cardBg, borderColor, textColor, mutedText } = useThemeTokens(preferences);
  const [macro, setMacro] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    getMacroData()
      .then(res => {
        if (isMounted && res?.data) {
          setMacro(res.data);
        }
      })
      .catch(err => {
        console.error("Error fetching macro data:", err.message);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => { isMounted = false; };
  }, []);

  if (loading || !marketData) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "92px",
          background: cardBg,
          border: `1px solid ${borderColor}`,
          borderRadius: "0.75rem",
          width: "100%"
        }}
      >
        <Loader2 size={24} className="animate-spin" style={{ color: "#3b82f6" }} />
        <span style={{ fontSize: "0.85rem", color: mutedText, marginLeft: "0.5rem", fontWeight: "600" }}>
          Đang tải dữ liệu vĩ mô & lãi suất...
        </span>
      </div>
    );
  }

  const isEnglish = language === "en";

  const fmt = (v, digits = 2) => {
    if (v == null || isNaN(Number(v))) return "—";
    return Number(v).toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  };

  const signStr = (v) => {
    if (v == null || isNaN(Number(v))) return "—";
    const num = Number(v);
    return num >= 0 ? `+${num.toFixed(2)}` : num.toFixed(2);
  };

  const pctStr = (v) => {
    if (v == null || isNaN(Number(v))) return "—";
    const num = Number(v);
    return num >= 0 ? `+${num.toFixed(2)}%` : `${num.toFixed(2)}%`;
  };

  // ── Retrieve dynamic values with local database / scraped fallbacks ────────
  const vnindex = macro?.vnindex;
  const vn30 = macro?.vn30;
  const usd = macro?.usd_vnd;
  const gold = macro?.gold_sjc;
  const oil = macro?.brent_oil;
  const sbv = macro?.sbv_rates;

  const onRate = sbv?.on_rate !== undefined ? sbv.on_rate * 100 : 4.25;
  const w1Rate = sbv?.["1w_rate"] !== undefined ? sbv["1w_rate"] * 100 : 4.35;
  const m1Rate = sbv?.["1m_rate"] !== undefined ? sbv["1m_rate"] * 100 : 4.50;

  const macroItems = [
    {
      label: "VN-INDEX",
      val: vnindex ? fmt(vnindex.close) : "—",
      change: vnindex ? signStr(vnindex.change) : "—",
      percent: vnindex ? pctStr(vnindex.pct) : "—",
      isUp: vnindex ? vnindex.change >= 0 : true,
      history: vnindex?.history || [],
      color: "#3b82f6",
      icon: Globe
    },
    {
      label: "VN30",
      val: vn30 ? fmt(vn30.close) : "—",
      change: vn30 ? signStr(vn30.change) : "—",
      percent: vn30 ? pctStr(vn30.pct) : "—",
      isUp: vn30 ? vn30.change >= 0 : true,
      history: vn30?.history || [],
      color: "#10b981",
      icon: Globe
    },
    {
      label: "USD/VND",
      val: usd ? fmt(usd.sell, 0) : "—",
      change: usd ? signStr(usd.change) : "—",
      percent: usd ? pctStr(usd.pct) : "—",
      isUp: usd ? usd.change >= 0 : true,
      history: usd?.history || [],
      color: "#6366f1",
      sub: usd ? `Nguồn: ${usd.source}` : null,
      icon: DollarSign
    },
    {
      label: "VÀNG SJC",
      val: gold ? `${fmt(gold.sell_m, 2)}M` : "—",
      change: "—",
      percent: "—",
      isUp: true,
      history: gold?.history || [],
      color: "#eab308",
      sub: gold ? `Mua: ${fmt(gold.buy_m, 2)}M · ${gold.source}` : null,
      icon: Coins
    },
    {
      label: "DẦU BRENT",
      val: oil ? `$${oil.price.toFixed(2)}` : "—",
      change: oil ? (oil.change >= 0 ? `+${oil.change.toFixed(2)}` : oil.change.toFixed(2)) : "—",
      percent: oil ? pctStr(oil.change_pct) : "—",
      isUp: oil ? oil.change >= 0 : true,
      history: oil?.history || [],
      color: "#ef4444",
      sub: oil ? `Nguồn: ${oil.source}` : null,
      icon: Flame
    },
    {
      label: isEnglish ? "Overnight (ON)" : "Qua đêm (ON)",
      val: `${onRate.toFixed(2)}%`,
      change: "—",
      percent: "—",
      isUp: true,
      history: sbv?.on_history || [],
      color: "#3b82f6",
      icon: TrendingUp
    },
    {
      label: isEnglish ? "1 Week" : "1 Tuần",
      val: `${w1Rate.toFixed(2)}%`,
      change: "—",
      percent: "—",
      isUp: true,
      history: sbv?.["1w_history"] || [],
      color: "#10b981",
      icon: TrendingUp
    },
    {
      label: isEnglish ? "1 Month" : "1 Tháng",
      val: `${m1Rate.toFixed(2)}%`,
      change: "—",
      percent: "—",
      isUp: true,
      history: sbv?.["1m_history"] || [],
      color: "#f59e0b",
      icon: TrendingUp
    }
  ];

  return (
    <>
      <style>{`
        .responsive-macro-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 0.75rem;
          width: 100%;
          margin-bottom: 0.5rem;
        }
        @media (max-width: 1200px) {
          .responsive-macro-grid {
            grid-template-columns: repeat(3, 1fr);
          }
        }
        @media (max-width: 768px) {
          .responsive-macro-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        @media (max-width: 480px) {
          .responsive-macro-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.25rem 0" }}>
        <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: textColor, display: "flex", alignItems: "center", gap: "0.35rem", margin: 0, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          🏦 {isEnglish ? "Macro Indicators & SBV Rates" : "Chỉ số vĩ mô & Lãi suất NHNN"}
        </h4>
        <span style={{ fontSize: "0.7rem", color: mutedText }}>
          {isEnglish ? "Real-time & Historical Data" : "Dữ liệu thời gian thực & Lịch sử"}
        </span>
      </div>

      <div className="responsive-macro-grid">
        {macroItems.map((item, idx) => {
          // Dynamically compute change and percentage from history if not supplied by API
          let change = item.change;
          let percent = item.percent;
          let isUp = item.isUp;
          let isNeutral = change === "—" || percent === "—";

          if (isNeutral && item.history && item.history.length >= 2) {
            const last = item.history[item.history.length - 1];
            const prev = item.history[item.history.length - 2];
            const diff = last - prev;
            const pct = prev > 0 ? (diff / prev) * 100 : 0;
            
            if (Math.abs(diff) >= 0.001) {
              change = `${diff >= 0 ? "+" : ""}${diff.toFixed(2)}`;
              percent = `${diff >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
              isUp = diff >= 0;
              isNeutral = false;
            } else {
              change = "+0.00";
              percent = "+0.00%";
              isUp = true;
              isNeutral = true;
            }
          }

          const color = isNeutral ? mutedText : (isUp ? "#10b981" : "#ef4444");
          const IconComponent = isNeutral ? item.icon : (isUp ? ArrowUpRight : ArrowDownRight);

          return (
            <div
              key={idx}
              className="macro-card-hover"
              style={{
                background: cardBg,
                border: `1px solid ${borderColor}`,
                borderRadius: "0.75rem",
                padding: "0.75rem 1rem",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                height: "82px",
                minHeight: "82px",
                boxSizing: "border-box",
                transition: "transform 0.2s, box-shadow 0.2s, border-color 0.2s"
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "0.1rem", minWidth: 0, flex: 1 }}>
                <span style={{ fontSize: "0.72rem", fontWeight: "800", color: mutedText, letterSpacing: "0.5px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {item.label}
                </span>
                
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.35rem", marginTop: "0.1rem" }}>
                  <span style={{ fontSize: "1.25rem", fontWeight: "900", color: textColor, letterSpacing: "-0.5px", lineHeight: "1.1" }}>
                    {item.val}
                  </span>
                  {percent && percent !== "—" && percent !== "—%" && (
                    <span style={{ fontSize: "0.7rem", fontWeight: "700", color, display: "flex", alignItems: "center", gap: "0.02rem", whiteSpace: "nowrap" }}>
                      {!isNeutral && <IconComponent size={9} />} {percent}
                    </span>
                  )}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", marginLeft: "0.5rem" }}>
                <Sparkline data={item.history} color={isUp || isNeutral ? item.color : "#ef4444"} height={26} width={80} />
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
