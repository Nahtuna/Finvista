import React, { useState } from "react";
import { Bell, Plus, Trash2, BellOff, Check, AlertTriangle, Clock } from "lucide-react";
import { useThemeTokens } from "../../app/useThemeTokens.js";

const CONDITION_TYPES = [
  { value: "price_gte", label: "Giá ≥" },
  { value: "price_lte", label: "Giá ≤" },
  { value: "index_gte", label: "Chỉ số ≥" },
  { value: "index_lte", label: "Chỉ số ≤" },
  { value: "delta_gte", label: "Delta ≥" },
  { value: "iv_gte", label: "IV ≥" },
  { value: "pct_change", label: "Biến động %" },
];

function StatusBadge({ status }) {
  if (status === "Triggered") return <span style={{ color: "#ef4444", fontWeight: "700", display: "flex", alignItems: "center", gap: "0.3rem" }}><AlertTriangle size={12} /> Đã kích hoạt</span>;
  if (status === "Inactive") return <span style={{ color: "#64748b", display: "flex", alignItems: "center", gap: "0.3rem" }}><BellOff size={12} /> Tắt</span>;
  return <span style={{ color: "#10b981", fontWeight: "700", display: "flex", alignItems: "center", gap: "0.3rem" }}>
    <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#10b981", animation: "pulse 2s infinite" }} /> Đang quét
  </span>;
}

function ChannelToggle({ label, active, onChange }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", fontSize: "0.8rem" }}>
      <div
        onClick={() => onChange(!active)}
        style={{ width: "36px", height: "20px", background: active ? "#2563eb" : "#1e293b", borderRadius: "10px", position: "relative", cursor: "pointer", transition: "background 0.2s", border: "1px solid #334155" }}>
        <div style={{ position: "absolute", top: "2px", left: active ? "17px" : "2px", width: "14px", height: "14px", background: "#fff", borderRadius: "50%", transition: "left 0.2s" }} />
      </div>
      {label}
    </label>
  );
}

export function AlertsPage({ language = "vi", preferences = {} }) {
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const [alerts, setAlerts] = useState([
    { id: 1, symbol: "CVPB2404", condType: "price_gte", condValue: "1250", current: "1,210 đ", status: "Active", channel: ["browser"], time: "10:30:21" },
    { id: 2, symbol: "VN-Index", condType: "index_lte", condValue: "1240", current: "1,245.32", status: "Triggered", channel: ["browser", "telegram"], time: "09:45:12" },
    { id: 3, symbol: "IV Index", condType: "iv_gte", condValue: "70", current: "68.5%", status: "Active", channel: ["email"], time: "09:15:03" },
    { id: 4, symbol: "CHPG2405", condType: "delta_gte", condValue: "0.6", current: "0.56", status: "Active", channel: ["browser"], time: "08:30:00" },
  ]);

  const [symbol, setSymbol] = useState("");
  const [condType, setCondType] = useState("price_gte");
  const [condValue, setCondValue] = useState("");
  const [channels, setChannels] = useState({ browser: true, email: false, telegram: false });
  const [showForm, setShowForm] = useState(false);

  function handleAdd() {
    if (!symbol.trim() || !condValue.trim()) return;
    const ch = Object.entries(channels).filter(([, v]) => v).map(([k]) => k);
    setAlerts(prev => [...prev, {
      id: Date.now(), symbol: symbol.trim().toUpperCase(), condType, condValue,
      current: "–", status: "Active", channel: ch,
      time: new Date().toLocaleTimeString("vi-VN")
    }]);
    setSymbol(""); setCondValue(""); setShowForm(false);
  }

  function toggleStatus(id) {
    setAlerts(prev => prev.map(a => a.id === id
      ? { ...a, status: a.status === "Active" ? "Inactive" : "Active" }
      : a));
  }

  const condLabel = (type, value) => {
    const found = CONDITION_TYPES.find(c => c.value === type);
    return `${found?.label || type} ${value}`;
  };

  const activeCount = alerts.filter(a => a.status === "Active").length;
  const triggeredCount = alerts.filter(a => a.status === "Triggered").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", color: textColor, background: bg }}>

      {/* HEADER */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ fontSize: "1.3rem", fontWeight: "900", margin: 0, color: textColor }}>🔔 Alerts — Quản lý cảnh báo</h2>
            <p style={{ fontSize: "0.8rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
              Thông báo tự động qua Browser · Email · Telegram khi giá chạm ngưỡng cắt lỗ/chốt lời
            </p>
          </div>
          <button onClick={() => setShowForm(v => !v)} style={{ background: showForm ? "#1e293b" : "#2563eb", color: "#fff", border: showForm ? "1px solid #334155" : "none", padding: "0.45rem 1rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Plus size={14} /> {showForm ? "Đóng" : "Tạo cảnh báo"}
          </button>
        </div>

        {/* Stats row */}
        <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
          {[
            { label: "Tổng cảnh báo", value: alerts.length, color: textColor },
            { label: "Đang quét", value: activeCount, color: "#10b981" },
            { label: "Đã kích hoạt", value: triggeredCount, color: "#ef4444" },
            { label: "Tắt", value: alerts.length - activeCount - triggeredCount, color: mutedText },
          ].map((s, i) => (
            <div key={i} style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "0.5rem 0.85rem" }}>
              <div style={{ fontSize: "0.65rem", color: mutedText, textTransform: "uppercase" }}>{s.label}</div>
              <div style={{ fontSize: "1.1rem", fontWeight: "900", color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* FORM TẠO CẢNH BÁO */}
      {showForm && (
        <div style={{ background: cardBg, border: "1px solid rgba(37,99,235,0.4)", borderRadius: "0.75rem", padding: "1.25rem" }}>
          <h4 style={{ margin: "0 0 1rem 0", color: "#60a5fa", fontSize: "0.9rem", fontWeight: "800" }}>📋 Tạo cảnh báo mới</h4>
          <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1.5fr 1fr auto", gap: "0.75rem", alignItems: "end", marginBottom: "1rem" }}>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem" }}>Mã tài sản</label>
              <input value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="CVPB2404, VN-Index..." style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.25rem", fontSize: "0.8rem", boxSizing: "border-box" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem" }}>Loại điều kiện</label>
              <select value={condType} onChange={e => setCondType(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.25rem", fontSize: "0.8rem" }}>
                {CONDITION_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem" }}>Ngưỡng</label>
              <input value={condValue} onChange={e => setCondValue(e.target.value)} placeholder="1250" style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.25rem", fontSize: "0.8rem", boxSizing: "border-box" }} />
            </div>
            <button onClick={handleAdd} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.45rem 1rem", borderRadius: "0.25rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer" }}>
              Thêm ✓
            </button>
          </div>
          <div style={{ display: "flex", gap: "1.5rem", paddingTop: "0.75rem", borderTop: `1px solid ${borderColor}` }}>
            <span style={{ fontSize: "0.75rem", color: mutedText, fontWeight: "600" }}>Kênh thông báo:</span>
            <ChannelToggle label="🌐 Browser" active={channels.browser} onChange={v => setChannels(c => ({ ...c, browser: v }))} />
            <ChannelToggle label="📧 Email" active={channels.email} onChange={v => setChannels(c => ({ ...c, email: v }))} />
            <ChannelToggle label="✈️ Telegram" active={channels.telegram} onChange={v => setChannels(c => ({ ...c, telegram: v }))} />
          </div>
        </div>
      )}

      {/* ALERTS TABLE */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <h3 style={{ fontSize: "0.95rem", fontWeight: "800", margin: "0 0 0.75rem 0", display: "flex", alignItems: "center", gap: "0.5rem", color: textColor }}>
          <Bell size={15} style={{ color: "#f59e0b" }} /> Danh sách cảnh báo ({alerts.length})
        </h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${borderColor}` }}>
              {["Mã tài sản", "Điều kiện", "Giá trị hiện tại", "Kênh", "Trạng thái", "Cập nhật", "Hành động"].map(h => (
                <th key={h} style={{ padding: "0.5rem", color: mutedText, fontWeight: "700", fontSize: "0.72rem", textAlign: "left" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {alerts.map(a => (
              <tr key={a.id} style={{ borderBottom: `1px solid ${borderColor}` }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(37,99,235,0.04)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                <td style={{ padding: "0.65rem 0.5rem", fontWeight: "800", color: "#60a5fa" }}>{a.symbol}</td>
                <td style={{ padding: "0.65rem 0.5rem" }}>
                  <span style={{ background: subBg, border: `1px solid ${borderColor}`, color: "#f59e0b", padding: "0.2rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.72rem", fontWeight: "700" }}>
                    {condLabel(a.condType, a.condValue)}
                  </span>
                </td>
                <td style={{ padding: "0.65rem 0.5rem", fontWeight: "700", color: textColor }}>{a.current}</td>
                <td style={{ padding: "0.65rem 0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.25rem" }}>
                    {a.channel?.map(ch => (
                      <span key={ch} style={{ background: subBg, color: mutedText, border: `1px solid ${borderColor}`, padding: "0.1rem 0.35rem", borderRadius: "0.2rem", fontSize: "0.65rem", fontWeight: "700", textTransform: "uppercase" }}>{ch}</span>
                    ))}
                  </div>
                </td>
                <td style={{ padding: "0.65rem 0.5rem" }}><StatusBadge status={a.status} /></td>
                <td style={{ padding: "0.65rem 0.5rem", color: mutedText, fontSize: "0.72rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                  <Clock size={11} /> {a.time}
                </td>
                <td style={{ padding: "0.65rem 0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.3rem" }}>
                    <button onClick={() => toggleStatus(a.id)}
                      style={{ background: a.status === "Active" ? "rgba(245,158,11,0.1)" : "rgba(16,185,129,0.1)", color: a.status === "Active" ? "#f59e0b" : "#10b981", border: `1px solid ${a.status === "Active" ? "rgba(245,158,11,0.3)" : "rgba(16,185,129,0.3)"}`, padding: "0.2rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.7rem", fontWeight: "700", cursor: "pointer" }}>
                      {a.status === "Active" ? "Tắt" : "Bật"}
                    </button>
                    <button onClick={() => setAlerts(prev => prev.filter(x => x.id !== a.id))}
                      style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)", padding: "0.2rem 0.45rem", borderRadius: "0.25rem", fontSize: "0.7rem", cursor: "pointer" }}>
                      <Trash2 size={11} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
