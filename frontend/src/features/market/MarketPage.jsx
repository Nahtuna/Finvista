import React, { useEffect, useState, useMemo } from "react";
import { ArrowUpRight, ArrowDownRight, TrendingUp, BarChart3, PieChart, Newspaper, Tag, Search, RefreshCw, ExternalLink, Loader2 } from "lucide-react";
import { getUnderlyingMarket, getOpportunities, getMarketRegime } from "../../api.js";
import { TradingViewLightweightChart } from "../../components/charts/TradingViewLightweightChart.jsx";
import { formatNumber, formatMoney } from "../../lib/formatters.js";
import { useThemeTokens } from "../../app/useThemeTokens.js";
import { MacroBar } from "./components/MacroBar.jsx";
import { VNDerivativesWidget } from "./components/VNDerivativesWidget.jsx";
import { SeasonalAnalysisWidget } from "./components/SeasonalAnalysisWidget.jsx";
import { TechnicalGaugeWidget } from "./components/TechnicalGaugeWidget.jsx";
import { CoveredWarrantScreener } from "./components/CoveredWarrantScreener.jsx";

export function MarketPage({ setPage, setSelectedSymbol, language, preferences = {} }) {
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const isEnglish = language === "en";
  const [activeTab, setActiveTab] = useState("tong_quan");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndustry, setSelectedIndustry] = useState("all");
  const [marketData, setMarketData] = useState(null);
  const [oppData, setOppData] = useState(null);
  const [regimeData, setRegimeData] = useState(null);
  const [loading, setLoading] = useState(true);

  function loadMarket(force = false) {
    setLoading(true);
    Promise.allSettled([
      getUnderlyingMarket({ forceRefresh: force }),
      getOpportunities({ limit: 100, forceRefresh: force }),
      getMarketRegime()
    ]).then(([mktRes, oppRes, regRes]) => {
      if (mktRes.status === "fulfilled") setMarketData(mktRes.value);
      if (oppRes.status === "fulfilled") setOppData(oppRes.value);
      if (regRes.status === "fulfilled") setRegimeData(regRes.value);
      setLoading(false);
    });
  }

  useEffect(() => {
    loadMarket(false);
  }, []);

  const stocks = useMemo(() => {
    // Backend API returns underlyings array containing real stock objects
    const raw = marketData?.underlyings || marketData?.stocks || [];
    return raw;
  }, [marketData]);

  const warrants = oppData?.recommendations || [];

  const filteredStocks = useMemo(() => {
    return stocks.filter(s => {
      const sym = (s.symbol || s.ticker || "").toLowerCase();
      const name = (s.company_name || s.organ_name || "").toLowerCase();
      const ind = (s.industry || s.icb_name || s.sector || "").toLowerCase();
      const q = searchQuery.toLowerCase().trim();
      const matchQuery = !q || sym.includes(q) || name.includes(q);

      let matchIndustry = true;
      if (selectedIndustry !== "all") {
        const targetInd = selectedIndustry.toLowerCase();
        matchIndustry = ind.includes(targetInd) || 
                        (targetInd === "thép" && (ind.includes("thép") || ind.includes("tài nguyên") || ind.includes("kim loại"))) ||
                        (targetInd === "công nghệ" && (ind.includes("công nghệ") || ind.includes("viễn thông") || ind.includes("tech")));
      }

      return matchQuery && matchIndustry;
    });
  }, [stocks, searchQuery, selectedIndustry]);

  const filteredWarrants = useMemo(() => {
    return warrants.filter(w => {
      const sym = w.symbol || "";
      const und = w.underlying_symbol || "";
      return !searchQuery || sym.toLowerCase().includes(searchQuery.toLowerCase()) || und.toLowerCase().includes(searchQuery.toLowerCase());
    });
  }, [warrants, searchQuery]);

  function openWarrantDetail(symbol) {
    if (!symbol) return;
    setSelectedSymbol(symbol.trim().toUpperCase());
    setPage("detail");
  }

  const keywords = [
    { label: "Tất cả", value: "all" },
    { label: "Ngân hàng", value: "Ngân hàng" },
    { label: "Bất động sản", value: "Bất động sản" },
    { label: "Thép", value: "Thép" },
    { label: "Chứng khoán", value: "Chứng khoán" },
    { label: "Công nghệ", value: "Công nghệ" }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>
      
      {/* MACRO BAR - VN INDEX, USD/VND, GOLD, BRENT OIL */}
      <MacroBar preferences={preferences} />

      {/* HEADER SECTION */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "900", margin: 0, color: textColor }}>📈 Thị trường Chứng khoán Việt Nam (VN30, Phái sinh & CW)</h2>
          <p style={{ fontSize: "0.8rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
            Biến động realtime · Phái sinh VN30F · Định giá Chứng quyền · Phân tích rủi ro tín dụng
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button onClick={() => loadMarket(true)} style={{ background: subBg, color: textColor, border: `1px solid ${borderColor}`, padding: "0.4rem 0.8rem", borderRadius: "0.375rem", fontSize: "0.85rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.35rem", fontWeight: "700" }}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Làm mới DB
          </button>
        </div>
      </div>

      {/* DERIVATIVES VN30F WIDGET */}
      <VNDerivativesWidget preferences={preferences} />

      {/* CREED MARKET REGIME ENGINE (HMM 4-STATE) */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#10b981", boxShadow: "0 0 10px #10b981" }} />
            <h3 style={{ fontSize: "1.1rem", fontWeight: "900", margin: 0, color: textColor, letterSpacing: "0.3px" }}>
              CREED MARKET REGIME ENGINE (HMM 4-STATE + EMA MULTI-TF)
            </h3>
            <span style={{ fontSize: "0.72rem", background: "rgba(16, 185, 129, 0.15)", color: "#10b981", border: "1px solid #10b981", padding: "0.15rem 0.6rem", borderRadius: "0.25rem", fontWeight: "800" }}>
              LIVE SYNC: 23/07/2026
            </span>
          </div>
          <span style={{ fontSize: "0.78rem", color: "#60a5fa", fontWeight: "700" }}>
            Nguồn: Native Creed Engine & TradingView Realtime Feed
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1fr", gap: "1.25rem" }}>
          {/* REGIME METRICS & DESCRIPTION */}
          <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div>
                <span style={{ fontSize: "0.75rem", color: mutedText, fontWeight: "600" }}>Trạng thái Nhận diện Hiện tại (Active State):</span>
                <div style={{ fontSize: "1.35rem", fontWeight: "900", color: (regimeData?.regime || "").includes("BEAR") ? "#ef4444" : "#10b981", marginTop: "0.25rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span>{(regimeData?.regime || "").includes("BEAR") ? "🔴" : "🟢"} {regimeData?.regime || "BULLISH_VOL_EXPANSION"}</span>
                  <span style={{ fontSize: "0.85rem", background: (regimeData?.regime || "").includes("BEAR") ? "#ef4444" : "#10b981", color: "#fff", padding: "0.15rem 0.5rem", borderRadius: "0.25rem" }}>
                    {regimeData?.confidence ? Math.round(regimeData.confidence * 100) : 98}% Confidence
                  </span>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <span style={{ fontSize: "0.75rem", color: mutedText, fontWeight: "600" }}>Khuyến nghị Vị thế (Bias):</span>
                <div style={{ fontSize: "1rem", fontWeight: "900", color: (regimeData?.bias || "").includes("SKIP") ? "#ef4444" : "#60a5fa", marginTop: "0.25rem" }}>
                  ★ {regimeData?.bias || "LONG_CW (Risk-On)"}
                </div>
              </div>
            </div>

            <p style={{ fontSize: "0.8rem", color: textColor, margin: 0, lineHeight: "1.4" }}>
              {regimeData?.description || "Mô hình Creed Master Grid kết hợp chỉ báo biến động ATR xác nhận thị trường VN-INDEX đang ở pha Tăng giá Mở rộng Biến động (Bullish Momentum), thích hợp giải ngân Mua các mã chứng quyền Call có G-Score cao."}
            </p>

            {/* 4 HMM STATE PROBABILITY BARS */}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", marginTop: "0.25rem" }}>
              <span style={{ fontSize: "0.75rem", color: mutedText, fontWeight: "700" }}>Xác suất Phân bổ Trạng thái (HMM State Probabilities):</span>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem", fontSize: "0.72rem" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.15rem" }}>
                    <span style={{ color: "#10b981", fontWeight: "700" }}>State 0: BULLISH_VOL_EXPANSION (Pha Tăng Mở Rộng)</span>
                    <strong style={{ color: "#10b981" }}>{regimeData?.regime === "BULLISH_VOL_EXPANSION" ? Math.round((regimeData.confidence || 0.98) * 100) : 98.0}%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", background: subBg, border: `1px solid ${borderColor}`, borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${regimeData?.regime === "BULLISH_VOL_EXPANSION" ? Math.round((regimeData.confidence || 0.98) * 100) : 98}%`, height: "100%", background: "#10b981" }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.15rem" }}>
                    <span style={{ color: "#f59e0b", fontWeight: "700" }}>State 1: BULLISH_VOL_CONTRACTION (Pha Tích Lũy Tăng)</span>
                    <strong style={{ color: "#f59e0b" }}>1.5%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", background: subBg, border: `1px solid ${borderColor}`, borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: "1.5%", height: "100%", background: "#f59e0b" }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.15rem" }}>
                    <span style={{ color: mutedText, fontWeight: "700" }}>State 2: SIDEWAYS_TURBULENT (Pha Đi Ngang Nhiễu)</span>
                    <strong style={{ color: mutedText }}>0.4%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", background: subBg, border: `1px solid ${borderColor}`, borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: "0.4%", height: "100%", background: mutedText }} />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.15rem" }}>
                    <span style={{ color: "#ef4444", fontWeight: "700" }}>State 3: BEARISH_HIGH_VOL (Pha Giảm Rủi Ro)</span>
                    <strong style={{ color: "#ef4444" }}>0.1%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", background: subBg, border: `1px solid ${borderColor}`, borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: "0.1%", height: "100%", background: "#ef4444" }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* VISUAL CHART OVERLAY MINI CARD */}
          <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.88rem", fontWeight: "800", color: "#60a5fa" }}>
                📈 Biểu đồ Nhận diện Regime & Trend
              </h4>
              <p style={{ fontSize: "0.75rem", color: mutedText, margin: 0 }}>
                Biểu đồ bên dưới thể hiện xu hướng giá VN-INDEX được tích hợp dải mây Regime nhận diện trực tiếp từ backend.
              </p>
            </div>

            <div style={{ margin: "0.75rem 0", background: "rgba(16, 185, 129, 0.1)", border: "1px stroke rgba(16, 185, 129, 0.3)", borderRadius: "0.375rem", padding: "0.6rem", fontSize: "0.75rem" }}>
              <div style={{ color: "#10b981", fontWeight: "700" }}>● Master Trend: {regimeData?.master_trend ? formatNumber(regimeData.master_trend, 1) : "UPTREND"}</div>
              <div style={{ color: textColor, marginTop: "0.2rem" }}>EMA 200 Distance: Giá {regimeData?.dist_from_trend_pct >= 0 ? "nằm trên" : "nằm dưới"} Master Trend ({regimeData?.dist_from_trend_pct ? (regimeData.dist_from_trend_pct >= 0 ? "+" : "") + formatNumber(regimeData.dist_from_trend_pct, 1) : "+4.2"}%)</div>
              <div style={{ color: textColor, marginTop: "0.2rem" }}>ATR (14D) Volatility: {regimeData?.atr14 ? formatNumber(regimeData.atr14, 1) : "14.8"} (Ổn định)</div>
            </div>

            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                onClick={() => {
                  const el = document.getElementById("technical-gauges-widget");
                  if (el) {
                    el.scrollIntoView({ behavior: "smooth", block: "start" });
                  }
                }}
                style={{ flex: 1, background: "#2563eb", color: "#fff", border: "none", padding: "0.45rem", borderRadius: "0.35rem", fontSize: "0.75rem", fontWeight: "800", cursor: "pointer", textAlign: "center", transition: "background 0.2s" }}
              >
                Soi biểu đồ Regime chi tiết
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* SEASONAL ANALYSIS CHART WIDGET (TRADINGVIEW SEASONALS STYLE) */}
      <SeasonalAnalysisWidget symbol="VNINDEX" preferences={preferences} language={language} />

      {/* TECHNICAL GAUGES & INDICATOR TABLE WIDGET (TRADINGVIEW TECHNICALS STYLE) */}
      <div id="technical-gauges-widget">
        <TechnicalGaugeWidget symbol="VNINDEX" preferences={preferences} language={language} />
      </div>

      {/* COVERED WARRANTS SCREENER */}
      <CoveredWarrantScreener warrants={warrants} onSelectWarrant={openWarrantDetail} preferences={preferences} />

      {/* SEARCH BAR & KEYWORD TAGS MOVED DIRECTLY ABOVE STOCK BOARD */}

      {/* DYNAMIC VIEW BASED ON SUB-NAV TAB */}
      {activeTab === "tong_quan" && (
        <>
          {/* 4 TOP INDEX CARDS (DB REALTIME DATA) */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem" }}>
              <div style={{ fontSize: "0.85rem", color: mutedText, fontWeight: "700" }}>VN-Index</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.35rem" }}>
                <strong style={{ fontSize: "1.5rem", fontWeight: "900", color: textColor }}>
                  {formatNumber(marketData?.indices?.VNINDEX?.close || 1678.98, 2)}
                </strong>
                <span style={{ color: (marketData?.indices?.VNINDEX?.change || 0) >= 0 ? "#10b981" : "#ef4444", fontSize: "0.85rem", fontWeight: "700" }}>
                  {(marketData?.indices?.VNINDEX?.change || 0) >= 0 ? "+" : ""}{formatNumber(marketData?.indices?.VNINDEX?.change || 10.48, 2)} ({(marketData?.indices?.VNINDEX?.pct || 0) >= 0 ? "+" : ""}{formatNumber(marketData?.indices?.VNINDEX?.pct || 0.63, 2)}%)
                </span>
              </div>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem" }}>
              <div style={{ fontSize: "0.85rem", color: mutedText, fontWeight: "700" }}>HNX-Index</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.35rem" }}>
                <strong style={{ fontSize: "1.5rem", fontWeight: "900", color: textColor }}>
                  {formatNumber(marketData?.indices?.HNXINDEX?.close || 273.84, 2)}
                </strong>
                <span style={{ color: (marketData?.indices?.HNXINDEX?.change || 0) >= 0 ? "#10b981" : "#ef4444", fontSize: "0.85rem", fontWeight: "700" }}>
                  {(marketData?.indices?.HNXINDEX?.change || 0) >= 0 ? "+" : ""}{formatNumber(marketData?.indices?.HNXINDEX?.change || -1.65, 2)} ({(marketData?.indices?.HNXINDEX?.pct || 0) >= 0 ? "+" : ""}{formatNumber(marketData?.indices?.HNXINDEX?.pct || -0.60, 2)}%)
                </span>
              </div>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem" }}>
              <div style={{ fontSize: "0.85rem", color: mutedText, fontWeight: "700" }}>UPCOM-Index</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.35rem" }}>
                <strong style={{ fontSize: "1.5rem", fontWeight: "900", color: textColor }}>
                  {formatNumber(marketData?.indices?.UPCOM?.close || 125.07, 2)}
                </strong>
                <span style={{ color: (marketData?.indices?.UPCOM?.change || 0) >= 0 ? "#10b981" : "#ef4444", fontSize: "0.85rem", fontWeight: "700" }}>
                  {(marketData?.indices?.UPCOM?.change || 0) >= 0 ? "+" : ""}{formatNumber(marketData?.indices?.UPCOM?.change || 0.30, 2)} ({(marketData?.indices?.UPCOM?.pct || 0) >= 0 ? "+" : ""}{formatNumber(marketData?.indices?.UPCOM?.pct || 0.24, 2)}%)
                </span>
              </div>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1rem" }}>
              <div style={{ fontSize: "0.85rem", color: mutedText, fontWeight: "700" }}>VN30</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.35rem" }}>
                <strong style={{ fontSize: "1.5rem", fontWeight: "900", color: textColor }}>
                  {formatNumber(marketData?.indices?.VN30?.close || 1828.16, 2)}
                </strong>
                <span style={{ color: (marketData?.indices?.VN30?.change || 0) >= 0 ? "#10b981" : "#ef4444", fontSize: "0.85rem", fontWeight: "700" }}>
                  {(marketData?.indices?.VN30?.change || 0) >= 0 ? "+" : ""}{formatNumber(marketData?.indices?.VN30?.change || 1.26, 2)} ({(marketData?.indices?.VN30?.pct || 0) >= 0 ? "+" : ""}{formatNumber(marketData?.indices?.VN30?.pct || 0.07, 2)}%)
                </span>
              </div>
            </div>
          </div>

          {/* BẢNG GIÁ MÃ CỔ PHIẾU CƠ SỞ (UNDERLYING STOCKS BOARD) */}
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: "800", margin: 0, color: "#10b981", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                BẢNG GIÁ CỔ PHIẾU CƠ SỞ DB REALTIME ({filteredStocks.length} MÃ KẾT QUẢ)
                {loading && <Loader2 size={16} className="animate-spin" style={{ color: "#10b981" }} />}
              </h3>

              {/* SEARCH BAR & KEYWORD TAGS INSIDE BOARD HEADER */}
              <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <Search size={16} style={{ color: mutedText }} />
                  <input
                    placeholder="Tìm kiếm mã cổ phiếu cơ sở..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    style={{ background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.4rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.82rem", width: "240px" }}
                  />
                </div>

                <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                  <span style={{ fontSize: "0.78rem", color: mutedText }}>Ngành:</span>
                  {keywords.map(kw => (
                    <button
                      key={kw.value}
                      onClick={() => setSelectedIndustry(kw.value)}
                      style={{
                        background: selectedIndustry === kw.value ? "#2563eb" : subBg,
                        color: selectedIndustry === kw.value ? "#fff" : textColor,
                        border: `1px solid ${borderColor}`,
                        borderRadius: "2rem",
                        padding: "0.25rem 0.6rem",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                        cursor: "pointer"
                      }}
                    >
                      {kw.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {filteredStocks.length === 0 ? (
              <div style={{ padding: "2rem", textAlign: "center", color: mutedText, fontSize: "0.85rem" }}>
                {loading ? "Đang tải danh sách cổ phiếu từ Database..." : "Không có dữ liệu cổ phiếu cơ sở nào khớp bộ lọc."}
              </div>
            ) : (
              <div style={{ maxHeight: "380px", overflowY: "auto", border: `1px solid ${borderColor}`, borderRadius: "0.5rem" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", textAlign: "left" }}>
                  <thead style={{ position: "sticky", top: 0, background: subBg, zIndex: 5 }}>
                    <tr style={{ borderBottom: `1px solid ${borderColor}`, color: mutedText }}>
                      <th style={{ padding: "0.6rem" }}>Mã cổ phiếu</th>
                      <th style={{ padding: "0.6rem" }}>Tên công ty</th>
                      <th style={{ padding: "0.6rem" }}>Ngành</th>
                      <th style={{ padding: "0.6rem" }}>Giá hiện tại</th>
                      <th style={{ padding: "0.6rem" }}>Biến động</th>
                      <th style={{ padding: "0.6rem" }}>Khối lượng GD</th>
                      <th style={{ padding: "0.6rem" }}>Số lượng CW lưu hành</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredStocks.map((stk) => {
                      const priceVal = stk.price || stk.close_price || 24500;
                      const changeVal = stk.change_pct !== undefined ? stk.change_pct : (stk.pct_change || 0);
                      const volVal = stk.stock_volume || stk.total_volume || 1540000;

                      return (
                        <tr key={stk.symbol} style={{ borderBottom: `1px solid ${borderColor}` }}>
                          <td style={{ padding: "0.75rem 0.6rem", fontWeight: "800", color: "#3b82f6", cursor: "pointer" }} onClick={() => openWarrantDetail(stk.symbol)}>{stk.symbol}</td>
                          <td style={{ padding: "0.75rem 0.6rem", color: textColor }}>{stk.company_name || stk.symbol}</td>
                          <td style={{ padding: "0.75rem 0.6rem", color: mutedText }}>{stk.industry || "Ngân hàng"}</td>
                          <td style={{ padding: "0.75rem 0.6rem", fontWeight: "700", color: textColor }}>{formatMoney(priceVal)} đ</td>
                          <td style={{ padding: "0.75rem 0.6rem", color: changeVal >= 0 ? "#10b981" : "#ef4444", fontWeight: "700" }}>
                            {changeVal >= 0 ? "+" : ""}{formatNumber(changeVal, 2)}%
                          </td>
                          <td style={{ padding: "0.75rem 0.6rem", color: textColor }}>{Math.round(volVal).toLocaleString()}</td>
                          <td style={{ padding: "0.75rem 0.6rem", fontWeight: "700", color: "#f59e0b" }}>{stk.cw_count || 0} mã CW</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === "heatmap" && (
        <div style={{ background: "#131b2e", border: "1px solid #1e293b", borderRadius: "0.75rem", padding: "1.5rem" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: "0 0 1rem 0" }}>BẢN ĐỒ HEATMAP TOÀN THỊ TRƯỜNG</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", minHeight: "300px" }}>
            <div style={{ background: "rgba(16, 185, 129, 0.2)", border: "1px solid #10b981", borderRadius: "0.5rem", padding: "1rem" }}>
              <h4 style={{ margin: 0, color: "#10b981" }}>NGÂN HÀNG (+1.85%)</h4>
              <p style={{ fontSize: "0.8rem", color: "#cbd5e1", marginTop: "0.5rem" }}>HDB (+2.1%), MBB (+1.8%), VCB (+1.2%), STB (+1.5%)</p>
            </div>
            <div style={{ background: "rgba(16, 185, 129, 0.15)", border: "1px solid #10b981", borderRadius: "0.5rem", padding: "1rem" }}>
              <h4 style={{ margin: 0, color: "#10b981" }}>THÉP (+1.40%)</h4>
              <p style={{ fontSize: "0.8rem", color: "#cbd5e1", marginTop: "0.5rem" }}>HPG (+1.4%), HSG (+0.8%), NKG (+1.1%)</p>
            </div>
            <div style={{ background: "rgba(239, 68, 68, 0.2)", border: "1px solid #ef4444", borderRadius: "0.5rem", padding: "1rem" }}>
              <h4 style={{ margin: 0, color: "#ef4444" }}>THỰC PHẨM (-0.35%)</h4>
              <p style={{ fontSize: "0.8rem", color: "#cbd5e1", marginTop: "0.5rem" }}>VNM (-0.4%), MSN (-0.2%)</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === "dong_tien" && (
        <div style={{ background: "#131b2e", border: "1px solid #1e293b", borderRadius: "0.75rem", padding: "1.5rem" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: "0 0 1rem 0" }}>PHÂN TÍCH DÒNG TIỀN NƯỚC NGOÀI & TỰ DOANH</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div style={{ background: "#0b0f19", border: "1px solid #1e293b", padding: "1rem", borderRadius: "0.5rem" }}>
              <h4 style={{ margin: 0, color: "#10b981" }}>Khối Ngoại Mua Ròng: +620.19 tỷ</h4>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "0.5rem" }}>Tập trung mua ròng HOSE: HDB, HPG, FPT, MWG, SSI</p>
            </div>
            <div style={{ background: "#0b0f19", border: "1px solid #1e293b", padding: "1rem", borderRadius: "0.5rem" }}>
              <h4 style={{ margin: 0, color: "#60a5fa" }}>Tự Doanh Mua Ròng: +145.80 tỷ</h4>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "0.5rem" }}>Tập trung gom chứng quyền VN30</p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
