import React, { useEffect, useState, useMemo, useCallback } from "react";
import { Search, RotateCcw, Star, TrendingUp, TrendingDown, ChevronUp, ChevronDown, RefreshCw, Loader2, Award, Flame } from "lucide-react";
import { getUnderlyingMarket, placeOrder } from "../../api.js";
import { useData } from "../../app/DataContext.jsx";
import { useToast } from "../../components/ui/toast.jsx";
import { formatNumber } from "../../lib/formatters.js";
import { useThemeTokens } from "../../app/useThemeTokens.js";

const PAGE_SIZE = 50;

function SignalBadge({ signal }) {
  const raw = (signal || "").toUpperCase();
  let bg, color, label;
  if (raw.includes("BUY") || raw === "ĐỊNH GIÁ THẤP" || raw === "UNDERVALUED") {
    bg = "rgba(16,185,129,0.15)"; color = "#10b981"; label = "MUA";
  } else if (raw.includes("SKIP") || raw.includes("RỦI RO") || raw === "DEEP OTM") {
    bg = "rgba(239,68,68,0.15)"; color = "#ef4444"; label = "Rủi ro cao";
  } else {
    bg = "rgba(245,158,11,0.15)"; color = "#f59e0b"; label = "Theo dõi";
  }
  return (
    <span style={{ background: bg, color, border: `1px solid ${color}40`, padding: "0.18rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.7rem", fontWeight: "800", whiteSpace: "nowrap" }}>
      {label}
    </span>
  );
}

function VolumeTurnoverChart({ data, cardBg, textColor, borderColor, mutedText, isEnglish }) {
  if (!data || data.length === 0) return <div style={{ height: "180px", display: "flex", alignItems: "center", justifyContent: "center", color: mutedText, fontSize: "0.78rem" }}>{isEnglish ? "No historical data" : "Không có dữ liệu lịch sử"}</div>;

  const [hoveredIdx, setHoveredIdx] = React.useState(null);

  const width = 520;
  const height = 190;
  const paddingLeft = 44;
  const paddingRight = 52;
  const paddingTop = 30;
  const paddingBottom = 28;

  const innerPadding = 15;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const volumes = data.map(d => d.volume);
  const turnovers = data.map(d => d.turnover);
  const maxVol = Math.max(...volumes, 1) * 1.15;
  const maxTurn = Math.max(...turnovers, 1) * 1.15;

  const fmtVol = v => v >= 1e6 ? (v/1e6).toFixed(1)+"tr" : (v/1e3).toFixed(0)+"k";
  const fmtTurn = v => v >= 1e12 ? (v/1e12).toFixed(1)+"nghìn tỷ" : v >= 1e9 ? (v/1e9).toFixed(1)+"tỷ" : (v/1e6).toFixed(0)+"tr";

  const points = data.map((d, idx) => {
    const x = paddingLeft + innerPadding + (idx / (data.length - 1)) * (chartWidth - 2 * innerPadding);
    const yVol = height - paddingBottom - (d.volume / maxVol) * chartHeight;
    const yTurn = height - paddingBottom - (d.turnover / maxTurn) * chartHeight;
    return { x, yVol, yTurn, date: d.date, vol: d.volume, turn: d.turnover };
  });

  const linePath = points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x} ${p.yTurn}`).join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto", overflow: "visible" }}>
      {/* Unit Headers */}
      <text x={paddingLeft} y={14} fill={mutedText} fontSize="8" fontWeight="700" textAnchor="start">
        {isEnglish ? "(Million CW)" : "(Triệu CQ)"}
      </text>
      <text x={width - paddingRight} y={14} fill={mutedText} fontSize="8" fontWeight="700" textAnchor="end">
        {isEnglish ? "(Billion VND)" : "(Tỷ đồng)"}
      </text>

      {/* Legend */}
      <g>
        <rect x={185} y={7} width={10} height={6} fill="rgba(96, 165, 250, 0.4)" rx="1" />
        <text x={200} y={13} fill={mutedText} fontSize="8" fontWeight="700">
          {isEnglish ? "Volume" : "Khối lượng"}
        </text>

        <line x1={265} y1={10} x2={275} y2={10} stroke="#2563eb" strokeWidth="1.8" />
        <circle cx={270} cy={10} r="2.5" fill="#2563eb" />
        <text x={282} y={13} fill={mutedText} fontSize="8" fontWeight="700">
          {isEnglish ? "Turnover" : "Giá trị"}
        </text>
      </g>
      {/* Grid Lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((r, i) => {
        const y = height - paddingBottom - r * chartHeight;
        return (
          <line key={i} x1={paddingLeft} y1={y} x2={width - paddingRight} y2={y} stroke={borderColor} strokeDasharray="3 3" strokeWidth="0.5" />
        );
      })}

      {/* Vertical Grid Lines at Date Intervals */}
      {points.filter((_, i) => i % Math.ceil(data.length / 5) === 0 || i === data.length - 1).map((p, idx) => (
        <line key={`v-grid-${idx}`} x1={p.x} y1={paddingTop} x2={p.x} y2={height - paddingBottom} stroke={borderColor} strokeDasharray="3 3" strokeWidth="0.5" />
      ))}

      {/* Solid Axis Lines */}
      <line x1={paddingLeft} y1={paddingTop} x2={paddingLeft} y2={height - paddingBottom} stroke="rgba(148, 163, 184, 0.35)" strokeWidth="1" />
      <line x1={width - paddingRight} y1={paddingTop} x2={width - paddingRight} y2={height - paddingBottom} stroke="rgba(148, 163, 184, 0.35)" strokeWidth="1" />
      <line x1={paddingLeft} y1={height - paddingBottom} x2={width - paddingRight} y2={height - paddingBottom} stroke="rgba(148, 163, 184, 0.35)" strokeWidth="1" />

      {/* Bars (Volume) */}
      {points.map((p, idx) => {
        const barWidth = Math.max(3, ((chartWidth - 2 * innerPadding) / data.length) * 0.55);
        return (
          <rect
            key={idx}
            x={p.x - barWidth / 2}
            y={p.yVol}
            width={barWidth}
            height={height - paddingBottom - p.yVol}
            fill={hoveredIdx === idx ? "rgba(96, 165, 250, 0.5)" : "rgba(96, 165, 250, 0.3)"}
            rx="1"
          />
        );
      })}

      {/* Line (Turnover) */}
      <path d={linePath} fill="none" stroke="#2563eb" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />

      {/* Interactive Dots */}
      {points.map((p, idx) => (
        <circle 
          key={idx} 
          cx={p.x} 
          cy={p.yTurn} 
          r={hoveredIdx === idx ? "4" : "2.5"} 
          fill={hoveredIdx === idx ? "#3b82f6" : "#2563eb"} 
          stroke={cardBg} 
          strokeWidth="1" 
        />
      ))}

      {/* Invisible hover zones */}
      {points.map((p, idx) => {
        const prevX = idx > 0 ? points[idx - 1].x : paddingLeft;
        const nextX = idx < points.length - 1 ? points[idx + 1].x : width - paddingRight;
        const xStart = (prevX + p.x) / 2;
        const xEnd = (nextX + p.x) / 2;
        return (
          <rect
            key={`hover-${idx}`}
            x={xStart}
            y={paddingTop}
            width={xEnd - xStart}
            height={chartHeight}
            fill="transparent"
            style={{ cursor: "crosshair" }}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          />
        );
      })}

      {/* Tooltip Overlay */}
      {hoveredIdx !== null && points[hoveredIdx] && (
        <g pointerEvents="none">
          {/* Vertical tracker line */}
          <line 
            x1={points[hoveredIdx].x} 
            y1={paddingTop} 
            x2={points[hoveredIdx].x} 
            y2={height - paddingBottom} 
            stroke="rgba(255, 255, 255, 0.25)" 
            strokeWidth="0.8" 
            strokeDasharray="2 2" 
          />
          {/* Tooltip Card */}
          <rect
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 160 : points[hoveredIdx].x + 10}
            y={Math.max(paddingTop, Math.min(points[hoveredIdx].yVol, points[hoveredIdx].yTurn) - 60)}
            width="148"
            height="62"
            fill="#0b0f19"
            stroke="#2563eb"
            strokeWidth="1"
            rx="5"
            opacity="0.97"
          />
          <text
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 150 : points[hoveredIdx].x + 18}
            y={Math.max(paddingTop, Math.min(points[hoveredIdx].yVol, points[hoveredIdx].yTurn) - 60) + 16}
            fill="#94a3b8"
            fontSize="9"
            fontWeight="700"
          >
            {isEnglish ? "Date: " : "Ngày: "}{points[hoveredIdx].date}
          </text>
          <text
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 150 : points[hoveredIdx].x + 18}
            y={Math.max(paddingTop, Math.min(points[hoveredIdx].yVol, points[hoveredIdx].yTurn) - 60) + 34}
            fill="#60a5fa"
            fontSize="9"
            fontWeight="800"
          >
            {isEnglish ? "Vol: " : "KL: "}{fmtVol(points[hoveredIdx].vol)} CQ
          </text>
          <text
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 150 : points[hoveredIdx].x + 18}
            y={Math.max(paddingTop, Math.min(points[hoveredIdx].yVol, points[hoveredIdx].yTurn) - 60) + 52}
            fill="#34d399"
            fontSize="9"
            fontWeight="800"
          >
            {isEnglish ? "Val: " : "GT: "}{fmtTurn(points[hoveredIdx].turn)}
          </text>
        </g>
      )}

      {/* Bottom Axis Dates */}
      {points.filter((_, i) => i % Math.ceil(data.length / 5) === 0 || i === data.length - 1).map((p, idx) => {
        const dStr = p.date ? p.date.substring(5, 10).replace("-", "/") : "";
        return (
          <text key={idx} x={p.x} y={height - 8} fill={mutedText} fontSize="8" textAnchor="middle" fontWeight="600">
            {dStr}
          </text>
        );
      })}

      {/* Left Axis Labels (Volume) */}
      {[0, 0.25, 0.5, 0.75, 1].map((r, i) => {
        const y = height - paddingBottom - r * chartHeight;
        return (
          <text key={`l-label-${i}`} x={2} y={y + 3} fill="#60a5fa" fontSize="8" fontWeight="800">
            {fmtVol(r * maxVol)}
          </text>
        );
      })}

      {/* Right Axis Labels (Turnover) */}
      {[0, 0.25, 0.5, 0.75, 1].map((r, i) => {
        const y = height - paddingBottom - r * chartHeight;
        return (
          <text key={`r-label-${i}`} x={width - paddingRight + 4} y={y + 3} fill="#2563eb" fontSize="8" fontWeight="800" textAnchor="start">
            {fmtTurn(r * maxTurn)}
          </text>
        );
      })}
    </svg>
  );
}

function ForeignFlowsChart({ data, cardBg, textColor, borderColor, mutedText, isEnglish }) {
  if (!data || data.length === 0) return <div style={{ height: "180px", display: "flex", alignItems: "center", justifyContent: "center", color: mutedText, fontSize: "0.78rem" }}>{isEnglish ? "No historical data" : "Không có dữ liệu lịch sử"}</div>;

  const [hoveredIdx, setHoveredIdx] = React.useState(null);

  const width = 520;
  const height = 190;
  const paddingLeft = 44;
  const paddingRight = 52;
  const paddingTop = 30;
  const paddingBottom = 28;

  const innerPadding = 15;
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const netFlows = data.map(d => d.foreign_net);
  const maxAbsNet = Math.max(...netFlows.map(Math.abs), 1) * 1.15;

  const buySells = [...data.map(d => d.foreign_buy || 0), ...data.map(d => d.foreign_sell || 0)];
  const maxBuySell = Math.max(...buySells, 1) * 1.15;

  const fmtFlow = v => {
    const abs = Math.abs(v);
    const sign = v < 0 ? "-" : "+";
    if (abs >= 1e9) return sign + (abs/1e9).toFixed(1)+"tỷ";
    return sign + (abs/1e6).toFixed(0)+"tr";
  };

  const baselineY = paddingTop + chartHeight / 2;

  const points = data.map((d, idx) => {
    const x = paddingLeft + innerPadding + (idx / (data.length - 1)) * (chartWidth - 2 * innerPadding);
    const yBuy = baselineY - ((d.foreign_buy || 0) / maxBuySell) * (chartHeight / 2);
    const ySell = baselineY + ((d.foreign_sell || 0) / maxBuySell) * (chartHeight / 2);
    const yNet = baselineY - (d.foreign_net / maxAbsNet) * (chartHeight / 2);
    return { x, yBuy, ySell, yNet, buy: d.foreign_buy || 0, sell: d.foreign_sell || 0, net: d.foreign_net, date: d.date };
  });

  const netLinePath = points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p.x} ${p.yNet}`).join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto", overflow: "visible" }}>
      {/* Unit Headers */}
      <text x={paddingLeft} y={14} fill={mutedText} fontSize="8" fontWeight="700" textAnchor="start">
        {isEnglish ? "(Buy/Sell VND B)" : "(Mua/Bán tỷ đồng)"}
      </text>
      <text x={width - paddingRight} y={14} fill={mutedText} fontSize="8" fontWeight="700" textAnchor="end">
        {isEnglish ? "(Net Flow VND B)" : "(Ròng tỷ đồng)"}
      </text>

      {/* Legend */}
      <g>
        <rect x={125} y={7} width={9} height={6} fill="rgba(148, 163, 184, 0.4)" rx="1" />
        <text x={138} y={13} fill={mutedText} fontSize="8" fontWeight="700">
          {isEnglish ? "Buy" : "Giá trị mua"}
        </text>

        <rect x={195} y={7} width={9} height={6} fill="rgba(71, 85, 105, 0.7)" rx="1" />
        <text x={208} y={13} fill={mutedText} fontSize="8" fontWeight="700">
          {isEnglish ? "Sell" : "Giá trị bán"}
        </text>

        <line x1={265} y1={10} x2={275} y2={10} stroke="#3b82f6" strokeWidth="1.8" />
        <circle cx={270} cy={10} r="2.5" fill="#3b82f6" />
        <text x={282} y={13} fill={mutedText} fontSize="8" fontWeight="700">
          {isEnglish ? "Net Flow" : "Giá trị ròng"}
        </text>
      </g>

      {/* Zero Line */}
      <line x1={paddingLeft} y1={baselineY} x2={width - paddingRight} y2={baselineY} stroke={mutedText} strokeWidth="0.8" strokeDasharray="2 2" />

      {/* Grid Lines */}
      {[-1, -0.5, 0.5, 1].map((r, i) => {
        const y = baselineY - r * (chartHeight / 2);
        return (
          <line key={i} x1={paddingLeft} y1={y} x2={width - paddingRight} y2={y} stroke={borderColor} strokeDasharray="3 3" strokeWidth="0.5" />
        );
      })}

      {/* Vertical Grid Lines at Date Intervals */}
      {points.filter((_, i) => i % Math.ceil(data.length / 5) === 0 || i === data.length - 1).map((p, idx) => (
        <line key={`v-grid-${idx}`} x1={p.x} y1={paddingTop} x2={p.x} y2={height - paddingBottom} stroke={borderColor} strokeDasharray="3 3" strokeWidth="0.5" />
      ))}

      {/* Solid Axis Lines */}
      <line x1={paddingLeft} y1={paddingTop} x2={paddingLeft} y2={height - paddingBottom} stroke="rgba(148, 163, 184, 0.35)" strokeWidth="1" />
      <line x1={width - paddingRight} y1={paddingTop} x2={width - paddingRight} y2={height - paddingBottom} stroke="rgba(148, 163, 184, 0.35)" strokeWidth="1" />
      <line x1={paddingLeft} y1={height - paddingBottom} x2={width - paddingRight} y2={height - paddingBottom} stroke="rgba(148, 163, 184, 0.35)" strokeWidth="1" />

      {/* Bars (Buy - Upwards) */}
      {points.map((p, idx) => {
        const barWidth = Math.max(3, ((chartWidth - 2 * innerPadding) / data.length) * 0.45);
        return (
          <rect
            key={`buy-${idx}`}
            x={p.x - barWidth / 2}
            y={p.yBuy}
            width={barWidth}
            height={baselineY - p.yBuy}
            fill={hoveredIdx === idx ? "rgba(148, 163, 184, 0.65)" : "rgba(148, 163, 184, 0.4)"}
            rx="1"
          />
        );
      })}

      {/* Bars (Sell - Downwards) */}
      {points.map((p, idx) => {
        const barWidth = Math.max(3, ((chartWidth - 2 * innerPadding) / data.length) * 0.45);
        return (
          <rect
            key={`sell-${idx}`}
            x={p.x - barWidth / 2}
            y={baselineY}
            width={barWidth}
            height={p.ySell - baselineY}
            fill={hoveredIdx === idx ? "rgba(71, 85, 105, 0.85)" : "rgba(71, 85, 105, 0.6)"}
            rx="1"
          />
        );
      })}

      {/* Net Flow Line */}
      <path d={netLinePath} fill="none" stroke="#3b82f6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />

      {/* Net Flow Dots */}
      {points.map((p, idx) => (
        <circle 
          key={`dot-${idx}`} 
          cx={p.x} 
          cy={p.yNet} 
          r={hoveredIdx === idx ? "4" : "2.5"} 
          fill={hoveredIdx === idx ? "#60a5fa" : "#3b82f6"} 
          stroke={cardBg} 
          strokeWidth="1" 
        />
      ))}

      {/* Invisible hover zones */}
      {points.map((p, idx) => {
        const prevX = idx > 0 ? points[idx - 1].x : paddingLeft;
        const nextX = idx < points.length - 1 ? points[idx + 1].x : width - paddingRight;
        const xStart = (prevX + p.x) / 2;
        const xEnd = (nextX + p.x) / 2;
        return (
          <rect
            key={`hover-${idx}`}
            x={xStart}
            y={paddingTop}
            width={xEnd - xStart}
            height={chartHeight}
            fill="transparent"
            style={{ cursor: "crosshair" }}
            onMouseEnter={() => setHoveredIdx(idx)}
            onMouseLeave={() => setHoveredIdx(null)}
          />
        );
      })}

      {/* Tooltip Overlay */}
      {hoveredIdx !== null && points[hoveredIdx] && (
        <g pointerEvents="none">
          {/* Vertical tracker line */}
          <line 
            x1={points[hoveredIdx].x} 
            y1={paddingTop} 
            x2={points[hoveredIdx].x} 
            y2={height - paddingBottom} 
            stroke="rgba(255, 255, 255, 0.25)" 
            strokeWidth="0.8" 
            strokeDasharray="2 2" 
          />
          {/* Tooltip Card */}
          <rect
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 160 : points[hoveredIdx].x + 10}
            y={Math.max(paddingTop, points[hoveredIdx].yNet - 70)}
            width="150"
            height="76"
            fill="#0b0f19"
            stroke="#2563eb"
            strokeWidth="1"
            rx="5"
            opacity="0.97"
          />
          <text
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 150 : points[hoveredIdx].x + 18}
            y={Math.max(paddingTop, points[hoveredIdx].yNet - 70) + 16}
            fill="#94a3b8"
            fontSize="9"
            fontWeight="700"
          >
            {isEnglish ? "Date: " : "Ngày: "}{points[hoveredIdx].date}
          </text>
          <text
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 150 : points[hoveredIdx].x + 18}
            y={Math.max(paddingTop, points[hoveredIdx].yNet - 70) + 34}
            fill="#94a3b8"
            fontSize="9"
            fontWeight="800"
          >
            {isEnglish ? "Buy: " : "Mua: "}{fmtFlow(points[hoveredIdx].buy)}
          </text>
          <text
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 150 : points[hoveredIdx].x + 18}
            y={Math.max(paddingTop, points[hoveredIdx].yNet - 70) + 52}
            fill="#cbd5e1"
            fontSize="9"
            fontWeight="800"
          >
            {isEnglish ? "Sell: " : "Bán: "}{fmtFlow(-points[hoveredIdx].sell)}
          </text>
          <text
            x={points[hoveredIdx].x + 10 + 150 > width - paddingRight ? points[hoveredIdx].x - 150 : points[hoveredIdx].x + 18}
            y={Math.max(paddingTop, points[hoveredIdx].yNet - 70) + 70}
            fill={points[hoveredIdx].net >= 0 ? "#34d399" : "#f87171"}
            fontSize="9"
            fontWeight="800"
          >
            {isEnglish ? "Net: " : "Ròng: "}{fmtFlow(points[hoveredIdx].net)}
          </text>
        </g>
      )}

      {/* Bottom Axis Dates */}
      {points.filter((_, i) => i % Math.ceil(data.length / 5) === 0 || i === data.length - 1).map((p, idx) => {
        const dStr = p.date ? p.date.substring(5, 10).replace("-", "/") : "";
        return (
          <text key={idx} x={p.x} y={height - 8} fill={mutedText} fontSize="8" textAnchor="middle" fontWeight="600">
            {dStr}
          </text>
        );
      })}

      {/* Left Axis Labels (Buy/Sell) */}
      {[-1, -0.5, 0, 0.5, 1].map((r, i) => {
        const y = baselineY - r * (chartHeight / 2);
        const val = r * maxBuySell;
        return (
          <text key={`l-label-${i}`} x={2} y={y + 3} fill="#94a3b8" fontSize="8" fontWeight="800">
            {fmtFlow(val)}
          </text>
        );
      })}

      {/* Right Axis Labels (Net Flow) */}
      {[-1, -0.5, 0, 0.5, 1].map((r, i) => {
        const y = baselineY - r * (chartHeight / 2);
        const val = r * maxAbsNet;
        const color = val > 0 ? "#10b981" : val < 0 ? "#ef4444" : mutedText;
        return (
          <text key={`r-label-${i}`} x={width - paddingRight + 4} y={y + 3} fill={color} fontSize="8" fontWeight="800" textAnchor="start">
            {fmtFlow(val)}
          </text>
        );
      })}
    </svg>
  );
}

function GScoreBar({ score }) {
  const val = Number(score);
  const isInvalid = score === null || score === undefined || Number.isNaN(val) || !Number.isFinite(val);
  const displayVal = isInvalid ? 25 : Math.min(100, Math.max(0, val));
  const pct = Math.min(100, Math.max(0, displayVal));
  const color = isInvalid ? "#ef4444" : (pct >= 70 ? "#10b981" : pct >= 50 ? "#60a5fa" : pct >= 30 ? "#f59e0b" : "#ef4444");
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
      <div style={{ flex: 1, height: "4px", background: "#1e293b", borderRadius: "2px", minWidth: "40px" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: "2px", transition: "width 0.3s" }} />
      </div>
      <span style={{ fontSize: "0.78rem", fontWeight: "800", color, minWidth: "28px" }}>
        {isInvalid ? "N/A" : Math.round(pct)}
      </span>
    </div>
  );
}

function SortHeader({ label, field, sortField, sortDir, onSort }) {
  const active = sortField === field;
  return (
    <th
      onClick={() => onSort(field)}
      style={{
        padding: "0.6rem 0.5rem",
        color: active ? "#3b82f6" : "inherit",
        cursor: "pointer",
        userSelect: "none",
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ display: "inline-flex", alignItems: "center", gap: "0.2rem" }}>
        {label}
        {active ? (sortDir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />) : <span style={{ opacity: 0.3 }}><ChevronDown size={12} /></span>}
      </span>
    </th>
  );
}

export function OpportunitiesPage({ setPage, setSelectedSymbol, language = "vi", preferences = {}, strategy = "balanced", setStrategy }) {
  const isEnglish = language === "en";
  const { addToast } = useToast();
  const { opportunitiesData, refreshDataType } = useData();

  const [activeTab, setActiveTab] = useState("nang_cao");
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  // Use data from DataContext (API returns data directly at root level)
  const data = opportunitiesData || {};

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIssuer, setSelectedIssuer] = useState("all");
  const [selectedUnderlying, setSelectedUnderlying] = useState("all");
  const [selectedMoneyness, setSelectedMoneyness] = useState("all");
  const [premiumMax, setPremiumMax] = useState(100);
  const [deltaMin, setDeltaMin] = useState(0);
  const [gearingMin, setGearingMin] = useState(0);
  const [daysMax, setDaysMax] = useState(365);
  const [gscoreMin, setGscoreMin] = useState(0);
  const [chkUndervalued, setChkUndervalued] = useState(false);
  const [chkBuyOnly, setChkBuyOnly] = useState(false);
  const [selectedIssuerTier, setSelectedIssuerTier] = useState("all");

  // Sorting
  const [sortField, setSortField] = useState("gscore");
  const [sortDir, setSortDir] = useState("desc");

  // Flows data for advanced tab
  const [flowData, setFlowData] = useState(null);
  const [flowLoading, setFlowLoading] = useState(false);
  const [marketHistory, setMarketHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Fetch market history on mount + every 5 minutes (auto-refresh)
  useEffect(() => {
    const backendBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8008";

    const fetchHistory = () => {
      setHistoryLoading(true);
      fetch(`${backendBase}/api/warrants/market-history`)
        .then(res => res.json())
        .then(resData => {
          if (resData.status === "success") setMarketHistory(resData.history);
        })
        .catch(err => console.error("Error loading market history:", err))
        .finally(() => setHistoryLoading(false));
    };

    fetchHistory();
    const interval = setInterval(fetchHistory, 5 * 60 * 1000); // refresh every 5 min
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeTab === "nang_cao") {
      setFlowLoading(true);
      const backendBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8008";
      fetch(`${backendBase}/api/warrants/flows`)
        .then(res => res.json())
        .then(resData => {
          if (resData.status === "success") setFlowData(resData);
        })
        .catch(err => console.error("Error loading flows:", err))
        .finally(() => setFlowLoading(false));
    }
  }, [activeTab]);

  // Underlying stocks state
  const [stocks, setStocks] = useState([]);
  const [stocksLoading, setStocksLoading] = useState(false);
  const [stockSearch, setStockSearch] = useState("");
  const [selectedIndustry, setSelectedIndustry] = useState("all");

  // Fetch stocks when changing tab
  const fetchStocksData = useCallback(async () => {
    try {
      setStocksLoading(true);
      const res = await getUnderlyingMarket();
      if (res && res.stocks) setStocks(res.stocks);
    } catch (err) {
      console.error("Failed to fetch stocks market overview:", err);
    } finally {
      setStocksLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "co_phieu") {
      fetchStocksData();
    }
  }, [activeTab, fetchStocksData]);

  const INDUSTRY_TAGS = [
    { label: "Tất cả", value: "all" },
    { label: "Ngân hàng", value: "ngân hàng" },
    { label: "Bất động sản", value: "bất động sản" },
    { label: "Thép", value: "thép" },
    { label: "Chứng khoán", value: "chứng khoán" },
    { label: "Công nghệ", value: "công nghệ" },
  ];

const ISSUER_NAMES = {
    "MSVN": "MSVN",
    "VPBS": "VPS",
    "HSC": "HSC",
    "PHS": "PHS",
    "SSV": "SSI",
    "LPBS": "LPBS",
    "KBSV": "KBSV",
    "KAFI": "KAFI",
    "VNDS": "VNDS",
    "ACBS": "ACBS",
    "KIS": "KIS",
    "TCBS": "TCBS",
    "MBS": "MBS",
    "SSI": "SSI",
  };

  const getIssuerTier = (issuer) => {
    const is = String(issuer || "").toUpperCase();
    if (["SSI", "HSC", "VNDS", "VND", "VCSC"].includes(is)) return "1";
    if (["VPBS", "VPS", "PHS", "LPBS", "KAFI", "SSV", "MSVN"].includes(is)) return "3";
    return "2";
  };

  function loadData(forceRefresh = false) {
    setLoading(true);
    setCurrentPage(1);
    refreshDataType("opportunities", forceRefresh);
    setLoading(false);
  }

  function loadStocks(forceRefresh = false) {
    setStocksLoading(true);
    getUnderlyingMarket({ forceRefresh })
      .then(res => setStocks(res?.underlyings || res?.stocks || []))
      .catch(() => {})
      .finally(() => setStocksLoading(false));
  }

  useEffect(() => { loadData(false); }, [strategy]);
  useEffect(() => { loadStocks(false); }, []);


  function handleReset() {
    setPremiumMax(100); setDeltaMin(0); setGearingMin(0); setDaysMax(365); setGscoreMin(0);
    setChkUndervalued(false); setChkBuyOnly(false);
    setSelectedIssuer("all"); setSelectedUnderlying("all"); setSelectedMoneyness("all");
    setSelectedIssuerTier("all");
    setSearchQuery("");
  }

  async function handleBuyOrder(row) {
    try {
      await placeOrder({ symbol: row.symbol, side: "BUY", quantity: 1000, price: row.price, reason: "Scanner Signal" });
    } catch (_) {}
    addToast(`Đã đặt lệnh MUA 1,000 ${row.symbol}!`, "success");
    setPage("portfolio");
  }

  function handleAddToWatchlist(symbol) {
    const list = JSON.parse(localStorage.getItem("finvista-watchlist") || "[]");
    if (!list.includes(symbol)) {
      list.push(symbol);
      localStorage.setItem("finvista-watchlist", JSON.stringify(list));
      addToast(`Đã thêm ${symbol} vào Watchlist!`, "success");
    } else {
      addToast(`${symbol} đã có trong Watchlist!`, "info");
    }
  }

  function openDetail(symbol) {
    if (!symbol) return;
    setSelectedSymbol(symbol.trim().toUpperCase());
    setPage("detail");
  }

  function handleSort(field) {
    if (sortField === field) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("desc"); }
  }

  // Map API rows with dynamic Strategy G-Score weighting
  const rawRows = useMemo(() => {
    const recs = data?.recommendations || [];
    if (!recs || recs.length === 0) return [];
    return recs.map(r => {
      const d = Number(r.delta || 0);
      const mState = r.moneyness_status || (d >= 0.6 ? "ITM" : d >= 0.4 ? "ATM" : "OTM");

      const rawGear = Number(r.effective_gearing ?? r.gearing);
      const gearVal = Number.isFinite(rawGear) && rawGear > 0 ? rawGear : 0;
      const gearDisplay = gearVal > 0 ? `${Math.round(gearVal * 10) / 10}x` : "-";

      const bkPrice = Number(r.break_even_price || 0) || Math.round((Number(r.market_price || r.price || 0)) * 1.08);
      const baseScore = Number(r.composite_g_score ?? r.score ?? 35.0);
      const prem = Math.round((Number(r.premium_pct || 0)) * 10) / 10;
      const dtmDays = Number(r.days_to_maturity || 0);
      const priceChg = Number(r.price_change_pct || 0);

      let calcScore = Number.isNaN(baseScore) ? 35.0 : baseScore;
      if (strategy === "delta_adaptive") {
        // Delta-Adaptive Exit: High weight on optimal Delta range (0.45 - 0.75), Theta safety & trend momentum
        const deltaOptimal = (d >= 0.45 && d <= 0.75) ? 30 : (d > 0.75 ? 20 : 10);
        const thetaSafety = dtmDays > 30 ? 25 : (dtmDays > 15 ? 10 : -20);
        calcScore = (calcScore * 0.35) + deltaOptimal + thetaSafety + (priceChg > 0 ? 10 : 0);
      } else if (strategy === "aggressive") {
        // Aggressive: Higher weight on leverage (gearing), Delta & momentum upside
        calcScore = (calcScore * 0.4) + (d * 35) + (Math.min(gearVal, 12) * 2.5) + (priceChg > 0 ? 8 : -5);
      } else if (strategy === "safe" || strategy === "defensive") {
        // Defensive: Higher weight on safety (low premium, longer DTM, ITM stability)
        calcScore = (calcScore * 0.4) + (prem < 15 ? 25 : prem < 25 ? 15 : 5) + (dtmDays > 60 ? 25 : 10) + (d >= 0.5 ? 15 : 5);
      }
      const rawGscore = Number.isNaN(calcScore) || !Number.isFinite(calcScore) ? 25.0 : calcScore;
      const finalGscore = Math.min(99, Math.max(15, Math.round(rawGscore * 10) / 10));

      return {
        symbol: r.warrant_symbol || r.symbol || "",
        underlying: r.underlying_symbol || r.underlying || "",
        issuer: r.issuer || "",
        price: r.market_price || r.price,
        premium: prem,
        delta: Math.round((d) * 100) / 100,
        gearing: gearDisplay,
        moneyness: mState,
        breakeven: bkPrice,
        iv: Math.round((Number(r.implied_volatility_pct || 0)) * 10) / 10,
        hv: Math.round((Number(r.historical_volatility_pct || 0)) * 10) / 10,
        gscore: finalGscore,
        dtm: dtmDays,
        volume: r.volume,
        changePct: priceChg,
        undMaAlign: r.und_ma_align_score !== undefined ? r.und_ma_align_score : 67.0,
        undMom: r.und_mom_score !== undefined ? r.und_mom_score : 50.0,
        signal: r.recommendation_signal || r.decision_signal || "",
        isBuy: (r.recommendation_signal || r.decision_signal || "").toUpperCase().includes("BUY"),
      };
    });
  }, [data, strategy]);

  // Top 5 Volume CWs
  const topVolume = useMemo(() => {
    return [...rawRows]
      .sort((a, b) => (b.volume || 0) - (a.volume || 0))
      .slice(0, 5);
  }, [rawRows]);

  // Top 5 Highest G-Score CWs
  const topScore = useMemo(() => {
    return [...rawRows]
      .sort((a, b) => (b.gscore || 0) - (a.gscore || 0))
      .slice(0, 5);
  }, [rawRows]);

  // Dynamic dropdown options from live data
  const underlyingOptions = useMemo(() => [...new Set(rawRows.map(r => r.underlying))].sort(), [rawRows]);
  const issuerOptions = useMemo(() => [...new Set(rawRows.map(r => r.issuer))].sort(), [rawRows]);

  // Helper to get Vietnamese issuer name
  const getIssuerName = (code) => ISSUER_NAMES[code] || code;

  // Watchlist for favorites tab
  const favList = useMemo(() => JSON.parse(localStorage.getItem("finvista-watchlist") || "[]"), []);

  // Filter
  const filteredRows = useMemo(() => {
    let rows = rawRows.filter(r => {
      if (activeTab === "yeu_thich" && !favList.includes(r.symbol)) return false;
      if (searchQuery && !r.symbol.toLowerCase().includes(searchQuery.toLowerCase()) && !r.underlying.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (selectedUnderlying !== "all" && r.underlying !== selectedUnderlying) return false;
      if (selectedIssuer !== "all" && r.issuer !== selectedIssuer) return false;
      if (selectedIssuerTier !== "all" && getIssuerTier(r.issuer) !== selectedIssuerTier) return false;
      if (selectedMoneyness !== "all" && r.moneyness !== selectedMoneyness) return false;
      if (r.premium > premiumMax) return false;
      if (r.delta < deltaMin) return false;
      if (r.gearing < gearingMin) return false;
      if (r.dtm > daysMax) return false;
      if (r.gscore < gscoreMin) return false;
      if (chkUndervalued && !r.isBuy) return false;
      if (chkBuyOnly && !r.signal.toUpperCase().includes("BUY")) return false;
      return true;
    });

    // Sort
    rows.sort((a, b) => {
      let va = a[sortField];
      let vb = b[sortField];
      
      const getPriority = (sig) => {
        const s = (sig || "").toUpperCase();
        if (s.startsWith("BUY")) return 3;
        if (s.startsWith("WATCH")) return 2;
        return 1;
      };

      if (sortField === "signal") {
        va = getPriority(a.signal);
        vb = getPriority(b.signal);
      }
      
      const isNumA = typeof va === "number" || (!isNaN(parseFloat(va)) && isFinite(va));
      const isNumB = typeof vb === "number" || (!isNaN(parseFloat(vb)) && isFinite(vb));
      
      let comp = 0;
      if (isNumA && isNumB) {
        comp = parseFloat(va) - parseFloat(vb);
      } else {
        const strA = String(va || "").toLowerCase();
        const strB = String(vb || "").toLowerCase();
        comp = strA.localeCompare(strB, "vi");
      }
      
      if (comp === 0) {
        if (sortField !== "gscore") {
          const scoreComp = b.gscore - a.gscore;
          if (scoreComp !== 0) return scoreComp;
        }
        if (sortField !== "signal") {
          const priComp = getPriority(b.signal) - getPriority(a.signal);
          if (priComp !== 0) return priComp;
        }
        return a.symbol.localeCompare(b.symbol, "vi");
      }
      
      return sortDir === "asc" ? (comp > 0 ? 1 : -1) : (comp < 0 ? 1 : -1);
    });

    return rows;
  }, [rawRows, activeTab, searchQuery, selectedUnderlying, selectedIssuer, selectedIssuerTier, selectedMoneyness, premiumMax, deltaMin, gearingMin, daysMax, gscoreMin, chkUndervalued, chkBuyOnly, sortField, sortDir, favList]);

  const displayRows = useMemo(() => {
    return filteredRows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  }, [filteredRows, currentPage]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedUnderlying, selectedIssuer, selectedIssuerTier, selectedMoneyness, premiumMax, deltaMin, gearingMin, daysMax, gscoreMin, chkUndervalued, chkBuyOnly, sortField, sortDir, strategy, activeTab]);

  const totalBuy = rawRows.filter(r => r.isBuy).length;
  const avgGscore = rawRows.length ? (rawRows.reduce((s, r) => s + r.gscore, 0) / rawRows.length).toFixed(1) : "--";

  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", color: textColor, background: bg }}>

      {/* HEADER */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.5rem", fontWeight: "900", margin: 0, letterSpacing: "0.3px", color: textColor }}>
              {isEnglish ? "CW SCANNER — WARRANT OPPORTUNITY SCANNER" : "CW SCANNER — TÌM KIẾM CƠ HỘI CHỨNG QUYỀN"}
            </h2>
            <p style={{ fontSize: "0.8rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
              Lọc định lượng thông minh theo Greeks · Delta · IV · Premium · G-Score · DB Realtime
            </p>
          </div>

          {/* Summary KPIs */}
          <div style={{ display: "flex", gap: "1rem", fontSize: "0.78rem" }}>
            <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "0.5rem 0.75rem", textAlign: "center" }}>
              <div style={{ color: mutedText }}>Tổng mã</div>
              <strong style={{ fontSize: "1.1rem", color: textColor }}>{rawRows.length}</strong>
            </div>
            <div style={{ background: subBg, border: "1px solid rgba(16,185,129,0.3)", borderRadius: "0.5rem", padding: "0.5rem 0.75rem", textAlign: "center" }}>
              <div style={{ color: mutedText }}>Tín hiệu MUA</div>
              <strong style={{ fontSize: "1.1rem", color: "#10b981" }}>{totalBuy}</strong>
            </div>
            <div style={{ background: subBg, border: "1px solid rgba(96,165,250,0.3)", borderRadius: "0.5rem", padding: "0.5rem 0.75rem", textAlign: "center" }}>
              <div style={{ color: mutedText }}>G-Score TB</div>
              <strong style={{ fontSize: "1.1rem", color: "#60a5fa" }}>{avgGscore}</strong>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", gap: "0.35rem", background: subBg, padding: "0.2rem", borderRadius: "0.4rem" }}>
            {[{ id: "co_ban", label: "Cơ bản" }, { id: "nang_cao", label: "Nâng cao" }, { id: "yeu_thich", label: "★ Yêu thích" }].map(t => (
              <button key={t.id} onClick={() => setActiveTab(t.id)} style={{ background: activeTab === t.id ? "#2563eb" : "transparent", color: activeTab === t.id ? "#fff" : textColor, border: "none", borderRadius: "0.3rem", padding: "0.35rem 1rem", fontSize: "0.8rem", fontWeight: "700", cursor: "pointer" }}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Strategy selector */}
          <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
            <span style={{ fontSize: "0.75rem", color: mutedText }}>Chiến lược:</span>
            {[{ id: "safe", label: "Phòng thủ" }, { id: "balanced", label: "Quân bình" }, { id: "aggressive", label: "Tấn công" }, { id: "delta_adaptive", label: "Delta-Adaptive Exit" }].map(s => (
              <button key={s.id} onClick={() => setStrategy(s.id)} style={{ background: strategy === s.id ? "#2563eb" : subBg, color: strategy === s.id ? "#fff" : textColor, border: "1px solid " + (strategy === s.id ? "#2563eb" : borderColor), borderRadius: "0.3rem", padding: "0.3rem 0.65rem", fontSize: "0.75rem", fontWeight: "700", cursor: "pointer" }}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* TỔNG QUAN THỊ TRƯỜNG & DÒNG TIỀN */}
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
        <div>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "900", margin: 0, color: textColor, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Award size={18} style={{ color: "#eab308" }} /> {isEnglish ? "MARKET OVERVIEW & FLOWS" : "TỔNG QUAN THỊ TRƯỜNG & DÒNG TIỀN"}
          </h3>
          <p style={{ fontSize: "0.75rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
            {isEnglish ? "Market overview of the most active covered warrants and proprietary flows" : "Bức tranh tổng quan các mã CW nổi bật và dòng tiền tự doanh, khối ngoại"}
          </p>
        </div>

        {/* Charts row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem" }}>
            <h4 style={{ fontSize: "0.82rem", fontWeight: "800", color: "#60a5fa", margin: "0 0 0.75rem 0" }}>
              {isEnglish ? "CW Volume & Turnover (Realtime EOD)" : "Khối lượng & Giá trị giao dịch CW (Realtime EOD)"}
            </h4>
            {historyLoading ? (
              <div style={{ height: "180px", display: "flex", alignItems: "center", justifyContent: "center", color: mutedText, fontSize: "0.75rem" }}>
                {isEnglish ? "Loading chart..." : "Đang tải biểu đồ..."}
              </div>
            ) : (
              <VolumeTurnoverChart data={marketHistory} cardBg={cardBg} textColor={textColor} borderColor={borderColor} mutedText={mutedText} isEnglish={isEnglish} />
            )}
          </div>
          <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem" }}>
            <h4 style={{ fontSize: "0.82rem", fontWeight: "800", color: "#eab308", margin: "0 0 0.75rem 0" }}>
              {isEnglish ? "Foreign Net Flows (Realtime EOD)" : "Giá trị mua/bán ròng khối ngoại (Realtime EOD)"}
            </h4>
            {historyLoading ? (
              <div style={{ height: "180px", display: "flex", alignItems: "center", justifyContent: "center", color: mutedText, fontSize: "0.75rem" }}>
                {isEnglish ? "Loading chart..." : "Đang tải biểu đồ..."}
              </div>
            ) : (
              <ForeignFlowsChart data={marketHistory} cardBg={cardBg} textColor={textColor} borderColor={borderColor} mutedText={mutedText} isEnglish={isEnglish} />
            )}
          </div>
        </div>

        {/* 5 tables/widgets in a unified grid layout */}
        <div style={{ 
          display: "grid", 
          gridTemplateColumns: activeTab === "nang_cao" ? "1fr 1fr 1.1fr" : "1fr 1fr", 
          gap: "1rem" 
        }}>
          {/* 1. Top Volume */}
          <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: "#60a5fa", margin: 0, display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <Flame size={15} color="#60a5fa" /> {isEnglish ? "Top Most Active CWs (Volume)" : "Top CW Thanh khoản Cao nhất"}
            </h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {topVolume.map((item, idx) => (
                <div
                  key={item.symbol + idx}
                  onClick={() => openDetail(item.symbol)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1.2fr 0.8fr 1fr 1fr",
                    alignItems: "center",
                    padding: "0.45rem 0.6rem",
                    background: cardBg,
                    borderRadius: "0.375rem",
                    border: `1px solid ${borderColor}`,
                    cursor: "pointer",
                    fontSize: "0.78rem",
                    transition: "border-color 0.15s, transform 0.1s"
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = "#2563eb";
                    e.currentTarget.style.transform = "translateY(-1px)";
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = borderColor;
                    e.currentTarget.style.transform = "none";
                  }}
                >
                  <strong style={{ color: "#60a5fa" }}>{item.symbol}</strong>
                  <span style={{ color: mutedText, fontSize: "0.72rem" }}>({item.underlying})</span>
                  <span style={{ fontWeight: "700", color: textColor, textAlign: "right", paddingRight: "0.5rem" }}>{formatNumber(item.price, 0)} đ</span>
                  <span style={{ color: item.changePct >= 0 ? "#10b981" : "#ef4444", fontWeight: "700", textAlign: "right" }}>
                    {item.changePct >= 0 ? "+" : ""}{formatNumber(item.changePct, 2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 2. Top G-Score */}
          <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: "#10b981", margin: 0, display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <TrendingUp size={15} color="#10b981" /> {isEnglish ? "Top G-Score CWs" : "Top CW G-Score Cao nhất"}
            </h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {topScore.map((item, idx) => (
                <div
                  key={item.symbol + idx}
                  onClick={() => openDetail(item.symbol)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1.2fr 1fr 1fr 0.8fr",
                    alignItems: "center",
                    padding: "0.45rem 0.6rem",
                    background: cardBg,
                    borderRadius: "0.375rem",
                    border: `1px solid ${borderColor}`,
                    cursor: "pointer",
                    fontSize: "0.78rem",
                    transition: "border-color 0.15s, transform 0.1s"
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = "#2563eb";
                    e.currentTarget.style.transform = "translateY(-1px)";
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = borderColor;
                    e.currentTarget.style.transform = "none";
                  }}
                >
                  <strong style={{ color: "#60a5fa" }}>{item.symbol}</strong>
                  <div style={{ display: "flex" }}>
                    <span style={{ background: "rgba(16,185,129,0.15)", color: "#10b981", padding: "0.1rem 0.35rem", borderRadius: "0.2rem", fontSize: "0.68rem", fontWeight: "800", display: "inline-block" }}>
                      Score: {Math.round(item.gscore)}
                    </span>
                  </div>
                  <span style={{ fontWeight: "700", color: textColor, textAlign: "right", paddingRight: "0.5rem" }}>{formatNumber(item.price, 0)} đ</span>
                  <span style={{ 
                    color: item.signal.toUpperCase().includes("BUY") ? "#10b981" : "#eab308", 
                    fontWeight: "800", 
                    fontSize: "0.7rem", 
                    textAlign: "right" 
                  }}>
                    {isEnglish ? (item.signal.toUpperCase().includes("BUY") ? "BUY" : "HOLD") : (item.signal.toUpperCase().includes("BUY") ? "MUA" : "THEO DÕI")}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 3. Foreign Flow by Underlying (Spans both rows on right side) */}
          {activeTab === "nang_cao" && (
            <div style={{ 
              background: subBg, 
              border: `1px solid ${borderColor}`, 
              borderRadius: "0.5rem", 
              padding: "1rem",
              gridRow: "span 2",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem"
            }}>
              <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: "#eab308", margin: 0, display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <TrendingUp size={15} color="#eab308" /> {isEnglish ? "Foreign Flow by Underlying" : "Phân bổ khối ngoại theo CS"}
              </h4>
              {flowLoading ? (
                <div style={{ color: mutedText, fontSize: "0.82rem", padding: "1rem 0" }}>Loading flows...</div>
              ) : flowData ? (
                <div style={{ 
                  display: "flex", 
                  flexDirection: "column", 
                  gap: "0.5rem", 
                  overflowY: "auto", 
                  flex: 1, 
                  minHeight: 0, 
                  paddingTop: "0.25rem", 
                  paddingBottom: "0.25rem", 
                  paddingRight: "0.25rem" 
                }}>
                  {flowData.foreign_flows.slice(0, 10).map((item, idx) => (
                    <div 
                      key={item.underlying + idx} 
                      style={{ 
                        display: "flex", 
                        flexDirection: "column", 
                        gap: "0.3rem",
                        padding: "0.45rem 0.6rem",
                        background: cardBg,
                        borderRadius: "0.375rem",
                        border: `1px solid ${borderColor}`
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", fontWeight: "800" }}>
                        <span style={{ color: textColor }}>{item.underlying}</span>
                        <span style={{ color: "#60a5fa" }}>{item.percentage}%</span>
                      </div>
                      <div style={{ width: "100%", height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "2rem", overflow: "hidden" }}>
                        <div style={{ width: `${item.percentage}%`, height: "100%", background: "linear-gradient(90deg, #2563eb, #60a5fa)", borderRadius: "2rem" }} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: mutedText, fontSize: "0.82rem" }}>No flow data loaded.</div>
              )}
            </div>
          )}

          {/* 4. Top Net Buy Flows */}
          {activeTab === "nang_cao" && (
            <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: "#10b981", margin: 0, display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <TrendingUp size={15} color="#10b981" /> {isEnglish ? "Top Net Buy (Prop)" : "Top Tự doanh Mua Ròng (Tr.đ)"}
              </h4>
              {flowLoading ? (
                <div style={{ color: mutedText, fontSize: "0.82rem", padding: "1rem 0" }}>Loading flows...</div>
              ) : flowData ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {flowData.prop_flows.net_buy.slice(0, 5).map((item, idx) => (
                    <div 
                      key={item.symbol + idx}
                      onClick={() => openDetail(item.symbol)}
                      style={{ 
                        display: "grid", 
                        gridTemplateColumns: "1.2fr 0.8fr 1fr 1fr", 
                        fontSize: "0.78rem", 
                        alignItems: "center",
                        padding: "0.45rem 0.6rem",
                        background: cardBg,
                        borderRadius: "0.375rem",
                        border: `1px solid ${borderColor}`,
                        cursor: "pointer",
                        transition: "border-color 0.15s, transform 0.1s"
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.borderColor = "#2563eb";
                        e.currentTarget.style.transform = "translateY(-1px)";
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.borderColor = borderColor;
                        e.currentTarget.style.transform = "none";
                      }}
                    >
                      <strong style={{ color: "#60a5fa" }}>{item.symbol}</strong>
                      <span style={{ color: mutedText }}>{item.underlying}</span>
                      <span style={{ color: mutedText, textAlign: "right", paddingRight: "0.5rem" }}>{item.issuer}</span>
                      <span style={{ color: "#10b981", fontWeight: "700", textAlign: "right" }}>+{item.value.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: mutedText, fontSize: "0.82rem" }}>No flow data loaded.</div>
              )}
            </div>
          )}

          {/* 5. Top Net Sell Flows */}
          {activeTab === "nang_cao" && (
            <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: "#ef4444", margin: 0, display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <TrendingDown size={15} color="#ef4444" /> {isEnglish ? "Top Net Sell (Prop)" : "Top Tự doanh Bán Ròng (Tr.đ)"}
              </h4>
              {flowLoading ? (
                <div style={{ color: mutedText, fontSize: "0.82rem", padding: "1rem 0" }}>Loading flows...</div>
              ) : flowData ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {flowData.prop_flows.net_sell.slice(0, 5).map((item, idx) => (
                    <div 
                      key={item.symbol + idx}
                      onClick={() => openDetail(item.symbol)}
                      style={{ 
                        display: "grid", 
                        gridTemplateColumns: "1.2fr 0.8fr 1fr 1fr", 
                        fontSize: "0.78rem", 
                        alignItems: "center",
                        padding: "0.45rem 0.6rem",
                        background: cardBg,
                        borderRadius: "0.375rem",
                        border: `1px solid ${borderColor}`,
                        cursor: "pointer",
                        transition: "border-color 0.15s, transform 0.1s"
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.borderColor = "#2563eb";
                        e.currentTarget.style.transform = "translateY(-1px)";
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.borderColor = borderColor;
                        e.currentTarget.style.transform = "none";
                      }}
                    >
                      <strong style={{ color: "#60a5fa" }}>{item.symbol}</strong>
                      <span style={{ color: mutedText }}>{item.underlying}</span>
                      <span style={{ color: mutedText, textAlign: "right", paddingRight: "0.5rem" }}>{item.issuer}</span>
                      <span style={{ color: "#ef4444", fontWeight: "700", textAlign: "right" }}>{item.value.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: mutedText, fontSize: "0.82rem" }}>No flow data loaded.</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* FILTER PANEL */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem 1.25rem" }}>

        {/* Always-visible: search + dropdowns */}
        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr 1fr 1fr auto", gap: "0.75rem", alignItems: "end", marginBottom: activeTab === "nang_cao" ? "1rem" : 0 }}>
          {/* Search */}
          <div>
            <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.3rem" }}>Tìm kiếm</label>
            <div style={{ position: "relative" }}>
              <Search size={13} style={{ position: "absolute", left: "0.5rem", top: "50%", transform: "translateY(-50%)", color: mutedText }} />
              <input
                placeholder="Mã CW hoặc cổ phiếu CS..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem 0.5rem 0.45rem 1.75rem", borderRadius: "0.375rem", fontSize: "0.8rem", boxSizing: "border-box" }}
              />
            </div>
          </div>

          {/* Mã cơ sở */}
          <div>
            <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.3rem" }}>Mã cơ sở</label>
            <select value={selectedUnderlying} onChange={e => setSelectedUnderlying(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.375rem", fontSize: "0.8rem" }}>
              <option value="all" style={{ background: cardBg, color: textColor }}>Tất cả ({underlyingOptions.length})</option>
              {underlyingOptions.map(u => <option key={u} value={u} style={{ background: cardBg, color: textColor }}>{u}</option>)}
            </select>
          </div>

          {/* Tổ chức PH */}
          <div>
            <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.3rem" }}>Tổ chức phát hành</label>
            <select value={selectedIssuer} onChange={e => setSelectedIssuer(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.375rem", fontSize: "0.8rem" }}>
              <option value="all" style={{ background: cardBg, color: textColor }}>Tất cả ({issuerOptions.length})</option>
              {issuerOptions.map(is => <option key={is} value={is} style={{ background: cardBg, color: textColor }}>{getIssuerName(is)}</option>)}
            </select>
          </div>

          {/* Phân hạng NPH */}
          <div>
            <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.3rem" }}>Phân hạng NPH</label>
            <select value={selectedIssuerTier} onChange={e => setSelectedIssuerTier(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.375rem", fontSize: "0.8rem" }}>
              <option value="all" style={{ background: cardBg, color: textColor }}>Tất cả phân hạng</option>
              <option value="1" style={{ background: cardBg, color: textColor }}>Tier 1 (Cao cấp)</option>
              <option value="2" style={{ background: cardBg, color: textColor }}>Tier 2 (Trung cấp)</option>
              <option value="3" style={{ background: cardBg, color: textColor }}>Tier 3 (Phổ thông)</option>
            </select>
          </div>

          {/* Moneyness */}
          <div>
            <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.3rem" }}>Trạng thái Giá (Moneyness)</label>
            <select value={selectedMoneyness} onChange={e => setSelectedMoneyness(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.375rem", fontSize: "0.8rem" }}>
              <option value="all" style={{ background: cardBg, color: textColor }}>Tất cả vị thế</option>
              <option value="ITM" style={{ background: cardBg, color: textColor }}>🟢 ITM (In The Money)</option>
              <option value="ATM" style={{ background: cardBg, color: textColor }}>🔵 ATM (At The Money)</option>
              <option value="OTM" style={{ background: cardBg, color: textColor }}>🔴 OTM (Out of The Money)</option>
            </select>
          </div>

          {/* G-Score min */}
          <div>
            <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "block", marginBottom: "0.3rem" }}>G-Score ≥ {gscoreMin}</label>
            <input type="range" min="0" max="90" step="5" value={gscoreMin} onChange={e => setGscoreMin(Number(e.target.value))} style={{ width: "100%" }} />
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: "0.4rem" }}>
            <button onClick={() => loadData(true)} disabled={loading} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.45rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.78rem", fontWeight: "800", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.3rem" }}>
              <RefreshCw size={13} className={loading ? "spin" : ""} />
              {loading ? "..." : "Làm mới"}
            </button>
            <button onClick={handleReset} style={{ background: subBg, color: textColor, border: `1px solid ${borderColor}`, padding: "0.45rem 0.6rem", borderRadius: "0.375rem", fontSize: "0.78rem", cursor: "pointer" }}>
              <RotateCcw size={13} />
            </button>
          </div>
        </div>

        {/* Advanced sliders — only in nang_cao tab */}
        {activeTab === "nang_cao" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 220px", gap: "1rem", paddingTop: "1rem", borderTop: `1px solid ${borderColor}`, alignItems: "center" }}>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "flex", justifyContent: "space-between" }}>
                <span>Premium tối đa</span><strong style={{ color: textColor }}>{premiumMax}%</strong>
              </label>
              <input type="range" min="0" max="100" value={premiumMax} onChange={e => setPremiumMax(Number(e.target.value))} style={{ width: "100%", marginTop: "0.4rem" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "flex", justifyContent: "space-between" }}>
                <span>Delta tối thiểu</span><strong style={{ color: "#60a5fa" }}>{deltaMin}</strong>
              </label>
              <input type="range" min="0" max="0.9" step="0.05" value={deltaMin} onChange={e => setDeltaMin(Number(e.target.value))} style={{ width: "100%", marginTop: "0.4rem" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "flex", justifyContent: "space-between" }}>
                <span>Đòn bẩy min</span><strong style={{ color: "#10b981" }}>{gearingMin}x</strong>
              </label>
              <input type="range" min="0" max="15" step="0.5" value={gearingMin} onChange={e => setGearingMin(Number(e.target.value))} style={{ width: "100%", marginTop: "0.4rem" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, fontWeight: "600", display: "flex", justifyContent: "space-between" }}>
                <span>Đáo hạn tối đa</span><strong style={{ color: textColor }}>{daysMax} ngày</strong>
              </label>
              <input type="range" min="1" max="365" step="7" value={daysMax} onChange={e => setDaysMax(Number(e.target.value))} style={{ width: "100%", marginTop: "0.4rem" }} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", paddingLeft: "1rem", borderLeft: `1px solid ${borderColor}`, justifyContent: "center" }}>
              <label style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", justifyContent: "flex-start", gap: "0.5rem", cursor: "pointer", color: textColor, fontWeight: "600", whiteSpace: "nowrap", width: "auto", margin: 0 }}>
                <input type="checkbox" checked={chkBuyOnly} onChange={e => setChkBuyOnly(e.target.checked)} style={{ width: "14px", height: "14px", margin: 0, cursor: "pointer" }} />
                <span>Chỉ tín hiệu MUA</span>
              </label>
              <label style={{ fontSize: "0.75rem", display: "flex", alignItems: "center", justifyContent: "flex-start", gap: "0.5rem", cursor: "pointer", color: textColor, fontWeight: "600", whiteSpace: "nowrap", width: "auto", margin: 0 }}>
                <input type="checkbox" checked={chkUndervalued} onChange={e => setChkUndervalued(e.target.checked)} style={{ width: "14px", height: "14px", margin: 0, cursor: "pointer" }} />
                <span>Định giá thấp</span>
              </label>
            </div>
          </div>
        )}

        {activeTab === "yeu_thich" && (
          <p style={{ fontSize: "0.82rem", color: mutedText, margin: 0 }}>
            Hiển thị các mã bạn đã bấm THEO DÕI. Danh sách hiện tại: {favList.length} mã.
          </p>
        )}
      </div>

      {/* RESULTS TABLE */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: "800", margin: 0, color: textColor }}>
              Danh sách tín hiệu CW ({filteredRows.length})
            </h3>
            <span style={{ background: "#2563eb20", color: "#60a5fa", border: "1px solid #2563eb40", padding: "0.15rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.72rem", fontWeight: "700" }}>
              {filteredRows.length} / {rawRows.length} mã
            </span>
            {loading && <span style={{ fontSize: "0.75rem", color: mutedText }}>Đang tải...</span>}
          </div>
          <span style={{ fontSize: "0.72rem", color: mutedText }}>Nhấn vào Mã CW để xem chi tiết · Sắp xếp bằng cách nhấn tiêu đề cột</span>
        </div>

        {filteredRows.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center" }}>
            <p style={{ color: mutedText, marginBottom: "0.75rem" }}>Không tìm thấy mã CW phù hợp với bộ lọc hiện tại.</p>
            <button onClick={handleReset} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.5rem 1.25rem", borderRadius: "0.375rem", fontSize: "0.82rem", fontWeight: "800", cursor: "pointer" }}>
              Đặt lại bộ lọc
            </button>
          </div>
        ) : (
          <>
            <div style={{ maxHeight: "480px", overflowY: "auto", border: `1px solid ${borderColor}`, borderRadius: "0.5rem" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                <thead style={{ position: "sticky", top: 0, background: subBg, zIndex: 5 }}>
                  <tr style={{ borderBottom: `2px solid ${borderColor}` }}>
                    <th style={{ padding: "0.55rem 0.5rem", textAlign: "left", fontSize: "0.75rem", fontWeight: "800", color: textColor }}>Mã CW</th>
                    <th style={{ padding: "0.55rem 0.5rem", textAlign: "left", fontSize: "0.75rem", fontWeight: "800", color: textColor }}>CS</th>
                    <th style={{ padding: "0.55rem 0.5rem", textAlign: "left", fontSize: "0.75rem", fontWeight: "800", color: textColor }}>PH</th>
                    <SortHeader label="Giá" field="price" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="±%" field="changePct" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="KL" field="volume" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="Premium" field="premium" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="Delta" field="delta" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="Đòn bẩy" field="gearing" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <th style={{ padding: "0.55rem 0.5rem", textAlign: "left", fontSize: "0.75rem", fontWeight: "800", color: textColor }}>Moneyness</th>
                    <SortHeader label="Hòa vốn" field="breakeven" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="IV%" field="iv" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="HV%" field="hv" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="DTM" field="dtm" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="G-Score" field="gscore" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="Tín hiệu" field="signal" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <th style={{ padding: "0.55rem 0.5rem", textAlign: "center", fontSize: "0.75rem", fontWeight: "800", color: textColor }}>Hành động</th>
                  </tr>
                </thead>
                <tbody>
                  {displayRows.map((row, idx) => {
                    const isEven = idx % 2 === 0;
                    return (
                      <tr
                        key={row.symbol + idx}
                        style={{ borderBottom: `1px solid ${borderColor}`, background: "transparent", transition: "background 0.1s" }}
                        onMouseEnter={e => e.currentTarget.style.background = "rgba(37,99,235,0.06)"}
                        onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                      >
                        <td
                          onClick={() => openDetail(row.symbol)}
                          style={{ padding: "0.55rem 0.5rem", fontWeight: "800", color: "#60a5fa", cursor: "pointer" }}
                        >
                          {row.symbol}
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", fontWeight: "700", color: textColor }}>
                          {row.underlying}
                          {row.undMaAlign !== undefined && (
                            <span 
                              title={`Xu hướng cổ phiếu cơ sở (MA Align: ${row.undMaAlign}%)`} 
                              style={{ 
                                marginLeft: "0.3rem", 
                                fontSize: "0.68rem", 
                                fontWeight: "800",
                                color: row.undMaAlign >= 67 ? "#10b981" : row.undMaAlign <= 33 ? "#ef4444" : "#f59e0b"
                              }}
                            >
                              {row.undMaAlign >= 67 ? "▲" : row.undMaAlign <= 33 ? "▼" : "◀▶"}
                            </span>
                          )}
                        </td>
                        <td style={{ 
                          padding: "0.55rem 0.5rem", 
                          fontWeight: "600",
                          color: getIssuerTier(row.issuer) === "1" ? "#60a5fa" : getIssuerTier(row.issuer) === "3" ? "#94a3b8" : textColor 
                        }}>
                          {getIssuerName(row.issuer)} (T{getIssuerTier(row.issuer)})
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", fontWeight: "700", color: textColor }}>
                          {row.price?.toLocaleString()} đ
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", fontWeight: "700", color: row.changePct >= 0 ? "#10b981" : "#ef4444" }}>
                          {row.changePct >= 0 ? "+" : ""}{formatNumber(row.changePct, 2)}%
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: textColor, fontWeight: "600" }}>
                          {row.volume?.toLocaleString() || "0"}
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: row.premium <= 10 ? "#10b981" : row.premium <= 20 ? "#f59e0b" : "#ef4444", fontWeight: "600" }}>
                          {row.premium}%
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: textColor, fontWeight: "600" }}>
                          {Math.round(row.delta * 100)}%
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: textColor, fontWeight: "600" }}>
                          {row.gearing}
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem" }}>
                          <span style={{
                            background: row.moneyness === "ITM" ? "rgba(16,185,129,0.15)" : row.moneyness === "ATM" ? "rgba(37,99,235,0.15)" : "rgba(239,68,68,0.15)",
                            color: row.moneyness === "ITM" ? "#10b981" : row.moneyness === "ATM" ? "#60a5fa" : "#ef4444",
                            padding: "0.15rem 0.4rem", borderRadius: "0.2rem", fontSize: "0.68rem", fontWeight: "800"
                          }}>
                            {row.moneyness}
                          </span>
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: mutedText, fontSize: "0.75rem" }}>
                          {row.breakeven?.toLocaleString()} đ
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: mutedText }}>{row.iv}%</td>
                        <td style={{ padding: "0.55rem 0.5rem", color: mutedText }}>{row.hv}%</td>
                        <td style={{ padding: "0.55rem 0.5rem", color: mutedText }}>{row.dtm || "-"}</td>
                        <td style={{ padding: "0.55rem 0.5rem", minWidth: "100px" }}>
                          <GScoreBar score={row.gscore} />
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem" }}>
                          <SignalBadge signal={row.signal} />
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", textAlign: "center", whiteSpace: "nowrap" }}>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleBuyOrder(row); }}
                            style={{ background: "#10b981", color: "#fff", border: "none", padding: "0.22rem 0.55rem", borderRadius: "0.25rem", fontSize: "0.7rem", fontWeight: "800", cursor: "pointer", marginRight: "0.3rem" }}
                          >
                            MUA
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleAddToWatchlist(row.symbol); }}
                            style={{ background: "transparent", color: mutedText, border: `1px solid ${borderColor}`, padding: "0.22rem 0.45rem", borderRadius: "0.25rem", fontSize: "0.7rem", cursor: "pointer" }}
                            title="Thêm vào Watchlist"
                          >
                            <Star size={11} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {filteredRows.length > 0 && (() => {
              const totalPages = Math.ceil(filteredRows.length / PAGE_SIZE) || 1;
              const validPage = Math.min(currentPage, totalPages);

              return (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem", paddingTop: "0.75rem", borderTop: `1px solid ${borderColor}`, flexWrap: "wrap", gap: "0.75rem" }}>
                  <span style={{ fontSize: "0.8rem", color: mutedText, fontWeight: "600" }}>
                    Trang {validPage} / {totalPages} · Tổng {filteredRows.length} mã
                  </span>

                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <button
                      disabled={validPage <= 1}
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      style={{
                        background: validPage <= 1 ? subBg : cardBg,
                        color: validPage <= 1 ? mutedText : textColor,
                        border: `1px solid ${borderColor}`,
                        padding: "0.35rem 0.75rem",
                        borderRadius: "0.375rem",
                        fontSize: "0.78rem",
                        fontWeight: "700",
                        cursor: validPage <= 1 ? "not-allowed" : "pointer",
                        opacity: validPage <= 1 ? 0.5 : 1
                      }}
                    >
                      ‹ Trước
                    </button>

                    {(() => {
                      const maxVisible = 5;
                      let startP = Math.max(1, validPage - Math.floor(maxVisible / 2));
                      let endP = startP + maxVisible - 1;
                      if (endP > totalPages) {
                        endP = totalPages;
                        startP = Math.max(1, endP - maxVisible + 1);
                      }
                      const pages = [];
                      for (let p = startP; p <= endP; p++) {
                        pages.push(p);
                      }
                      return pages.map(pNum => (
                        <button
                          key={pNum}
                          onClick={() => setCurrentPage(pNum)}
                          style={{
                            background: validPage === pNum ? "#2563eb" : cardBg,
                            color: validPage === pNum ? "#ffffff" : textColor,
                            border: `1px solid ${validPage === pNum ? "#2563eb" : borderColor}`,
                            padding: "0.35rem 0.65rem",
                            borderRadius: "0.375rem",
                            fontSize: "0.78rem",
                            fontWeight: "800",
                            cursor: "pointer"
                          }}
                        >
                          {pNum}
                        </button>
                      ));
                    })()}

                    <button
                      disabled={validPage >= totalPages}
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      style={{
                        background: validPage >= totalPages ? subBg : cardBg,
                        color: validPage >= totalPages ? mutedText : textColor,
                        border: `1px solid ${borderColor}`,
                        padding: "0.35rem 0.75rem",
                        borderRadius: "0.375rem",
                        fontSize: "0.78rem",
                        fontWeight: "700",
                        cursor: validPage >= totalPages ? "not-allowed" : "pointer",
                        opacity: validPage >= totalPages ? 0.5 : 1
                      }}
                    >
                      Sau ›
                    </button>
                  </div>
                </div>
              );
            })()}
          </>
        )}
      </div>

    </div>
  );
}
