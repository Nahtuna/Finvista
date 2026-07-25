import React, { useState, useEffect, useMemo } from "react";
import { Calendar, RefreshCw } from "lucide-react";
import { useThemeTokens } from "../../../app/useThemeTokens.js";
import { API_BASE_URL } from "../../../api/client.js";

export function SeasonalAnalysisWidget({ preferences = {}, language = "vi" }) {
  const { cardBg, subBg, borderColor, textColor, mutedText } = useThemeTokens(preferences);
  const isEn = language === "en";

  const [inputSymbol, setInputSymbol] = useState("VNINDEX");
  const [displaySymbol, setDisplaySymbol] = useState("VNINDEX");
  const [loading, setLoading] = useState(false);
  const [realtimeSeasonals, setRealtimeSeasonals] = useState(null);

  const monthNames = isEn
    ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    : ["Th1", "Th2", "Th3", "Th4", "Th5", "Th6", "Th7", "Th8", "Th9", "Th10", "Th11", "Th12"];

  // Fetch OHLCV data directly from UDF endpoint and compute exact monthly Seasonals
  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    const nowSeconds = Math.floor(Date.now() / 1000);
    const fromSeconds = nowSeconds - (15 * 365 * 86400);  // 15 years back
    const toSeconds   = nowSeconds + (2 * 365 * 86400);   // +2 years forward (covers future-dated DB entries)

    fetch(`${API_BASE_URL}/api/udf/history?symbol=${encodeURIComponent(displaySymbol)}&resolution=1D&from=${fromSeconds}&to=${toSeconds}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        const contentType = res.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          throw new Error("Received non-JSON response from UDF API");
        }
        return res.json();
      })
      .then(data => {
        if (!isMounted) return;

        if (data && data.s === "ok" && data.t && data.t.length > 0) {
          const yearMap = {};

          for (let i = 0; i < data.t.length; i++) {
            const date = new Date(data.t[i] * 1000);
            const yr = date.getFullYear();
            const mo = date.getMonth();
            const closeP = data.c[i];

            if (!yearMap[yr]) yearMap[yr] = {};
            if (!yearMap[yr][mo]) yearMap[yr][mo] = [];
            yearMap[yr][mo].push(closeP);
          }

          const colors = [
            "#ef4444", "#10b981", "#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#ec4899",
            "#14b8a6", "#f97316", "#84cc16", "#a855f7", "#6366f1", "#0284c7", "#059669"
          ];

          const computedYears = Object.keys(yearMap)
            .sort((a, b) => Number(b) - Number(a))
            .map((yrStr, idx) => {
              const yrNum = Number(yrStr);
              const monthsData = yearMap[yrNum];

              let yearStartPrice = null;
              let yearEndPrice = null;
              const months = [];

              for (let m = 0; m < 12; m++) {
                const arr = monthsData[m];
                if (arr && arr.length > 0) {
                  if (yearStartPrice === null) yearStartPrice = arr[0];
                  const mStart = arr[0];
                  const mEnd = arr[arr.length - 1];
                  yearEndPrice = mEnd;
                  const mPct = mStart > 0 ? ((mEnd - mStart) / mStart) * 100 : 0;
                  months.push(Number(mPct.toFixed(2)));
                }
              }

              const totalYtdPct = yearStartPrice && yearEndPrice ? ((yearEndPrice - yearStartPrice) / yearStartPrice) * 100 : 0;
              const returnPctStr = `${totalYtdPct >= 0 ? "+" : ""}${totalYtdPct.toFixed(2)}%`;

              return {
                year: yrNum === new Date().getFullYear() ? `${yrNum} (YTD)` : `${yrNum}`,
                returnPct: returnPctStr,
                rawReturn: totalYtdPct,
                months,
                color: colors[idx % colors.length]
              };
            });

          setRealtimeSeasonals(computedYears);
        }
      })
      .catch(err => console.error("Error computing UDF Seasonals:", err))
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, [displaySymbol]);

  const [startYear, setStartYear] = useState(2015);
  const [endYear, setEndYear] = useState(2026);

  // Filtered Seasonals Dataset by Symbol and Range Slider — UDF data only
  const allHistoricalYears = useMemo(() => {
    const baseList = realtimeSeasonals || [];
    return baseList.filter(sy => {
      const yrNum = parseInt(sy.year);
      return yrNum >= startYear && yrNum <= endYear;
    });
  }, [realtimeSeasonals, startYear, endYear]);

  // Rises and falls counts per month
  const risesAndFalls = useMemo(() => {
    const counts = monthNames.map((_, mIdx) => {
      let up = 0, down = 0;
      allHistoricalYears.forEach(y => {
        const val = y.months[mIdx];
        if (val !== undefined) {
          if (val >= 0) up++;
          else down++;
        }
      });
      return { up, down };
    });
    return counts;
  }, [allHistoricalYears]);

  // Automated Seasonal Insights computation
  const seasonalInsights = useMemo(() => {
    if (!allHistoricalYears || allHistoricalYears.length === 0) return null;

    let bestMonthIdx = 0, bestWinRate = 0;
    let worstMonthIdx = 0, worstWinRate = 100;

    risesAndFalls.forEach((rf, idx) => {
      const total = rf.up + rf.down;
      if (total > 0) {
        const winRate = (rf.up / total) * 100;
        if (winRate > bestWinRate) {
          bestWinRate = winRate;
          bestMonthIdx = idx;
        }
        if (winRate < worstWinRate) {
          worstWinRate = winRate;
          worstMonthIdx = idx;
        }
      }
    });

    const bestMonthName = monthNames[bestMonthIdx].toUpperCase();
    const worstMonthName = monthNames[worstMonthIdx].toUpperCase();
    const yearsCount = allHistoricalYears.length;

    return {
      bestMonthName,
      bestWinRate: Math.round(bestWinRate),
      bestUpCount: risesAndFalls[bestMonthIdx].up,
      worstMonthName,
      worstWinRate: Math.round(worstWinRate),
      worstDownCount: risesAndFalls[worstMonthIdx].down,
      yearsCount,
      summaryText: isEn
        ? `Over ${yearsCount} historical years (${startYear}-${endYear}), **${displaySymbol}** has the highest probability of gains in **${bestMonthName}** (Win rate **${Math.round(bestWinRate)}%** — ${risesAndFalls[bestMonthIdx].up}/${yearsCount} years positive). Conversely, **${worstMonthName}** faces the highest downward risk (${100 - Math.round(worstWinRate)}% probability of decline).`
        : `Trong ${yearsCount} năm lịch sử (${startYear}-${endYear}), **${displaySymbol}** có xác suất tăng cao nhất vào **${bestMonthName}** (Tỷ lệ thắng **${Math.round(bestWinRate)}%** với ${risesAndFalls[bestMonthIdx].up}/${yearsCount} năm tăng giá). Ngược lại, tháng **${worstMonthName}** thường đối mặt áp lực điều chỉnh rủi ro nhất (Xác suất giảm **${100 - Math.round(worstWinRate)}%**).`
    };
  }, [allHistoricalYears, risesAndFalls, displaySymbol, startYear, endYear]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (inputSymbol.trim()) {
      setDisplaySymbol(inputSymbol.trim().toUpperCase());
    }
  };

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
      {/* Header Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
        <div>
          <h3 style={{ fontSize: "1.15rem", fontWeight: "900", margin: 0, color: textColor, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Calendar size={18} style={{ color: "#3b82f6" }} /> {displaySymbol} • {isEn ? "Seasonal Cycle Matrix (Seasonals Heatmap)" : "Ma trận Chu kỳ Mùa vụ (Seasonals Heatmap)"}
          </h3>
          <p style={{ fontSize: "0.78rem", color: mutedText, margin: "0.2rem 0 0 0" }}>
            {isEn ? "Monthly % gain/loss performance computed directly from UDF candle data" : "Hiệu suất % tăng/giảm từng tháng thực tế tính trực tiếp từ dữ liệu nến UDF"}
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.35rem" }}>
            <input
              value={inputSymbol}
              onChange={e => setInputSymbol(e.target.value)}
              placeholder={isEn ? "Enter ticker (VNINDEX, HPG)..." : "Nhập mã (VNINDEX, HPG)..."}
              style={{
                background: subBg,
                border: `1px solid ${borderColor}`,
                color: textColor,
                padding: "0.35rem 0.6rem",
                borderRadius: "0.35rem",
                fontSize: "0.78rem",
                width: "140px"
              }}
            />
            <button type="submit" style={{ background: "#2563eb", color: "#fff", border: "none", borderRadius: "0.35rem", padding: "0.35rem 0.75rem", fontSize: "0.78rem", cursor: "pointer" }}>{isEn ? "Search" : "Xem mã"}</button>
          </form>

          <div style={{ display: "flex", gap: "0.25rem" }}>
            {["VNINDEX", "HPG", "FPT", "VIC"].map(s => (
              <button
                key={s}
                onClick={() => { setInputSymbol(s); setDisplaySymbol(s); }}
                style={{
                  background: displaySymbol === s ? "rgba(59,130,246,0.2)" : subBg,
                  color: displaySymbol === s ? "#3b82f6" : mutedText,
                  border: `1px solid ${displaySymbol === s ? "#3b82f6" : borderColor}`,
                  borderRadius: "0.25rem",
                  padding: "0.25rem 0.45rem",
                  fontSize: "0.72rem",
                  fontWeight: "800",
                  cursor: "pointer"
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Single Compact TradingView Style Year Range Slider Bar */}
      <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "0.45rem 0.85rem", display: "flex", alignItems: "center", gap: "1.25rem" }}>
        <div style={{ fontSize: "0.78rem", fontWeight: "800", color: mutedText, whiteSpace: "nowrap" }}>
          📅 {isEn ? "YEAR RANGE:" : "KHOẢNG NĂM:"} <strong style={{ color: "#3b82f6" }}>{startYear} ── {endYear}</strong> ({endYear - startYear + 1} {isEn ? "Yrs" : "Năm"})
        </div>

        {/* Single Seamless Range Track with handle */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", width: "320px" }}>
          <span style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: "800" }}>2000</span>
          <input
            type="range"
            min="2000"
            max="2026"
            value={startYear}
            onChange={e => {
              const val = Number(e.target.value);
              if (val <= endYear) setStartYear(val);
            }}
            style={{ flex: 1, accentColor: "#3b82f6", cursor: "pointer", height: "5px" }}
          />
          <span style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: "800" }}>{isEn ? "to" : "đến"}</span>
          <input
            type="range"
            min="2000"
            max="2026"
            value={endYear}
            onChange={e => {
              const val = Number(e.target.value);
              if (val >= startYear) setEndYear(val);
            }}
            style={{ flex: 1, accentColor: "#3b82f6", cursor: "pointer", height: "5px" }}
          />
          <span style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: "800" }}>2026</span>
        </div>

        <div style={{ display: "flex", gap: "0.3rem", marginLeft: "auto" }}>
          {[
            { label: isEn ? "5 Yrs" : "5 Năm", start: 2021, end: 2026 },
            { label: isEn ? "10 Yrs" : "10 Năm", start: 2016, end: 2026 },
            { label: isEn ? "All" : "Tất cả", start: 2000, end: 2026 }
          ].map(preset => {
            const isActive = startYear === preset.start && endYear === preset.end;
            return (
              <button
                key={preset.label}
                onClick={() => { setStartYear(preset.start); setEndYear(preset.end); }}
                style={{
                  background: isActive ? "#2563eb" : subBg,
                  color: isActive ? "#fff" : mutedText,
                  border: `1px solid ${isActive ? "#2563eb" : borderColor}`,
                  borderRadius: "0.35rem",
                  padding: "0.25rem 0.6rem",
                  fontSize: "0.72rem",
                  fontWeight: "800",
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
      </div>

      {loading && (
        <div style={{ fontSize: "0.78rem", color: "#3b82f6", display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: "700", padding: "0.25rem 0" }}>
          <RefreshCw size={14} className="spin" /> {isEn ? `Computing UDF candle data for ${displaySymbol}...` : `Đang tính toán dữ liệu UDF nến thực tế cho ${displaySymbol}...`}
        </div>
      )}

      {!loading && allHistoricalYears.length === 0 && (
        <div style={{ textAlign: "center", padding: "2.5rem 1rem", color: mutedText, fontSize: "0.85rem" }}>
          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📡</div>
          <div style={{ fontWeight: "700", color: textColor, marginBottom: "0.35rem" }}>
            {isEn ? `No data available for ${displaySymbol}` : `Chưa có dữ liệu cho mã ${displaySymbol}`}
          </div>
          <div style={{ fontSize: "0.75rem" }}>
            {isEn
              ? "The UDF server returned no historical candles for this symbol and date range. Try VNINDEX, VN30, or a stock listed in the database."
              : "UDF server không trả về dữ liệu nến lịch sử cho mã này và khoảng năm đã chọn. Thử VNINDEX, VN30 hoặc mã cổ phiếu có trong cơ sở dữ liệu."}
          </div>
        </div>
      )}

      {/* Pure Heatmap Table — only render when data available */}
      {!loading && allHistoricalYears.length > 0 && (
      <div style={{ overflowX: "auto", borderTop: `1px solid ${borderColor}`, paddingTop: "0.5rem" }}>
        <table style={{ width: "100%", tableLayout: "fixed", borderCollapse: "collapse", fontSize: "0.78rem" }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${borderColor}`, color: mutedText, fontSize: "0.75rem" }}>
              <th style={{ width: "95px", padding: "0.5rem 0.25rem", textAlign: "left", fontWeight: "900", color: "#94a3b8" }}>{isEn ? "YEAR" : "NĂM"}</th>
              {monthNames.map(m => (
                <th key={m} style={{ padding: "0.5rem 0.15rem", textAlign: "center", fontWeight: "900", color: "#94a3b8" }}>{m.toUpperCase()}</th>
              ))}
              <th style={{ width: "85px", padding: "0.5rem 0.25rem", textAlign: "right", fontWeight: "900", color: "#94a3b8" }}>YTD</th>
            </tr>
          </thead>

          <tbody>
            {allHistoricalYears.map((sy, idx) => (
              <tr key={idx} style={{ borderBottom: `1px solid ${borderColor}15` }}>
                <td style={{ padding: "0.35rem 0.25rem", fontWeight: "900", color: sy.color, fontSize: "0.8rem", whiteSpace: "nowrap" }}>
                  {sy.year}
                </td>
                {monthNames.map((m, mIdx) => {
                  const val = sy.months[mIdx];
                  if (val === undefined) return <td key={m} style={{ textAlign: "center", color: "#475569", fontWeight: "700" }}>-</td>;

                  const isUp = val >= 0;
                  // Modern sleek TradingView color gradient fills
                  const cellBg = isUp
                    ? `rgba(20, 83, 45, ${Math.min(1, 0.45 + Math.abs(val) / 25)})`
                    : `rgba(127, 29, 29, ${Math.min(1, 0.45 + Math.abs(val) / 25)})`;
                  const cellColor = isUp ? "#4ade80" : "#fca5a5";

                  return (
                    <td key={m} style={{ padding: "0.2rem 0.1rem" }}>
                      <div
                        style={{
                          padding: "0.35rem 0.1rem",
                          textAlign: "center",
                          fontWeight: "800",
                          color: cellColor,
                          background: cellBg,
                          borderRadius: "0.25rem",
                          fontSize: "0.75rem",
                          boxShadow: isUp ? "inset 0 0 4px rgba(74, 222, 128, 0.15)" : "inset 0 0 4px rgba(252, 165, 165, 0.15)"
                        }}
                      >
                        {isUp ? "+" : ""}{val.toFixed(2)}%
                      </div>
                    </td>
                  );
                })}
                <td style={{ padding: "0.35rem 0.25rem", textAlign: "right", fontWeight: "900", fontSize: "0.82rem", color: sy.returnPct.startsWith("+") ? "#10b981" : "#ef4444" }}>
                  {sy.returnPct}
                </td>
              </tr>
            ))}

            {/* Bottom Summary Row: Rises and Falls counts */}
            <tr style={{ borderTop: `2px solid ${borderColor}`, background: subBg }}>
              <td style={{ padding: "0.45rem 0.25rem", fontWeight: "900", color: textColor, fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                {isEn ? "Up / Down Stats" : "Thống kê Tăng / Giảm"}
              </td>
              {risesAndFalls.map((rf, idx) => (
                <td key={idx} style={{ padding: "0.45rem 0.05rem", textAlign: "center", fontSize: "0.72rem", fontWeight: "900" }}>
                  <div style={{ display: "flex", justifyContent: "center", gap: "0.15rem", alignItems: "center" }}>
                    <span style={{ color: "#4ade80", background: "rgba(34,197,94,0.15)", padding: "0.1rem 0.25rem", borderRadius: "0.2rem" }}>▲{rf.up}</span>
                    <span style={{ color: "#fca5a5", background: "rgba(239,68,68,0.15)", padding: "0.1rem 0.25rem", borderRadius: "0.2rem" }}>▼{rf.down}</span>
                  </div>
                </td>
              ))}
              <td style={{ padding: "0.45rem 0.25rem", textAlign: "right", fontWeight: "900", color: "#3b82f6", fontSize: "0.78rem", whiteSpace: "nowrap" }}>
                {allHistoricalYears.length} {isEn ? "Hist. Years" : "Năm Lịch Sử"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      )}

      {/* AI SEASONALS INTELLIGENCE INSIGHT CARD */}
      {seasonalInsights && (
        <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "0.85rem 1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.82rem", fontWeight: "900", color: "#3b82f6", display: "flex", alignItems: "center", gap: "0.4rem" }}>
              💡 {isEn ? `SMART SEASONAL TREND ANALYSIS (${displaySymbol})` : `NHẬN ĐỊNH XU HƯỚNG MÙA VỤ THÔNG MINH (${displaySymbol})`}
            </span>
            <span style={{ fontSize: "0.7rem", background: "rgba(59,130,246,0.15)", color: "#3b82f6", padding: "0.15rem 0.5rem", borderRadius: "0.2rem", fontWeight: "800" }}>
              {isEn ? `${seasonalInsights.yearsCount}-year pattern` : `Mẫu ${seasonalInsights.yearsCount} năm lịch sử`}
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", margin: "0.2rem 0" }}>
            <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "0.375rem", padding: "0.55rem 0.75rem" }}>
              <div style={{ fontSize: "0.72rem", color: "#10b981", fontWeight: "700" }}>🔥 {isEn ? "HIGHEST PROBABILITY UPMONTH" : "THÁNG CÓ XÁC SUẤT TĂNG CAO NHẤT"}</div>
              <div style={{ fontSize: "0.95rem", fontWeight: "900", color: textColor, marginTop: "0.15rem" }}>
                {seasonalInsights.bestMonthName} <span style={{ color: "#10b981" }}>({seasonalInsights.bestWinRate}% {isEn ? "Win Rate" : "Tỷ lệ thắng"})</span>
              </div>
              <div style={{ fontSize: "0.7rem", color: mutedText, marginTop: "0.15rem" }}>
                {seasonalInsights.bestUpCount}/{seasonalInsights.yearsCount} {isEn ? "years recorded positive" : "năm ghi nhận tăng trưởng dương"}
              </div>
            </div>

            <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "0.375rem", padding: "0.55rem 0.75rem" }}>
              <div style={{ fontSize: "0.72rem", color: "#ef4444", fontWeight: "700" }}>⚠️ {isEn ? "HIGHEST CORRECTION RISK MONTH" : "THÁNG RỦI RO ĐIỀU CHỈNH CAO NHẤT"}</div>
              <div style={{ fontSize: "0.95rem", fontWeight: "900", color: textColor, marginTop: "0.15rem" }}>
                {seasonalInsights.worstMonthName} <span style={{ color: "#ef4444" }}>({100 - seasonalInsights.worstWinRate}% {isEn ? "Decline Rate" : "Tỷ lệ giảm"})</span>
              </div>
              <div style={{ fontSize: "0.7rem", color: mutedText, marginTop: "0.15rem" }}>
                {seasonalInsights.worstDownCount}/{seasonalInsights.yearsCount} {isEn ? "years faced sell-off pressure" : "năm gặp áp lực chốt lời giảm giá"}
              </div>
            </div>
          </div>

          <p style={{ fontSize: "0.76rem", color: textColor, margin: 0, lineHeight: "1.45" }}>
            📌 <strong>{isEn ? "Trend Summary:" : "Tóm tắt xu hướng:"}</strong> {isEn
              ? <>Based on actual candle data from the selected year range, <strong>{displaySymbol}</strong> tends to perform best in <strong>{seasonalInsights.bestMonthName}</strong>. Conversely, traders should exercise caution and reduce exposure entering <strong>{seasonalInsights.worstMonthName}</strong>.</>
              : <>Dựa trên dữ liệu nến thực tế tính toán từ mốc năm kéo chọn, <strong>{displaySymbol}</strong> thường có hiệu suất giao dịch vượt trội nhất vào <strong>{seasonalInsights.bestMonthName}</strong>. Trái lại, Trader nên cẩn trọng quản trị rủi ro hạ tỷ trọng khi bước vào <strong>{seasonalInsights.worstMonthName}</strong>.</>}
          </p>
        </div>
      )}
    </div>
  );
}
