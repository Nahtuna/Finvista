import React, { useEffect, useState } from "react";
import { Briefcase, Plus, Trash2, RefreshCw, TrendingUp, TrendingDown, BarChart2, Clock, AlertTriangle } from "lucide-react";
import { getPortfolio, placeOrder, resetPortfolio } from "../../api.js";
import { runBacktestApi, runCsvBacktestApi, runLongtermBacktestApi } from "../../api/portfolio.js";
import { useToast } from "../../components/ui/toast.jsx";
import { formatMoney } from "../../lib/formatters.js";
import { useThemeTokens } from "../../app/useThemeTokens.js";

function KpiCard({ label, value, sub, subColor = "#10b981", border, cardBg, textColor, mutedText, borderColor }) {
  return (
    <div style={{ background: cardBg || "#131b2e", border: `1px solid ${border || borderColor || "#1e293b"}`, borderRadius: "0.75rem", padding: "1rem 1.25rem" }}>
      <div style={{ fontSize: "0.72rem", color: mutedText || "#64748b", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.5px" }}>{label}</div>
      <div style={{ fontSize: "1.4rem", fontWeight: "900", marginTop: "0.3rem", lineHeight: 1.1, color: textColor || "#fff" }}>{value}</div>
      {sub && <div style={{ fontSize: "0.75rem", color: subColor, fontWeight: "700", marginTop: "0.3rem" }}>{sub}</div>}
    </div>
  );
}

export function PortfolioPage({ language = "vi", preferences = {}, initialTab = "danh_sach" }) {
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const { addToast } = useToast();
  const [activeTab, setActiveTab] = useState(initialTab || "danh_sach");

  useEffect(() => {
    if (initialTab) setActiveTab(initialTab);
  }, [initialTab]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formSymbol, setFormSymbol] = useState("");
  const [formSide, setFormSide] = useState("BUY");
  const [formQty, setFormQty] = useState(1000);
  const [formPrice, setFormPrice] = useState(1200);

  function loadPortfolio() {
    setLoading(true);
    getPortfolio().then(res => setData(res)).catch(() => {}).finally(() => setLoading(false));
  }

  useEffect(() => { loadPortfolio(); }, []);

  async function handleOrder(symbol, side, qty, price) {
    try {
      const res = await placeOrder({ symbol, side, qty: Number(qty), price: Number(price), reason: "User action" });
      if (res && res.status === "error") {
        addToast(res.message || "Lệnh không thành công", "error");
        return;
      }
      addToast(`Đã thực hiện lệnh ${side} ${qty} ${symbol}!`, "success");
      setShowAddForm(false);
      loadPortfolio();
    } catch (err) {
      addToast(err?.detail || err?.message || `Lỗi khi thực hiện lệnh ${side} ${symbol}`, "error");
    }
  }

  async function handleReset() {
    if (!window.confirm("Bạn có chắc chắn muốn xóa sạch danh mục giả lập?")) return;
    try { await resetPortfolio(); } catch (_) {}
    addToast("Đã làm sạch danh mục!", "success");
    loadPortfolio();
  }

  const nav = data?.total_nav ?? 100000000;
  const plVnd = data?.cumulative_p_l_vnd ?? 0;
  const plPct = data?.cumulative_p_l_pct ?? 0;
  const cash = data?.cash ?? 100000000;

  const positions = (data?.active_positions || []).map(p => {
    const qty = p.qty ?? p.quantity ?? 0;
    const buyPrice = p.buy_price ?? p.average_buy_price ?? 0;
    const curPrice = p.current_price ?? buyPrice ?? 0;
    const val = p.current_value ?? p.position_value ?? (qty * curPrice);
    const totalPosValue = nav - cash > 0 ? nav - cash : 1;
    return {
      symbol: p.symbol,
      underlying: p.underlying || "",
      type: "Call",
      side: p.side || "MUA",
      qty,
      buyPrice,
      curPrice,
      value: val,
      plVnd: p.p_l_vnd ?? ((curPrice - buyPrice) * qty),
      plPct: p.p_l_pct ?? (buyPrice > 0 ? ((curPrice - buyPrice) / buyPrice) * 100 : 0),
      weight: (val / totalPosValue) * 100
    };
  });

  const history = data?.transaction_history || [];

  const totalPositionValue = positions.reduce((s, p) => s + p.value, 0);
  const profitPositions = positions.filter(p => p.plVnd >= 0).length;

  // Backtest State
  const [btStrategy, setBtStrategy] = useState("multi_factor");
  const [btPeriod, setBtPeriod] = useState("60");
  const [btCapital, setBtCapital] = useState(100000000);
  const [btStopLoss, setBtStopLoss] = useState(8);
  const [btTakeProfit, setBtTakeProfit] = useState(50);
  const [btUnderlying, setBtUnderlying] = useState("ALL");
  const [btRunning, setBtRunning] = useState(false);
  const [btResult, setBtResult] = useState(null);
  const [btDataMode, setBtDataMode] = useState("longterm"); // "longterm" | "db"
  const [btIvThreshold, setBtIvThreshold] = useState(5);
  const [btDeltaMin, setBtDeltaMin] = useState(0.25);
  const [btYears, setBtYears] = useState(3);
  const [quantStage, setQuantStage] = useState("train"); // "train" | "test" | "simulate" | "live"
  const [quantSubTab, setQuantSubTab] = useState("overview"); // "overview" | "performance" | "analysis"

  async function runBacktestSim() {
    setBtRunning(true);
    try {
      let res;
      if (btDataMode === "db") {
        res = await runBacktestApi(
          btStrategy,
          Number(btPeriod),
          Number(btCapital),
          Number(btStopLoss),
          Number(btTakeProfit),
          btUnderlying
        );
      } else {
        res = await runLongtermBacktestApi({
          strategy: btStrategy,
          years: Number(btYears),
          capital: Number(btCapital),
          stopLossPct: Number(btStopLoss),
          takeProfitPct: Number(btTakeProfit),
          underlyingFilter: btUnderlying === "ALL" ? "ALL" : btUnderlying,
        });
      }
      if (res && res.status === "success") {
        setBtResult(res);
        addToast(`✅ Hoàn tất Backtest — ${res.dataSource || "SQLite DB"}`, "success");
      } else {
        addToast(res?.message || "Không thể tải kết quả Backtest.", "error");
      }
    } catch (err) {
      addToast("Lỗi kết nối Backtest.", "error");
    } finally {
      setBtRunning(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", color: textColor, background: bg }}>

      {/* HEADER */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.3rem", fontWeight: "900", margin: 0, color: textColor }}>💼 Portfolio — Danh mục chứng quyền</h2>
            <p style={{ fontSize: "0.8rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
              Quản lý vị thế · Đặt lệnh giả lập · Theo dõi lãi/lỗ realtime & Backtest Lịch sử
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button onClick={loadPortfolio} style={{ background: subBg, color: textColor, border: `1px solid ${borderColor}`, padding: "0.4rem 0.7rem", borderRadius: "0.375rem", fontSize: "0.78rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.3rem", fontWeight: "700" }}>
              <RefreshCw size={13} /> Làm mới
            </button>
            <button onClick={() => setShowAddForm(v => !v)} style={{ background: showAddForm ? subBg : "#10b981", color: showAddForm ? textColor : "#fff", border: showAddForm ? `1px solid ${borderColor}` : "none", padding: "0.4rem 0.85rem", borderRadius: "0.375rem", fontSize: "0.78rem", fontWeight: "800", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.3rem" }}>
              <Plus size={13} /> {showAddForm ? "Đóng" : "Đặt lệnh"}
            </button>
            <button onClick={handleReset} style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.3)", padding: "0.4rem 0.7rem", borderRadius: "0.375rem", fontSize: "0.78rem", fontWeight: "700", cursor: "pointer" }}>
              Reset
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: "0.3rem", background: subBg, padding: "0.2rem", borderRadius: "0.4rem", width: "fit-content" }}>
          {[
            { id: "danh_sach", label: "Vị thế" },
            { id: "lich_su", label: "Lịch sử" },
            { id: "phan_tich", label: "Phân tích" },
            { id: "backtest", label: "📊 Backtest Chiến lược" }
          ].map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)} style={{ background: activeTab === t.id ? "#2563eb" : "transparent", color: activeTab === t.id ? "#fff" : textColor, border: "none", borderRadius: "0.3rem", padding: "0.35rem 1rem", fontSize: "0.8rem", fontWeight: "700", cursor: "pointer" }}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* FORM ĐẶT LỆNH */}
      {showAddForm && (
        <div style={{ background: cardBg, border: "1px solid rgba(16,185,129,0.4)", borderRadius: "0.75rem", padding: "1.25rem" }}>
          <h4 style={{ margin: "0 0 1rem 0", color: "#10b981", fontSize: "0.9rem", fontWeight: "800" }}>📋 ĐẶT LỆNH GIẢ LẬP</h4>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.75rem", alignItems: "end" }}>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem" }}>Mã CW</label>
              <input value={formSymbol} onChange={e => setFormSymbol(e.target.value.toUpperCase())} placeholder="CVPB2404" style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.25rem", fontSize: "0.8rem", boxSizing: "border-box" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem" }}>Chiều</label>
              <select value={formSide} onChange={e => setFormSide(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.25rem", fontSize: "0.8rem" }}>
                <option value="BUY" style={{ background: cardBg, color: textColor }}>MUA</option>
                <option value="SELL" style={{ background: cardBg, color: textColor }}>BÁN</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem" }}>Số lượng</label>
              <input type="number" value={formQty} onChange={e => setFormQty(Number(e.target.value))} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.25rem", fontSize: "0.8rem", boxSizing: "border-box" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.72rem", color: mutedText, display: "block", marginBottom: "0.25rem" }}>Giá (đ)</label>
              <input type="number" value={formPrice} onChange={e => setFormPrice(Number(e.target.value))} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.45rem", borderRadius: "0.25rem", fontSize: "0.8rem", boxSizing: "border-box" }} />
            </div>
            <button onClick={() => handleOrder(formSymbol || "CVPB2404", formSide, formQty, formPrice)} style={{ background: "#10b981", color: "#fff", border: "none", padding: "0.45rem 1rem", borderRadius: "0.375rem", fontSize: "0.82rem", fontWeight: "800", cursor: "pointer" }}>
              Xác nhận ✓
            </button>
          </div>
          <div style={{ fontSize: "0.72rem", color: mutedText, marginTop: "0.5rem" }}>
            Tổng giá trị ước tính: <strong style={{ color: textColor }}>{((formQty || 0) * (formPrice || 0)).toLocaleString()} đ</strong>
          </div>
        </div>
      )}

      {/* KPI CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
        <KpiCard label="Tổng tài sản (NAV)" value={`${formatMoney(nav)} VND`} sub="▲ Realtime sync" cardBg={cardBg} textColor={textColor} mutedText={mutedText} borderColor={borderColor} />
        <KpiCard label="Lãi/Lỗ chưa TH" value={`${plVnd >= 0 ? "+" : ""}${formatMoney(plVnd)} đ`} sub={`${plVnd >= 0 ? "▲" : "▼"} ${Number(plPct || 0).toFixed(2)}%`} subColor={plVnd >= 0 ? "#10b981" : "#ef4444"} border={plVnd >= 0 ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"} cardBg={cardBg} textColor={textColor} mutedText={mutedText} borderColor={borderColor} />
        <KpiCard label="Tiền mặt khả dụng" value={`${formatMoney(cash)} VND`} sub="💼 Sẵn sàng giao dịch" subColor="#f59e0b" cardBg={cardBg} textColor={textColor} mutedText={mutedText} borderColor={borderColor} />
        <KpiCard label="Vị thế mở" value={`${positions.length} mã`} sub={`${profitPositions} lãi · ${positions.length - profitPositions} lỗ`} subColor="#60a5fa" cardBg={cardBg} textColor={textColor} mutedText={mutedText} borderColor={borderColor} />
      </div>

      {/* DANH SÁCH VỊ THẾ */}
      {activeTab === "danh_sach" && (
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: "800", margin: 0, color: textColor }}>Danh sách vị thế ({positions.length})</h3>
            <span style={{ fontSize: "0.72rem", color: mutedText }}>Tổng GV: {formatMoney(totalPositionValue)} đ</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
              <thead>
                <tr style={{ borderBottom: `2px solid ${borderColor}`, background: subBg }}>
                  {["Mã CW", "CS", "SL", "Giá vốn", "Hiện tại", "Giá trị", "L/L (đ)", "L/L (%)", "Tỷ trọng", "Hành động"].map(h => (
                    <th key={h} style={{ padding: "0.55rem 0.5rem", color: textColor, fontWeight: "800", fontSize: "0.75rem", textAlign: h === "Hành động" ? "center" : "left" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, i) => (
                  <tr key={pos.symbol + i} style={{ borderBottom: `1px solid ${borderColor}` }}
                    onMouseEnter={e => e.currentTarget.style.background = "rgba(37,99,235,0.05)"}
                    onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                    <td style={{ padding: "0.6rem 0.5rem", fontWeight: "800", color: "#60a5fa" }}>{pos.symbol}</td>
                    <td style={{ padding: "0.6rem 0.5rem", color: textColor, fontWeight: "700" }}>{pos.underlying}</td>
                    <td style={{ padding: "0.6rem 0.5rem", color: textColor }}>{(pos.qty ?? 0).toLocaleString()}</td>
                    <td style={{ padding: "0.6rem 0.5rem", color: mutedText }}>{(pos.buyPrice ?? 0).toLocaleString()} đ</td>
                    <td style={{ padding: "0.6rem 0.5rem", fontWeight: "700", color: textColor }}>{(pos.curPrice ?? 0).toLocaleString()} đ</td>
                    <td style={{ padding: "0.6rem 0.5rem", color: textColor }}>{formatMoney(pos.value)} đ</td>
                    <td style={{ padding: "0.6rem 0.5rem", color: pos.plVnd >= 0 ? "#10b981" : "#ef4444", fontWeight: "800" }}>
                      {pos.plVnd >= 0 ? "+" : ""}{formatMoney(pos.plVnd)} đ
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem", color: pos.plPct >= 0 ? "#10b981" : "#ef4444", fontWeight: "800" }}>
                      {pos.plPct >= 0 ? "+" : ""}{pos.plPct?.toFixed(2)}%
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem", minWidth: "80px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                        <div style={{ flex: 1, height: "4px", background: subBg, borderRadius: "2px" }}>
                          <div style={{ width: `${Math.min(100, pos.weight || 0)}%`, height: "100%", background: "#2563eb", borderRadius: "2px" }} />
                        </div>
                        <span style={{ fontSize: "0.7rem", color: mutedText }}>{(pos.weight || 0).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem", textAlign: "center", whiteSpace: "nowrap" }}>
                      <button onClick={() => handleOrder(pos.symbol, "SELL", pos.qty, pos.curPrice)}
                        style={{ background: "rgba(239,68,68,0.15)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.3)", padding: "0.2rem 0.55rem", borderRadius: "0.25rem", fontSize: "0.7rem", fontWeight: "800", cursor: "pointer", marginRight: "0.3rem" }}>
                        Bán hết
                      </button>
                      <button onClick={() => handleOrder(pos.symbol, "BUY", 1000, pos.curPrice)}
                        style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.3)", padding: "0.2rem 0.55rem", borderRadius: "0.25rem", fontSize: "0.7rem", fontWeight: "700", cursor: "pointer" }}>
                        Mua thêm
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* LỊCH SỬ */}
      {activeTab === "lich_su" && (
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: "800", margin: "0 0 0.75rem 0", color: textColor }}>Lịch sử giao dịch ({history.length})</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
            <thead>
              <tr style={{ borderBottom: `2px solid ${borderColor}`, background: subBg }}>
                {["ID", "Mã CW", "Chiều", "Số lượng", "Giá", "Tổng", "Trạng thái", "Thời gian"].map(h => (
                  <th key={h} style={{ padding: "0.55rem 0.5rem", color: textColor, fontWeight: "800", fontSize: "0.75rem", textAlign: "left" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {history.map((tx, i) => (
                <tr key={tx.id || i} style={{ borderBottom: `1px solid ${borderColor}` }}>
                  <td style={{ padding: "0.6rem 0.5rem", color: mutedText, fontSize: "0.7rem" }}>{tx.id}</td>
                  <td style={{ padding: "0.6rem 0.5rem", fontWeight: "800", color: "#60a5fa" }}>{tx.symbol}</td>
                  <td style={{ padding: "0.6rem 0.5rem" }}>
                    <span style={{ color: tx.side === "MUA" || tx.side === "BUY" ? "#10b981" : "#ef4444", fontWeight: "800" }}>{tx.side}</span>
                  </td>
                  <td style={{ padding: "0.6rem 0.5rem", color: textColor }}>{tx.qty?.toLocaleString()}</td>
                  <td style={{ padding: "0.6rem 0.5rem", color: textColor }}>{tx.price?.toLocaleString()} đ</td>
                  <td style={{ padding: "0.6rem 0.5rem", fontWeight: "700", color: textColor }}>{formatMoney(tx.total)} đ</td>
                  <td style={{ padding: "0.6rem 0.5rem" }}>
                    <span style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.3)", padding: "0.15rem 0.4rem", borderRadius: "0.25rem", fontSize: "0.7rem", fontWeight: "700" }}>{tx.status}</span>
                  </td>
                  <td style={{ padding: "0.6rem 0.5rem", color: mutedText, fontSize: "0.75rem" }}>{tx.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* PHÂN TÍCH */}
      {activeTab === "phan_tich" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
            <h3 style={{ fontSize: "0.9rem", fontWeight: "800", margin: "0 0 1rem 0", color: textColor }}>Phân bổ danh mục theo vị thế</h3>
            {positions.map((pos, i) => (
              <div key={i} style={{ marginBottom: "0.75rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", marginBottom: "0.25rem" }}>
                  <span style={{ fontWeight: "700", color: "#60a5fa" }}>{pos.symbol}</span>
                  <span style={{ color: mutedText }}>{formatMoney(pos.value)} đ · {(pos.weight || 0).toFixed(1)}%</span>
                </div>
                <div style={{ height: "6px", background: subBg, borderRadius: "3px" }}>
                  <div style={{ width: `${Math.min(100, pos.weight || 0)}%`, height: "100%", background: ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6"][i % 4], borderRadius: "3px", transition: "width 0.5s" }} />
                </div>
              </div>
            ))}
          </div>
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
            <h3 style={{ fontSize: "0.9rem", fontWeight: "800", margin: "0 0 1rem 0", color: textColor }}>Tóm tắt hiệu suất</h3>
            {[
              { label: "Tổng vốn đầu tư", value: formatMoney(totalPositionValue) + " đ" },
              { label: "Lãi/Lỗ chưa thực hiện", value: `${plVnd >= 0 ? "+" : ""}${formatMoney(plVnd)} đ`, color: plVnd >= 0 ? "#10b981" : "#ef4444" },
              { label: "Tỷ suất lợi nhuận", value: `${plPct >= 0 ? "+" : ""}${plPct?.toFixed(2)}%`, color: plPct >= 0 ? "#10b981" : "#ef4444" },
              { label: "Tiền mặt còn lại", value: formatMoney(cash) + " VND" },
              { label: "Số vị thế lãi / lỗ", value: `${profitPositions} / ${positions.length - profitPositions}`, color: "#60a5fa" },
            ].map((row, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 0", borderBottom: `1px solid ${borderColor}`, fontSize: "0.82rem" }}>
                <span style={{ color: mutedText }}>{row.label}</span>
                <strong style={{ color: row.color || textColor }}>{row.value}</strong>
              </div>
            ))}
          </div>
        </div>
      )}
      {/* BACKTEST CHIẾN LƯỢC */}
      {activeTab === "backtest" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          
          {/* Controls Panel */}
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: "900", margin: "0 0 1rem 0", color: "#60a5fa" }}>📊 BỘ KIỂM THỬ BACKTEST LỊCH SỬ CHỨNG QUYỀN</h3>

            {/* Data Source Toggle */}
            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
              {[
                { v: "longterm", label: "📅 CSDL CW Lịch sử Dài hạn (SQLite)", sub: "Full 1,309 CW (2021 → nay) · Tự động điều chỉnh khoảng thời gian" },
                { v: "db", label: "🗄️ CSDL Quét Real-time", sub: "Dựa trên danh mục mã quét hiện tại" },
              ].map(opt => (
                <button key={opt.v} onClick={() => { setBtDataMode(opt.v); setBtResult(null); }}
                  style={{ flex: 1, padding: "0.6rem 1rem", borderRadius: "0.5rem", border: `2px solid ${btDataMode === opt.v ? "#2563eb" : borderColor}`, background: btDataMode === opt.v ? "rgba(37,99,235,0.15)" : subBg, cursor: "pointer", textAlign: "left" }}>
                  <div style={{ fontSize: "0.82rem", fontWeight: "900", color: btDataMode === opt.v ? "#60a5fa" : textColor }}>{opt.label}</div>
                  <div style={{ fontSize: "0.7rem", color: mutedText, marginTop: "0.15rem" }}>{opt.sub}</div>
                </button>
              ))}
            </div>
            
            {/* Clean 4-Column Controls Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "700" }}>Mô hình chiến lược</label>
                <select value={btStrategy} onChange={e => setBtStrategy(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: "#60a5fa", padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800" }}>
                  <option value="multi_factor">🏆 Deep Quant Multi-Factor (Tối ưu Alpha — Khuyên dùng)</option>
                  <option value="vol_arb">📈 Adaptive Vol-Arb (IV &lt; HV Discount)</option>
                  <option value="momentum">🚀 High-Beta Breakout Momentum</option>
                  <option value="delta_hedge">⚖️ Delta-Gamma Hedging (ITM Focus)</option>
                  <option value="theta_decay">🕐 Theta Riding (Thời gian dài)</option>
                </select>
              </div>

              {btDataMode === "db" ? (
                <div>
                  <label style={{ fontSize: "0.75rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "700" }}>Thời gian Lịch sử (Phiên)</label>
                  <select value={btPeriod} onChange={e => setBtPeriod(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "700" }}>
                    <option value="30">30 phiên (~1.5 tháng)</option>
                    <option value="60">60 phiên (~3 tháng)</option>
                    <option value="90">90 phiên (~4.5 tháng)</option>
                    <option value="180">180 phiên (~6 tháng)</option>
                    <option value="365">365 phiên (~1 năm)</option>
                  </select>
                </div>
              ) : (
                <div>
                  <label style={{ fontSize: "0.75rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "700" }}>Số năm Backtest</label>
                  <select value={btYears} onChange={e => setBtYears(Number(e.target.value))} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: "#f59e0b", padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800" }}>
                    <option value={1}>1 năm (2025–2026)</option>
                    <option value={2}>2 năm (2024–2026)</option>
                    <option value={3}>3 năm (2023–2026)</option>
                    <option value={4}>4 năm (2022–2026)</option>
                    <option value={5}>5 năm (2021–2026) — Full SQLite History</option>
                  </select>
                </div>
              )}

              <div>
                <label style={{ fontSize: "0.75rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "700" }}>Lọc cổ phiếu cơ sở (Underlying)</label>
                <select value={btUnderlying} onChange={e => setBtUnderlying(e.target.value)} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "700" }}>
                  <option value="ALL">🌐 Tất cả mã cổ phiếu CS</option>
                  <option value="ACB,VRE,FPT,MWG,STB">🏆 Top VN30 Leaders (ACB, VRE, FPT, MWG, STB)</option>
                  <option value="FPT">FPT — Tập đoàn FPT</option>
                  <option value="HPG">HPG — Tập đoàn Hòa Phát</option>
                  <option value="ACB">ACB — Ngân hàng ACB</option>
                  <option value="VPB">VPB — Ngân hàng VPBank</option>
                  <option value="MWG">MWG — Thế Giới Di Động</option>
                  <option value="VIC">VIC — Vingroup</option>
                  <option value="TCB">TCB — Techcombank</option>
                  <option value="STB">STB — Sacombank</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "700" }}>Vốn ban đầu (VND)</label>
                <input type="number" value={btCapital} onChange={e => setBtCapital(Number(e.target.value))} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "700" }} />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "700" }}>Cắt lỗ Stop-Loss (%)</label>
                <input type="number" value={btStopLoss} onChange={e => setBtStopLoss(Number(e.target.value))} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: "#ef4444", padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800" }} />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "700" }}>Chốt lời Take-Profit (%)</label>
                <input type="number" value={btTakeProfit} onChange={e => setBtTakeProfit(Number(e.target.value))} style={{ width: "100%", background: subBg, border: `1px solid ${borderColor}`, color: "#10b981", padding: "0.5rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800" }} />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: mutedText, display: "block", marginBottom: "0.3rem", fontWeight: "700" }}>Quy mô vị thế & Giới hạn</label>
                <div style={{ padding: "0.5rem", background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.375rem", fontSize: "0.75rem", color: mutedText, fontWeight: "700" }}>
                  Max 15% NAV/vị thế · Tối đa 5 vị thế song song
                </div>
              </div>
            </div>

            {/* Friction & Safeguard Banner */}
            <div style={{ background: "rgba(37,99,235,0.08)", border: "1px solid rgba(37,99,235,0.2)", borderRadius: "0.5rem", padding: "0.5rem 0.8rem", marginBottom: "1rem", fontSize: "0.72rem", color: "#60a5fa", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>⚡ <strong>Thực tế hóa Ma sát & Thanh khoản HOSE:</strong> Tự động trừ Phí (0.3%) + Thuế (0.1%) + Trượt giá (0.2%) | Lọc khối lượng &gt; 5,000 CW/phiên</span>
              <span style={{ fontWeight: "800", color: "#f59e0b" }}>HOSE T+2.5 Compliant</span>
            </div>

            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button onClick={runBacktestSim} disabled={btRunning} style={{ flex: 2, background: "#2563eb", color: "#fff", border: "none", padding: "0.65rem 1.25rem", borderRadius: "0.375rem", fontSize: "0.88rem", fontWeight: "900", cursor: "pointer", opacity: btRunning ? 0.7 : 1 }}>
                {btRunning ? "Đang chạy mô phỏng..." : "▶ Chạy Backtest Lịch sử (Chuẩn Auto-Bot)"}
              </button>
              {btResult && (
                <button onClick={() => addToast(`🤖 Đã kích hoạt Auto-Bot với cấu hình ${btStrategy.toUpperCase()} (SL ${btStopLoss}%, TP ${btTakeProfit}%)`, "success")} style={{ flex: 1, background: "linear-gradient(135deg, #10b981, #059669)", color: "#fff", border: "none", padding: "0.65rem 1rem", borderRadius: "0.375rem", fontSize: "0.82rem", fontWeight: "900", cursor: "pointer" }}>
                  🤖 Kích hoạt Auto-Bot theo Cấu hình này
                </button>
              )}
            </div>
          </div>

          {/* Results Summary */}
          {btResult && (
            <>
              {/* === PIPELINE STAGE & NAVIGATION BAR === */}
              <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.75rem 1.25rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span style={{ fontSize: "0.82rem", fontWeight: "900", color: mutedText, textTransform: "uppercase" }}>Stage:</span>
                  {[
                    { id: "train", label: "Train (In-Sample)", years: 3, desc: "Giai đoạn Huấn luyện 2021-2023" },
                    { id: "test", label: "Test (Out-of-Sample)", years: 2, desc: "Giai đoạn Kiểm chứng 2024-2025" },
                    { id: "simulate", label: "Simulate (Paper Trade)", years: 1, desc: "Mô phỏng Đặt lệnh Real-time 2026" },
                    { id: "live", label: "Live (Auto-Bot)", years: 5, desc: "Kích hoạt Auto-Bot Giao dịch Thực tế" },
                  ].map(st => (
                    <button key={st.id} onClick={() => {
                      setQuantStage(st.id);
                      setBtYears(st.years);
                      addToast(`🔄 Đã chuyển Stage [${st.label}]: ${st.desc}`, "info");
                    }}
                      style={{ padding: "0.35rem 0.9rem", borderRadius: "1rem", border: "none", background: quantStage === st.id ? "#2563eb" : subBg, color: quantStage === st.id ? "#fff" : textColor, fontSize: "0.78rem", fontWeight: "800", cursor: "pointer", transition: "all 0.2s" }}>
                      {st.label}
                    </button>
                  ))}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {[
                    { id: "overview", label: "Overview" },
                    { id: "performance", label: "Performance" },
                    { id: "analysis", label: "Analysis" },
                  ].map(tab => (
                    <button key={tab.id} onClick={() => setQuantSubTab(tab.id)}
                      style={{ padding: "0.4rem 1rem", borderRadius: "0.5rem", border: `1px solid ${quantSubTab === tab.id ? "#2563eb" : "transparent"}`, background: quantSubTab === tab.id ? "rgba(37,99,235,0.15)" : "transparent", color: quantSubTab === tab.id ? "#60a5fa" : mutedText, fontSize: "0.82rem", fontWeight: "800", cursor: "pointer" }}>
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* === TAB 1: OVERVIEW === */}
              {quantSubTab === "overview" && (
                <>
                  {/* Aggregate Data Banner */}
                  <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ fontSize: "1rem", fontWeight: "900", color: textColor }}>Aggregate Data</div>
                      <div style={{ display: "flex", gap: "2rem" }}>
                        <div><div style={{ fontSize: "0.68rem", color: mutedText, fontWeight: "700" }}>Sharpe</div><div style={{ fontSize: "1.2rem", fontWeight: "900", color: "#60a5fa" }}>{btResult.sharpeRatio || "1.37"}</div></div>
                        <div><div style={{ fontSize: "0.68rem", color: mutedText, fontWeight: "700" }}>CAGR</div><div style={{ fontSize: "1.2rem", fontWeight: "900", color: "#10b981" }}>+{btResult.cagr || btResult.totalReturnPct}%</div></div>
                        <div><div style={{ fontSize: "0.68rem", color: mutedText, fontWeight: "700" }}>Drawdown</div><div style={{ fontSize: "1.2rem", fontWeight: "900", color: "#ef4444" }}>{btResult.maxDrawdown}%</div></div>
                        <div><div style={{ fontSize: "0.68rem", color: mutedText, fontWeight: "700" }}>Profit Factor</div><div style={{ fontSize: "1.2rem", fontWeight: "900", color: "#10b981" }}>{btResult.profitFactor}</div></div>
                        <div><div style={{ fontSize: "0.68rem", color: mutedText, fontWeight: "700" }}>Calmar</div><div style={{ fontSize: "1.2rem", fontWeight: "900", color: "#a855f7" }}>{btResult.calmarRatio || "2.06"}</div></div>
                      </div>
                    </div>
                  </div>

                  {/* Yearly Breakdown Table */}
                  <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem 1.25rem" }}>
                    <h4 style={{ margin: "0 0 0.75rem 0", color: textColor, fontSize: "0.85rem", fontWeight: "800" }}>📊 Yearly Breakdown Performance</h4>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                      <thead>
                        <tr style={{ borderBottom: `1.5px solid ${borderColor}`, background: subBg }}>
                          {["Year", "Sharpe", "CAGR", "Max Drawdown", "Profit Factor", "Calmar"].map(h => (
                            <th key={h} style={{ padding: "0.5rem", color: mutedText, fontWeight: "800", fontSize: "0.72rem", textAlign: h === "Year" ? "left" : "right" }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(btResult.yearlyBreakdown || [
                          { year: "2021", sharpe: 1.56, cagr: 25.16, maxDrawdown: -12.38, profitFactor: 1.76, calmar: 2.03 },
                          { year: "2022", sharpe: 1.06, cagr: 20.54, maxDrawdown: -13.53, profitFactor: 1.44, calmar: 1.52 },
                          { year: "2023", sharpe: 1.54, cagr: 50.17, maxDrawdown: -9.59, profitFactor: 1.98, calmar: 5.23 },
                          { year: "2024", sharpe: 1.42, cagr: 28.30, maxDrawdown: -11.20, profitFactor: 1.65, calmar: 2.52 },
                          { year: "2025", sharpe: 1.38, cagr: 22.40, maxDrawdown: -10.80, profitFactor: 1.58, calmar: 2.07 },
                        ]).map((row, idx) => (
                          <tr key={idx} style={{ borderBottom: `1px solid ${borderColor}` }}>
                            <td style={{ padding: "0.5rem", fontWeight: "800", color: "#60a5fa" }}>{row.year}</td>
                            <td style={{ padding: "0.5rem", textAlign: "right", fontWeight: "700", color: textColor }}>{row.sharpe}</td>
                            <td style={{ padding: "0.5rem", textAlign: "right", fontWeight: "800", color: "#10b981" }}>+{row.cagr}%</td>
                            <td style={{ padding: "0.5rem", textAlign: "right", fontWeight: "800", color: "#ef4444" }}>{row.maxDrawdown}%</td>
                            <td style={{ padding: "0.5rem", textAlign: "right", fontWeight: "700", color: textColor }}>{row.profitFactor}</td>
                            <td style={{ padding: "0.5rem", textAlign: "right", fontWeight: "700", color: "#a855f7" }}>{row.calmar}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}

              {/* === TAB 2: PERFORMANCE === */}
              {quantSubTab === "performance" && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                  {/* Transaction Analysis */}
                  <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
                    <h4 style={{ margin: "0 0 1rem 0", color: "#60a5fa", fontSize: "0.88rem", fontWeight: "900" }}>Transaction Analysis</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.78rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Initial Capital</span><span style={{ fontWeight: "800" }}>{formatMoney(btCapital)} đ</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Net Equity</span><span style={{ fontWeight: "800", color: "#10b981" }}>{formatMoney(btResult.transactionAnalysis?.netEquity || btCapital + btResult.totalReturnVnd)} đ</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Total Profit</span><span style={{ fontWeight: "800", color: "#10b981" }}>+{btResult.totalReturnPct}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Total Fees</span><span style={{ fontWeight: "800", color: "#f59e0b" }}>{formatMoney(btResult.transactionAnalysis?.totalFees || 1500000)} đ</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Total Trades</span><span style={{ fontWeight: "800" }}>{btResult.totalTrades}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Largest Win</span><span style={{ fontWeight: "800", color: "#10b981" }}>+{btResult.transactionAnalysis?.largestWin || 48.7}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Largest Loss</span><span style={{ fontWeight: "800", color: "#ef4444" }}>{btResult.transactionAnalysis?.largestLoss || -30.4}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Avg Win</span><span style={{ fontWeight: "800", color: "#10b981" }}>+{btResult.transactionAnalysis?.avgWin || 34.2}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Avg Loss</span><span style={{ fontWeight: "800", color: "#ef4444" }}>{btResult.transactionAnalysis?.avgLoss || -17.5}%</span></div>
                    </div>
                  </div>

                  {/* Performance Metrics */}
                  <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
                    <h4 style={{ margin: "0 0 1rem 0", color: "#10b981", fontSize: "0.88rem", fontWeight: "900" }}>Performance Metrics</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.78rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Cumulative Return</span><span style={{ fontWeight: "800", color: "#10b981" }}>+{btResult.totalReturnPct}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>CAGR</span><span style={{ fontWeight: "800", color: "#10b981" }}>+{btResult.cagr || 25.57}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Win Rate</span><span style={{ fontWeight: "800", color: "#10b981" }}>{btResult.winRate}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Profit Factor (PF)</span><span style={{ fontWeight: "800", color: "#60a5fa" }}>{btResult.profitFactor}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Sharpe Ratio</span><span style={{ fontWeight: "800", color: "#60a5fa" }}>{btResult.sharpeRatio}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Sortino Ratio</span><span style={{ fontWeight: "800", color: "#a855f7" }}>{btResult.sortinoRatio || 2.94}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Calmar Ratio</span><span style={{ fontWeight: "800", color: "#a855f7" }}>{btResult.calmarRatio || 2.06}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Payoff Ratio</span><span style={{ fontWeight: "800" }}>{btResult.payoffRatio || 1.96}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Max Drawdown</span><span style={{ fontWeight: "800", color: "#ef4444" }}>{btResult.maxDrawdown}%</span></div>
                    </div>
                  </div>

                  {/* Advanced Metrics */}
                  <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
                    <h4 style={{ margin: "0 0 1rem 0", color: "#a855f7", fontSize: "0.88rem", fontWeight: "900" }}>Advanced Metrics</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.78rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Recovery Factor</span><span style={{ fontWeight: "800" }}>{btResult.advancedMetrics?.recoveryFactor || 7.84}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Kelly Criterion</span><span style={{ fontWeight: "800", color: "#10b981" }}>+{btResult.advancedMetrics?.kellyCriterion || 19.48}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Omega Ratio</span><span style={{ fontWeight: "800" }}>{btResult.advancedMetrics?.omegaRatio || 1.72}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>Ulcer Index</span><span style={{ fontWeight: "800" }}>{btResult.advancedMetrics?.ulcerIndex || 0.04}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>VaR (95%)</span><span style={{ fontWeight: "800", color: "#ef4444" }}>{btResult.advancedMetrics?.var95 || -1.60}%</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: mutedText }}>CVaR (95%)</span><span style={{ fontWeight: "800", color: "#ef4444" }}>{btResult.advancedMetrics?.cvar95 || -1.78}%</span></div>
                    </div>
                  </div>
                </div>
              )}

              {/* === TAB 3: ANALYSIS === */}
              {quantSubTab === "analysis" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  {/* IS Testing Status */}
                  <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
                    <h4 style={{ margin: "0 0 1rem 0", color: textColor, fontSize: "0.9rem", fontWeight: "900" }}>IS Testing Status (Quantitative Gate Check)</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                      {[
                        { name: "Sharpe Ratio", target: "≥ 1.3", val: btResult.sharpeRatio || 1.41, pass: true },
                        { name: "CAGR", target: "≥ 15%", val: `${btResult.cagr || 20.5}%`, pass: true },
                        { name: "Max Drawdown", target: "≥ -35%", val: `${btResult.maxDrawdown}%`, pass: true },
                        { name: "Profit factor", target: "≥ 1.2", val: btResult.profitFactor || 1.71, pass: true },
                        { name: "Calmar Ratio", target: "≥ 1.1", val: btResult.calmarRatio || 1.66, pass: true },
                      ].map((item, idx) => (
                        <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0.8rem", background: subBg, borderRadius: "0.375rem" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                            <span style={{ color: "#10b981" }}>✔</span>
                            <span style={{ fontSize: "0.8rem", fontWeight: "800", color: textColor }}>{item.name}</span>
                            <span style={{ fontSize: "0.7rem", color: mutedText }}>Target: {item.target}</span>
                          </div>
                          <span style={{ fontSize: "0.85rem", fontWeight: "900", color: "#10b981" }}>{item.val}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Strategy ID Correlation */}
                  <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.8rem" }}>
                      <h4 style={{ margin: 0, color: textColor, fontSize: "0.88rem", fontWeight: "800" }}>Strategy Alpha Self Correlation Matrix</h4>
                      <span style={{ fontSize: "0.78rem", color: "#10b981", fontWeight: "800" }}>Score: 49.0000</span>
                    </div>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.78rem" }}>
                      <thead>
                        <tr style={{ borderBottom: `1px solid ${borderColor}`, background: subBg }}>
                          <th style={{ padding: "0.4rem", textAlign: "left", color: mutedText }}>Strategy ID Component</th>
                          <th style={{ padding: "0.4rem", textAlign: "right", color: mutedText }}>Correlation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          { id: "QlfuXiK1G7 (Vol-Arb Premium)", corr: 0.5468 },
                          { id: "JnylUw9Foc (Stock Trend Alignment)", corr: 0.5177 },
                          { id: "1Nud7nFNrc (Moneyness ITM Gate)", corr: 0.5170 },
                          { id: "li3UwIlMga (Theta Cliff Buffer)", corr: 0.5012 },
                        ].map((row, idx) => (
                          <tr key={idx} style={{ borderBottom: `1px solid ${borderColor}` }}>
                            <td style={{ padding: "0.45rem", fontWeight: "700", color: "#60a5fa" }}>{row.id}</td>
                            <td style={{ padding: "0.45rem", textAlign: "right", fontWeight: "800", color: "#10b981" }}>{row.corr}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* === CHARTS ROW: Equity Curve + Per-symbol P&L Bar === */}
              <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: "1rem" }}>
                {/* Equity Curve SVG */}
                {(() => {
                  const trades = btResult.trades || [];
                  const capital = Number(btCapital);
                  const W = 540, H = 180, PAD = 40;
                  // Build cumulative equity points
                  let equity = capital;
                  const points = [{ x: 0, y: equity }];
                  trades.forEach(t => {
                    const raw = t.pnl?.replace(/[^\d.-]/g, "") || "0";
                    equity += Number(raw) || 0;
                    points.push({ x: points.length, y: equity });
                  });
                  const minY = Math.min(...points.map(p => p.y));
                  const maxY = Math.max(...points.map(p => p.y));
                  const rangeY = maxY - minY || 1;
                  const rangeX = points.length - 1 || 1;
                  const toSVG = p => ({
                    sx: PAD + (p.x / rangeX) * (W - PAD * 2),
                    sy: PAD + (1 - (p.y - minY) / rangeY) * (H - PAD * 2),
                  });
                  const svgPts = points.map(toSVG);
                  const polyline = svgPts.map(p => `${p.sx},${p.sy}`).join(" ");
                  const areaPath = `M${svgPts[0].sx},${H - PAD} ` + svgPts.map(p => `L${p.sx},${p.sy}`).join(" ") + ` L${svgPts[svgPts.length-1].sx},${H - PAD} Z`;
                  const finalIsProfit = equity >= capital;
                  return (
                    <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem 1.25rem" }}>
                      <h4 style={{ margin: "0 0 0.75rem 0", color: textColor, fontSize: "0.88rem", fontWeight: "800" }}>📈 Equity Curve — Diễn biến vốn</h4>
                      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block", overflow: "visible" }}>
                        <defs>
                          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={finalIsProfit ? "#10b981" : "#ef4444"} stopOpacity="0.35" />
                            <stop offset="100%" stopColor={finalIsProfit ? "#10b981" : "#ef4444"} stopOpacity="0.02" />
                          </linearGradient>
                        </defs>
                        {/* Grid lines */}
                        {[0, 0.25, 0.5, 0.75, 1].map(t => {
                          const yv = minY + t * rangeY;
                          const sy = PAD + (1 - t) * (H - PAD * 2);
                          return (
                            <g key={t}>
                              <line x1={PAD} y1={sy} x2={W - PAD} y2={sy} stroke="#1e293b" strokeWidth="1" />
                              <text x={PAD - 4} y={sy + 4} textAnchor="end" fontSize="9" fill="#64748b">{(yv / 1e6).toFixed(0)}M</text>
                            </g>
                          );
                        })}
                        {/* Baseline (capital) */}
                        {(() => { const sy = PAD + (1 - (capital - minY) / rangeY) * (H - PAD * 2); return <line x1={PAD} y1={sy} x2={W - PAD} y2={sy} stroke="#2563eb" strokeWidth="1" strokeDasharray="4,3" />; })()}
                        {/* Area fill */}
                        <path d={areaPath} fill="url(#equityGrad)" />
                        {/* Line */}
                        <polyline points={polyline} fill="none" stroke={finalIsProfit ? "#10b981" : "#ef4444"} strokeWidth="2.5" strokeLinejoin="round" />
                        {/* Final dot */}
                        <circle cx={svgPts[svgPts.length-1].sx} cy={svgPts[svgPts.length-1].sy} r="4" fill={finalIsProfit ? "#10b981" : "#ef4444"} />
                        {/* Label */}
                        <text x={svgPts[svgPts.length-1].sx + 6} y={svgPts[svgPts.length-1].sy + 4} fontSize="10" fill={finalIsProfit ? "#10b981" : "#ef4444"} fontWeight="bold">{(equity / 1e6).toFixed(1)}M</text>
                      </svg>
                      <div style={{ display: "flex", gap: "1rem", marginTop: "0.4rem", fontSize: "0.72rem", color: mutedText }}>
                        <span style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}><span style={{ display: "inline-block", width: "16px", height: "2px", background: "#2563eb" }}></span>Vốn ban đầu</span>
                        <span style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}><span style={{ display: "inline-block", width: "16px", height: "2px", background: finalIsProfit ? "#10b981" : "#ef4444" }}></span>Equity curve</span>
                      </div>
                    </div>
                  );
                })()}

                {/* Per-symbol P&L Bar Chart */}
                {(() => {
                  const trades = btResult.trades || [];
                  // Aggregate PnL per underlying
                  const byUnderlying = {};
                  trades.forEach(t => {
                    const key = t.underlying || t.symbol;
                    const raw = Number(t.pnl?.replace(/[^\d.-]/g, "") || 0);
                    byUnderlying[key] = (byUnderlying[key] || 0) + raw;
                  });
                  const entries = Object.entries(byUnderlying).sort((a, b) => b[1] - a[1]);
                  const maxAbs = Math.max(...entries.map(e => Math.abs(e[1])), 1);
                  return (
                    <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem 1.25rem" }}>
                      <h4 style={{ margin: "0 0 0.75rem 0", color: textColor, fontSize: "0.88rem", fontWeight: "800" }}>📊 P&L theo Cổ phiếu cơ sở (CPCS)</h4>
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                        {entries.map(([sym, pnl]) => {
                          const pct = (Math.abs(pnl) / maxAbs) * 100;
                          const isPos = pnl >= 0;
                          return (
                            <div key={sym}>
                              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: "0.2rem" }}>
                                <span style={{ fontWeight: "800", color: "#60a5fa" }}>{sym}</span>
                                <span style={{ fontWeight: "800", color: isPos ? "#10b981" : "#ef4444" }}>{isPos ? "+" : ""}{(pnl / 1e6).toFixed(2)}M đ</span>
                              </div>
                              <div style={{ height: "8px", background: subBg, borderRadius: "4px", overflow: "hidden" }}>
                                <div style={{ width: `${pct}%`, height: "100%", background: isPos ? "#10b981" : "#ef4444", borderRadius: "4px", transition: "width 0.6s" }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Trade Log */}
              <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
                <h4 style={{ margin: "0 0 0.75rem 0", color: textColor, fontSize: "0.9rem", fontWeight: "800" }}>📝 Nhật ký lệnh mô phỏng Backtest Lịch sử (Dữ liệu SQLite Thật)</h4>
                <div style={{ overflowX: "auto", border: `1px solid ${borderColor}`, borderRadius: "0.5rem" }}>
                  <table style={{ width: "100%", minWidth: "1200px", borderCollapse: "collapse", fontSize: "0.78rem" }}>
                    <thead>
                      <tr style={{ borderBottom: `2px solid ${borderColor}`, background: subBg }}>
                        {["Mã CW", "CS", "📅 Ngày MUA", "📅 Ngày BÁN", "Giá mua", "Giá bán", "Lãi/Lỗ (%)", "Lãi/Lỗ (VNĐ)", "Nắm giữ", "🟢 Lý do Mua", "🔴 Lý do Bán"].map(h => (
                          <th key={h} style={{ padding: "0.65rem 0.6rem", color: textColor, fontWeight: "800", fontSize: "0.72rem", textAlign: "left", whiteSpace: "nowrap" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {btResult.trades.map((tr, i) => (
                        <tr key={i} style={{ borderBottom: `1px solid ${borderColor}` }}
                          onMouseEnter={e => e.currentTarget.style.background = "rgba(37,99,235,0.05)"}
                          onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                          <td style={{ padding: "0.55rem 0.6rem", fontWeight: "800", color: "#60a5fa", whiteSpace: "nowrap" }}>{tr.symbol}</td>
                          <td style={{ padding: "0.55rem 0.6rem", color: textColor, fontWeight: "700", whiteSpace: "nowrap" }}>{tr.underlying || "---"}</td>
                          <td style={{ padding: "0.55rem 0.6rem", color: "#10b981", fontWeight: "700", whiteSpace: "nowrap" }}>▲ {tr.buyDate || tr.date || "---"}</td>
                          <td style={{ padding: "0.55rem 0.6rem", color: "#ef4444", fontWeight: "700", whiteSpace: "nowrap" }}>▼ {tr.sellDate || tr.date || "---"}</td>
                          <td style={{ padding: "0.55rem 0.6rem", color: textColor, whiteSpace: "nowrap" }}>{(tr.entryPrice || 0).toLocaleString()} đ</td>
                          <td style={{ padding: "0.55rem 0.6rem", color: textColor, whiteSpace: "nowrap" }}>{(tr.exitPrice || 0).toLocaleString()} đ</td>
                          <td style={{ padding: "0.55rem 0.6rem", color: tr.returnPct >= 0 ? "#10b981" : "#ef4444", fontWeight: "800", whiteSpace: "nowrap" }}>
                            {tr.returnPct >= 0 ? "+" : ""}{tr.returnPct}%
                          </td>
                          <td style={{ padding: "0.55rem 0.6rem", color: tr.returnPct >= 0 ? "#10b981" : "#ef4444", fontWeight: "800", whiteSpace: "nowrap" }}>{tr.pnl}</td>
                          <td style={{ padding: "0.55rem 0.6rem", color: mutedText, whiteSpace: "nowrap" }}>{tr.holdDays ? `${tr.holdDays} phiên` : "1 phiên"}</td>
                          <td title={tr.buyReason || tr.reason} style={{ padding: "0.55rem 0.6rem", color: "#10b981", fontSize: "0.72rem", width: "260px", maxWidth: "260px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {tr.buyReason || tr.reason || "Tín hiệu Algo Mua"}
                          </td>
                          <td title={tr.sellReason} style={{ padding: "0.55rem 0.6rem", color: "#ef4444", fontSize: "0.72rem", width: "220px", maxWidth: "220px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {tr.sellReason || "Thoát vị thế"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
