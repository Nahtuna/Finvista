import React, { useEffect, useState, useMemo } from "react";
import { ArrowUpRight, ArrowDownRight, TrendingUp, BarChart3, PieChart, Newspaper, Tag, Search, RefreshCw, ExternalLink, Loader2, Maximize2, Minimize2 } from "lucide-react";
import { useData } from "../../app/DataContext.jsx";
import { TradingViewLightweightChart } from "../../components/charts/TradingViewLightweightChart.jsx";
import { formatNumber, formatMoney } from "../../lib/formatters.js";
import { useThemeTokens } from "../../app/useThemeTokens.js";
import { refreshMarketScan } from "../../api/warrants.js";
import { ErrorBoundary } from "../../components/ErrorBoundary.jsx";
import { MacroBar } from "./components/MacroBar.jsx";
import { VNDerivativesWidget } from "./components/VNDerivativesWidget.jsx";
import { SeasonalAnalysisWidget } from "./components/SeasonalAnalysisWidget.jsx";
import { TechnicalGaugeWidget } from "./components/TechnicalGaugeWidget.jsx";

export function MarketPage({ setPage, setSelectedSymbol, language, preferences = {} }) {
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const isEnglish = language === "en";
  const { marketData, opportunitiesData, regimeData, refreshDataType } = useData();
  const [activeTab, setActiveTab] = useState("tong_quan");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndustry, setSelectedIndustry] = useState("all");
  const [loading, setLoading] = useState(false);
  const [forceRefresh, setForceRefresh] = useState(0);
  const [isChartFullscreen, setIsChartFullscreen] = useState(false);
  const [showSR, setShowSR] = useState(true);
  const [showForecast, setShowForecast] = useState(true);
  const [showRegime, setShowRegime] = useState(true);
  const [showStructure, setShowStructure] = useState(false);
  const getRegimeDescription = (regime, isEn) => {
    const r = regime || "BULLISH_VOL_EXPANSION";
    if (r.includes("BULLISH_VOL_EXPANSION")) {
      return isEn 
        ? "The market is in a Bullish Volume Expansion phase (high momentum & high volatility). Ideal environment for buying Call covered warrants with high G-Scores."
        : "Thị trường đang ở pha Tăng giá Mở rộng Biến động (động lực tăng và biến động cao). Môi trường tối ưu để giải ngân Mua các mã chứng quyền Call có G-Score cao.";
    }
    if (r.includes("BULLISH_VOL_CONTRACTION")) {
      return isEn
        ? "The market is in a Bullish Volume Contraction phase (steady accumulation & low volatility). Suitable for steady holding and accumulating quality stocks."
        : "Thị trường đang ở pha Tăng giá Tích lũy (tăng trưởng ổn định và biến động thấp). Thích hợp để nắm giữ và gom thêm cổ phiếu chất lượng.";
    }
    if (r.includes("SIDEWAYS")) {
      return isEn
        ? "The market is in a Sideways/Turbulent phase. Volatility is high but trend direction is unclear. Caution is advised, consider reducing position size."
        : "Thị trường đang ở pha Đi ngang biến động. Biến động cao nhưng xu hướng không rõ ràng. Khuyến nghị thận trọng, cân nhắc hạ tỷ trọng danh mục.";
    }
    if (r.includes("BEARISH")) {
      return isEn
        ? "The market is in a Bearish High Volatility phase (Risk-Off). Significant downside risk detected. Recommend holding cash and avoiding new covered warrant entries."
        : "Thị trường đang ở pha Giảm giá rủi ro cao (Risk-Off). Phát hiện rủi ro giảm giá lớn. Khuyến nghị ưu tiên giữ tiền mặt và tạm dừng mua mới chứng quyền.";
    }
    return isEn 
      ? "Market regime state identified by HMM Multi-Timeframe engine."
      : "Trạng thái thị trường được xác định bởi mô hình HMM đa khung thời gian.";
  };

  async function loadMarket(force = false) {
    setLoading(true);
    try {
      if (force) {
        await refreshMarketScan("balanced");
      }
      await refreshDataType("market", force);
      await refreshDataType("opportunities", force);
    } catch (e) {
      console.error("Error refreshing market:", e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMarket(false);
  }, [forceRefresh]);

  const stocks = useMemo(() => {
    // Backend API returns underlyings array containing real stock objects
    const raw = marketData?.underlyings || marketData?.stocks || [];
    return raw;
  }, [marketData]);

  const warrants = opportunitiesData?.opportunities || [];

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
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg, paddingBottom: "4rem" }}>

      {/* HEADER SECTION */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: "900", margin: 0, color: textColor }}>
            {isEnglish ? "VIETNAM STOCK MARKET (VN30, DERIVATIVES & WARRANTS)" : "THỊ TRƯỜNG CHỨNG KHOÁN VIỆT NAM (VN30, PHÁI SINH & CW)"}
          </h2>
          <p style={{ fontSize: "0.8rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
            Biến động realtime · Phái sinh VN30F · Định giá Chứng quyền · Phân tích rủi ro tín dụng
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button 
            onClick={() => loadMarket(true)} 
            disabled={loading}
            style={{ 
              background: "#059669", 
              color: "#fff", 
              border: "none", 
              padding: "0.4rem 0.8rem", 
              borderRadius: "0.375rem", 
              fontSize: "0.85rem", 
              cursor: loading ? "not-allowed" : "pointer", 
              display: "flex", 
              alignItems: "center", 
              gap: "0.35rem", 
              fontWeight: "700",
              opacity: loading ? 0.6 : 1
            }}
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Làm mới DB
          </button>
        </div>
      </div>

      {/* 1. MACRO BAR */}
      <ErrorBoundary fallback="Failed to load macro data">
        <MacroBar marketData={marketData} preferences={preferences} language={language} />
      </ErrorBoundary>

      {/* 2. DERIVATIVES BAR */}
      <ErrorBoundary fallback="Failed to load derivatives data">
        <VNDerivativesWidget marketData={marketData} preferences={preferences} language={language} />
      </ErrorBoundary>

      {/* 3. MARKET BREADTH BAR */}
      {(() => {
        const allStocks = stocks;
        const advances = allStocks.filter(s => (s.change_pct ?? s.pct_change ?? 0) > 0).length;
        const declines = allStocks.filter(s => (s.change_pct ?? s.pct_change ?? 0) < 0).length;
        const unchanged = allStocks.length - advances - declines;
        const totalVol = allStocks.reduce((sum, s) => sum + (s.stock_volume || s.total_volume || 0), 0);
        const regime = regimeData?.regime || "";
        const regimeColor = regime.includes("BEAR") ? "#ef4444" : regime.includes("SIDEWAYS") ? "#f59e0b" : "#10b981";
        return (
          <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.85rem 1.25rem", display: "flex", alignItems: "center", gap: "1.5rem", flexWrap: "wrap" }}>
            <div style={{ display: "flex", gap: "1rem", fontSize: "0.82rem", fontWeight: "700", alignItems: "center" }}>
              <span style={{ color: mutedText }}>{isEnglish ? "Market Breadth (HOSE):" : "Độ rộng thị trường (HOSE):"}</span>
              <span style={{ color: "#10b981" }}>▲ {advances} {isEnglish ? "Up" : "Tăng"}</span>
              <span style={{ color: "#ef4444" }}>▼ {declines} {isEnglish ? "Down" : "Giảm"}</span>
              <span style={{ color: mutedText }}>— {unchanged} {isEnglish ? "Flat" : "Đứng"}</span>
            </div>
            <div style={{ fontSize: "0.82rem", color: mutedText, fontWeight: "600" }}>
              {isEnglish ? "Total Vol:" : "Tổng KLGD:"} <span style={{ color: textColor, fontWeight: "700" }}>{(totalVol / 1e6).toFixed(1)}M</span>
            </div>
            {regime && (
              <span
                style={{ marginLeft: "auto", background: `${regimeColor}20`, color: regimeColor, border: `1px solid ${regimeColor}`, borderRadius: "0.375rem", padding: "0.25rem 0.75rem", fontSize: "0.75rem", fontWeight: "800" }}
              >
                CREED: {regime}
              </span>
            )}
          </div>
        );
      })()}

      {/* 4. UNDERLYING STOCKS BOARD (FULL WIDTH) */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: "800", margin: 0, color: "#10b981", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            BẢNG GIÁ CỔ PHIẾU CƠ SỞ DB REALTIME ({filteredStocks.length} MÃ KẾT QUẢ)
            {loading && <Loader2 size={16} className="animate-spin" style={{ color: "#10b981" }} />}
          </h3>

          {/* SEARCH BAR & KEYWORD TAGS */}
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Search size={16} style={{ color: mutedText }} />
              <input
                placeholder="Tìm kiếm mã cổ phiếu cơ sở..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.4rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.82rem", width: "220px" }}
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
                  <th style={{ padding: "0.6rem", textAlign: "left" }}>Mã cổ phiếu</th>
                  <th style={{ padding: "0.6rem", textAlign: "left" }}>Tên công ty</th>
                  <th style={{ padding: "0.6rem", textAlign: "left" }}>Ngành</th>
                  <th style={{ padding: "0.6rem", textAlign: "right" }}>Giá hiện tại</th>
                  <th style={{ padding: "0.6rem", textAlign: "right" }}>Biến động</th>
                  <th style={{ padding: "0.6rem", textAlign: "center" }}>Chi tiết</th>
                  <th style={{ padding: "0.6rem", textAlign: "right" }}>Khối lượng GD</th>
                  <th style={{ padding: "0.6rem", textAlign: "right" }}>Số lượng CW</th>
                </tr>
              </thead>
              <tbody>
                {filteredStocks.map((stk) => {
                  const priceVal = stk.price || stk.close_price;
                  const changeVal = stk.change_pct !== undefined ? stk.change_pct : (stk.pct_change);
                  const volVal = stk.stock_volume || stk.total_volume;

                  return (
                    <tr key={stk.symbol} style={{ borderBottom: `1px solid ${borderColor}` }}>
                      <td style={{ padding: "0.75rem 0.6rem", fontWeight: "800", color: "#3b82f6", cursor: "pointer", textAlign: "left" }} onClick={() => openWarrantDetail(stk.symbol)}>{stk.symbol}</td>
                      <td style={{ padding: "0.75rem 0.6rem", color: textColor, textAlign: "left" }}>{stk.company_name || stk.symbol}</td>
                      <td style={{ padding: "0.75rem 0.6rem", color: mutedText, textAlign: "left" }}>{stk.industry || "Ngân hàng"}</td>
                      <td style={{ padding: "0.75rem 0.6rem", fontWeight: "700", color: textColor, textAlign: "right" }}>{formatMoney(priceVal)} đ</td>
                      <td style={{ padding: "0.75rem 0.6rem", color: changeVal >= 0 ? "#10b981" : "#ef4444", fontWeight: "700", textAlign: "right" }}>
                        {changeVal >= 0 ? "+" : ""}{formatNumber(changeVal, 2)}%
                      </td>
                      <td style={{ padding: "0.75rem 0.6rem", textAlign: "center" }}>
                        <button
                          onClick={() => openWarrantDetail(stk.symbol)}
                          style={{
                            background: "rgba(59,130,246,0.1)",
                            color: "#3b82f6",
                            border: "1px solid rgba(59,130,246,0.3)",
                            padding: "0.3rem 0.6rem",
                            borderRadius: "0.3rem",
                            fontSize: "0.72rem",
                            fontWeight: "700",
                            cursor: "pointer",
                            transition: "all 0.15s"
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = "rgba(59,130,246,0.2)"}
                          onMouseLeave={e => e.currentTarget.style.background = "rgba(59,130,246,0.1)"}
                        >
                          Chi tiết
                        </button>
                      </td>
                      <td style={{ padding: "0.75rem 0.6rem", color: textColor, textAlign: "right" }}>{Math.round(volVal).toLocaleString()}</td>
                      <td style={{ padding: "0.75rem 0.6rem", fontWeight: "700", color: "#f59e0b", textAlign: "right" }}>{stk.cw_count || 0} mã</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 4. TECHNICAL ANALYSIS GAUGES & SEASONAL ANALYSIS */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1.25rem" }}>
        <ErrorBoundary fallback="Failed to load technical gauges">
          <TechnicalGaugeWidget symbol="VNINDEX" preferences={preferences} language={language} />
        </ErrorBoundary>

        <ErrorBoundary fallback="Failed to load seasonal analysis">
          <SeasonalAnalysisWidget symbol="VNINDEX" preferences={preferences} language={language} />
        </ErrorBoundary>
      </div>

      {/* FIREANT-STYLE MODAL FOR FULL-SCREEN CHART */}
      {isChartFullscreen && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(11, 15, 25, 0.8)",
          backdropFilter: "blur(12px)",
          zIndex: 9999,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "2rem",
        }}>
          <div 
            onClick={() => setIsChartFullscreen(false)} 
            style={{ position: "absolute", inset: 0 }} 
          />
          
          <div style={{
            position: "relative",
            width: "92%",
            maxWidth: "1280px",
            height: "85vh",
            background: "#131b2e",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: "0.85rem",
            display: "grid",
            gridTemplateColumns: "2fr 1fr",
            overflow: "hidden",
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.6)",
            zIndex: 10000,
          }}>
            {/* LEFT SIDE: Active Chart */}
            <div style={{ display: "flex", flexDirection: "column", borderRight: "1px solid rgba(255, 255, 255, 0.08)", padding: "1.25rem", height: "100%", minWidth: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <div>
                  <h3 style={{ fontSize: "1.25rem", fontWeight: "900", margin: 0, color: "#fff", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    VNINDEX <span style={{ fontSize: "0.75rem", background: "rgba(16, 185, 129, 0.12)", color: "#10b981", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "2rem", padding: "0.15rem 0.5rem", fontWeight: "700" }}>Live</span>
                  </h3>
                  <span style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: "500" }}>
                    {isEnglish ? "Market Regime & Greeks Analysis" : "Mô hình Trạng thái Thị trường & Greeks"}
                  </span>
                </div>
                {/* Control Toggles */}
                <div style={{ display: "flex", gap: "0.35rem" }}>
                  <button
                    onClick={() => setShowSR(!showSR)}
                    style={{
                      background: showSR ? "rgba(16, 185, 129, 0.15)" : "transparent",
                      border: `1px solid ${showSR ? "rgba(16, 185, 129, 0.4)" : "rgba(255,255,255,0.08)"}`,
                      borderRadius: "0.35rem",
                      color: showSR ? "#10b981" : "#94a3b8",
                      padding: "0.2rem 0.5rem",
                      fontSize: "0.7rem",
                      fontWeight: "700",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.25rem",
                      transition: "all 0.2s"
                    }}
                  >
                    🔍 S/R
                  </button>
                  <button
                    onClick={() => setShowForecast(!showForecast)}
                    style={{
                      background: showForecast ? "rgba(245, 158, 11, 0.15)" : "transparent",
                      border: `1px solid ${showForecast ? "rgba(245, 158, 11, 0.4)" : "rgba(255,255,255,0.08)"}`,
                      borderRadius: "0.35rem",
                      color: showForecast ? "#f59e0b" : "#94a3b8",
                      padding: "0.2rem 0.5rem",
                      fontSize: "0.7rem",
                      fontWeight: "700",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.25rem",
                      transition: "all 0.2s"
                    }}
                  >
                    🔮 {isEnglish ? "Forecast" : "Dự báo"}
                  </button>
                  <button
                    onClick={() => setShowRegime(!showRegime)}
                    style={{
                      background: showRegime ? "rgba(59, 130, 246, 0.15)" : "transparent",
                      border: `1px solid ${showRegime ? "rgba(59, 130, 246, 0.4)" : "rgba(255,255,255,0.08)"}`,
                      borderRadius: "0.35rem",
                      color: showRegime ? "#3b82f6" : "#94a3b8",
                      padding: "0.2rem 0.5rem",
                      fontSize: "0.7rem",
                      fontWeight: "700",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.25rem",
                      transition: "all 0.2s"
                    }}
                  >
                    🌐 Regime
                  </button>
                  <button
                    onClick={() => setShowStructure(!showStructure)}
                    style={{
                      background: showStructure ? "rgba(245, 158, 11, 0.15)" : "transparent",
                      border: `1px solid ${showStructure ? "rgba(245, 158, 11, 0.4)" : "rgba(255,255,255,0.08)"}`,
                      borderRadius: "0.35rem",
                      color: showStructure ? "#f59e0b" : "#94a3b8",
                      padding: "0.2rem 0.5rem",
                      fontSize: "0.7rem",
                      fontWeight: "700",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.25rem",
                      transition: "all 0.2s"
                    }}
                  >
                    📐 {isEnglish ? "Structure" : "Cấu trúc"}
                  </button>
                </div>
              </div>
              
              <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
                <TradingViewLightweightChart
                  symbol="VNINDEX"
                  height={window.innerHeight * 0.85 - 120}
                  resolution="1D"
                  timeframe="3M"
                  theme="dark"
                  showSR={showSR}
                  showForecast={showForecast}
                  showRegime={showRegime}
                  showStructure={showStructure}
                />
              </div>
            </div>

            {/* RIGHT SIDE: Profile Stats */}
            <div style={{ display: "flex", flexDirection: "column", height: "100%", overflowY: "auto", padding: "1.25rem", background: "#0b0f19" }}>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "0.75rem" }}>
                <button 
                  onClick={() => setIsChartFullscreen(false)}
                  style={{
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "0.375rem",
                    padding: "0.35rem 0.75rem",
                    fontSize: "0.8rem",
                    color: "#f1f5f9",
                    cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.1)"}
                  onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
                >
                  ✕ Đóng
                </button>
              </div>

              <div>
                <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: "#3b82f6", marginTop: 0, marginBottom: "1rem", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  {isEnglish ? "Market Summary" : "Thống kê tổng hợp"}
                </h4>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  {[
                    { label: "Mã chứng khoán", value: "VNINDEX", color: "#fff" },
                    { label: "Giá hiện tại", value: formatNumber(marketData?.indices?.VNINDEX?.close ?? 1777.23, 2), color: "#fff" },
                    { label: "Thay đổi", value: `${(marketData?.indices?.VNINDEX?.change ?? 14.39) >= 0 ? "+" : ""}${formatNumber(marketData?.indices?.VNINDEX?.change ?? 14.39, 2)} (${formatNumber(marketData?.indices?.VNINDEX?.pct ?? 0.82, 2)}%)`, color: (marketData?.indices?.VNINDEX?.change ?? 0.82) >= 0 ? "#10b981" : "#ef4444" },
                    { label: "Khối lượng GD", value: formatNumber(marketData?.indices?.VNINDEX?.volume ?? 686900000, 0), color: "#fff" },
                    { label: "Trạng thái chính (Regime)", value: regimeData?.regime || "BEARISH_VOL_CONTRACTION", color: "#f59e0b" },
                    { label: "Độ tin cậy mô hình", value: `${Math.round((regimeData?.confidence ?? 0.66) * 100)}%`, color: "#fff" },
                    { label: "Xu hướng Master", value: regimeData?.master_trend || "UPTREND", color: "#10b981" },
                    { label: "Vị thế khuyến nghị", value: regimeData?.bias || "CASH_ONLY", color: "#ef4444" },
                    { label: "Độ lệch EMA 200", value: `${(regimeData?.dist_from_trend_pct ?? 4.2) >= 0 ? "+" : ""}${formatNumber(regimeData?.dist_from_trend_pct ?? 4.2, 1)}%`, color: (regimeData?.dist_from_trend_pct ?? 0) >= 0 ? "#10b981" : "#ef4444" },
                    { label: "Biến động ATR (14D)", value: formatNumber(regimeData?.atr14 ?? 14.8, 1), color: "#fff" },
                  ].map(item => (
                    <div key={item.label} style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 0", borderBottom: "1px solid rgba(255,255,255,0.04)", fontSize: "0.82rem" }}>
                      <span style={{ color: "#64748b", fontWeight: "500" }}>{item.label}</span>
                      <span style={{ color: item.color, fontWeight: "700" }}>{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
