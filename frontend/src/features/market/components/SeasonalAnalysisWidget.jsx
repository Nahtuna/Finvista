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
    const toSeconds = nowSeconds + (2 * 365 * 86400);   // +2 years forward (covers future-dated DB entries)

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
      .catch(err => console.error("Error computing UDF Seasonals:", err?.message || String(err)))
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

  // Automated Seasonal Insights computation with Rich Quantitative Analytics
  const seasonalInsights = useMemo(() => {
    if (!allHistoricalYears || allHistoricalYears.length === 0) return null;

    const yearsCount = allHistoricalYears.length;

    // Calculate detailed stats per month
    const monthStats = monthNames.map((m, mIdx) => {
      let totalReturn = 0;
      let count = 0;
      let maxGain = -Infinity;
      let maxLoss = Infinity;
      let upCount = 0;
      let downCount = 0;

      allHistoricalYears.forEach(y => {
        const val = y.months[mIdx];
        if (val !== undefined) {
          totalReturn += val;
          count++;
          if (val > maxGain) maxGain = val;
          if (val < maxLoss) maxLoss = val;
          if (val >= 0) upCount++;
          else downCount++;
        }
      });

      const avgReturn = count > 0 ? totalReturn / count : 0;
      const winRate = count > 0 ? (upCount / count) * 100 : 0;

      return {
        monthName: m.toUpperCase(),
        monthIdx: mIdx,
        avgReturn,
        winRate: Math.round(winRate),
        upCount,
        downCount,
        count,
        maxGain: maxGain === -Infinity ? 0 : maxGain,
        maxLoss: maxLoss === Infinity ? 0 : maxLoss
      };
    });

    // Find Best Month & Worst Month
    let best = monthStats[0];
    let worst = monthStats[0];

    monthStats.forEach(ms => {
      if (ms.winRate > best.winRate || (ms.winRate === best.winRate && ms.avgReturn > best.avgReturn)) {
        best = ms;
      }
      if (ms.winRate < worst.winRate || (ms.winRate === worst.winRate && ms.avgReturn < worst.avgReturn)) {
        worst = ms;
      }
    });

    // Rigorous Compounded Quarterly Performance Calculation across all historical years
    const computeQuarterAvg = (startMonthIdx) => {
      let totalQReturn = 0;
      let validYears = 0;
      allHistoricalYears.forEach(y => {
        let qProduct = 1;
        let hasData = false;
        for (let i = 0; i < 3; i++) {
          const mVal = y.months[startMonthIdx + i];
          if (mVal !== undefined) {
            qProduct *= (1 + mVal / 100);
            hasData = true;
          }
        }
        if (hasData) {
          totalQReturn += (qProduct - 1) * 100;
          validYears++;
        }
      });
      return validYears > 0 ? totalQReturn / validYears : 0;
    };

    const q1Avg = computeQuarterAvg(0);
    const q2Avg = computeQuarterAvg(3);
    const q3Avg = computeQuarterAvg(6);
    const q4Avg = computeQuarterAvg(9);

    const quarters = [
      { name: "Quý 1 (T1-T3)", avgReturn: q1Avg, labelEn: "Q1 (Jan-Mar)" },
      { name: "Quý 2 (T4-T6)", avgReturn: q2Avg, labelEn: "Q2 (Apr-Jun)" },
      { name: "Quý 3 (T7-T9)", avgReturn: q3Avg, labelEn: "Q3 (Jul-Sep)" },
      { name: "Quý 4 (T10-T12)", avgReturn: q4Avg, labelEn: "Q4 (Oct-Dec)" }
    ];

    const sortedQuarters = [...quarters].sort((a, b) => b.avgReturn - a.avgReturn);
    const bestQuarter = sortedQuarters[0];
    const worstQuarter = sortedQuarters[sortedQuarters.length - 1];

    return {
      best,
      worst,
      monthStats,
      quarters,
      bestQuarter,
      worstQuarter,
      yearsCount
    };
  }, [allHistoricalYears, risesAndFalls, displaySymbol, startYear, endYear]);

  // Sync seasonal insights to global window context for AI Chat Assistant memory
  useEffect(() => {
    if (seasonalInsights) {
      window.__FINVISTA_SEASONALS_CONTEXT__ = {
        symbol: displaySymbol,
        startYear,
        endYear,
        yearsCount: seasonalInsights.yearsCount,
        bestMonth: seasonalInsights.best.monthName,
        bestAvg: seasonalInsights.best.avgReturn.toFixed(2),
        bestWin: seasonalInsights.best.winRate,
        bestPeak: seasonalInsights.best.maxGain.toFixed(2),
        worstMonth: seasonalInsights.worst.monthName,
        worstAvg: seasonalInsights.worst.avgReturn.toFixed(2),
        worstWin: seasonalInsights.worst.winRate,
        worstDrawdown: seasonalInsights.worst.maxLoss.toFixed(2),
        q1: seasonalInsights.quarters[0].avgReturn.toFixed(2),
        q2: seasonalInsights.quarters[1].avgReturn.toFixed(2),
        q3: seasonalInsights.quarters[2].avgReturn.toFixed(2),
        q4: seasonalInsights.quarters[3].avgReturn.toFixed(2)
      };
    }
  }, [seasonalInsights, displaySymbol, startYear, endYear]);

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
          <table style={{ width: "100%", minWidth: "750px", borderCollapse: "collapse", fontSize: "0.78rem" }}>
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
                  {allHistoricalYears.length} {isEn ? "Yrs" : "Năm Lịch Sử"}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* AI SEASONALS INTELLIGENCE INSIGHT CARD */}
      {seasonalInsights && (
        <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "0.85rem 1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: "900", color: "#3b82f6", display: "flex", alignItems: "center", gap: "0.4rem" }}>
              🧠 {isEn ? `QUANTITATIVE SEASONAL INSIGHTS (${displaySymbol})` : `NHẬN ĐỊNH ĐỊNH LƯỢNG MÙA VỤ CHI TIẾT (${displaySymbol})`}
            </span>
            <span style={{ fontSize: "0.7rem", background: "rgba(59,130,246,0.15)", color: "#3b82f6", padding: "0.15rem 0.5rem", borderRadius: "0.2rem", fontWeight: "800" }}>
              {isEn ? `${seasonalInsights.yearsCount}-year sample backtest` : `Mẫu ${seasonalInsights.yearsCount} năm backtest`}
            </span>
          </div>

          {/* Key Extremes Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <div style={{ background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.25)", borderRadius: "0.375rem", padding: "0.6rem 0.75rem" }}>
              <div style={{ fontSize: "0.72rem", color: "#10b981", fontWeight: "800", display: "flex", justifyContent: "space-between" }}>
                <span>🔥 {isEn ? "BEST MONTH" : "THÁNG TỐT NHẤT"}</span>
                <span>Avg: +{seasonalInsights.best.avgReturn.toFixed(2)}%</span>
              </div>
              <div style={{ fontSize: "1rem", fontWeight: "900", color: textColor, marginTop: "0.2rem" }}>
                {seasonalInsights.best.monthName} <span style={{ color: "#10b981", fontSize: "0.82rem" }}>({seasonalInsights.best.winRate}% {isEn ? "Win" : "Thắng"})</span>
              </div>
              <div style={{ fontSize: "0.7rem", color: mutedText, marginTop: "0.25rem", display: "flex", gap: "0.6rem" }}>
                <span>Tăng: {seasonalInsights.best.upCount}/{seasonalInsights.yearsCount} năm</span>
                <span>Peak Max: <strong style={{ color: "#10b981" }}>+{seasonalInsights.best.maxGain.toFixed(2)}%</strong></span>
              </div>
            </div>

            <div style={{ background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "0.375rem", padding: "0.6rem 0.75rem" }}>
              <div style={{ fontSize: "0.72rem", color: "#ef4444", fontWeight: "800", display: "flex", justifyContent: "space-between" }}>
                <span>⚠️ {isEn ? "WORST MONTH" : "THÁNG RỦI RO NHẤT"}</span>
                <span>Avg: {seasonalInsights.worst.avgReturn.toFixed(2)}%</span>
              </div>
              <div style={{ fontSize: "1rem", fontWeight: "900", color: textColor, marginTop: "0.2rem" }}>
                {seasonalInsights.worst.monthName} <span style={{ color: "#ef4444", fontSize: "0.82rem" }}>({100 - seasonalInsights.worst.winRate}% {isEn ? "Decline" : "Giảm"})</span>
              </div>
              <div style={{ fontSize: "0.7rem", color: mutedText, marginTop: "0.25rem", display: "flex", gap: "0.6rem" }}>
                <span>Giảm: {seasonalInsights.worst.downCount}/{seasonalInsights.yearsCount} năm</span>
                <span>Drawdown Max: <strong style={{ color: "#ef4444" }}>{seasonalInsights.worst.maxLoss.toFixed(2)}%</strong></span>
              </div>
            </div>
          </div>

          {/* Quarterly Seasonality Breakdown */}
          <div style={{ background: preferences.colorMode === "light" ? "#f1f5f9" : "rgba(30,41,59,0.5)", border: `1px solid ${borderColor}`, borderRadius: "0.375rem", padding: "0.6rem 0.75rem" }}>
            <div style={{ fontSize: "0.74rem", fontWeight: "800", color: "#94a3b8", marginBottom: "0.4rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
              📊 {isEn ? "QUARTERLY SEASONAL CYCLE PERFORMANCE" : "HIỆU SUẤT TRUNG BÌNH THEO CHU KỲ QUÝ (QUARTERLY PERFORMANCE)"}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.5rem" }}>
              {seasonalInsights.quarters.map(q => {
                const isPositive = q.avgReturn >= 0;
                const isBestQ = q.name === seasonalInsights.bestQuarter.name;
                return (
                  <div
                    key={q.name}
                    style={{
                      background: isBestQ ? (preferences.colorMode === "light" ? "rgba(37,99,235,0.08)" : "rgba(59,130,246,0.15)") : (preferences.colorMode === "light" ? "#f8fafc" : "rgba(15,23,42,0.6)"),
                      border: `1px solid ${isBestQ ? "#3b82f6" : borderColor}`,
                      borderRadius: "0.25rem",
                      padding: "0.35rem 0.45rem",
                      textAlign: "center"
                    }}
                  >
                    <div style={{ fontSize: "0.68rem", color: mutedText, fontWeight: "700" }}>
                      {isEn ? q.labelEn : q.name}
                    </div>
                    <div style={{ fontSize: "0.82rem", fontWeight: "900", color: isPositive ? "#10b981" : "#ef4444", marginTop: "0.1rem" }}>
                      {isPositive ? "+" : ""}{q.avgReturn.toFixed(2)}%
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Actionable Strategy Playbook */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.25rem" }}>
            <div style={{ fontSize: "0.78rem", fontWeight: "800", color: "#f59e0b", display: "flex", alignItems: "center", gap: "0.35rem" }}>
              💡 {isEn ? "ACTIONABLE TRADING PLAYBOOK" : "CHIẾN LƯỢC GIAO DỊCH THEO MÙA VỤ"}
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", background: "rgba(16, 185, 129, 0.04)", border: `1px solid ${borderColor}`, borderLeft: "4px solid #10b981", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", fontSize: "0.76rem" }}>
                <span style={{ fontSize: "1rem" }}>🟢</span>
                <div style={{ flex: 1 }}>
                  <strong>{isEn ? "Accumulation Window:" : "Tích lũy vị thế:"}</strong>{" "}
                  {isEn
                    ? `Buy ahead of ${seasonalInsights.best.monthName} (Win Rate: ${seasonalInsights.best.winRate}%, Avg: +${seasonalInsights.best.avgReturn.toFixed(2)}%)`
                    : `Gom mua trước ${seasonalInsights.best.monthName} (Tỷ lệ thắng: ${seasonalInsights.best.winRate}%, TB: +${seasonalInsights.best.avgReturn.toFixed(2)}%)`}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", background: "rgba(239, 68, 68, 0.04)", border: `1px solid ${borderColor}`, borderLeft: "4px solid #ef4444", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", fontSize: "0.76rem" }}>
                <span style={{ fontSize: "1rem" }}>🔴</span>
                <div style={{ flex: 1 }}>
                  <strong>{isEn ? "De-risk / Profit Taking:" : "Hạ tỷ trọng / Phòng vệ:"}</strong>{" "}
                  {isEn
                    ? `De-risk prior to ${seasonalInsights.worst.monthName} (Correction Freq: ${100 - seasonalInsights.worst.winRate}%, Avg: ${seasonalInsights.worst.avgReturn.toFixed(2)}%)`
                    : `Hạ margin/phòng vệ trước ${seasonalInsights.worst.monthName} (Tần suất giảm: ${100 - seasonalInsights.worst.winRate}%, TB: ${seasonalInsights.worst.avgReturn.toFixed(2)}%)`}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", background: "rgba(59, 130, 246, 0.04)", border: `1px solid ${borderColor}`, borderLeft: "4px solid #3b82f6", borderRadius: "0.375rem", padding: "0.5rem 0.75rem", fontSize: "0.76rem" }}>
                <span style={{ fontSize: "1rem" }}>⭐</span>
                <div style={{ flex: 1 }}>
                  <strong>{isEn ? "Best Quarter:" : "Quý bùng nổ nhất:"}</strong>{" "}
                  {isEn
                    ? `${seasonalInsights.bestQuarter.labelEn} (Avg: +${seasonalInsights.bestQuarter.avgReturn.toFixed(2)}%)`
                    : `${seasonalInsights.bestQuarter.name} (Tăng trưởng TB: +${seasonalInsights.bestQuarter.avgReturn.toFixed(2)}%)`}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
