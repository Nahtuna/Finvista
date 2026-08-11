import React, { useEffect, useState, useRef, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { getWarrantHistory, getWarrantSimulation, getCreditHealth, request } from "../../api.js";
import { useData } from "../../app/DataContext.jsx";
import { TradingViewLightweightChart } from "../../components/charts/TradingViewLightweightChart.jsx";
import { formatNumber } from "../../lib/formatters.js";
import { useThemeTokens } from "../../app/useThemeTokens.js";
import { ConfluenceScoreWidget } from "../market/components/ConfluenceScoreWidget.jsx";
import { PositionSizingWidget } from "../market/components/PositionSizingWidget.jsx";

/* ─────────────────────────────────────────────────────────
   Interactive IV / HV chart with hover crosshair
───────────────────────────────────────────────────────── */
function VolatilityChart({ historyData, isDark, borderColor, textColor, mutedText, subBg }) {
  const svgRef = useRef(null);
  const [hovered, setHovered] = useState(null); // { idx, x, y, iv, hv, date }

  if (!historyData || historyData.length < 2) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: mutedText, fontSize: "0.85rem" }}>
        Chưa có đủ dữ liệu lịch sử biến động (cần ít nhất 2 phiên).
      </div>
    );
  }

  const W = 900, H = 360;
  const PL = 52, PR = 20, PT = 16, PB = 36;
  const cW = W - PL - PR, cH = H - PT - PB;

  const ivs = historyData.map(d => d.implied_volatility_pct ?? 0);
  const hvs = historyData.map(d => d.historical_volatility_pct ?? 0);
  const dates = historyData.map(d => d.date ?? "");

  const allVals = [...ivs, ...hvs].filter(v => v > 0);
  const maxV = Math.max(...allVals, 80);
  const minV = Math.max(0, Math.min(...allVals) - 5);
  const rangeV = maxV - minV || 1;

  const gx = i => PL + (i / (historyData.length - 1)) * cW;
  const gy = v => PT + cH - ((v - minV) / rangeV) * cH;

  const ivPts = ivs.map((v, i) => `${gx(i)},${gy(v)}`).join(" ");
  const hvPts = hvs.map((v, i) => `${gx(i)},${gy(v)}`).join(" ");

  // area between curves
  let areaPath = ivs.map((v, i) => `${i === 0 ? "M" : "L"} ${gx(i)} ${gy(v)}`).join(" ");
  for (let i = historyData.length - 1; i >= 0; i--) areaPath += ` L ${gx(i)} ${gy(hvs[i])}`;
  areaPath += " Z";

  const yTicks = Array.from({ length: 5 }, (_, i) => minV + (i * rangeV) / 4);

  // x-axis labels every ~6 steps
  const xStep = Math.max(1, Math.ceil(historyData.length / 7));

  function handleMouseMove(e) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (W / rect.width);
    const relX = mx - PL;
    const idx = Math.round((relX / cW) * (historyData.length - 1));
    const clamped = Math.max(0, Math.min(historyData.length - 1, idx));
    setHovered({ idx: clamped, x: gx(clamped), iv: ivs[clamped], hv: hvs[clamped], date: dates[clamped] });
  }

  const lastIV = ivs[ivs.length - 1];
  const lastHV = hvs[hvs.length - 1];
  const ivHvDiff = lastIV - lastHV;
  const isExpensive = ivHvDiff > 10;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
      {/* Legend + summary */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
        <div style={{ display: "flex", gap: "1.5rem", fontSize: "0.8rem", fontWeight: "700" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ width: 14, height: 3, background: "#ef4444", display: "inline-block", borderRadius: 2 }} />
            IV – Biến động ngầm định ({lastIV.toFixed(1)}%)
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ width: 14, height: 3, background: "#3b82f6", display: "inline-block", borderRadius: 2 }} />
            HV – Biến động lịch sử ({lastHV.toFixed(1)}%)
          </span>
          <span style={{
            background: isExpensive ? "rgba(239,68,68,0.12)" : "rgba(16,185,129,0.12)",
            color: isExpensive ? "#ef4444" : "#10b981",
            border: `1px solid ${isExpensive ? "#ef444440" : "#10b98140"}`,
            padding: "0.15rem 0.55rem", borderRadius: "0.25rem", fontSize: "0.72rem", fontWeight: "800"
          }}>
            {isExpensive ? `⚠️ IV đắt hơn HV ${ivHvDiff.toFixed(1)}%` : `✅ Định giá hợp lý (IV-HV: ${ivHvDiff.toFixed(1)}%)`}
          </span>
        </div>
        {hovered && (
          <div style={{ fontSize: "0.75rem", color: mutedText, background: subBg, padding: "0.2rem 0.6rem", borderRadius: "0.3rem", border: `1px solid ${borderColor}` }}>
            {hovered.date} &nbsp;|&nbsp;
            <span style={{ color: "#ef4444", fontWeight: "700" }}>IV {hovered.iv?.toFixed(1)}%</span>
            &nbsp;|&nbsp;
            <span style={{ color: "#3b82f6", fontWeight: "700" }}>HV {hovered.hv?.toFixed(1)}%</span>
            &nbsp;|&nbsp;
            <span style={{ color: (hovered.iv - hovered.hv) > 0 ? "#ef4444" : "#10b981", fontWeight: "700" }}>
              Δ {(hovered.iv - hovered.hv).toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* SVG chart */}
      <div
        style={{ position: "relative", background: isDark ? "rgba(15,23,42,0.5)" : "#f8fafc", border: `1px solid ${borderColor}`, borderRadius: "0.5rem", overflow: "hidden" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHovered(null)}
      >
        <svg ref={svgRef} width="100%" height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
          {/* Y grid + labels */}
          {yTicks.map((v, i) => {
            const y = gy(v);
            return (
              <g key={i}>
                <line x1={PL} y1={y} x2={W - PR} y2={y} stroke={borderColor} strokeWidth="1" strokeDasharray="4 3" opacity="0.6" />
                <text x={PL - 6} y={y + 4} fill={mutedText} fontSize="10" textAnchor="end" fontWeight="600">{Math.round(v)}%</text>
              </g>
            );
          })}

          {/* X grid + labels */}
          {historyData.map((_, idx) => {
            if (idx % xStep !== 0 && idx !== historyData.length - 1) return null;
            const x = gx(idx);
            const parts = dates[idx].split("-");
            const lbl = parts.length === 3 ? `${parts[2]}/${parts[1]}` : dates[idx];
            return (
              <g key={idx}>
                <line x1={x} y1={PT} x2={x} y2={PT + cH} stroke={borderColor} strokeWidth="1" strokeDasharray="3 4" opacity="0.25" />
                <text x={x} y={PT + cH + 20} fill={mutedText} fontSize="10" textAnchor="middle" fontWeight="600">{lbl}</text>
              </g>
            );
          })}

          {/* Shaded area between IV and HV */}
          <path d={areaPath} fill={isExpensive ? "rgba(239,68,68,0.07)" : "rgba(16,185,129,0.06)"} stroke="none" />

          {/* HV line */}
          <polyline points={hvPts} fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          {/* IV line */}
          <polyline points={ivPts} fill="none" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Endpoint dots */}
          <circle cx={gx(ivs.length - 1)} cy={gy(lastIV)} r="5" fill="#ef4444" stroke="#fff" strokeWidth="1.5" />
          <circle cx={gx(hvs.length - 1)} cy={gy(lastHV)} r="5" fill="#3b82f6" stroke="#fff" strokeWidth="1.5" />

          {/* Crosshair on hover */}
          {hovered && (
            <g>
              <line x1={hovered.x} y1={PT} x2={hovered.x} y2={PT + cH} stroke={isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.2)"} strokeWidth="1" strokeDasharray="4 3" />
              <circle cx={hovered.x} cy={gy(hovered.iv)} r="5" fill="#ef4444" stroke="#fff" strokeWidth="2" />
              <circle cx={hovered.x} cy={gy(hovered.hv)} r="5" fill="#3b82f6" stroke="#fff" strokeWidth="2" />
            </g>
          )}
        </svg>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Mini KPI card
───────────────────────────────────────────────────────── */
function Kpi({ label, value, sub, color, cardBg, borderColor, mutedText, textColor }) {
  return (
    <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.65rem", padding: "0.85rem 1rem" }}>
      <span style={{ fontSize: "0.72rem", color: mutedText, display: "block" }}>{label}</span>
      <strong style={{ fontSize: "1.25rem", fontWeight: "900", display: "block", marginTop: "0.15rem", color: color || textColor, lineHeight: 1.2 }}>{value ?? "--"}</strong>
      {sub && <span style={{ fontSize: "0.7rem", color: mutedText }}>{sub}</span>}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Section title
───────────────────────────────────────────────────────── */
function SectionTitle({ icon, title, textColor }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.85rem" }}>
      <span style={{ fontSize: "1.1rem" }}>{icon}</span>
      <h3 style={{ margin: 0, fontSize: "0.95rem", fontWeight: "800", color: textColor }}>{title}</h3>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Main component
───────────────────────────────────────────────────────── */
export function WarrantDetailPage({ selectedSymbol, setSelectedSymbol, language = "vi", preferences = {} }) {
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);
  const { opportunitiesData, marketData } = useData();

  const [symbol, setSymbol] = useState(selectedSymbol || "");
  const [detailData, setDetailData] = useState(null);
  const [creditHealth, setCreditHealth] = useState(null);
  const [flowData, setFlowData] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [forceRefresh, setForceRefresh] = useState(0);
  const [chartType, setChartType] = useState("warrant");

  const realOpportunities = opportunitiesData?.recommendations || [];
  const liveUnderlyingMap = marketData?.tickers || {};

  useEffect(() => {
    const t = (selectedSymbol || "").trim().toUpperCase();
    if (t) { setSymbol(t); loadDetail(t); setChartType("warrant"); }
  }, [selectedSymbol]);

  async function loadDetail(tgt) {
    if (!tgt) return;
    setLoading(true);
    try {
      const parsedMatch = tgt.toUpperCase().match(/^C([A-Z]{3,4})(\d{4,5})$/);
      const underlying = parsedMatch ? parsedMatch[1] : tgt;
      const [resSim, resCredit, resHist, resFlow] = await Promise.allSettled([
        getWarrantSimulation(tgt),
        getCreditHealth(underlying),
        getWarrantHistory(tgt, 60),
        request(`/api/market/flow-stats?symbol=${underlying}`)
      ]);
      if (resSim.status === "fulfilled") setDetailData(resSim.value);
      if (resCredit.status === "fulfilled") setCreditHealth(resCredit.value);
      if (resFlow.status === "fulfilled" && resFlow.value?.status === "ok") {
        setFlowData(resFlow.value);
      } else {
        setFlowData(null);
      }
      setHistoryData(
        resHist.status === "fulfilled" && resHist.value?.history ? resHist.value.history : []
      );
    } catch (_) {
      setDetailData(null); setHistoryData([]); setFlowData(null);
    } finally {
      setLoading(false);
    }
  }

  const sym = (symbol || "").toUpperCase();
  const knownTickers = ["ACB","HPG","FPT","VPB","MBB","VNM","STB","TCB","MSN","MWG","VHM","VIC","SSI"];
  const parsedMatch = sym.match(/^C([A-Z]{3,4})(\d{4,5})$/);
  const underlyingSym = parsedMatch ? parsedMatch[1] : (knownTickers.find(tk => sym.includes(tk)) || "ACB");

  const realCwItem = realOpportunities.find(item =>
    (item.warrant_symbol || item.symbol || item.A_MaCW || "").toUpperCase() === sym
  );

  const underlyingPrice = realCwItem?.underlying_price || liveUnderlyingMap[underlyingSym]?.close || detailData?.underlying_current_price;
  const curPrice = realCwItem?.market_price || detailData?.current_price;
  const changePct = realCwItem?.price_change_pct;
  const ratio = realCwItem?.ratio || "1:1";
  const strike = realCwItem?.strike_price || detailData?.strike_price;
  const breakeven = realCwItem?.break_even_price;
  const dtm = realCwItem?.days_to_maturity || detailData?.days_to_maturity;
  const issuer = realCwItem?.issuer;
  const moneyness = realCwItem?.moneyness_status;
  const sxVal = strike && underlyingPrice ? underlyingPrice - strike : null;

  const delta = realCwItem?.delta ?? detailData?.delta;
  const gamma = realCwItem?.gamma ?? null;
  const theta = realCwItem?.theta_daily_burn ?? detailData?.theta_daily_burn;
  const vega = realCwItem?.vega ?? null;
  const rho = realCwItem?.rho ?? null;
  const iv = realCwItem?.implied_volatility_pct ?? detailData?.implied_volatility_pct;
  const hv = realCwItem?.historical_volatility_pct ?? detailData?.historical_volatility_pct;

  const bsPrice = detailData?.scenarios?.[0]?.matrix?.[3]?.theoretical_price || detailData?.current_price;
  const rawDiff = curPrice > 0 && bsPrice > 0 ? ((curPrice - bsPrice) / bsPrice) * 100 : 0;
  const diffPct = Number.isNaN(rawDiff) ? 0 : Math.round(rawDiff * 10) / 10;
  const valuationStatus = diffPct < -3 ? `⬇ Định giá thấp (${diffPct}%)` : diffPct > 3 ? `⬆ Định giá cao (+${diffPct}%)` : "✅ Định giá phù hợp";

  const signalRaw = (realCwItem?.recommendation_signal || realCwItem?.decision_signal || "WATCH").toUpperCase();
  let signalLabel = "THEO DÕI", signalBg = "rgba(245,158,11,0.15)", signalColor = "#f59e0b";
  if (signalRaw.includes("BUY") || signalRaw === "MUA TÍCH LŨY" || signalRaw === "UNDERVALUED") {
    signalLabel = "MUA KHUYẾN NGHỊ"; signalBg = "rgba(16,185,129,0.15)"; signalColor = "#10b981";
  } else if (signalRaw.includes("SKIP") || signalRaw.includes("RISK") || signalRaw === "DEEP OTM") {
    signalLabel = "RỦI RO CAO"; signalBg = "rgba(239,68,68,0.15)"; signalColor = "#ef4444";
  }

  const card = { background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" };

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "420px", color: textColor, ...card }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
        <RefreshCw size={36} className="animate-spin" style={{ color: "#2563eb" }} />
        <span style={{ fontSize: "0.9rem", fontWeight: "700", color: mutedText }}>Đang tải dữ liệu realtime…</span>
      </div>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>

      {/* ── HEADER ── */}
      <div style={card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.7rem", flexWrap: "wrap" }}>
              <h2 style={{ fontSize: "1.8rem", fontWeight: "900", margin: 0, color: "#60a5fa" }}>{sym || "—"}</h2>
              <span style={{ background: signalBg, color: signalColor, border: `1px solid ${signalColor}40`, padding: "0.15rem 0.65rem", borderRadius: "0.25rem", fontSize: "0.75rem", fontWeight: "800" }}>{signalLabel}</span>
              {moneyness && <span style={{ background: subBg, color: mutedText, border: `1px solid ${borderColor}`, padding: "0.15rem 0.55rem", borderRadius: "0.25rem", fontSize: "0.72rem", fontWeight: "700" }}>{moneyness}</span>}
            </div>
            <div style={{ fontSize: "0.82rem", color: mutedText, marginTop: "0.35rem" }}>
              Cơ sở: <strong style={{ color: textColor }}>{underlyingSym}</strong>
              &nbsp;({formatNumber(underlyingPrice, 0)} đ) &nbsp;·&nbsp; TCPH: <strong style={{ color: "#60a5fa" }}>{issuer || "—"}</strong>
              &nbsp;·&nbsp; DTM: <strong style={{ color: dtm <= 30 ? "#ef4444" : dtm <= 60 ? "#f59e0b" : "#10b981" }}>{dtm ?? "—"} ngày</strong>
            </div>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <input
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === "Enter" && loadDetail(symbol)}
              placeholder="Mã CW (vd: CACB2511)"
              style={{ background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.4rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.8rem", width: "170px" }}
            />
            <button onClick={() => loadDetail(symbol)} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.4rem 0.9rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer" }}>Tra cứu</button>
            <button onClick={() => { setForceRefresh(p => p + 1); loadDetail(symbol); }} style={{ background: "#059669", color: "#fff", border: "none", padding: "0.4rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.3rem" }}>
              <RefreshCw size={14} /> Làm mới
            </button>
          </div>
        </div>
      </div>

      {/* ── SECTION 1: KPI GRID ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "0.85rem" }}>
        <Kpi label="Giá CW hiện tại" value={`${formatNumber(curPrice, 0)} đ`}
          sub={changePct !== undefined ? `${changePct >= 0 ? "▲ +" : "▼ "}${formatNumber(Math.abs(changePct), 2)}%` : undefined}
          color={changePct >= 0 ? "#10b981" : "#ef4444"}
          cardBg={cardBg} borderColor={borderColor} mutedText={mutedText} textColor={textColor} />
        <Kpi label="Giá thực hiện (X)" value={`${formatNumber(strike, 0)} đ`} sub={`Tỷ lệ: ${ratio}`}
          cardBg={cardBg} borderColor={borderColor} mutedText={mutedText} textColor={textColor} />
        <Kpi label="Giá hòa vốn" value={`${formatNumber(breakeven, 0)} đ`} sub={`S - X: ${formatNumber(sxVal, 0)} đ`}
          color="#f59e0b" cardBg={cardBg} borderColor={borderColor} mutedText={mutedText} textColor={textColor} />
        <Kpi label="Giá lý thuyết BSM" value={`${formatNumber(bsPrice, 0)} đ`} sub={valuationStatus}
          color="#10b981" cardBg={cardBg} borderColor={borderColor} mutedText={mutedText} textColor={textColor} />
        <Kpi label="IV / HV" value={`${iv ? iv.toFixed(1) : "--"}% / ${hv ? hv.toFixed(1) : "--"}%`}
          sub={iv && hv ? (iv > hv * 1.1 ? "⚠️ IV đắt" : "✅ Hợp lý") : undefined}
          color={iv && hv ? (iv > hv * 1.1 ? "#ef4444" : "#10b981") : textColor}
          cardBg={cardBg} borderColor={borderColor} mutedText={mutedText} textColor={textColor} />
        <Kpi label="Thời gian còn lại" value={`${dtm ?? "--"} ngày`}
          sub={dtm ? (dtm <= 15 ? "⚠️ Gần đáo hạn" : dtm <= 30 ? "⏳ Theo dõi sát" : "🟢 Còn nhiều thời gian") : undefined}
          color={dtm <= 15 ? "#ef4444" : dtm <= 30 ? "#f59e0b" : "#10b981"}
          cardBg={cardBg} borderColor={borderColor} mutedText={mutedText} textColor={textColor} />
      </div>

      {/* ── SECTION 2: PRICE CHART + GREEKS side-by-side ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.9fr 1fr", gap: "1.25rem" }}>
        {/* Price chart */}
        <div style={card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
            <SectionTitle icon="📈" title={`Biểu đồ kỹ thuật ${chartType === "warrant" ? sym : underlyingSym}`} textColor={textColor} />
            <div style={{ display: "flex", gap: "0.2rem", background: subBg, padding: "0.15rem", borderRadius: "0.3rem" }}>
              {[["warrant", "Chứng quyền"], ["underlying", "Cổ phiếu cơ sở"]].map(([k, lbl]) => (
                <button key={k} onClick={() => setChartType(k)} style={{ border: "none", background: chartType === k ? "#2563eb" : "transparent", color: chartType === k ? "#fff" : mutedText, padding: "0.2rem 0.6rem", borderRadius: "0.2rem", fontSize: "0.72rem", fontWeight: "800", cursor: "pointer" }}>{lbl}</button>
              ))}
            </div>
          </div>
          <div style={{ width: "100%", height: "420px", borderRadius: "0.5rem", overflow: "hidden" }}>
            <TradingViewLightweightChart
              key={(chartType === "warrant" ? sym : underlyingSym) + (preferences.colorMode || "") + forceRefresh}
              symbol={chartType === "warrant" ? sym : underlyingSym}
              theme={isDark ? "dark" : "light"}
              height={420}
              targetPrice={chartType === "warrant" ? curPrice : underlyingPrice}
              showSR={chartType === "underlying"}
            />
          </div>
        </div>

        {/* Greeks panel */}
        <div style={card}>
          <SectionTitle icon="⚡" title="Bộ chỉ số Greeks & Định giá" textColor={textColor} />
          <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem", fontSize: "0.82rem" }}>
            {[
              { label: "Delta (Δ) – Độ nhạy giá", value: delta?.toFixed(4), color: "#60a5fa", hint: delta ? `Giá CW tăng ${(delta * 1000).toFixed(0)}đ khi CS tăng 1,000đ` : null },
              { label: "Gamma (Γ) – Gia tốc Delta", value: gamma?.toFixed(6), color: "#8b5cf6" },
              { label: "Theta (Θ) – Hao mòn ngày", value: theta ? `${theta.toFixed(2)} đ/ngày` : null, color: "#ef4444", hint: theta ? `Giá CW mất ${theta.toFixed(2)}đ mỗi ngày` : null },
              { label: "Vega (ν) – Nhạy biến động", value: vega?.toFixed(4), color: "#eab308" },
              { label: "Rho (ρ) – Nhạy lãi suất", value: rho?.toFixed(4), color: "#ec4899" },
              { label: "Implied Volatility (IV)", value: iv ? `${iv.toFixed(2)}%` : null, color: "#f59e0b" },
              { label: "Historical Volatility (HV)", value: hv ? `${hv.toFixed(2)}%` : null, color: "#6b7280" },
              { label: "Giá lý thuyết Black-Scholes", value: `${formatNumber(bsPrice, 0)} đ`, color: "#10b981" },
              { label: "Trạng thái định giá", value: valuationStatus, color: diffPct < -3 ? "#10b981" : diffPct > 3 ? "#ef4444" : "#10b981" },
            ].map(({ label, value, color, hint }) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.45rem" }}>
                <div>
                  <span style={{ color: mutedText }}>{label}</span>
                  {hint && <div style={{ fontSize: "0.68rem", color: mutedText, marginTop: "0.1rem" }}>{hint}</div>}
                </div>
                <strong style={{ color: color || textColor, textAlign: "right", marginLeft: "0.5rem" }}>{value ?? "--"}</strong>
              </div>
            ))}
          </div>

          {/* IV vs HV bar gauge */}
          {iv != null && hv != null && (
            <div style={{ marginTop: "1rem", padding: "0.7rem", background: subBg, borderRadius: "0.4rem", border: `1px solid ${borderColor}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.73rem", marginBottom: "0.4rem" }}>
                <span style={{ color: mutedText }}>So sánh IV – HV</span>
                <strong style={{ color: iv > hv * 1.1 ? "#ef4444" : "#10b981" }}>
                  {iv > hv * 1.1 ? `Đắt (+${(iv - hv).toFixed(1)}%)` : `Hợp lý (${(iv - hv).toFixed(1)}%)`}
                </strong>
              </div>
              <div style={{ display: "flex", height: "8px", borderRadius: "4px", overflow: "hidden", background: borderColor }}>
                <div style={{ width: `${Math.min(100, (hv / (iv + hv)) * 100)}%`, background: "#3b82f6" }} />
                <div style={{ width: `${Math.min(100, (iv / (iv + hv)) * 100)}%`, background: iv > hv * 1.1 ? "#ef4444" : "#10b981" }} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.67rem", color: mutedText, marginTop: "0.3rem" }}>
                <span>HV {hv.toFixed(1)}% (Lam)</span>
                <span>IV {iv.toFixed(1)}% (Đỏ/Lục)</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── AI ANALYSIS: Confluence Score + Position Sizing ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginTop: "0.5rem" }}>
        <ConfluenceScoreWidget symbol={underlyingSym || sym} language={language} preferences={preferences} />
        <PositionSizingWidget symbol={underlyingSym || sym} entryPrice={underlyingPrice} language={language} preferences={preferences} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", alignItems: "stretch" }}>
        {/* IV/HV chart */}
        <div style={card}>
          <SectionTitle icon="📊" title="Biến động IV vs HV (60 phiên gần nhất)" textColor={textColor} />
          <VolatilityChart
            historyData={historyData}
            isDark={isDark}
            borderColor={borderColor}
            textColor={textColor}
            mutedText={mutedText}
            subBg={subBg}
          />
          <div style={{ marginTop: "0.75rem", fontSize: "0.76rem", color: mutedText, background: isDark ? "rgba(30,41,59,0.4)" : "#f1f5f9", padding: "0.65rem 0.85rem", borderRadius: "0.4rem", lineHeight: 1.65 }}>
            <strong style={{ color: textColor }}>💡 </strong>
            Khi <span style={{ color: "#ef4444", fontWeight: "700" }}>IV</span> vượt xa <span style={{ color: "#3b82f6", fontWeight: "700" }}>HV</span> (&gt;10%), CW đang được định giá đắt. Hover để xem từng ngày.
          </div>
        </div>

        {/* Scenario P&L matrix */}
        {detailData?.scenarios ? (
          <div style={card}>
            <SectionTitle icon="🎯" title={`Kịch bản Lãi/Lỗ – ${underlyingSym}`} textColor={textColor} />
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", fontSize: "0.74rem", borderCollapse: "collapse", textAlign: "center" }}>
                <thead>
                  <tr style={{ background: subBg, color: mutedText }}>
                    <th style={{ padding: "0.45rem 0.5rem", border: `1px solid ${borderColor}`, textAlign: "left" }}>Ngày giữ</th>
                    {detailData.scenarios[0]?.matrix.map(m => (
                      <th key={m.change_pct} style={{ padding: "0.45rem 0.4rem", border: `1px solid ${borderColor}`, color: m.change_pct > 0 ? "#10b981" : m.change_pct < 0 ? "#ef4444" : textColor }}>
                        {m.change_pct >= 0 ? "+" : ""}{m.change_pct}%
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {detailData.scenarios.map(row => (
                    <tr key={row.holding_days} style={{ borderBottom: `1px solid ${borderColor}` }}>
                      <td style={{ padding: "0.45rem 0.5rem", border: `1px solid ${borderColor}`, fontWeight: "700", background: subBg, textAlign: "left", whiteSpace: "nowrap" }}>
                        {row.holding_days}ng <span style={{ color: mutedText, fontWeight: "400", fontSize: "0.68rem" }}>(còn {row.remaining_days})</span>
                      </td>
                      {row.matrix.map((cell, ci) => {
                        const pl = cell.p_l_pct;
                        const bg = pl > 0 ? `rgba(16,185,129,${Math.min(0.32, pl / 150)})` : pl < 0 ? `rgba(239,68,68,${Math.min(0.32, Math.abs(pl) / 150)})` : "transparent";
                        return (
                          <td key={ci} style={{ padding: "0.45rem 0.35rem", border: `1px solid ${borderColor}`, background: bg, color: pl > 0 ? "#10b981" : pl < 0 ? "#ef4444" : textColor, fontWeight: "700" }}>
                            {pl >= 0 ? "+" : ""}{pl.toFixed(1)}%
                            <div style={{ fontSize: "0.62rem", color: mutedText, fontWeight: "normal" }}>{formatNumber(cell.theoretical_price, 0)}đ</div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div style={{ ...card, display: "flex", alignItems: "center", justifyContent: "center", color: mutedText, fontSize: "0.85rem" }}>
            Chưa có dữ liệu kịch bản. Nhấn Tra cứu để tải.
          </div>
        )}
      </div>

      {/* ── SECTION 5: GREEKS DEEP DIVE ── */}
      <div style={card}>
        <SectionTitle icon="🧮" title="Phân tích sâu: Định giá BSM & Mô hình Greeks" textColor={textColor} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
          {[
            { sym: "Δ Delta", val: delta?.toFixed(4), color: "#60a5fa", desc: `Giá CW thay đổi ${delta ? (delta * 1000).toFixed(0) : "--"}đ khi CS tăng 1.000đ` },
            { sym: "Γ Gamma", val: gamma?.toFixed(6), color: "#8b5cf6", desc: "Gia tốc thay đổi của Delta" },
            { sym: "Θ Theta", val: theta ? `${theta.toFixed(2)} đ/ng` : "--", color: "#ef4444", desc: `CW mất ${theta ? theta.toFixed(2) : "--"}đ giá trị mỗi ngày trôi qua` },
            { sym: "ν Vega", val: vega?.toFixed(4), color: "#eab308", desc: "Độ nhạy giá CW với 1% thay đổi Vol" },
          ].map(({ sym: gsym, val, color, desc }) => (
            <div key={gsym} style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <div style={{ fontSize: "0.8rem", color, fontWeight: "800", marginBottom: "0.2rem" }}>{gsym}</div>
              <strong style={{ fontSize: "1.4rem", color: textColor, display: "block", margin: "0.2rem 0" }}>{val ?? "--"}</strong>
              <div style={{ fontSize: "0.7rem", color: mutedText, lineHeight: 1.4 }}>{desc}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginTop: "1rem" }}>
          <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
            <span style={{ fontSize: "0.75rem", color: mutedText }}>Giá CW thị trường</span>
            <strong style={{ fontSize: "1.3rem", display: "block", color: textColor, marginTop: "0.15rem" }}>{formatNumber(curPrice, 0)} đ</strong>
          </div>
          <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
            <span style={{ fontSize: "0.75rem", color: mutedText }}>Giá lý thuyết BSM</span>
            <strong style={{ fontSize: "1.3rem", display: "block", color: "#10b981", marginTop: "0.15rem" }}>{formatNumber(bsPrice, 0)} đ</strong>
          </div>
          <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
            <span style={{ fontSize: "0.75rem", color: mutedText }}>Chênh lệch Premium/Discount</span>
            <strong style={{ fontSize: "1.3rem", display: "block", color: diffPct > 3 ? "#ef4444" : diffPct < -3 ? "#10b981" : "#f59e0b", marginTop: "0.15rem" }}>
              {diffPct > 0 ? "+" : ""}{diffPct}% — {valuationStatus}
            </strong>
          </div>
        </div>
      </div>

      {/* ── SECTION 6: CREDIT HEALTH & INVESTOR FLOW ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "1.25rem" }}>
        
        {/* Credit Health Column */}
        <div style={card}>
          <SectionTitle icon="🏥" title={`Sức khỏe Tín dụng cổ phiếu cơ sở ${underlyingSym}`} textColor={textColor} />
          {creditHealth?.is_bank ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1rem" }}>
                {[
                  { label: "NPL – Nợ xấu", val: creditHealth?.financial_ratios?.npl !== undefined ? (creditHealth.financial_ratios.npl * 100).toFixed(2) + "%" : "--", color: creditHealth?.financial_ratios?.npl > 0.03 ? "#ef4444" : "#10b981", badge: creditHealth?.financial_ratios?.npl > 0.03 ? "VƯỢT TRẦN >3%" : "AN TOÀN <3%" },
                  { label: "CAR – Hệ số vốn", val: creditHealth?.financial_ratios?.car !== undefined ? (creditHealth.financial_ratios.car * 100).toFixed(2) + "%" : "--", color: creditHealth?.financial_ratios?.car < 0.08 ? "#ef4444" : "#60a5fa", badge: creditHealth?.financial_ratios?.car < 0.08 ? "DƯỚI CHUẨN <8%" : "ĐẠT CHUẨN BASEL ≥8%" },
                  { label: "NIM – Biên lãi thuần", val: creditHealth?.financial_ratios?.nim !== undefined ? (creditHealth.financial_ratios.nim * 100).toFixed(2) + "%" : "--", color: "#f59e0b", badge: "Hiệu quả sinh lời TS" },
                ].map(({ label, val, color, badge }) => (
                  <div key={label} style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
                    <span style={{ fontSize: "0.75rem", color: mutedText }}>{label}</span>
                    <strong style={{ fontSize: "1.5rem", display: "block", color, marginTop: "0.15rem" }}>{val}</strong>
                    <span style={{ fontSize: "0.72rem", color, fontWeight: "700" }}>● {badge}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
                {[
                  { label: "LLR – Bao phủ nợ xấu", val: creditHealth?.financial_ratios?.llr !== undefined ? (creditHealth.financial_ratios.llr * 100).toFixed(1) + "%" : "--" },
                  { label: "CIR – Chi phí/Doanh thu", val: creditHealth?.financial_ratios?.cir !== undefined ? (creditHealth.financial_ratios.cir * 100).toFixed(1) + "%" : "--" },
                  { label: "LDR – Dư nợ/Huy động", val: creditHealth?.financial_ratios?.ldr !== undefined ? (creditHealth.financial_ratios.ldr * 100).toFixed(1) + "%" : "--" },
                  { label: "ROE – Hiệu suất vốn CSH", val: creditHealth?.financial_ratios?.roe !== undefined ? (creditHealth.financial_ratios.roe * 100).toFixed(1) + "%" : "--", color: "#10b981" },
                ].map(({ label, val, color }) => (
                  <div key={label} style={{ background: subBg, padding: "0.75rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
                    <span style={{ fontSize: "0.72rem", color: mutedText }}>{label}</span>
                    <strong style={{ fontSize: "1.15rem", display: "block", color: color || textColor, marginTop: "0.1rem" }}>{val}</strong>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
              {[
                { label: "Altman Z-Score", val: creditHealth?.distress_scores?.altman_z_score ? formatNumber(creditHealth.distress_scores.altman_z_score, 2) : "--", color: "#10b981", risk: creditHealth?.distress_scores?.altman_z_score < 1.81 },
                { label: "Springate S-Score", val: creditHealth?.distress_scores?.springate_s_score ? formatNumber(creditHealth.distress_scores.springate_s_score, 2) : "--", color: "#60a5fa", risk: creditHealth?.distress_scores?.springate_distressed },
                { label: "Zmijewski X-Score", val: creditHealth?.distress_scores?.zmijewski_x_score ? formatNumber(creditHealth.distress_scores.zmijewski_x_score, 2) : "--", color: "#f59e0b", risk: creditHealth?.distress_scores?.zmijewski_distressed },
              ].map(({ label, val, color, risk }) => (
                <div key={label} style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
                  <span style={{ fontSize: "0.75rem", color: mutedText }}>{label}</span>
                  <strong style={{ fontSize: "1.5rem", display: "block", color, marginTop: "0.15rem" }}>{val}</strong>
                  <span style={{ fontSize: "0.72rem", color: risk ? "#ef4444" : "#10b981", fontWeight: "700" }}>● {risk ? "RỦI RO CAO" : "VÙNG AN TOÀN"}</span>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem", marginTop: "1rem" }}>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <span style={{ fontSize: "0.75rem", color: mutedText }}>Xác suất Phá sản (ML XGBoost)</span>
              <strong style={{ fontSize: "1.35rem", display: "block", color: "#10b981", marginTop: "0.15rem" }}>
                {creditHealth?.credit_metrics?.bankruptcy_probability ? formatNumber(creditHealth.credit_metrics.bankruptcy_probability * 100, 2) + "%" : "--"}
              </strong>
            </div>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <span style={{ fontSize: "0.75rem", color: mutedText }}>Xếp hạng rủi ro tổng hợp</span>
              <strong style={{ fontSize: "1.35rem", display: "block", color: "#60a5fa", marginTop: "0.15rem" }}>
                {creditHealth?.credit_metrics?.risk_zone || "--"}
              </strong>
            </div>
          </div>
        </div>

        {/* Investor Flow Column */}
        <div style={card}>
          <SectionTitle icon="💧" title={`Dòng tiền Tự doanh & Khối ngoại – ${underlyingSym}`} textColor={textColor} />
          {flowData?.groups ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
              {Object.entries(flowData.groups).map(([key, value]) => {
                const isNetBuy = value.net_val >= 0;
                const netColor = isNetBuy ? "#10b981" : "#ef4444";
                const totalVal = Math.abs(value.buy_val) + Math.abs(value.sell_val) || 1;
                const buyPct = (value.buy_val / totalVal) * 100;
                
                return (
                  <div key={key} style={{ background: subBg, padding: "0.65rem 0.85rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.25rem" }}>
                      <strong style={{ fontSize: "0.8rem", color: textColor }}>{value.name}</strong>
                      <span style={{
                        background: isNetBuy ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)",
                        color: netColor,
                        padding: "0.1rem 0.45rem",
                        borderRadius: "0.25rem",
                        fontSize: "0.72rem",
                        fontWeight: "800"
                      }}>
                        {isNetBuy ? "Mua ròng +" : "Bán ròng "}{value.net_val.toFixed(2)} tỷ
                      </span>
                    </div>

                    {/* Progress Bar (Buy vs Sell Ratio) */}
                    <div style={{ height: "5px", borderRadius: "2.5px", overflow: "hidden", background: isDark ? "rgba(255,255,255,0.1)" : "#e2e8f0", display: "flex", margin: "0.35rem 0" }}>
                      <div style={{ width: `${buyPct}%`, background: "#10b981" }} />
                      <div style={{ width: `${100 - buyPct}%`, background: "#ef4444" }} />
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: mutedText }}>
                      <span>Mua: <strong style={{ color: "#10b981" }}>{value.buy_val}T</strong> (TB: {formatNumber(value.avg_buy_price, 1)}đ)</span>
                      <span>Bán: <strong style={{ color: "#ef4444" }}>{value.sell_val}T</strong> (TB: {formatNumber(value.avg_sell_price, 1)}đ)</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "80%", color: mutedText, fontSize: "0.82rem" }}>
              Đang tải hoặc chưa có dữ liệu dòng tiền cho {underlyingSym}...
            </div>
          )}
        </div>
      </div>

      {/* ── SECTION 7: PEER COMPARISON TABLE ── */}
      <div style={card}>
        <SectionTitle icon="🔍" title={`So sánh Chứng quyền cùng mã cơ sở ${underlyingSym}`} textColor={textColor} />
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", fontSize: "0.78rem", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: subBg, color: mutedText, textAlign: "left" }}>
                {["Mã CW", "Giá đóng cửa", "Thay đổi", "Giá thực hiện", "Hòa vốn", "S – X", "TCPH", "DTM", "IV%", "Delta"].map(h => (
                  <th key={h} style={{ padding: "0.5rem 0.6rem", borderBottom: `2px solid ${borderColor}`, whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(() => {
                const peers = realOpportunities
                  .filter(item => (item.underlying_symbol || item.underlying || "").toUpperCase() === underlyingSym.toUpperCase())
                  .sort((a, b) => (b.composite_g_score || b.score || 0) - (a.composite_g_score || a.score || 0));

                const rows = peers.length > 0 ? peers : [{ warrant_symbol: sym, market_price: curPrice, price_change_pct: changePct, strike_price: strike, break_even_price: breakeven, underlying_price: underlyingPrice, issuer, days_to_maturity: dtm, implied_volatility_pct: iv, delta }];

                return rows.map((row, i) => {
                  const rs = (row.warrant_symbol || row.symbol || "").toUpperCase();
                  const rp = row.market_price || curPrice;
                  const rc = row.price_change_pct ?? 0;
                  const rX = row.strike_price || strike;
                  const rBk = row.break_even_price || "--";
                  const rSx = (row.underlying_price || underlyingPrice) - rX;
                  const isCur = rs === sym;
                  return (
                    <tr key={rs + i} onClick={() => { setSymbol(rs); setSelectedSymbol(rs); }}
                      style={{ borderBottom: `1px solid ${borderColor}`, cursor: "pointer", background: isCur ? (isDark ? "rgba(37,99,235,0.12)" : "rgba(37,99,235,0.06)") : "transparent" }}>
                      <td style={{ padding: "0.5rem 0.6rem", fontWeight: "800", color: isCur ? "#2563eb" : "#60a5fa" }}>
                        {rs} {isCur && <span style={{ fontSize: "0.65rem", color: "#10b981" }}>◀ Đang xem</span>}
                      </td>
                      <td style={{ padding: "0.5rem 0.6rem", fontWeight: "700", color: textColor }}>{formatNumber(rp, 0)} đ</td>
                      <td style={{ padding: "0.5rem 0.6rem", fontWeight: "700", color: rc >= 0 ? "#10b981" : "#ef4444" }}>{rc >= 0 ? "▲+" : "▼"}{formatNumber(Math.abs(rc), 2)}%</td>
                      <td style={{ padding: "0.5rem 0.6rem", color: textColor }}>{formatNumber(rX, 0)} đ</td>
                      <td style={{ padding: "0.5rem 0.6rem", color: textColor }}>{formatNumber(rBk, 0)} đ</td>
                      <td style={{ padding: "0.5rem 0.6rem", color: rSx >= 0 ? "#10b981" : "#ef4444", fontWeight: "700" }}>{formatNumber(rSx, 0)} đ</td>
                      <td style={{ padding: "0.5rem 0.6rem", color: mutedText }}>{row.issuer || issuer}</td>
                      <td style={{ padding: "0.5rem 0.6rem", color: (row.days_to_maturity || dtm) <= 30 ? "#ef4444" : mutedText }}>{row.days_to_maturity || dtm} ng</td>
                      <td style={{ padding: "0.5rem 0.6rem", color: "#f59e0b" }}>{row.implied_volatility_pct ? row.implied_volatility_pct.toFixed(1) + "%" : "--"}</td>
                      <td style={{ padding: "0.5rem 0.6rem", color: "#60a5fa" }}>{row.delta ? row.delta.toFixed(3) : "--"}</td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
