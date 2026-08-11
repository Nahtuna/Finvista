import React, { useState, useEffect } from "react";
import { TrendingUp, ShieldAlert, Users, Globe, ArrowUpRight, ArrowDownRight, Loader2, Coins, BarChart3 } from "lucide-react";
import { useThemeTokens } from "../../../app/useThemeTokens.js";
import { API_BASE_URL } from "../../../api/client.js";

export function VNDerivativesWidget({ marketData, preferences = {}, language = "vi" }) {
  const { cardBg, subBg, borderColor, textColor, mutedText } = useThemeTokens(preferences);
  const [derivatives, setDerivatives] = useState(null);
  const [loading, setLoading] = useState(true);
  const isEnglish = language === "en";

  useEffect(() => {
    let isMounted = true;
    fetch(`${API_BASE_URL}/api/market/derivatives`)
      .then(res => {
        if (!res.ok) throw new Error("API failed");
        return res.json();
      })
      .then(data => {
        if (isMounted && data && data.status === "ok") {
          setDerivatives(data);
        }
      })
      .catch(err => console.error("Error fetching derivatives:", err?.message || String(err)))
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, []);

  if (!marketData) {
    return (
      <div 
        style={{ 
          display: "flex", 
          flexDirection: "column",
          justifyContent: "center", 
          alignItems: "center", 
          height: "180px", 
          background: cardBg, 
          border: `1px solid ${borderColor}`, 
          borderRadius: "0.75rem", 
          width: "100%" 
        }}
      >
        <Loader2 size={32} className="animate-spin" style={{ color: "#3b82f6" }} />
        <span style={{ fontSize: "0.85rem", color: mutedText, marginTop: "0.5rem", fontWeight: "600" }}>
          {isEnglish ? "Loading derivatives..." : "Đang tải dữ liệu phái sinh..."}
        </span>
      </div>
    );
  }

  const vn30Data = marketData?.indices?.VN30;
  const basis = 1.70;
  const vn30f1mPrice = vn30Data ? vn30Data.close + basis : 1312.80;
  const vn30f1mPriceStr = vn30f1mPrice.toLocaleString("vi-VN", { minimumFractionDigits: 2 });
  
  const changePctStr = vn30Data ? (vn30Data.pct >= 0 ? "+" : "") + vn30Data.pct.toFixed(2) + "%" : "+0.00%";
  const changeAmtStr = vn30Data ? (vn30Data.change >= 0 ? "+" : "") + vn30Data.change.toFixed(2) : "+0.00";
  const isUp = vn30Data ? vn30Data.change >= 0 : true;

  // Format helper to translate API response texts to English if needed
  const formatNetFlow = (netStr) => {
    if (!netStr) return "";
    if (!isEnglish) return netStr;
    return netStr
      .replace("Ròng Mua Long", "Net Long")
      .replace("Ròng Bán Short", "Net Short");
  };

  const formatBasis = (basisStr) => {
    if (!basisStr) return "";
    if (!isEnglish) return basisStr;
    return basisStr
      .replace("Khả quan", "Positive")
      .replace("Hạn chế", "Limited");
  };

  // Use real data from API, or fallback to mock
  const futuresData = derivatives ? {
    code: derivatives.code,
    price: derivatives.price,
    change: derivatives.change,
    isUp: derivatives.isUp,
    basis: formatBasis(derivatives.basis),
    oi: derivatives.oi,
    volume: derivatives.volume,
    foreignPosition: {
      long: derivatives.foreignPosition.long,
      short: derivatives.foreignPosition.short,
      net: formatNetFlow(derivatives.foreignPosition.net)
    },
    propPosition: {
      long: derivatives.propPosition.long,
      short: derivatives.propPosition.short,
      net: formatNetFlow(derivatives.propPosition.net)
    }
  } : {
    code: "VN30F1M",
    price: vn30f1mPriceStr,
    change: `${changeAmtStr} (${changePctStr})`,
    isUp: isUp,
    basis: isEnglish ? `+${basis.toFixed(2)} (Positive)` : `+${basis.toFixed(2)} (Khả quan)`,
    oi: isEnglish ? "58,420 Contracts" : "58,420 HĐ",
    volume: isEnglish ? "214,500 Contracts" : "214,500 HĐ",
    foreignPosition: {
      long: "8,450",
      short: "6,200",
      net: isEnglish ? "+2,250 (Net Long)" : "+2,250 (Ròng Mua Long)"
    },
    propPosition: {
      long: "4,100",
      short: "5,300",
      net: isEnglish ? "-1,200 (Net Short)" : "-1,200 (Ròng Bán Short)"
    }
  };

  const basisParts = futuresData.basis ? futuresData.basis.split(" ") : ["—", ""];
  const basisVal = basisParts[0];
  const basisLabel = basisParts.slice(1).join(" ");
  const isBasisPositive = basisVal.startsWith("+") || parseFloat(basisVal) >= 0;

  const oiParts = futuresData.oi ? futuresData.oi.split(" ") : ["—", ""];
  const oiVal = oiParts[0];
  const oiLabel = oiParts.slice(1).join(" ");

  const volParts = futuresData.volume ? futuresData.volume.split(" ") : ["—", ""];
  const volVal = volParts[0];
  const volLabel = volParts.slice(1).join(" ");

  const foreignParts = futuresData.foreignPosition?.net ? futuresData.foreignPosition.net.split(" (") : ["—", ""];
  const foreignVal = foreignParts[0];
  const foreignLabel = foreignParts[1] ? `(${foreignParts[1]}` : "";
  const isForeignBuy = foreignVal.startsWith("+") || parseFloat(foreignVal.replace(/,/g, "")) >= 0;

  const propParts = futuresData.propPosition?.net ? futuresData.propPosition.net.split(" (") : ["—", ""];
  const propVal = propParts[0];
  const propLabel = propParts[1] ? `(${propParts[1]}` : "";
  const isPropBuy = propVal.startsWith("+") || parseFloat(propVal.replace(/,/g, "")) >= 0;

  const items = [
    {
      label: isEnglish ? "VN30F1M FUTURES PRICE" : "GIÁ HĐTL VN30F1M",
      val: futuresData.price,
      sub: futuresData.change,
      isUp: futuresData.isUp,
      isNeutral: false,
      icon: TrendingUp
    },
    {
      label: isEnglish ? "BASIS SPREAD" : "ĐỘ LỆCH BASIS",
      val: basisVal,
      sub: basisLabel,
      isUp: isBasisPositive,
      isNeutral: false,
      icon: ShieldAlert
    },
    {
      label: isEnglish ? "OPEN INTEREST (OI)" : "KHỐI LƯỢNG MỞ (OI)",
      val: oiVal,
      sub: oiLabel,
      isUp: true,
      isNeutral: true,
      icon: Users
    },
    {
      label: isEnglish ? "TRADING VOLUME" : "THỂ TÍCH GIAO DỊCH (KLGD)",
      val: volVal,
      sub: volLabel,
      isUp: true,
      isNeutral: true,
      icon: BarChart3
    },
    {
      label: isEnglish ? "FOREIGN NET FLOW" : "KHỐI NGOẠI RÒNG FLOW",
      val: foreignVal,
      sub: foreignLabel,
      isUp: isForeignBuy,
      isNeutral: false,
      icon: Globe
    },
    {
      label: isEnglish ? "PROP NET FLOW" : "TỰ DOANH RÒNG FLOW",
      val: propVal,
      sub: propLabel,
      isUp: isPropBuy,
      isNeutral: false,
      icon: Coins
    }
  ];

  return (
    <>
      <style>{`
        .responsive-derivatives-grid {
          display: grid;
          grid-template-columns: repeat(6, 1fr);
          gap: 0.75rem;
          width: 100%;
          margin-bottom: 0.5rem;
        }
        @media (max-width: 1200px) {
          .responsive-derivatives-grid {
            grid-template-columns: repeat(3, 1fr);
          }
        }
        @media (max-width: 768px) {
          .responsive-derivatives-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        @media (max-width: 480px) {
          .responsive-derivatives-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
      <div className="responsive-derivatives-grid">
        {items.map((item, idx) => {
          const isNeutral = item.isNeutral || item.sub === "—" || item.sub === "";
          const color = isNeutral ? mutedText : (item.isUp ? "#10b981" : "#ef4444");
          const IconComponent = isNeutral ? item.icon : (item.isUp ? ArrowUpRight : ArrowDownRight);

          return (
            <div
              key={idx}
              className="macro-card-hover"
              style={{
                background: cardBg,
                border: `1px solid ${borderColor}`,
                borderRadius: "0.75rem",
                padding: "0.85rem 1.1rem",
                display: "flex",
                flexDirection: "column",
                justifyContent: "flex-start",
                minHeight: "92px",
                boxSizing: "border-box",
                transition: "transform 0.2s, box-shadow 0.2s, border-color 0.2s"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: "800", color: mutedText, letterSpacing: "0.5px" }}>
                  {item.label}
                </span>
                <item.icon size={14} style={{ color: mutedText, opacity: 0.8 }} />
              </div>

              <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.3rem" }}>
                <span style={{ fontSize: "1.35rem", fontWeight: "900", color: textColor, letterSpacing: "-0.5px", lineHeight: "1.1" }}>
                  {item.val}
                </span>
                {item.sub && (
                  <span style={{ fontSize: "0.75rem", fontWeight: "700", color, display: "flex", alignItems: "center", gap: "0.15rem" }}>
                    {!isNeutral && <IconComponent size={12} />} {item.sub}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
