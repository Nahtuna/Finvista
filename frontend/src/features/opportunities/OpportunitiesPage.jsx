import React, { useEffect, useState, useMemo, useCallback } from "react";
import { Search, RotateCcw, Star, TrendingUp, TrendingDown, ChevronUp, ChevronDown, RefreshCw, Loader2 } from "lucide-react";
import { getOpportunities, getUnderlyingMarket, placeOrder } from "../../api.js";
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

function GScoreBar({ score }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 70 ? "#10b981" : pct >= 50 ? "#60a5fa" : pct >= 30 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
      <div style={{ flex: 1, height: "4px", background: "#1e293b", borderRadius: "2px", minWidth: "40px" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: "2px", transition: "width 0.3s" }} />
      </div>
      <span style={{ fontSize: "0.78rem", fontWeight: "800", color, minWidth: "28px" }}>{Math.round(pct)}</span>
    </div>
  );
}

function SortHeader({ label, field, sortField, sortDir, onSort }) {
  const active = sortField === field;
  return (
    <th
      onClick={() => onSort(field)}
      style={{ padding: "0.6rem 0.5rem", color: active ? "#60a5fa" : "#64748b", cursor: "pointer", userSelect: "none", whiteSpace: "nowrap", fontWeight: "700", fontSize: "0.75rem" }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: "0.2rem" }}>
        {label}
        {active ? (sortDir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />) : <span style={{ opacity: 0.3 }}><ChevronDown size={12} /></span>}
      </span>
    </th>
  );
}

export function OpportunitiesPage({ setPage, setSelectedSymbol, language = "vi", preferences = {}, strategy = "balanced", setStrategy }) {
  const isEnglish = language === "en";
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState("nang_cao");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

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

  // Sorting
  const [sortField, setSortField] = useState("gscore");
  const [sortDir, setSortDir] = useState("desc");

  // Underlying stocks state
  const [stocks, setStocks] = useState([]);
  const [stocksLoading, setStocksLoading] = useState(false);
  const [stockSearch, setStockSearch] = useState("");
  const [selectedIndustry, setSelectedIndustry] = useState("all");

  const INDUSTRY_TAGS = [
    { label: "Tất cả", value: "all" },
    { label: "Ngân hàng", value: "ngân hàng" },
    { label: "Bất động sản", value: "bất động sản" },
    { label: "Thép", value: "thép" },
    { label: "Chứng khoán", value: "chứng khoán" },
    { label: "Công nghệ", value: "công nghệ" },
  ];

  function loadData(forceRefresh = false) {
    setLoading(true);
    setCurrentPage(1);
    getOpportunities({ strategy, limit: 5000, forceRefresh })
      .then(res => {
        setData(res);
        if (forceRefresh) addToast("Đã làm mới dữ liệu CW từ DB!", "success");
      })
      .catch(() => addToast("Đang kết nối lại server...", "warning"))
      .finally(() => setLoading(false));
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
    setSearchQuery(""); setVisibleCount(PAGE_SIZE);
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
    setVisibleCount(PAGE_SIZE);
  }

  // Map API rows with dynamic Strategy G-Score weighting
  const rawRows = useMemo(() => {
    const recs = data?.recommendations;
    if (!recs || recs.length === 0) return [];
    return recs.map(r => {
      const d = r.delta ?? 0.5;
      const mState = r.moneyness_status || (d >= 0.6 ? "ITM" : d >= 0.4 ? "ATM" : "OTM");
      const gear = Math.round((r.effective_gearing || r.gearing || (d * 9.5)) * 10) / 10;
      const bkPrice = r.breakeven_price || Math.round((r.market_price || r.price || 1000) * 1.08);
      const baseScore = r.composite_g_score || r.score || 50;
      const prem = Math.round((r.premium_pct || 0) * 10) / 10;
      const dtmDays = r.days_to_maturity || 90;
      const priceChg = r.price_change_pct || 0;

      let calcScore = baseScore;
      if (strategy === "aggressive") {
        // Aggressive: Higher weight on leverage (gearing), Delta & momentum upside
        calcScore = (baseScore * 0.4) + (d * 35) + (Math.min(gear, 12) * 2.5) + (priceChg > 0 ? 8 : -5);
      } else if (strategy === "safe" || strategy === "defensive") {
        // Defensive: Higher weight on safety (low premium, longer DTM, ITM stability)
        calcScore = (baseScore * 0.4) + (prem < 15 ? 25 : prem < 25 ? 15 : 5) + (dtmDays > 60 ? 25 : 10) + (d >= 0.5 ? 15 : 5);
      }
      const finalGscore = Math.min(99, Math.max(15, Math.round(calcScore * 10) / 10));

      return {
        symbol: r.warrant_symbol || r.symbol || "",
        underlying: r.underlying_symbol || r.underlying || "",
        issuer: r.issuer || "",
        price: r.market_price || r.price || 0,
        premium: prem,
        delta: Math.round((r.delta || 0) * 100) / 100,
        gearing: gear,
        moneyness: mState,
        breakeven: bkPrice,
        iv: Math.round((r.implied_volatility_pct || 0) * 10) / 10,
        gscore: finalGscore,
        dtm: dtmDays,
        volume: r.volume || 0,
        changePct: priceChg,
        signal: r.recommendation_signal || r.decision_signal || "",
        isBuy: (r.recommendation_signal || r.decision_signal || "").toUpperCase().includes("BUY"),
      };
    });
  }, [data, strategy]);

  // Dynamic dropdown options from live data
  const underlyingOptions = useMemo(() => [...new Set(rawRows.map(r => r.underlying))].sort(), [rawRows]);
  const issuerOptions = useMemo(() => [...new Set(rawRows.map(r => r.issuer))].sort(), [rawRows]);

  // Watchlist for favorites tab
  const favList = useMemo(() => JSON.parse(localStorage.getItem("finvista-watchlist") || "[]"), []);

  // Filter
  const filteredRows = useMemo(() => {
    let rows = rawRows.filter(r => {
      if (activeTab === "yeu_thich" && !favList.includes(r.symbol)) return false;
      if (searchQuery && !r.symbol.toLowerCase().includes(searchQuery.toLowerCase()) && !r.underlying.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (selectedUnderlying !== "all" && r.underlying !== selectedUnderlying) return false;
      if (selectedIssuer !== "all" && r.issuer !== selectedIssuer) return false;
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
      const va = a[sortField] ?? 0, vb = b[sortField] ?? 0;
      return sortDir === "asc" ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });

    return rows;
  }, [rawRows, activeTab, searchQuery, selectedUnderlying, selectedIssuer, selectedMoneyness, premiumMax, deltaMin, gearingMin, daysMax, gscoreMin, chkUndervalued, chkBuyOnly, sortField, sortDir, favList]);

  const displayRows = useMemo(() => {
    return filteredRows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  }, [filteredRows, currentPage]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedUnderlying, selectedIssuer, selectedMoneyness, premiumMax, deltaMin, gearingMin, daysMax, gscoreMin, chkUndervalued, chkBuyOnly, sortField, sortDir, strategy, activeTab]);

  const totalBuy = rawRows.filter(r => r.isBuy).length;
  const avgGscore = rawRows.length ? (rawRows.reduce((s, r) => s + r.gscore, 0) / rawRows.length).toFixed(1) : "--";

  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", color: textColor, background: bg }}>

      {/* HEADER */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.3rem", fontWeight: "900", margin: 0, letterSpacing: "0.3px", color: textColor }}>
              🔍 CW Scanner — Tìm kiếm cơ hội chứng quyền
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
            {[{ id: "balanced", label: "Quân bình" }, { id: "aggressive", label: "Tấn công" }, { id: "safe", label: "Phòng thủ" }].map(s => (
              <button key={s.id} onClick={() => setStrategy(s.id)} style={{ background: strategy === s.id ? "#2563eb" : subBg, color: strategy === s.id ? "#fff" : textColor, border: "1px solid " + (strategy === s.id ? "#2563eb" : borderColor), borderRadius: "0.3rem", padding: "0.3rem 0.65rem", fontSize: "0.75rem", fontWeight: "700", cursor: "pointer" }}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* FILTER PANEL */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem 1.25rem" }}>

        {/* Always-visible: search + dropdowns */}
        <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1fr 1fr 1fr 1fr auto", gap: "0.75rem", alignItems: "end", marginBottom: activeTab === "nang_cao" ? "1rem" : 0 }}>
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
              {issuerOptions.map(is => <option key={is} value={is} style={{ background: cardBg, color: textColor }}>{is}</option>)}
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
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "1rem", paddingTop: "1rem", borderTop: `1px solid ${borderColor}`, alignItems: "center" }}>
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
            <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
              <label style={{ fontSize: "0.78rem", display: "flex", alignItems: "center", gap: "0.3rem", cursor: "pointer", color: textColor, fontWeight: "600" }}>
                <input type="checkbox" checked={chkBuyOnly} onChange={e => setChkBuyOnly(e.target.checked)} />
                <span>Chỉ tín hiệu MUA</span>
              </label>
              <label style={{ fontSize: "0.78rem", display: "flex", alignItems: "center", gap: "0.3rem", cursor: "pointer", color: textColor, fontWeight: "600" }}>
                <input type="checkbox" checked={chkUndervalued} onChange={e => setChkUndervalued(e.target.checked)} />
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
                    <SortHeader label="Premium" field="premium" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="Delta" field="delta" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="Đòn bẩy" field="gearing" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <th style={{ padding: "0.55rem 0.5rem", textAlign: "center", fontSize: "0.75rem", fontWeight: "800", color: textColor }}>Moneyness</th>
                    <SortHeader label="Hòa vốn" field="breakeven" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="IV%" field="iv" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="DTM" field="dtm" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <SortHeader label="G-Score" field="gscore" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                    <th style={{ padding: "0.55rem 0.5rem", fontSize: "0.75rem", fontWeight: "800", color: textColor }}>Tín hiệu</th>
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
                        <td style={{ padding: "0.55rem 0.5rem", fontWeight: "700", color: textColor }}>{row.underlying}</td>
                        <td style={{ padding: "0.55rem 0.5rem" }}>
                          <span style={{ fontWeight: "800", color: "#3b82f6", fontSize: "0.8rem" }}>{row.symbol}</span>
                          <span style={{ fontSize: "0.68rem", color: mutedText, display: "block" }}>{row.issuer}</span>
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem" }}>
                          <span style={{ fontWeight: "700", color: textColor }}>{row.underlying}</span>
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", fontWeight: "700", color: textColor }}>
                          {row.price?.toLocaleString()} đ
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", fontWeight: "700", color: row.changePct >= 0 ? "#10b981" : "#ef4444" }}>
                          {row.changePct >= 0 ? "+" : ""}{formatNumber(row.changePct, 2)}%
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: row.premium <= 10 ? "#10b981" : row.premium <= 20 ? "#f59e0b" : "#ef4444", fontWeight: "600" }}>
                          {row.premium}%
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: textColor, fontWeight: "600" }}>
                          {row.delta}
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", color: textColor, fontWeight: "600" }}>
                          {row.gearing}x
                        </td>
                        <td style={{ padding: "0.55rem 0.5rem", textAlign: "center" }}>
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
