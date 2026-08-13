import React, { useState, useEffect, useMemo } from "react";

export function MarketBreadthChart({ warrants = [], language = "vi", preferences = {} }) {
  const isEnglish = language === "en";

  // Standard theme tokens
  const isDark = preferences.theme !== "light";
  const cardBg = isDark ? "#131b2e" : "#ffffff";
  const subBg = isDark ? "#0b0f19" : "#f1f5f9";
  const borderColor = isDark ? "rgba(255, 255, 255, 0.08)" : "#e2e8f0";
  const textColor = isDark ? "#f1f5f9" : "#0f172a";
  const mutedText = isDark ? "#94a3b8" : "#64748b";

  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Fetch real breadth history from database via API
  useEffect(() => {
    const backendBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8008";
    setLoading(true);
    fetch(`${backendBase}/api/market/breadth-history?limit=35`)
      .then(res => res.json())
      .then(resData => {
        if (resData.status === "success" && resData.history?.length > 0) {
          setHistory(resData.history);
        }
      })
      .catch(err => console.error("Error loading market breadth history:", err))
      .finally(() => setLoading(false));
  }, []);

  // Merge with real-time EOD today data if warrants contains the latest session updates
  const chartData = useMemo(() => {
    if (history.length === 0) {
      // Fallback Seeded ratios if DB history is completely empty (safeguard)
      const dates = [
        "15/07/2026", "16/07/2026", "17/07/2026", "20/07/2026", "21/07/2026",
        "22/07/2026", "23/07/2026", "24/07/2026", "27/07/2026", "28/07/2026",
        "29/07/2026", "30/07/2026", "31/07/2026", "03/08/2026", "04/08/2026",
        "05/08/2026", "06/08/2026", "07/08/2026", "10/08/2026", "11/08/2026", "12/08/2026"
      ];
      const mockRatios = [
        { up: 18, flat: 15, down: 67, up_count: 22, flat_count: 18, down_count: 80 },
        { up: 52, flat: 18, down: 30, up_count: 62, flat_count: 22, down_count: 36 },
        { up: 33, flat: 17, down: 50, up_count: 40, flat_count: 20, down_count: 60 },
        { up: 8,  flat: 12, down: 80, up_count: 10, flat_count: 14, down_count: 96 },
        { up: 35, flat: 20, down: 45, up_count: 42, flat_count: 24, down_count: 54 },
        { up: 15, flat: 15, down: 70, up_count: 18, flat_count: 18, down_count: 84 },
        { up: 40, flat: 25, down: 35, up_count: 48, flat_count: 30, down_count: 42 },
        { up: 22, flat: 18, down: 60, up_count: 26, flat_count: 22, down_count: 72 },
        { up: 21, flat: 21, down: 58, up_count: 25, flat_count: 25, down_count: 70 },
        { up: 38, flat: 15, down: 47, up_count: 46, flat_count: 18, down_count: 56 },
        { up: 55, flat: 12, down: 33, up_count: 66, flat_count: 14, down_count: 40 },
        { up: 66, flat: 14, down: 20, up_count: 79, flat_count: 17, down_count: 24 },
        { up: 14, flat: 16, down: 70, up_count: 17, flat_count: 19, down_count: 84 },
        { up: 72, flat: 13, down: 15, up_count: 86, flat_count: 16, down_count: 18 },
        { up: 42, flat: 18, down: 40, up_count: 50, flat_count: 22, down_count: 48 },
        { up: 28, flat: 17, down: 55, up_count: 34, flat_count: 20, down_count: 66 },
        { up: 20, flat: 18, down: 62, up_count: 24, flat_count: 22, down_count: 74 },
        { up: 43, flat: 17, down: 40, up_count: 52, flat_count: 20, down_count: 48 },
        { up: 56, flat: 14, down: 30, up_count: 67, flat_count: 17, down_count: 36 },
        { up: 30, flat: 18, down: 52, up_count: 36, flat_count: 22, down_count: 62 },
        { up: 36, flat: 14, down: 50, up_count: 43, flat_count: 17, down_count: 60 }
      ];
      return dates.map((date, index) => {
        const ratio = mockRatios[index];
        return {
          date,
          up: ratio.up,
          flat: ratio.flat,
          down: ratio.down,
          up_count: ratio.up_count,
          flat_count: ratio.flat_count,
          down_count: ratio.down_count
        };
      });
    }

    const dataList = [...history];
    if (warrants.length > 0) {
      const up = warrants.filter(w => (w.price_change_pct ?? w.change_pct ?? w.pct_change ?? 0) > 0).length;
      const down = warrants.filter(w => (w.price_change_pct ?? w.change_pct ?? w.pct_change ?? 0) < 0).length;
      const flat = Math.max(0, warrants.length - up - down);
      const total = up + down + flat || 1;

      const upPct = Math.round((up / total) * 100);
      const downPct = Math.round((down / total) * 100);
      const flatPct = 100 - upPct - downPct;

      const today = new Date();
      const dd = String(today.getDate()).padStart(2, '0');
      const mm = String(today.getMonth() + 1).padStart(2, '0');
      const yyyy = today.getFullYear();
      const todayFormatted = `${dd}/${mm}/${yyyy}`;

      const lastIdx = dataList.findIndex(h => h.date === todayFormatted);
      if (lastIdx !== -1) {
        dataList[lastIdx] = {
          date: todayFormatted,
          up: upPct,
          down: downPct,
          flat: flatPct,
          up_count: up,
          down_count: down,
          flat_count: flat
        };
      } else {
        dataList.push({
          date: todayFormatted,
          up: upPct,
          down: downPct,
          flat: flatPct,
          up_count: up,
          down_count: down,
          flat_count: flat
        });
        if (dataList.length > 21) {
          dataList.shift();
        }
      }
    }

    return dataList;
  }, [history, warrants]);

  // Width and height constants for the SVG viewport
  const viewWidth = 720;
  const viewHeight = 350;
  const paddingRight = 45; 
  const paddingLeft = 10;
  const paddingTop = 10;
  const paddingBottom = 75; 

  const chartAreaWidth = viewWidth - paddingLeft - paddingRight;
  const chartAreaHeight = viewHeight - paddingTop - paddingBottom;

  // Thick bars with narrow spacing to match the user's screenshot exactly
  const barWidth = Math.max(12, Math.floor((chartAreaWidth / chartData.length) * 0.70));
  const spacing = (chartAreaWidth - barWidth * chartData.length) / (chartData.length - 1 || 1);

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltipPos({
      x: e.clientX - rect.left + 15,
      y: e.clientY - rect.top - 70
    });
  };

  return (
    <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem", position: "relative" }}>
      {/* Centered clean title exactly matching the screenshot */}
      <div style={{ textAlign: "center" }}>
        <h4 style={{ fontSize: "1.1rem", fontWeight: "700", margin: 0, color: isDark ? "#38bdf8" : "#1e3a8a" }}>
          {isEnglish ? "Market Breadth in the last 35 sessions. Unit: Percent" : "Độ rộng thị trường trong 35 phiên gần nhất. Đvt: Phần trăm"}
        </h4>
      </div>

      <div 
        style={{ position: "relative", width: "100%", height: "350px" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredIdx(null)}
      >
        {loading && history.length === 0 ? (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%", color: mutedText, fontSize: "0.82rem" }}>
            {isEnglish ? "Loading Breadth Data..." : "Đang tải dữ liệu độ rộng..."}
          </div>
        ) : (
          <svg viewBox={`0 0 ${viewWidth} ${viewHeight}`} width="100%" height="100%">
            {/* Grid lines for 10%, 20%, ..., 100% */}
            {[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map(pct => {
              const y = paddingTop + chartAreaHeight * (1 - pct / 100);
              return (
                <g key={pct}>
                  <line
                    x1={paddingLeft}
                    y1={y}
                    x2={paddingLeft + chartAreaWidth}
                    y2={y}
                    stroke={isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.03)"}
                    strokeWidth="1"
                  />
                  <text
                    x={paddingLeft + chartAreaWidth + 10}
                    y={y + 3}
                    fill={isDark ? "#94a3b8" : "#1e293b"}
                    fontSize="10"
                    fontWeight="700"
                    textAnchor="start"
                  >
                    {pct}%
                  </text>
                </g>
              );
            })}

            {/* Render the stacked bars */}
            {chartData.map((d, index) => {
              const x = paddingLeft + index * (barWidth + spacing);
              
              const upHeight = chartAreaHeight * (d.up / 100);
              const downHeight = chartAreaHeight * (d.down / 100);
              const flatHeight = chartAreaHeight * (d.flat / 100);

              const upY = paddingTop + chartAreaHeight - upHeight;
              const downY = upY - downHeight;
              const flatY = downY - flatHeight;

              const isHovered = hoveredIdx === index;

              return (
                <g key={d.date + index}>
                  {/* Up Segment (Green) */}
                  {d.up > 0 && (
                    <rect
                      x={x}
                      y={upY}
                      width={barWidth}
                      height={upHeight}
                      fill={isHovered ? "#16a34a" : "#139043"}
                      style={{ transition: "fill 0.15s ease" }}
                    />
                  )}

                  {/* Down Segment (Red) */}
                  {d.down > 0 && (
                    <rect
                      x={x}
                      y={downY}
                      width={barWidth}
                      height={downHeight}
                      fill={isHovered ? "#ef4444" : "#e11d48"}
                      style={{ transition: "fill 0.15s ease" }}
                    />
                  )}

                  {/* Flat Segment (Yellow) */}
                  {d.flat > 0 && (
                    <rect
                      x={x}
                      y={flatY}
                      width={barWidth}
                      height={flatHeight}
                      fill={isHovered ? "#fde047" : "#facc15"}
                      style={{ transition: "fill 0.15s ease" }}
                    />
                  )}

                  {/* Invisible broad mouse hover catcher rect over the full column height */}
                  <rect
                    x={x - spacing/2}
                    y={paddingTop}
                    width={barWidth + spacing}
                    height={chartAreaHeight}
                    fill="transparent"
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() => setHoveredIdx(index)}
                  />

                  {/* Date Label rotated */}
                  <text
                    x={x + barWidth / 2}
                    y={paddingTop + chartAreaHeight + 15}
                    fill={isHovered ? "#3b82f6" : textColor}
                    fontSize="9.5"
                    fontWeight="800"
                    textAnchor="end"
                    transform={`rotate(-45, ${x + barWidth / 2}, ${paddingTop + chartAreaHeight + 15})`}
                  >
                    {d.date}
                  </text>
                </g>
              );
            })}
          </svg>
        )}

        {/* Hover Tooltip card element */}
        {hoveredIdx !== null && chartData[hoveredIdx] && (
          <div
            style={{
              position: "absolute",
              left: `${tooltipPos.x}px`,
              top: `${tooltipPos.y}px`,
              background: "rgba(11, 15, 25, 0.95)",
              border: "1px solid rgba(255, 255, 255, 0.15)",
              borderRadius: "0.4rem",
              padding: "0.5rem 0.75rem",
              color: "#fff",
              fontSize: "0.75rem",
              pointerEvents: "none",
              zIndex: 10,
              boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
              display: "flex",
              flexDirection: "column",
              gap: "0.2rem",
              minWidth: "160px"
            }}
          >
            <div style={{ fontWeight: "900", borderBottom: "1px solid rgba(255,255,255,0.15)", paddingBottom: "0.2rem", color: "#3b82f6" }}>
              {chartData[hoveredIdx].date}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "#10b981", fontWeight: "700" }}>
              <span>{isEnglish ? "Up:" : "Tăng:"}</span>
              <span>{chartData[hoveredIdx].up_count !== undefined ? `${chartData[hoveredIdx].up_count} mã` : ""} ({chartData[hoveredIdx].up}%)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "#ef4444", fontWeight: "700" }}>
              <span>{isEnglish ? "Down:" : "Giảm:"}</span>
              <span>{chartData[hoveredIdx].down_count !== undefined ? `${chartData[hoveredIdx].down_count} mã` : ""} ({chartData[hoveredIdx].down}%)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", color: "#f59e0b", fontWeight: "700" }}>
              <span>{isEnglish ? "Flat:" : "Đứng giá:"}</span>
              <span>{chartData[hoveredIdx].flat_count !== undefined ? `${chartData[hoveredIdx].flat_count} mã` : ""} ({chartData[hoveredIdx].flat}%)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
