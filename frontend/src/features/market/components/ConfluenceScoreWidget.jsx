import React, { useEffect, useState, useCallback } from "react";

/**
 * ConfluenceScoreWidget — Hiển thị Confluence Score 0-100 cho 1 mã cổ phiếu.
 * Gọi GET /api/regime/{symbol}/confluence
 */
export function ConfluenceScoreWidget({ symbol, language, preferences = {} }) {
  const [data, setData] = useState(null);
  const [mtf, setMtf]   = useState(null);
  const [loading, setLoading] = useState(false);
  const isEnglish = language === "en";
  const backendBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8008";

  const fetchData = useCallback(() => {
    if (!symbol) return;
    setLoading(true);
    Promise.all([
      fetch(`${backendBase}/api/regime/${symbol}/confluence`).then(r => r.json()),
      fetch(`${backendBase}/api/regime/${symbol}/mtf-bias`).then(r => r.json()),
    ])
      .then(([conf, m]) => {
        if (conf.status === "ok") setData(conf);
        if (m.status === "ok")    setMtf(m);
      })
      .catch(err => console.error("ConfluenceWidget error:", err))
      .finally(() => setLoading(false));
  }, [symbol, backendBase]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const score  = data?.score ?? null;
  const verdict = data?.verdict ?? "--";
  const grade  = mtf?.entry_grade ?? "?";

  const scoreColor = score === null ? "#64748b"
    : score >= 70 ? "#10b981"
    : score >= 55 ? "#3b82f6"
    : score >= 40 ? "#f59e0b"
    : "#ef4444";

  const gradeColor = { A: "#10b981", B: "#3b82f6", C: "#f59e0b", D: "#ef4444" }[grade] ?? "#94a3b8";
  const gradeLabel = { A: "Vào lệnh đủ tỷ trọng", B: "Vào 50-75%", C: "Chờ thêm tín hiệu", D: "Không vào lệnh" };
  const verdictLabel = {
    "DONG_THUAN_TANG": "Đồng thuận Tăng", "DONG_THUAN_GIAM": "Đồng thuận Giảm",
    "TRUNG_LAT": "Trung lập", "TRUNG_LAT_TICH_CUC": "TL Tích cực",
    "TRUNG_LAT_TIEU_CUC": "TL Tiêu cực",
  };

  const card = {
    background: "#131b2e", borderRadius: "0.75rem",
    border: "1px solid rgba(37,99,235,0.2)", padding: "1rem",
  };

  const row = { display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "0.4rem 0", borderBottom: "1px solid rgba(255,255,255,0.04)", fontSize: "0.78rem" };

  if (loading) return (
    <div style={{ ...card, textAlign: "center", color: "#64748b", padding: "2rem" }}>
      <div style={{ fontSize: "1.2rem", marginBottom: "0.5rem" }}>⏳</div>
      Đang tính toán Confluence Score...
    </div>
  );

  return (
    <div style={card}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.8rem", fontWeight: "800", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          🎯 {isEnglish ? "Confluence Score" : "Điểm Hội Tụ"} · {symbol}
        </span>
        <button
          onClick={fetchData}
          style={{ background: "rgba(37,99,235,0.15)", border: "1px solid rgba(37,99,235,0.3)", borderRadius: "0.3rem",
            color: "#60a5fa", fontSize: "0.68rem", fontWeight: "700", padding: "0.2rem 0.5rem", cursor: "pointer" }}
        >↻ Cập nhật</button>
      </div>

      {/* Score Gauge */}
      <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", marginBottom: "1rem" }}>
        {/* Ring */}
        <div style={{ position: "relative", width: "80px", height: "80px", flexShrink: 0 }}>
          <svg width="80" height="80" viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="33" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="7" />
            <circle
              cx="40" cy="40" r="33" fill="none"
              stroke={scoreColor} strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 33}
              strokeDashoffset={2 * Math.PI * 33 * (1 - (score ?? 50) / 100)}
              transform="rotate(-90 40 40)"
              style={{ transition: "stroke-dashoffset 0.6s ease, stroke 0.4s ease" }}
            />
          </svg>
          <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)",
            textAlign: "center", lineHeight: 1 }}>
            <div style={{ fontSize: "1.4rem", fontWeight: "900", color: scoreColor }}>
              {score !== null ? Math.round(score) : "--"}
            </div>
            <div style={{ fontSize: "0.55rem", color: "#64748b", fontWeight: "700" }}>/ 100</div>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "0.95rem", fontWeight: "800", color: scoreColor, marginBottom: "0.3rem" }}>
            {verdictLabel[verdict?.replace(/_/g, "_")] ?? verdict?.replace(/_/g, " ")}
          </div>
          {/* MTF Entry Grade */}
          <div style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem",
            background: `${gradeColor}18`, border: `1px solid ${gradeColor}40`,
            borderRadius: "0.35rem", padding: "0.2rem 0.55rem" }}>
            <span style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: "600" }}>Entry Grade:</span>
            <span style={{ fontSize: "0.9rem", fontWeight: "900", color: gradeColor }}>{grade}</span>
          </div>
          <div style={{ fontSize: "0.68rem", color: "#64748b", marginTop: "0.3rem" }}>
            {gradeLabel[grade] ?? "--"}
          </div>
        </div>
      </div>

      {/* Component Bars */}
      {data?.components && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem", marginBottom: "0.85rem" }}>
          {[
            { key: "regime",    label: "Regime",       color: "#8b5cf6" },
            { key: "ema_trend", label: "EMA Trend",    color: "#3b82f6" },
            { key: "rsi",       label: "RSI",          color: "#f59e0b" },
            { key: "sr_pos",    label: "Vị trí S/R",   color: "#10b981" },
          ].map(({ key, label, color }) => {
            const comp = data.components[key];
            if (!comp) return null;
            const pct = (comp.score ?? 50);
            return (
              <div key={key}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", marginBottom: "0.2rem" }}>
                  <span style={{ color: "#94a3b8", fontWeight: "600" }}>
                    {label} <span style={{ color: "#475569", fontSize: "0.62rem" }}>({comp.weight})</span>
                  </span>
                  <span style={{ color, fontWeight: "800" }}>
                    {comp.signal ?? comp.value ?? "--"}
                  </span>
                </div>
                <div style={{ height: "4px", background: "rgba(255,255,255,0.06)", borderRadius: "2px", overflow: "hidden" }}>
                  <div style={{ width: `${pct}%`, height: "100%", background: color,
                    borderRadius: "2px", transition: "width 0.5s ease" }} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* MTF Layers */}
      {mtf && (
        <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: "0.5rem",
          border: "1px solid rgba(255,255,255,0.06)", padding: "0.65rem" }}>
          <div style={{ fontSize: "0.68rem", fontWeight: "800", color: "#64748b", textTransform: "uppercase",
            letterSpacing: "0.5px", marginBottom: "0.5rem" }}>
            📊 Đa Khung Thời Gian
          </div>
          {[
            { label: "Dài hạn (EMA100)",   value: mtf.monthly_bias,  score: mtf.monthly_score },
            { label: "Tuần (EMA5/20)",      value: mtf.weekly_trend,  score: mtf.weekly_score  },
            { label: "Ngắn hạn (RSI/Day)", value: mtf.daily_signal,  score: mtf.daily_score   },
          ].map(({ label, value, score: s }) => {
            const c = value === "UP" || value === "BULLISH" || value === "BUY" ? "#10b981"
                    : value === "DOWN" || value === "BEARISH" || value === "SELL" ? "#ef4444"
                    : "#f59e0b";
            return (
              <div key={label} style={row}>
                <span style={{ color: "#64748b" }}>{label}</span>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ color: c, fontWeight: "800", fontSize: "0.75rem" }}>{value}</span>
                  <div style={{ width: "36px", height: "3px", background: "rgba(255,255,255,0.06)", borderRadius: "2px" }}>
                    <div style={{ width: `${s ?? 50}%`, height: "100%", background: c, borderRadius: "2px" }} />
                  </div>
                </div>
              </div>
            );
          })}
          <div style={{ fontSize: "0.67rem", color: "#475569", marginTop: "0.5rem", lineHeight: 1.4 }}>
            {mtf.description}
          </div>
        </div>
      )}
    </div>
  );
}
