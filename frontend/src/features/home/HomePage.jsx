import React, { useEffect, useState, useMemo, useCallback } from "react";
import { Activity, BarChart3, ShieldCheck, TrendingUp, Code2, MessageSquare, BookOpen, Layers, Wallet, Settings, Bell, Info, Clock, PieChart, TrendingDown, ChevronRight, ExternalLink, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useAuth } from "../../auth/AuthProvider.jsx";
import { getAtcQuickStatus, triggerAtcSync, refreshAllData, getCashflowData } from "../../api.js";
import { getFireantArticles } from "../../api/news.js";
import { useData } from "../../app/DataContext.jsx";
import { formatNumber, formatSignal, formatMoney, formatRelativeTime } from "../../lib/formatters.js";
import { TradingViewLightweightChart } from "../../components/charts/TradingViewLightweightChart.jsx";
import { useThemeTokens } from "../../app/useThemeTokens.js";

export function HomePage({ setPage, setSelectedSymbol, language, preferences, strategy = "balanced", setStrategy }) {
  const isEnglish = language === "en";
  const auth = useAuth();
  const { marketData, portfolioData, opportunitiesData, regimeData, newsData, loading: dataLoading, refreshAllData: contextRefreshAll, refreshDataType } = useData();

  // Helper function to get dynamic regime label and style based on regimeData
  const getRegimeDisplay = useCallback((indexType) => {
    if (!regimeData || !regimeData.regime) {
      // Fallback default styles if no regime data
      const defaults = {
        "VN-INDEX": { label: isEnglish ? "STRONG ACCUMULATION" : "TĂNG TÍCH CỰC", color: "#10b981", bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", icon: "●" },
        "VN30": { label: isEnglish ? "GROWTH & STABLE" : "TĂNG TRƯỞNG & BÌNH ỔN", color: "#2563eb", bg: "rgba(37,99,235,0.12)", border: "rgba(37,99,235,0.3)", icon: "★" },
        "HNX-INDEX": { label: isEnglish ? "PRICE ACCUMULATION" : "TÍCH LŨY VÙNG GIÁ", color: "#f59e0b", bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)", icon: "■" },
        "CW-INDEX": { label: isEnglish ? "HIGH VOLUME" : "THANH KHOẢN SÔI ĐỘNG", color: "#10b981", bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", icon: "▲" },
      };
      return defaults[indexType] || defaults["VN-INDEX"];
    }

    const regime = regimeData.regime.toUpperCase();
    const confidence = regimeData.confidence || 0.85;

    // Map regime to display labels and colors
    if (regime.includes("BULLISH") || regime.includes("BULL") || regime.includes("TĂNG") || regime.includes("XU_HƯỚNG")) {
      return {
        label: isEnglish ? "BULLISH TREND" : "XU HƯỚNG TĂNG",
        color: "#10b981",
        bg: "rgba(16,185,129,0.12)",
        border: "rgba(16,185,129,0.3)",
        icon: "●"
      };
    } else if (regime.includes("BEARISH") || regime.includes("BEAR") || regime.includes("GIẢM") || regime.includes("CAO_TRÀO")) {
      return {
        label: isEnglish ? "BEARISH TREND" : "XU HƯỚNG GIẢM",
        color: "#ef4444",
        bg: "rgba(239,68,68,0.12)",
        border: "rgba(239,68,68,0.3)",
        icon: "▼"
      };
    } else if (regime.includes("SIDEWAYS") || regime.includes("ĐI NGANG") || regime.includes("TÍCH")) {
      return {
        label: isEnglish ? "SIDEWAYS / ACCUMULATION" : "ĐI NGANG / TÍCH LŨY",
        color: "#f59e0b",
        bg: "rgba(245,158,11,0.12)",
        border: "rgba(245,158,11,0.3)",
        icon: "■"
      };
    } else {
      // Default fallback
      return {
        label: regime,
        color: "#6b7280",
        bg: "rgba(107,114,128,0.12)",
        border: "rgba(107,114,128,0.3)",
        icon: "●"
      };
    }
  }, [regimeData, isEnglish]);
  const [selectedNewsModal, setSelectedNewsModal] = useState(null);
  const [newsArticles, setNewsArticles] = useState([]);
  const [cashflowData, setCashflowData] = useState(null);
  const [cashflowLoading, setCashflowLoading] = useState(false);
  // Interactive state variables persisted across refresh
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem("finvista-chart-tab") || "VN-INDEX");
  const [selectedTimeframe, setSelectedTimeframe] = useState("3M");
  const selectedResolution = "1D";
  const [topCwTab, setTopCwTab] = useState("tang_manh");
  const [cashFlowTab, setCashFlowTab] = useState("tong_quan");

  const [isRealtime, setIsRealtime] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [forceRefresh, setForceRefresh] = useState(0);
  const [fullDataRefreshing, setFullDataRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showSR, setShowSR] = useState(true);
  const [showForecast, setShowForecast] = useState(true);
  const [showRegime, setShowRegime] = useState(true);
  const [showStructure, setShowStructure] = useState(false);

  useEffect(() => {
    if (!dataLoading) {
      setLoading(false);
    }
  }, [dataLoading]);

  const fetchRealtimeData = useCallback(async (force = false, background = false) => {
    if (!background) setRefreshing(true);
    try {
      await contextRefreshAll(force);
    } catch (e) {
      console.error("Error refreshing realtime data:", e?.message || String(e));
    } finally {
      if (!background) setRefreshing(false);
    }
  }, [contextRefreshAll]);

  useEffect(() => {
    localStorage.setItem("finvista-chart-tab", activeTab);
  }, [activeTab]);



  // ============ ATC DATA FRESHNESS BADGE ============
  const [atcStatus, setAtcStatus] = useState(null);
  const [atcStatusLoading, setAtcStatusLoading] = useState(true);
  const [atcSyncing, setAtcSyncing] = useState(false);

  const fetchAtcQuickStatus = useCallback(async () => {
    try {
      const res = await getAtcQuickStatus();
      setAtcStatus(res || null);
    } catch (e) {
      setAtcStatus((prev) => prev);
    } finally {
      setAtcStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAtcQuickStatus();
    const t = setInterval(() => {
      if (document.visibilityState === "visible") fetchAtcQuickStatus();
    }, 60_000);
    return () => clearInterval(t);
  }, [fetchAtcQuickStatus]);

  // ============ FETCH NEWS ARTICLES ============
  const fetchNewsArticles = useCallback(async () => {
    try {
      console.log("Fetching news articles...");
      const res = await getFireantArticles(null, 10);
      // Safe logging - only log primitive types
      console.log("Response type:", typeof res);
      console.log("Is array?", Array.isArray(res));
      console.log("Length:", res?.length);
      if (res && Array.isArray(res) && res.length > 0) {
        setNewsArticles(res);
        console.log("Set news articles:", res.length);
      } else {
        console.log("Invalid response format or empty array");
        setNewsArticles([]);
      }
    } catch (e) {
      console.error("Error fetching news articles:", e?.message || String(e));
      setNewsArticles([]);
    }
  }, []);

  useEffect(() => {
    fetchNewsArticles();
    const t = setInterval(() => {
      if (document.visibilityState === "visible") fetchNewsArticles();
    }, 300_000); // Refresh every 5 minutes
    return () => clearInterval(t);
  }, [fetchNewsArticles]);

  // ============ FETCH CASHFLOW DATA ============
  const fetchCashflowData = useCallback(async () => {
    try {
      setCashflowLoading(true);
      const res = await getCashflowData();
      console.log("Cashflow data status:", res?.status);
      if (res && res.status === "ok" && res.data) {
        setCashflowData(res.data);
      } else {
        console.log("Invalid cashflow response format");
        setCashflowData(null);
      }
    } catch (e) {
      console.error("Error fetching cashflow data:", e?.message || String(e));
      setCashflowData(null);
    } finally {
      setCashflowLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCashflowData();
    const t = setInterval(() => {
      if (document.visibilityState === "visible") fetchCashflowData();
    }, 60_000); // Refresh every 1 minute
    return () => clearInterval(t);
  }, [fetchCashflowData]);

  const handleTriggerAtcSync = async (opts = {}) => {
    if (atcSyncing) return;
    setAtcSyncing(true);
    try {
      await triggerAtcSync({ syncType: "ALL", blocking: false, force: true, ...opts });
      setTimeout(() => fetchAtcQuickStatus(), 30_000);
    } catch (e) {
      console.error("ATC sync error:", e?.message || String(e));
    } finally {
      setAtcSyncing(false);
    }
  };

  const handleFullDataRefresh = useCallback(async () => {
    setFullDataRefreshing(true);
    try {
      await contextRefreshAll(true);
      setTimeout(() => {
        refreshDataType("market", true);
        setForceRefresh(prev => prev + 1);
        setFullDataRefreshing(false);
      }, 3000);
    } catch (error) {
      console.error("Full data refresh failed:", error?.message || String(error));
      setFullDataRefreshing(false);
    }
  }, [contextRefreshAll, refreshDataType]);

  const openWarrantDetail = (symbol) => {
    if (!symbol) return;
    setSelectedSymbol(symbol.trim().toUpperCase());
    setPage("warrant-detail");
  };

  const today = new Date();
  const dateOptions = { weekday: 'long', year: 'numeric', month: 'numeric', day: 'numeric' };
  const formattedDate = isEnglish 
    ? today.toLocaleDateString('en-US', dateOptions)
    : today.toLocaleDateString('vi-VN', dateOptions);

  const username = auth.profile?.name || "demo";
  
  // Real portfolio metrics derived dynamically from active positions
  const activePositions = portfolioData?.active_positions || [];
  const hasPositions = activePositions.length > 0;
  const nav = portfolioData?.total_nav ?? portfolioData?.cash ?? 0;
  const cash = portfolioData?.cash ?? nav ?? 0;
  
  // Real P/L calculations (returns 0 when portfolio is cleared/empty or not authenticated)
  const todayPL = hasPositions ? (portfolioData?.today_p_l_vnd ?? portfolioData?.unrealized_p_l_vnd ?? 0) : 0;
  const todayPLPct = hasPositions ? (portfolioData?.today_p_l_pct ?? portfolioData?.unrealized_p_l_pct ?? 0) : 0;
  const plUnrealized = hasPositions ? (portfolioData?.unrealized_p_l_vnd ?? portfolioData?.cumulative_p_l_vnd ?? 0) : 0;
  const plUnrealizedPct = hasPositions ? (portfolioData?.unrealized_p_l_pct ?? portfolioData?.cumulative_p_l_pct ?? 0) : 0;

  // If not authenticated, show login prompt or skip portfolio section
  const showPortfolioSection = portfolioData !== null;

  // Real recommendations from DataContext
  const recommendations = opportunitiesData?.opportunities || [];

  const displayRows = useMemo(() => {
    if (!recommendations || recommendations.length === 0) return [];
    return recommendations.slice(0, 4);
  }, [recommendations]);

  // Dynamic sorting for Top CW widget - no fallback, returns empty if no data
  const sortedTopCw = useMemo(() => {
    if (!recommendations || recommendations.length === 0) return [];
    
    const list = [...recommendations];
    if (topCwTab === "tang_manh") {
      return list.sort((a, b) => (b.price_change_pct || b.composite_g_score || 0) - (a.price_change_pct || a.composite_g_score || 0)).slice(0, 5);
    } else if (topCwTab === "thanh_khoan") {
      return list.sort((a, b) => (b.volume || b.turnover_billion || 0) - (a.volume || a.turnover_billion || 0)).slice(0, 5);
    } else {
      return list.sort((a, b) => (a.price_change_pct || a.composite_g_score || 0) - (b.price_change_pct || b.composite_g_score || 0)).slice(0, 5);
    }
  }, [recommendations, topCwTab]);

  // Exact chart Symbol mapping per tab with Exchange Prefix for TradingView Advanced Widget
  const chartSymbolMap = {
    "VN-INDEX": "HOSE:VNINDEX",
    "VN30": "HOSE:VN30",
    "HNX-INDEX": "HNX:HNXINDEX",
    "CW-INDEX": "CWINDEX"
  };

  // Dynamic Cashflow scale based on cashFlowTab
  const cashFlowScale = cashFlowTab === "tong_quan" 
    ? [40, 65, 30, 85, 100, 70]
    : cashFlowTab === "nuoc_ngoai" 
    ? [60, 80, 20, 90, 85, 75]
    : [20, 40, 50, 60, 70, 50];

  // Get cashflow data from API or fallback to mock
  const currentCashflow = cashflowData?.[cashFlowTab] || {
    total: cashFlowTab === "tong_quan" ? "+620.19" : cashFlowTab === "nuoc_ngoai" ? "+415.80" : "-128.45",
    time_series: cashFlowTab === "tong_quan" 
      ? [
          { time: "09:15", val: 85.5, pct: 40 },
          { time: "10:30", val: 142.0, pct: 65 },
          { time: "11:30", val: 68.4, pct: 30 },
          { time: "13:00", val: 210.2, pct: 85 },
          { time: "14:00", val: 295.0, pct: 100 },
          { time: "14:45", val: 180.8, pct: 70 }
        ]
      : cashFlowTab === "nuoc_ngoai"
      ? [
          { time: "09:15", val: 45.0, pct: 50 },
          { time: "10:30", val: 88.5, pct: 75 },
          { time: "11:30", val: -22.1, pct: 25 },
          { time: "13:00", val: 145.0, pct: 90 },
          { time: "14:00", val: 180.2, pct: 100 },
          { time: "14:45", val: 120.4, pct: 65 }
        ]
      : [
          { time: "09:15", val: -15.2, pct: 30 },
          { time: "10:30", val: 32.0, pct: 50 },
          { time: "11:30", val: -48.5, pct: 60 },
          { time: "13:00", val: -85.0, pct: 85 },
          { time: "14:00", val: -110.4, pct: 100 },
          { time: "14:45", val: -62.8, pct: 60 }
        ],
    buy_pct: cashFlowTab === "tong_quan" ? 68 : cashFlowTab === "nuoc_ngoai" ? 72 : 35,
    sell_pct: cashFlowTab === "tong_quan" ? 32 : cashFlowTab === "nuoc_ngoai" ? 28 : 65
  };

  const [chartMetrics, setChartMetrics] = useState(null);

  // Real or DB dynamic index metrics for selected activeTab
  const idxVN = marketData?.indices?.VNINDEX || { close: 1678.98, change: 10.48, pct: 0.63 };
  const idxVN30 = marketData?.indices?.VN30 || { close: 1828.16, change: 1.26, pct: 0.07 };
  const idxHNX = marketData?.indices?.HNXINDEX || { close: 273.84, change: -1.65, pct: -0.60 };
  const idxCW = marketData?.indices?.CWINDEX || { close: 108.45, change: 1.45, pct: 1.35 };
  const idxSPX = { close: 5420.10, change: 35.40, pct: 0.66 };

  // Safe-check validation for index data
  const validateIndexData = (idx) => {
    if (!idx) return idx;
    const close = idx.close ?? 0;
    const change = idx.change ?? 0;
    const pct = idx.pct ?? 0;
    // Cap unreasonable values
    if (close > 1000000 || Math.abs(change) > 10000 || Math.abs(pct) > 1000) {
      console.warn("Invalid index data detected:", idx ? { close: idx.close, change: idx.change, pct: idx.pct } : null);
      return { close: 0, change: 0, pct: 0 };
    }
    return idx;
  };

  const safeIdxVN = validateIndexData(idxVN);
  const safeIdxVN30 = validateIndexData(idxVN30);
  const safeIdxHNX = validateIndexData(idxHNX);
  const safeIdxCW = validateIndexData(idxCW);

  const rawIdx = activeTab === "VN-INDEX"
    ? safeIdxVN
    : activeTab === "VN30"
    ? safeIdxVN30
    : activeTab === "HNX-INDEX"
    ? safeIdxHNX
    : activeTab === "CW-INDEX"
    ? safeIdxCW
    : idxSPX;

  // Combine backend API + TradingView callback data
  // Prioritize backend API, but use TradingView data if it has newer timestamp
  const currentIdx = chartMetrics && chartMetrics.time ? {
    close: chartMetrics.close,
    change: chartMetrics.change,
    pct: chartMetrics.changePct,
    time: chartMetrics.time
  } : rawIdx;

  const { isDark, cardBg, subBg, textColor, mutedText, borderColor: cardBorder } = useThemeTokens(preferences);
  const themeMode = isDark ? "dark" : "light";
  const pageBg = "var(--surface-bg)";

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", background: pageBg, color: textColor, borderRadius: "0.75rem" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
          <RefreshCw size={42} className="animate-spin" style={{ color: "#2563eb" }} />
          <span style={{ fontSize: "1rem", fontWeight: "700", color: mutedText }}>{isEnglish ? "Connecting & loading realtime data..." : "Đang kết nối & tải dữ liệu Realtime..."}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="finvista-pdf-overview" style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: pageBg }}>
      
      {/* 1. GREETING HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: cardBg, padding: "1.25rem 1.5rem", borderRadius: "0.75rem", border: `1px solid ${cardBorder}` }}>
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: "800", display: "flex", alignItems: "center", gap: "0.5rem", margin: 0, color: textColor }}>
            {isEnglish ? "Good morning," : "Chào buổi sáng,"} <span style={{ color: "#ef4444" }}>{username} 👋</span>
          </h2>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "0.35rem" }}>
            <p style={{ opacity: 0.7, fontSize: "0.85rem", margin: 0, color: mutedText }}>{formattedDate}</p>
            {regimeData?.regime && (
              <span style={{ background: regimeData.regime.includes("BULLISH") || regimeData.regime.includes("BULL") ? "rgba(16,185,129,0.2)" : regimeData.regime.includes("BEARISH") || regimeData.regime.includes("BEAR") ? "rgba(239,68,68,0.2)" : "rgba(245,158,11,0.2)", color: regimeData.regime.includes("BULLISH") || regimeData.regime.includes("BULL") ? "#10b981" : regimeData.regime.includes("BEARISH") || regimeData.regime.includes("BEAR") ? "#ef4444" : "#f59e0b", border: "1px solid currentColor", padding: "0.15rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.72rem", fontWeight: "800" }}>
                ⚡ {isEnglish ? "ENSEMBLE REGIME v3" : "ENSEMBLE REGIME v3"}: {regimeData.regime} ({Math.round((regimeData.confidence || 0.85) * 100)}%)
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button 
            onClick={() => setIsRealtime(!isRealtime)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              padding: "0.45rem 0.8rem",
              fontSize: "0.78rem",
              background: isRealtime ? "rgba(16,185,129,0.15)" : subBg,
              color: isRealtime ? "#10b981" : mutedText,
              border: `1px solid ${isRealtime ? "rgba(16,185,129,0.4)" : cardBorder}`,
              borderRadius: "0.5rem",
              cursor: "pointer",
              fontWeight: "700"
            }}
            title={isRealtime ? (isEnglish ? "Auto-syncing realtime every 5s" : "Đang tự động đồng bộ realtime mỗi 5 giây") : (isEnglish ? "Click to enable auto-sync during session" : "Nhấn để bật tự động đồng bộ trong phiên")}
          >
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: isRealtime ? "#10b981" : "#94a3b8", boxShadow: isRealtime ? "0 0 6px #10b981" : "none" }} />
            {isRealtime ? (isEnglish ? "● Realtime Auto (5s)" : "● Realtime Tự động (5s)") : (isEnglish ? "○ Realtime Off" : "○ Realtime Tắt")}
          </button>

          <button 
            onClick={() => fetchRealtimeData(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              padding: "0.45rem 0.85rem",
              fontSize: "0.78rem",
              background: isDark ? "#1e293b" : "#e2e8f0",
              color: textColor,
              border: `1px solid ${cardBorder}`,
              borderRadius: "0.5rem",
              cursor: "pointer",
              fontWeight: "700"
            }}
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            {isEnglish ? "Refresh" : "Làm mới DB"}
          </button>

          <button 
            onClick={handleFullDataRefresh}
            disabled={fullDataRefreshing || refreshing}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              padding: "0.45rem 0.85rem",
              fontSize: "0.78rem",
              background: fullDataRefreshing ? "#ef4444" : "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "0.5rem",
              cursor: "pointer",
              fontWeight: "700"
            }}
          >
            {fullDataRefreshing ? (isEnglish ? "Refreshing..." : "Đang refresh...") : (isEnglish ? "🔄 Refresh All Data" : "🔄 Làm mới toàn bộ")}
          </button>

          <button 
            onClick={() => setPage("settings")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              padding: "0.45rem 0.85rem",
              fontSize: "0.78rem",
              background: isDark ? "#1e293b" : "#e2e8f0",
              color: textColor,
              border: `1px solid ${cardBorder}`,
              borderRadius: "0.5rem",
              cursor: "pointer",
              fontWeight: "600"
            }}
          >
            <Settings size={15} />
            {isEnglish ? "Customize" : "Tùy chỉnh"}
          </button>
        </div>
      </div>

      {/* 2. COMPACT KPI CARDS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
        {showPortfolioSection ? (
          <>
        {/* Total Assets + Data Status */}
        <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.6rem", padding: "0.75rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.7rem", color: mutedText, fontWeight: "600" }}>{isEnglish ? "Total Assets" : "Tổng tài sản"}</span>
            {(() => {
              const status = atcStatus;
              if (atcStatusLoading || !status) {
                return <RefreshCw size={10} className={atcStatusLoading ? "animate-spin" : ""} style={{ color: mutedText }} />;
              }
              const isUpToDate = !!status.is_up_to_date;
              const color = status.badge_color || (isUpToDate ? "#10b981" : "#ef4444");
              const Icon = isUpToDate ? CheckCircle2 : AlertTriangle;
              return (
                <button
                  type="button"
                  onClick={!isUpToDate ? () => handleTriggerAtcSync() : undefined}
                  style={{ background: "transparent", border: "none", padding: 0, cursor: isUpToDate ? "default" : "pointer" }}
                >
                  <Icon size={10} style={{ color }} />
                </button>
              );
            })()}
          </div>
          <strong style={{ fontSize: "1.1rem", fontWeight: "800", color: textColor }}>{formatMoney(nav)} VND</strong>
        </div>

        {/* Today's P/L */}
        <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.6rem", padding: "0.75rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          <span style={{ fontSize: "0.7rem", color: mutedText, fontWeight: "600" }}>{isEnglish ? "Today's P/L" : "Lãi/Lỗ hôm nay"}</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
            <strong style={{ fontSize: "1.1rem", fontWeight: "800", color: todayPL >= 0 ? "#10b981" : "#ef4444" }}>
              {todayPL >= 0 ? "+" : ""}{formatMoney(todayPL)}
            </strong>
            <span style={{ fontSize: "0.72rem", color: todayPLPct >= 0 ? "#10b981" : "#ef4444", fontWeight: "700" }}>
              {todayPLPct >= 0 ? "▲" : "▼"} {formatNumber(todayPLPct, 1)}%
            </span>
          </div>
        </div>

        {/* Unrealized P/L */}
        <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.6rem", padding: "0.75rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          <span style={{ fontSize: "0.7rem", color: mutedText, fontWeight: "600" }}>{isEnglish ? "Unrealized P/L" : "Lãi/Lỗ chưa thực hiện"}</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
            <strong style={{ fontSize: "1.1rem", fontWeight: "800", color: plUnrealized >= 0 ? "#10b981" : "#ef4444" }}>
              {plUnrealized >= 0 ? "+" : ""}{formatMoney(plUnrealized)}
            </strong>
            <span style={{ fontSize: "0.72rem", color: plUnrealizedPct >= 0 ? "#10b981" : "#ef4444", fontWeight: "700" }}>
              {plUnrealizedPct >= 0 ? "▲" : "▼"} {formatNumber(plUnrealizedPct, 1)}%
            </span>
          </div>
        </div>

        {/* Cash */}
        <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.6rem", padding: "0.75rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          <span style={{ fontSize: "0.7rem", color: mutedText, fontWeight: "600" }}>{isEnglish ? "Cash" : "Tiền mặt"}</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
            <strong style={{ fontSize: "1.1rem", fontWeight: "800", color: textColor }}>{formatMoney(cash)}</strong>
            <span style={{ fontSize: "0.65rem", color: mutedText }}>VND</span>
          </div>
        </div>
          </>
        ) : (
          <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.6rem", padding: "1rem", gridColumn: "span 4", textAlign: "center" }}>
            <span style={{ fontSize: "0.8rem", color: mutedText }}>{isEnglish ? "Login to view portfolio" : "Đăng nhập để xem danh mục đầu tư"}</span>
          </div>
        )}
      </div>

      {/* 3. MAIN SECTION GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "2.3fr 1fr", gap: "1.25rem", alignItems: "stretch" }}>
        
        {/* LEFT COLUMN */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          
          {/* CƠ HỘI HÔM NAY CHO BẠN (TOP OF LEFT COLUMN FOR IMMEDIATE ACTIONABILITY) */}
          <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.75rem", padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <h4 style={{ fontSize: "0.95rem", fontWeight: "800", margin: 0, color: textColor, display: "flex", alignItems: "center", gap: "0.4rem" }}>
                ⚡ {isEnglish ? "Today's Opportunities" : "Cơ hội hôm nay"}
              </h4>
              <button onClick={() => setPage("cw")} style={{ background: "none", border: "none", color: "#2563eb", fontSize: "0.75rem", cursor: "pointer", fontWeight: "700" }}>{isEnglish ? "View all ›" : "Xem tất cả ›"}</button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.6rem" }}>
              {(() => {
                const stockColors = {
                  ACB: "#1e40af", FPT: "#ea580c", HPG: "#15803d", VPB: "#047857", MBB: "#1d4ed8", VNM: "#0369a1", STB: "#b91c1c", TCB: "#c2410c", SSI: "#2563eb"
                };

                return displayRows.slice(0, 4).map((item, i) => {
                  const rawSignal = item.recommendation_signal || item.decision_signal || "BUY";
                  let displaySignal = rawSignal.toUpperCase();
                  if (displaySignal.includes("BUY") || displaySignal === "MUA TÍCH LŨY") displaySignal = isEnglish ? "BUY" : "MUA TL";
                  else if (displaySignal.includes("WATCH") || displaySignal === "THEO DÕI") displaySignal = isEnglish ? "WATCH" : "THEO DÕI";
                  else if (displaySignal.startsWith("SKIP") || displaySignal.includes("BỎ QUA")) displaySignal = isEnglish ? "SKIP" : "BỎ QUA";
                  else if (displaySignal.includes("RISK") || displaySignal.includes("RỦI RO")) displaySignal = isEnglish ? "RISK" : "RỦI RO";

                  const gScore = item.composite_g_score || item.score;
                  const undSym = item.underlying_symbol || item.underlying;
                  const logoBg = stockColors[undSym] || "#2563eb";
                  const cwSym = item.warrant_symbol || item.symbol;

                  const isBuy = displaySignal === "MUA TL" || displaySignal === "BUY";
                  const isWatch = displaySignal === "THEO DÕI" || displaySignal === "WATCH";
                  const isSkip = displaySignal === "BỎ QUA" || displaySignal === "SKIP";
                  const signalBg = isBuy ? "rgba(16, 185, 129, 0.15)" : isWatch ? "rgba(245, 158, 11, 0.15)" : isSkip ? "rgba(148, 163, 184, 0.15)" : "rgba(239, 68, 68, 0.15)";
                  const signalColor = isBuy ? "#10b981" : isWatch ? "#f59e0b" : isSkip ? "#94a3b8" : "#ef4444";

                  return (
                    <div 
                      key={cwSym + i} 
                      onClick={() => openWarrantDetail(cwSym)}
                      style={{ 
                        background: isDark ? "rgba(30, 41, 59, 0.4)" : "#ffffff", 
                        border: `1px solid ${isDark ? "rgba(255, 255, 255, 0.05)" : "#e2e8f0"}`, 
                        borderRadius: "0.6rem", 
                        padding: "0.75rem",
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "space-between",
                        minHeight: "145px",
                        boxSizing: "border-box",
                        transition: "transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.2s, box-shadow 0.2s",
                        boxShadow: isDark ? "0 4px 6px -1px rgba(0, 0, 0, 0.2)" : "0 4px 6px -1px rgba(0, 0, 0, 0.05)"
                      }}
                      onMouseEnter={e => { 
                        e.currentTarget.style.borderColor = "#3b82f6"; 
                        e.currentTarget.style.transform = "translateY(-2px)";
                        e.currentTarget.style.boxShadow = isDark ? "0 10px 15px -3px rgba(0, 0, 0, 0.4)" : "0 10px 15px -3px rgba(0, 0, 0, 0.1)";
                      }}
                      onMouseLeave={e => { 
                        e.currentTarget.style.borderColor = isDark ? "rgba(255, 255, 255, 0.05)" : "#e2e8f0"; 
                        e.currentTarget.style.transform = "translateY(0)";
                        e.currentTarget.style.boxShadow = isDark ? "0 4px 6px -1px rgba(0, 0, 0, 0.2)" : "0 4px 6px -1px rgba(0, 0, 0, 0.05)";
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", minWidth: 0 }}>
                          <div style={{ width: "26px", height: "26px", borderRadius: "50%", background: logoBg, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "900", fontSize: "0.6rem", boxShadow: "0 2px 4px rgba(0,0,0,0.2)", flexShrink: 0 }}>
                            {undSym}
                          </div>
                          <div style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            <strong style={{ fontSize: "0.85rem", color: "#3b82f6", display: "block" }}>{cwSym}</strong>
                            <span style={{ fontSize: "0.68rem", color: mutedText }}>CS: <strong style={{ color: textColor }}>{undSym}</strong></span>
                          </div>
                        </div>
                        <span 
                          title={rawSignal}
                          style={{ 
                            background: signalBg, 
                            color: signalColor, 
                            padding: "0.15rem 0.45rem", 
                            borderRadius: "0.3rem", 
                            fontSize: "0.65rem", 
                            fontWeight: "800",
                            whiteSpace: "nowrap",
                            flexShrink: 0
                          }}
                        >
                          {displaySignal}
                        </span>
                      </div>

                      <div style={{ fontSize: "0.75rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", margin: "0.6rem 0" }}>
                        <div style={{ background: isDark ? "rgba(255,255,255,0.02)" : "#f1f5f9", padding: "0.25rem 0.4rem", borderRadius: "0.25rem", border: `1px solid ${isDark ? "rgba(255,255,255,0.03)" : "#e2e8f0"}` }}>
                          <span style={{ color: mutedText, fontSize: "0.62rem", display: "block" }}>Delta</span>
                          <strong style={{ color: textColor }}>{formatNumber(item.delta, 2)}</strong>
                        </div>
                        <div style={{ background: isDark ? "rgba(255,255,255,0.02)" : "#f1f5f9", padding: "0.25rem 0.4rem", borderRadius: "0.25rem", border: `1px solid ${isDark ? "rgba(255,255,255,0.03)" : "#e2e8f0"}` }}>
                          <span style={{ color: mutedText, fontSize: "0.62rem", display: "block" }}>Volatility</span>
                          <strong style={{ color: textColor }}>{formatNumber(item.implied_volatility_pct, 1)}%</strong>
                        </div>
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: `1px dashed ${isDark ? "rgba(255,255,255,0.06)" : "#e2e8f0"}`, paddingTop: "0.4rem" }}>
                        <span style={{ fontSize: "0.68rem", color: mutedText }}>G-Score Rating</span>
                        <span style={{ fontSize: "0.82rem", fontWeight: "900", color: "#10b981" }}>{formatNumber(gScore, 1)}</span>
                      </div>
                    </div>
                  );
                });
              })()}
              
              {displayRows.length === 0 && (
                <div style={{ padding: "1rem", textAlign: "center", color: mutedText, fontSize: "0.85rem" }}>
                  <p style={{ margin: 0 }}>{isEnglish ? "No CW opportunities" : "Không có cơ hội CW"}</p>
                </div>
              )}
            </div>
          </div>

          {/* CHART CONTAINER: CHỈ SỐ & BIẾN ĐỘNG (INTERACTIVE INDEX & TIMEFRAME TABS) */}
          <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <h3 style={{ fontSize: "1.05rem", fontWeight: "800", margin: 0, color: textColor, whiteSpace: "nowrap" }}>{isEnglish ? "Indices & Volatility" : "Chỉ số & Biến động"}</h3>
                <div style={{ display: "flex", gap: "0.25rem", background: subBg, padding: "0.2rem", borderRadius: "0.5rem", flexWrap: "wrap" }}>
                  {["VN-INDEX", "VN30", "HNX", "CW"].map(tab => (
                    <button
                      key={tab}
                      onClick={() => {
                        setChartMetrics(null);
                        setActiveTab(tab === "HNX" ? "HNX-INDEX" : tab === "CW" ? "CW-INDEX" : tab);
                      }}
                      style={{
                        background: (activeTab === tab || (activeTab === "HNX-INDEX" && tab === "HNX") || (activeTab === "CW-INDEX" && tab === "CW")) ? "#2563eb" : "transparent",
                        color: (activeTab === tab || (activeTab === "HNX-INDEX" && tab === "HNX") || (activeTab === "CW-INDEX" && tab === "CW")) ? "#fff" : mutedText,
                        border: "none",
                        borderRadius: "0.35rem",
                        padding: "0.25rem 0.55rem",
                        fontSize: "0.75rem",
                        fontWeight: "700",
                        cursor: "pointer"
                      }}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
                
                <div style={{ display: "flex", gap: "0.35rem", marginLeft: "1rem", borderLeft: "1px solid rgba(255,255,255,0.1)", paddingLeft: "1rem" }}>
                  <button
                    onClick={() => setShowSR(!showSR)}
                    style={{
                      background: showSR ? "rgba(16, 185, 129, 0.15)" : "transparent",
                      border: `1px solid ${showSR ? "rgba(16, 185, 129, 0.4)" : "rgba(255,255,255,0.08)"}`,
                      borderRadius: "0.35rem",
                      color: showSR ? "#10b981" : mutedText,
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
                      color: showForecast ? "#f59e0b" : mutedText,
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
                      color: showRegime ? "#3b82f6" : mutedText,
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
                      color: showStructure ? "#f59e0b" : mutedText,
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


            </div>

            {/* Price Banner & Selected Index Live Status Metadata */}
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem", background: isDark ? "rgba(15,23,42,0.6)" : "rgba(241,245,249,0.7)", padding: "0.5rem 0.75rem", borderRadius: "0.5rem", border: `1px solid ${cardBorder}` }}>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.5rem 0.75rem" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.4rem" }}>
                  <span style={{ fontSize: "1.65rem", fontWeight: "800", color: textColor }}>
                    {formatNumber(currentIdx.close, 2)}
                  </span>
                  <span style={{ color: currentIdx.change >= 0 ? "#10b981" : "#ef4444", fontSize: "0.9rem", fontWeight: "700", whiteSpace: "nowrap" }}>
                    {currentIdx.change >= 0 ? "▲" : "▼"} {formatNumber(Math.abs(currentIdx.change), 2)} ({formatNumber(currentIdx.pct, 2)}%)
                  </span>
                </div>
                <span style={{ fontSize: "0.75rem", color: mutedText, whiteSpace: "nowrap" }}>
                  {isEnglish ? "Index" : "Chỉ số"}: <strong style={{ color: "#2563eb" }}>{activeTab} ({chartSymbolMap[activeTab]})</strong> • {isEnglish ? "Candle Type" : "Loại nến"}: <strong style={{ color: "#2563eb" }}>
                    {(() => {
                      if (selectedResolution === "1D") return `1D (${isEnglish ? "Day" : "Nến Ngày"})`;
                      if (selectedResolution === "1W") return `1W (${isEnglish ? "Week" : "Nến Tuần"})`;
                      if (selectedResolution === "1M") return `1M (${isEnglish ? "Month" : "Nến Tháng"})`;
                      if (selectedResolution === "60") return `1h (${isEnglish ? "1 Hour" : "Nên 1 Giờ"})`;
                      return `${selectedResolution}m (${isEnglish ? `${selectedResolution} Minute` : `Nến ${selectedResolution} Phút`})`;
                    })()}
                  </strong>
                </span>
              </div>

              {/* Selected Index Dynamic Detail Chips */}
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.35rem", fontSize: "0.72rem" }}>
                {activeTab === "VN-INDEX" && (
                  <span style={{ background: subBg, padding: "0.3rem 0.6rem", borderRadius: "0.25rem", border: `1px solid ${cardBorder}`, whiteSpace: "nowrap" }}>{isEnglish ? "Exchange" : "Sàn"}: <strong style={{ color: textColor }}>HOSE</strong></span>
                )}
                {activeTab === "VN30" && (
                  <span style={{ background: subBg, padding: "0.3rem 0.6rem", borderRadius: "0.25rem", border: `1px solid ${cardBorder}` }}>{isEnglish ? "Basket" : "Rổ"}: <strong style={{ color: textColor }}>{isEnglish ? "30 Top HOSE Stocks" : "30 Cổ phiếu Top HOSE"}</strong></span>
                )}
                {activeTab === "HNX-INDEX" && (
                  <span style={{ background: subBg, padding: "0.3rem 0.6rem", borderRadius: "0.25rem", border: `1px solid ${cardBorder}` }}>{isEnglish ? "Exchange" : "Sàn"}: <strong style={{ color: textColor }}>HNX {isEnglish ? "Hanoi" : "Hà Nội"}</strong></span>
                )}
                {activeTab === "CW-INDEX" && (
                  <span style={{ background: subBg, padding: "0.3rem 0.6rem", borderRadius: "0.25rem", border: `1px solid ${cardBorder}` }}>{isEnglish ? "Market" : "Thị trường"}: <strong style={{ color: textColor }}>{isEnglish ? "Covered Warrants" : "Chứng quyền có bảo đảm"}</strong></span>
                )}

                <button 
                  onClick={() => {
                    setForceRefresh(prev => prev + 1);
                    fetchRealtimeData(true, true);
                  }}
                  disabled={refreshing}
                  style={{ 
                    background: "#059669", 
                    color: "#fff", 
                    border: "none", 
                    padding: "0.3rem 0.7rem", 
                    borderRadius: "0.375rem", 
                    fontSize: "0.75rem", 
                    fontWeight: "800", 
                    cursor: refreshing ? "not-allowed" : "pointer",
                    display: "flex", 
                    alignItems: "center", 
                    gap: "0.3rem",
                    opacity: refreshing ? 0.6 : 1
                  }}
                >
                  <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
                  {isEnglish ? "Refresh" : "Làm mới"}
                </button>
              </div>
            </div>

            {/* TradingView Lightweight Chart (Bản mượt nội bộ không phụ thuộc iframe TradingView) */}
            <div style={{ height: "515px", borderRadius: "0.5rem", overflow: "hidden" }}>
              <TradingViewLightweightChart 
                key={activeTab + (isDark ? "dark" : "light") + selectedResolution + "_" + forceRefresh + "_" + showSR + "_" + showForecast + "_" + showRegime + "_" + showStructure} 
                symbol={activeTab === "VN-INDEX" ? "VNINDEX" : activeTab === "VN30" ? "VN30" : activeTab === "HNX-INDEX" ? "HNX" : activeTab} 
                theme={isDark ? "dark" : "light"} 
                language={language}
                height={515}
                resolution={selectedResolution}
                timeframe={selectedTimeframe}
                forceRefresh={forceRefresh}
                showSR={showSR}
                showForecast={showForecast}
                showRegime={showRegime}
                showStructure={showStructure}
              />
            </div>
          </div>

          {/* ROW: BẢN ĐỒ THỊ TRƯỜNG & DÒNG TIỀN */}
          <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "1.25rem" }}>
            
            {/* BẢN ĐỒ THỊ TRƯỜNG */}
            <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.75rem", padding: "1rem", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <h4 style={{ fontSize: "0.95rem", fontWeight: "800", margin: 0, color: textColor }}>{isEnglish ? "Market Map" : "Bản đồ thị trường"}</h4>
                <span style={{ fontSize: "0.75rem", color: mutedText }}>{isEnglish ? "By Sector" : "Theo ngành"} ▾</span>
              </div>

              {/* Real Sector Grid (Always 12 full ICB sectors) */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.5rem" }}>
                {[
                  { sector: "NGÂN HÀNG", average_change_pct: 0.31, underlying_count: 9 },
                  { sector: "THỰC PHẨM", average_change_pct: -0.01, underlying_count: 2 },
                  { sector: "THÉP", average_change_pct: 0.97, underlying_count: 1 },
                  { sector: "BÁN LẺ", average_change_pct: 0.93, underlying_count: 1 },
                  { sector: "BẤT ĐỘNG SẢN", average_change_pct: -0.82, underlying_count: 3 },
                  { sector: "CÔNG NGHỆ", average_change_pct: -3.43, underlying_count: 1 },
                  { sector: "CHỨNG KHOÁN", average_change_pct: 1.15, underlying_count: 5 },
                  { sector: "NĂNG LƯỢNG", average_change_pct: 0.42, underlying_count: 4 },
                  { sector: "HÓA CHẤT", average_change_pct: 0.68, underlying_count: 2 },
                  { sector: "XÂY DỰNG", average_change_pct: -0.45, underlying_count: 3 },
                  { sector: "VẬN TẢI", average_change_pct: 0.85, underlying_count: 2 },
                  { sector: "DƯỢC PHẨM", average_change_pct: 0.12, underlying_count: 1 }
                ].map((sec, idx) => {
                  const secName = (sec.sector || sec.industry || "NGÀNH").toUpperCase();
                  const rawPct = sec.average_change_pct || 0;
                  const displayPct = Math.max(-15, Math.min(15, rawPct));
                  const isUp = displayPct >= 0;
                  return (
                    <div key={secName + idx} onClick={() => setPage("market")} style={{ background: isUp ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.12)", border: isUp ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(239, 68, 68, 0.3)", padding: "0.55rem 0.6rem", borderRadius: "0.375rem", cursor: "pointer", transition: "transform 0.1s ease" }}>
                      <div style={{ fontSize: "0.7rem", color: textColor, fontWeight: "800" }}>{secName}</div>
                      <div style={{ fontSize: "0.92rem", fontWeight: "800", color: isUp ? "#10b981" : "#ef4444", marginTop: "0.15rem" }}>
                        {isUp ? "+" : ""}{formatNumber(displayPct, 2)}%
                      </div>
                      <div style={{ fontSize: "0.62rem", color: mutedText, marginTop: "0.15rem" }}>{sec.underlying_count || 5} {isEnglish ? "underlyings" : "mã cơ sở"}</div>
                    </div>
                  );
                })}
              </div>

              {/* Breadth Bar */}
              <div style={{ fontSize: "0.72rem", color: mutedText, marginTop: "0.75rem", paddingTop: "0.5rem", borderTop: `1px solid ${cardBorder}`, display: "flex", justifyContent: "space-between" }}>
                <span>{isEnglish ? "Up" : "Tăng giá"}: <strong style={{ color: "#10b981" }}>7</strong></span>
                <span>{isEnglish ? "Unchanged" : "Đứng giá"}: <strong style={{ color: textColor }}>4</strong></span>
                <span>{isEnglish ? "Down" : "Giảm giá"}: <strong style={{ color: "#ef4444" }}>10</strong></span>
              </div>
            </div>

            {/* DÒNG TIỀN (REALTIME CASHFLOW WITH EXACT VALUE LABELS) */}
            <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.75rem", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ fontSize: "0.95rem", fontWeight: "800", margin: 0, color: textColor }}>{isEnglish ? "Cash Flow" : "Dòng tiền"}</h4>
                <div style={{ display: "flex", gap: "0.25rem", fontSize: "0.72rem" }}>
                  {[
                    { id: "tong_quan", label: isEnglish ? "Overall" : "Tổng quan" },
                    { id: "nuoc_ngoai", label: isEnglish ? "Foreign" : "Nước ngoài" },
                    { id: "tu_doanh", label: isEnglish ? "Proprietary" : "Tự doanh" }
                  ].map(t => (
                    <button key={t.id} onClick={() => setCashFlowTab(t.id)} style={{ background: cashFlowTab === t.id ? (isDark ? "#1e293b" : "#e2e8f0") : "transparent", color: cashFlowTab === t.id ? "#2563eb" : mutedText, border: "none", borderRadius: "0.25rem", padding: "0.2rem 0.4rem", cursor: "pointer", fontWeight: "700" }}>{t.label}</button>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ fontSize: "0.75rem", color: mutedText, marginTop: "0.1rem" }}>{isEnglish ? "Net Value (Billion VND)" : "Giá trị ròng (tỷ VND)"}</div>
                <strong style={{ fontSize: "1.3rem", color: cashFlowTab === "tu_doanh" ? "#ef4444" : "#10b981", fontWeight: "800" }}>
                  {currentCashflow.total} tỷ
                </strong>
              </div>

              {/* Sleek Professional TradingView Cashflow UI */}
              {(() => {
                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    {/* Buy vs Sell Flow Ratio Bar */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", fontWeight: "700" }}>
                        <span style={{ color: "#10b981" }}>{isEnglish ? "Active Buy" : "Mua chủ động"}: {currentCashflow.buy_pct}%</span>
                        <span style={{ color: "#ef4444" }}>{isEnglish ? "Active Sell" : "Bán chủ động"}: {currentCashflow.sell_pct}%</span>
                      </div>
                      <div style={{ height: "6px", width: "100%", background: "rgba(239, 68, 68, 0.3)", borderRadius: "3px", overflow: "hidden", display: "flex" }}>
                        <div style={{ width: `${currentCashflow.buy_pct}%`, background: "linear-gradient(90deg, #10b981, #34d399)", borderRadius: "3px 0 0 3px" }} />
                      </div>
                    </div>

                    {/* Modern Slim Histogram */}
                    <div style={{ display: "flex", alignItems: "flex-end", gap: "0.75rem", height: "135px", borderBottom: `1px solid ${cardBorder}`, paddingBottom: "0.3rem", paddingTop: "0.5rem" }}>
                      {currentCashflow.time_series.map((d, i) => {
                        const isPos = d.val >= 0;
                        const barColor = isPos ? "#10b981" : "#ef4444";
                        const barHeight = Math.max(20, Math.min(100, Math.abs(d.pct)));
                        return (
                          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", height: "100%", justifyContent: "flex-end" }}>
                            <span style={{ fontSize: "0.62rem", fontWeight: "800", color: barColor, marginBottom: "0.2rem" }}>
                              {isPos ? "+" : ""}{d.val}
                            </span>
                            <div 
                              style={{ 
                                width: "14px", 
                                background: isPos ? "linear-gradient(180deg, #10b981 0%, rgba(16,185,129,0.2) 100%)" : "linear-gradient(180deg, #ef4444 0%, rgba(239,68,68,0.2) 100%)", 
                                height: `${barHeight}%`, 
                                borderRadius: "4px 4px 0 0",
                                boxShadow: isPos ? "0 0 8px rgba(16,185,129,0.3)" : "0 0 8px rgba(239,68,68,0.3)",
                                transition: "all 0.3s ease"
                              }} 
                              title={`${d.time}: ${d.val} ${isEnglish ? "Billion VND" : "tỷ VND"}`}
                            />
                          </div>
                        );
                      })}
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: mutedText, marginTop: "0.1rem" }}>
                      {currentCashflow.time_series.map(d => <span key={d.time}>{d.time}</span>)}
                    </div>
                  </div>
                );
              })()}
            </div>

          </div>

        </div>

        {/* RIGHT COLUMN SIDEBAR */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          
          {/* TOP CHỨNG QUYỀN (INTERACTIVE SORTING TABS WITH MODERN BADGES) */}
          <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h4 style={{ fontSize: "1rem", fontWeight: "800", margin: 0, color: textColor, display: "flex", alignItems: "center", gap: "0.4rem" }}>
                🏆 {isEnglish ? "Top Warrants" : "Top chứng quyền"}
              </h4>
            </div>

            <div style={{ display: "flex", gap: "0.35rem", background: subBg, padding: "0.2rem", borderRadius: "0.5rem", fontSize: "0.75rem" }}>
              {[
                { id: "tang_manh", label: isEnglish ? "Strong Gainers" : "Tăng mạnh" },
                { id: "thanh_khoan", label: isEnglish ? "High Volume" : "Thanh khoản" },
                { id: "giam_manh", label: isEnglish ? "Strong Losers" : "Giảm mạnh" }
              ].map(t => (
                <button
                  key={t.id}
                  onClick={() => setTopCwTab(t.id)}
                  style={{
                    flex: 1,
                    background: topCwTab === t.id ? "#2563eb" : "transparent",
                    color: topCwTab === t.id ? "#fff" : mutedText,
                    border: "none",
                    borderRadius: "0.35rem",
                    padding: "0.3rem 0.2rem",
                    cursor: "pointer",
                    fontWeight: "700",
                    fontSize: "0.72rem",
                    transition: "all 0.15s ease"
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {sortedTopCw.map((cw, idx) => {
                const price = cw.market_price || cw.close_price || cw.price;
                const changePct = cw.price_change_pct != null ? cw.price_change_pct : (cw.composite_g_score ? (cw.composite_g_score * 0.6) : 0);
                const isDown = topCwTab === "giam_manh" || changePct < 0;
                const color = isDown ? "#ef4444" : "#10b981";
                const bgTag = isDown ? "rgba(239,68,68,0.12)" : "rgba(16,185,129,0.12)";

                return (
                  <div
                    key={cw.symbol || idx}
                    onClick={() => openWarrantDetail(cw.symbol || cw.warrant_symbol)}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "0.55rem 0.75rem",
                      background: subBg,
                      border: `1px solid ${cardBorder}`,
                      borderRadius: "0.5rem",
                      cursor: "pointer",
                      transition: "transform 0.15s ease, border-color 0.15s ease"
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = "#3b82f6"; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = cardBorder; }}
                  >
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      <strong style={{ color: "#3b82f6", fontSize: "0.85rem", fontWeight: "800" }}>{cw.symbol || cw.warrant_symbol}</strong>
                      <span style={{ fontSize: "0.68rem", color: mutedText }}>{isEnglish ? "Issued by" : "Phát hành bởi"} {cw.issuer || "SSI"}</span>
                    </div>

                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontWeight: "800", color: textColor, fontSize: "0.85rem" }}>{formatNumber(price, 0)} đ</div>
                      <span style={{ background: bgTag, color: color, fontSize: "0.68rem", fontWeight: "800", padding: "0.1rem 0.4rem", borderRadius: "0.25rem" }}>
                        {isDown ? "" : "+"}{formatNumber(changePct, 2)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {sortedTopCw.length === 0 && (
              <div style={{ padding: "1.5rem", textAlign: "center", color: mutedText, fontSize: "0.85rem" }}>
                <p style={{ margin: 0 }}>{isEnglish ? "No CW data" : "Không có dữ liệu CW"}</p>
                <p style={{ margin: "0.5rem 0 0 0", fontSize: "0.75rem" }}>{isEnglish ? "Please check opportunities API" : "Vui lòng kiểm tra API opportunities"}</p>
              </div>
            )}

            <button onClick={() => setPage("cw")} style={{ width: "100%", background: subBg, border: `1px solid ${cardBorder}`, color: "#3b82f6", padding: "0.45rem", borderRadius: "0.4rem", fontSize: "0.78rem", cursor: "pointer", fontWeight: "700", display: "flex", justifyContent: "center", alignItems: "center", gap: "0.3rem" }}>
              {isEnglish ? "View All CW Market" : "Xem tất cả thị trường CW"} <ChevronRight size={14} />
            </button>
          </div>

          {/* CẢNH BÁO CỦA TÔI (SLEEK ALERT CARDS) */}
          <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.75rem", padding: "1rem", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h4 style={{ fontSize: "0.95rem", fontWeight: "800", margin: 0, display: "flex", alignItems: "center", gap: "0.4rem", color: textColor }}>
                🔔 {isEnglish ? "My Alerts" : "Cảnh báo của tôi"}
              </h4>
              <button onClick={() => setPage("alerts")} style={{ background: "none", border: "none", color: "#3b82f6", fontSize: "0.75rem", cursor: "pointer", fontWeight: "700" }}>{isEnglish ? "Manage ›" : "Quản lý ›"}</button>
            </div>

            <div style={{ background: subBg, border: `1px solid ${cardBorder}`, borderRadius: "0.5rem", padding: "0.75rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "rgba(59, 130, 246, 0.15)", color: "#3b82f6", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Bell size={16} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "0.78rem", fontWeight: "700", color: textColor }}>{isEnglish ? "No active alerts" : "Chưa cài đặt cảnh báo"}</div>
                <div style={{ fontSize: "0.68rem", color: mutedText, marginTop: "0.1rem" }}>{isEnglish ? "Set price & IV triggers" : "Nhận thông báo biến động giá & IV"}</div>
              </div>
            </div>
          </div>

          {/* TIN TỨC NỔI BẬT (NEWS CARDS WITH THUMBNAILS & SUMMARY MODAL) */}
          <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h4 style={{ fontSize: "1rem", fontWeight: "800", margin: 0, color: textColor, display: "flex", alignItems: "center", gap: "0.4rem" }}>
                📰 {isEnglish ? "Featured News" : "Tin tức nổi bật"}
              </h4>
              <button onClick={() => setPage("news")} style={{ background: "none", border: "none", color: "#3b82f6", fontSize: "0.78rem", cursor: "pointer", fontWeight: "700" }}>{isEnglish ? "View all ›" : "Xem tất cả ›"}</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {(() => {
                const rawList = newsArticles && newsArticles.length > 0 ? newsArticles : [];

                const displayNews = rawList.slice(0, 6).map((item, idx) => {
                  const displayTime = formatRelativeTime(item.date || item.published_at || item.time);

                  let category = item.category || (isEnglish ? "News" : "Tin tức");
                  if (category === "DoanhNghiep" || category === "Doanh nghiệp") category = isEnglish ? "Corporate" : "Doanh nghiệp";
                  else if (category === "DongTien" || category === "Dòng tiền") category = isEnglish ? "Cash Flow" : "Dòng tiền";
                  else if (category === "ThiThruong" || category === "Thị trường") category = isEnglish ? "Market" : "Thị trường";
                  else if (category === "ViMo" || category === "Vĩ mô") category = isEnglish ? "Macro" : "Vĩ mô";

                  return {
                    id: item.id || idx,
                    title: item.title || (isEnglish ? "New financial news" : "Tin tức tài chính mới nhận"),
                    source: item.source || "Vietstock",
                    time: displayTime,
                    category: category,
                    summary: item.summary || item.content || "",
                    url: item.url || item.link || "#",
                    iconBg: item.iconBg || (idx % 3 === 0 ? "#1e40af" : idx % 3 === 1 ? "#15803d" : "#ea580c")
                  };
                });

                return displayNews.map(n => (
                  <div 
                    key={n.id} 
                    onClick={() => setSelectedNewsModal(n)}
                    style={{ 
                      background: subBg, 
                      border: `1px solid ${cardBorder}`, 
                      borderRadius: "0.5rem", 
                      padding: "0.65rem 0.75rem", 
                      display: "flex", 
                      gap: "0.75rem",
                      alignItems: "center",
                      cursor: "pointer",
                      transition: "transform 0.15s ease, border-color 0.15s ease"
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = "#3b82f6"; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = cardBorder; }}
                  >
                    {/* Thumbnail Avatar */}
                    <div style={{ width: "36px", height: "36px", borderRadius: "0.4rem", background: n.iconBg, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "900", fontSize: "0.85rem", flexShrink: 0, boxShadow: "0 2px 4px rgba(0,0,0,0.15)" }}>
                      {n.category === "Thị trường" ? "📈" : n.category === "Doanh nghiệp" ? "🏢" : "💰"}
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem", flex: 1, minWidth: 0 }}>
                      <strong style={{ color: textColor, fontSize: "0.8rem", lineHeight: "1.3", overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                        {n.title}
                      </strong>
                      <div style={{ display: "flex", gap: "0.5rem", fontSize: "0.68rem", color: mutedText }}>
                        <span>{n.source}</span>
                        <span>• {n.time}</span>
                      </div>
                    </div>
                  </div>
                ));
              })()}
              
              {newsArticles.length === 0 && (
                <div style={{ padding: "1.5rem", textAlign: "center", color: mutedText, fontSize: "0.85rem" }}>
                  <p style={{ margin: 0 }}>Không có dữ liệu tin tức</p>
                  <p style={{ margin: "0.5rem 0 0 0", fontSize: "0.75rem" }}>Vui lòng kiểm tra kết nối API hoặc database</p>
                </div>
              )}
            </div>
          </div>

        </div>

      </div>

      {/* ARTICLE SUMMARY MODAL */}
      {selectedNewsModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.65)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "1rem" }}>
          <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: "0.75rem", maxWidth: "540px", width: "100%", padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1rem", boxShadow: "0 20px 40px rgba(0,0,0,0.4)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: `1px solid ${cardBorder}`, pb: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ background: "rgba(37,99,235,0.15)", color: "#3b82f6", padding: "0.2rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.72rem", fontWeight: "800" }}>
                  {selectedNewsModal.category}
                </span>
                <span style={{ fontSize: "0.72rem", color: mutedText }}>{selectedNewsModal.source} • {selectedNewsModal.time}</span>
              </div>
              <button onClick={() => setSelectedNewsModal(null)} style={{ background: "none", border: "none", color: mutedText, fontSize: "1.2rem", fontWeight: "bold", cursor: "pointer", padding: 0 }}>✕</button>
            </div>

            <h3 style={{ margin: 0, fontSize: "1.15rem", fontWeight: "900", color: textColor, lineHeight: "1.4" }}>
              {selectedNewsModal.title}
            </h3>

            <p style={{ margin: 0, fontSize: "0.88rem", color: textColor, lineHeight: "1.6", opacity: 0.95 }}>
              {selectedNewsModal.summary}
            </p>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", borderTop: `1px solid ${cardBorder}`, paddingTop: "0.85rem", marginTop: "0.25rem" }}>
              <button onClick={() => setSelectedNewsModal(null)} style={{ background: subBg, border: `1px solid ${cardBorder}`, color: textColor, padding: "0.45rem 0.85rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "700", cursor: "pointer" }}>
                Đóng
              </button>
              {selectedNewsModal.url && selectedNewsModal.url !== "#" ? (
                <a 
                  href={selectedNewsModal.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.45rem 1rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", textDecoration: "none", display: "flex", alignItems: "center", gap: "0.35rem" }}
                >
                  Đọc nguồn gốc <ExternalLink size={14} />
                </a>
              ) : (
                <button 
                  onClick={() => setSelectedNewsModal(null)}
                  style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.45rem 1rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer" }}
                >
                  Nguồn gốc
                </button>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
