import React, { useState } from "react";

/**
 * PositionSizingWidget — Workflow #8
 * Tính toán khối lượng vị thế dựa vào:
 *   - Tổng vốn tài khoản (VND)
 *   - % Rủi ro tối đa mỗi lệnh
 *   - Giá entry và giá cắt lỗ (Stop Loss)
 */
export function PositionSizingWidget({ entryPrice = null, symbol = "", language, preferences = {} }) {
  const isEnglish = language === "en";

  const [account,  setAccount]  = useState(500000000); // 500tr VND
  const [riskPct,  setRiskPct]  = useState(2);         // 2%
  const [entry,    setEntry]    = useState(entryPrice ?? 0);
  const [stopLoss, setStopLoss] = useState(0);

  const riskAmount   = account * (riskPct / 100);
  const stopDist     = entry > 0 && stopLoss > 0 && stopLoss < entry ? entry - stopLoss : 0;
  const stopDistPct  = entry > 0 && stopDist > 0 ? (stopDist / entry * 100) : 0;
  const shares       = stopDist > 0 ? Math.floor(riskAmount / stopDist / 100) * 100 : 0; // round to 100
  const positionSize = shares * entry;
  const positionPct  = account > 0 ? (positionSize / account * 100) : 0;
  const rewardTarget = entry > 0 && stopDist > 0 ? entry + stopDist * 3 : 0; // RR 1:3 default

  const fmt = v => v >= 1e9 ? `${(v/1e9).toFixed(1)} tỷ` : v >= 1e6 ? `${(v/1e6).toFixed(0)} tr` : v.toLocaleString("vi");
  const fmtNum = v => v.toLocaleString("vi");

  const card = {
    background: "#131b2e", borderRadius: "0.75rem",
    border: "1px solid rgba(37,99,235,0.2)", padding: "1rem",
  };
  const input = {
    width: "100%", background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)", borderRadius: "0.35rem",
    color: "#f1f5f9", padding: "0.4rem 0.6rem", fontSize: "0.8rem",
    outline: "none", boxSizing: "border-box",
  };
  const label = { fontSize: "0.7rem", color: "#64748b", fontWeight: "600", marginBottom: "0.2rem", display: "block" };
  const resultRow = { display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "0.42rem 0", borderBottom: "1px solid rgba(255,255,255,0.04)", fontSize: "0.8rem" };

  const isValid = shares > 0 && positionSize > 0;

  return (
    <div style={card}>
      <div style={{ fontSize: "0.8rem", fontWeight: "800", color: "#94a3b8",
        textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "0.85rem" }}>
        ⚖️ {isEnglish ? "Position Sizing" : "Tính Khối Lượng Vị Thế"}
        {symbol && <span style={{ color: "#3b82f6", marginLeft: "0.4rem" }}>· {symbol}</span>}
      </div>

      {/* Inputs */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem", marginBottom: "0.85rem" }}>
        <div>
          <label style={label}>💰 Tổng vốn (VND)</label>
          <input
            type="number" style={input} value={account}
            onChange={e => setAccount(Number(e.target.value))}
            step={10000000}
          />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
          <div>
            <label style={label}>⚠️ Rủi ro / lệnh (%)</label>
            <input type="number" style={input} value={riskPct}
              onChange={e => setRiskPct(Math.min(10, Math.max(0.1, Number(e.target.value))))}
              step={0.5} min={0.5} max={10} />
          </div>
          <div>
            <label style={label}>📈 Giá mua (Entry)</label>
            <input type="number" style={input} value={entry}
              onChange={e => setEntry(Number(e.target.value))}
              step={100} />
          </div>
        </div>
        <div>
          <label style={label}>
            🛑 Giá cắt lỗ (Stop Loss)
            {entry > 0 && stopLoss > 0 && stopLoss < entry && (
              <span style={{ color: "#ef4444", marginLeft: "0.4rem" }}>
                ({stopDistPct.toFixed(1)}% từ entry)
              </span>
            )}
          </label>
          <input type="number" style={{ ...input, borderColor: stopLoss > 0 && stopLoss >= entry ? "#ef4444" : "rgba(255,255,255,0.1)" }}
            value={stopLoss}
            onChange={e => setStopLoss(Number(e.target.value))}
            step={100} />
          {stopLoss > 0 && stopLoss >= entry && (
            <div style={{ fontSize: "0.65rem", color: "#ef4444", marginTop: "0.2rem" }}>
              Stop Loss phải nhỏ hơn giá mua
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: "0.5rem",
        border: "1px solid rgba(255,255,255,0.06)",
        padding: "0.65rem" }}>
        <div style={{ fontSize: "0.68rem", fontWeight: "800", color: "#64748b",
          textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "0.5rem" }}>
          Kết quả tính toán
        </div>

        {!isValid ? (
          <div style={{ textAlign: "center", color: "#475569", fontSize: "0.75rem", padding: "0.5rem 0" }}>
            Nhập giá entry và stop loss hợp lệ để tính
          </div>
        ) : (
          <>
            <div style={resultRow}>
              <span style={{ color: "#64748b" }}>Số tiền rủi ro</span>
              <span style={{ color: "#ef4444", fontWeight: "800" }}>{fmt(riskAmount)}</span>
            </div>
            <div style={resultRow}>
              <span style={{ color: "#64748b" }}>Khoảng cắt lỗ</span>
              <span style={{ color: "#f59e0b", fontWeight: "800" }}>
                {fmtNum(stopDist)} đ ({stopDistPct.toFixed(1)}%)
              </span>
            </div>
            <div style={{ ...resultRow, borderBottom: "none", paddingTop: "0.6rem" }}>
              <span style={{ color: "#94a3b8", fontWeight: "700" }}>📦 Số lượng CP</span>
              <span style={{ color: "#10b981", fontWeight: "900", fontSize: "1.1rem" }}>
                {fmtNum(shares)} CP
              </span>
            </div>
            <div style={resultRow}>
              <span style={{ color: "#64748b" }}>Giá trị vị thế</span>
              <span style={{ color: "#f1f5f9", fontWeight: "800" }}>
                {fmt(positionSize)} ({positionPct.toFixed(1)}% vốn)
              </span>
            </div>
            <div style={{ ...resultRow, borderBottom: "none" }}>
              <span style={{ color: "#64748b" }}>🎯 Target (RR 1:3)</span>
              <span style={{ color: "#10b981", fontWeight: "800" }}>
                {fmtNum(Math.round(rewardTarget))} đ
              </span>
            </div>

            {/* Risk bar */}
            <div style={{ marginTop: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem",
                color: "#475569", marginBottom: "0.25rem" }}>
                <span>Tỷ trọng danh mục</span>
                <span style={{ color: positionPct > 30 ? "#ef4444" : positionPct > 20 ? "#f59e0b" : "#10b981" }}>
                  {positionPct.toFixed(1)}%
                  {positionPct > 30 && " ⚠️ Quá nhiều!"}
                </span>
              </div>
              <div style={{ height: "6px", background: "rgba(255,255,255,0.06)", borderRadius: "3px", overflow: "hidden" }}>
                <div style={{
                  width: `${Math.min(100, positionPct)}%`, height: "100%", borderRadius: "3px",
                  background: positionPct > 30 ? "#ef4444" : positionPct > 20 ? "#f59e0b" : "#10b981",
                  transition: "width 0.4s ease"
                }} />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Quick RR presets */}
      <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.65rem" }}>
        {[1, 2, 3].map(p => (
          <button key={p} onClick={() => setRiskPct(p)} style={{
            flex: 1, padding: "0.3rem", fontSize: "0.68rem", fontWeight: "700",
            border: riskPct === p ? "1px solid rgba(37,99,235,0.4)" : "1px solid rgba(255,255,255,0.1)",
            background: riskPct === p ? "rgba(37,99,235,0.2)" : "transparent",
            borderRadius: "0.3rem", color: riskPct === p ? "#60a5fa" : "#64748b", cursor: "pointer"
          }}>
            R {p}%
          </button>
        ))}
      </div>
    </div>
  );
}
