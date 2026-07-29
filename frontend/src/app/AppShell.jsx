import React, { useEffect, useState, useCallback } from "react";

import { getHealth, getUnderlyingMarket, getAtcQuickStatus } from "../api.js";
import { getMarketRegime } from "../api/regime.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { ProfileMenu } from "../components/layout/ProfileMenu.jsx";
import { HomePage } from "../features/home/HomePage.jsx";
import { MarketPage } from "../features/market/MarketPage.jsx";
import { OpportunitiesPage } from "../features/opportunities/OpportunitiesPage.jsx";
import { SettingsPage } from "../features/settings/SettingsPage.jsx";
import { WarrantDetailPage } from "../features/warrant-detail/WarrantDetailPage.jsx";
import { PortfolioPage } from "../features/portfolio/PortfolioPage.jsx";

import { WatchlistPage } from "../features/watchlist/WatchlistPage.jsx";
import { LearningPage } from "../features/learning/LearningPage.jsx";
import { AlertsPage } from "../features/alerts/AlertsPage.jsx";
import { ProductsPage } from "../features/products/ProductsPage.jsx";
import { NewsPage } from "../features/news/NewsPage.jsx";
import { AIChatWidget } from "../components/chat/AIChatWidget.jsx";
import { LoginPage } from "../pages/LoginPage.jsx";
import { LandingPage } from "../pages/LandingPage.jsx";
import { NAV_ITEMS, STORAGE_KEYS } from "./config.js";
import { usePreferences } from "./usePreferences.js";
import {
  Sun, Moon, Bell, BellOff, HelpCircle, Mail,
  LayoutDashboard, BarChart2, ScanLine, PieChart, Briefcase,
  Bookmark, BookOpen, Newspaper, Zap
} from "lucide-react";

// Icon component map keyed by icon name string from config
const NAV_ICONS = {
  LayoutDashboard, BarChart2, ScanLine, PieChart, Briefcase,
  Bookmark, BookOpen, Newspaper, Bell, Zap
};


export function AppShell() {
  const auth = useAuth();
  const [page, setPage] = useState(() => {
    const saved = localStorage.getItem("finvista-active-page");
    // Show landing page only for brand-new visitors (no saved page)
    return saved || "landing";
  });
  const { language, setLanguage, preferences, setPreferences } = usePreferences();
  const [strategy, setStrategy] = useState(() => localStorage.getItem(STORAGE_KEYS.strategy) || "balanced");
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [regime, setRegime] = useState(null);

  // ========== ATC STATUS (for sidebar Market Active badge) ==========
  const [atcQuick, setAtcQuick] = useState(null);
  const refreshAtcQuick = useCallback(() => {
    getAtcQuickStatus().then((r) => setAtcQuick(r || null)).catch(() => {});
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.strategy, strategy);
  }, [strategy]);
  const [marketIndices, setMarketIndices] = useState(() => {
    try {
      const saved = localStorage.getItem("finvista-market-indices");
      return saved ? JSON.parse(saved) : null;
    } catch (_) {
      return null;
    }
  });
  const [showAlertsDropdown, setShowAlertsDropdown] = useState(false);

  useEffect(() => {
    localStorage.setItem("finvista-active-page", page);
  }, [page]);

  // Notifications: empty until real alert system is implemented
  const notifications = [];

  async function refreshHealth() {
    setHealthLoading(true);
    setHealthError("");
    try {
      const result = await getHealth();
      setHealth(result);
    } catch (err) {
      setHealthError(err.message);
    } finally {
      setHealthLoading(false);
    }
  }

  useEffect(() => {
    refreshHealth();
    refreshAtcQuick();
    getMarketRegime().then(setRegime).catch(() => {});
    getUnderlyingMarket().then(res => {
      if (res?.indices) {
        setMarketIndices(res.indices);
        localStorage.setItem("finvista-market-indices", JSON.stringify(res.indices));
      }
    }).catch(() => {});

    // Regime: 10s poll (signal-critical)
    const regimeInterval = setInterval(() => {
      getMarketRegime().then(setRegime).catch(() => {});
    }, 10_000);

    // Market indices: 30s poll (less volatile)
    const marketInterval = setInterval(() => {
      getUnderlyingMarket({ forceRefresh: false }).then(res => {
        if (res?.indices) {
          setMarketIndices(res.indices);
          localStorage.setItem("finvista-market-indices", JSON.stringify(res.indices));
        }
      }).catch(() => {});
    }, 30_000);

    // ATC data freshness: 2 minutes poll (non-critical, just for badge display)
    const atcInterval = setInterval(() => {
      if (document.visibilityState === "visible") refreshAtcQuick();
    }, 120_000);

    return () => {
      clearInterval(regimeInterval);
      clearInterval(marketInterval);
      clearInterval(atcInterval);
    };
  }, [refreshAtcQuick]);


  const currentNavItems = NAV_ITEMS[language] || NAV_ITEMS.en;

  if (auth.authEnabled && auth.loading) {
    return (
      <main className={`login-shell color-${preferences.colorMode}`}>
        <section className="login-panel">
          <div className="brand-mark">F</div>
          <p className="notice loading" style={{ marginTop: "1.25rem" }}>
            {language === "en" ? "Checking your sign-in session…" : "Đang kiểm tra phiên đăng nhập…"}
          </p>
        </section>
      </main>
    );
  }

  if (auth.authEnabled && !auth.profile) {
    return <LoginPage auth={auth} language={language} colorMode={preferences.colorMode} />;
  }

  const toggleColorMode = () => {
    setPreferences({
      ...preferences,
      colorMode: preferences.colorMode === "light" ? "dark" : "light"
    });
  };

  const isDark = preferences.colorMode === "dark";
  // Use CSS custom properties for colors — avoids duplicating theme logic in JS
  const sidebarBorder = isDark ? "rgba(255,255,255,0.08)" : "#e2e8f0";
  const sidebarTextColor = isDark ? "#94a3b8" : "#475569";
  const sidebarActiveBg = isDark ? "rgba(37,99,235,0.15)" : "#e0e7ff";
  const sidebarActiveColor = isDark ? "#60a5fa" : "#1d4ed8";
  const headerBorder = isDark ? "rgba(255,255,255,0.08)" : "#e2e8f0";
  const headerTextColor = isDark ? "#ffffff" : "#0f172a";
  const searchBg = isDark ? "rgba(255,255,255,0.04)" : "#f1f5f9";
  const searchBorder = isDark ? "rgba(255,255,255,0.1)" : "#cbd5e1";
  const searchColor = isDark ? "#fff" : "#0f172a";


  // Full-screen landing page — no sidebar/header
  if (page === "landing") {
    return <LandingPage onEnterApp={() => setPage("intro")} />;
  }

  return (
    <div
      className={[
        "app-shell",
        `theme-${preferences.theme}`,
        `color-${preferences.colorMode}`,
        `density-${preferences.density}`,
        preferences.smoothMotion ? "motion-smooth" : "motion-static",
        preferences.tableHints ? "hints-on" : "hints-off"
      ].join(" ")}
      style={{ display: "grid", gridTemplateColumns: "260px 1fr", minHeight: "100vh" }}
    >
      {/* LEFT SIDEBAR NAVIGATION */}
      <aside className="sidebar-nav" style={{
        background: isDark ? "var(--surface-bg, #0b0f19)" : "#ffffff",
        borderRight: `1px solid ${sidebarBorder}`,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        height: "100vh",
        position: "sticky",
        top: 0,
        padding: "1.25rem 1rem"
      }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Logo brand from Finvista.pdf */}
          <button className="brand" onClick={() => setPage("intro")} style={{ background: "none", border: "none", textAlign: "left", display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.25rem 0", cursor: "pointer" }}>
            <span className="brand-mark" style={{ background: "linear-gradient(135deg, #ef4444 0%, #2563eb 100%)", color: "#fff", width: "38px", height: "38px", borderRadius: "0.6rem", display: "grid", placeItems: "center", fontWeight: "900", fontSize: "1.25rem", boxShadow: "0 4px 14px rgba(239, 68, 68, 0.35)", flexShrink: 0 }}>F</span>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: "1.15rem", fontWeight: "900", color: isDark ? "#ffffff" : "#0f172a", letterSpacing: "0.75px", lineHeight: "1.1" }}>FINVISTA</span>
              <span style={{ fontSize: "0.6rem", color: isDark ? "#94a3b8" : "#64748b", fontWeight: "600", marginTop: "0.15rem" }}>Quantitative Edge, Smarter Decisions.</span>
            </div>
          </button>

          {/* Navigation Links */}
          <nav aria-label="Main navigation" style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            {currentNavItems.map((item) => {
              const Icon = NAV_ICONS[item.icon];
              return (
                <button
                  key={item.id}
                  className={`sidebar-nav-item ${page === item.id ? "active" : ""}`}
                  onClick={() => setPage(item.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.6rem",
                    width: "100%",
                    padding: "0.6rem 0.85rem",
                    borderRadius: "0.375rem",
                    background: page === item.id ? sidebarActiveBg : "transparent",
                    color: page === item.id ? sidebarActiveColor : sidebarTextColor,
                    border: page === item.id ? (isDark ? "1px solid rgba(255,255,255,0.12)" : "1px solid rgba(0,0,0,0.12)") : "1px solid transparent",
                    fontSize: "0.875rem",
                    fontWeight: page === item.id ? "700" : "500",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 0.15s"
                  }}
                >
                  {Icon && <Icon size={15} style={{ flexShrink: 0, opacity: page === item.id ? 1 : 0.7 }} />}
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer Extras */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", borderTop: `1px solid ${sidebarBorder}`, paddingTop: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: sidebarTextColor, fontSize: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "0.35rem", color: "#10b981", fontWeight: "600" }}>
              <span style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: atcQuick?.badge_color || "#10b981",
                boxShadow: `0 0 0 2px ${(atcQuick?.badge_color || "#10b981")}22`,
              }}></span>
              {language === "en" ? "Market Active" : "Thị trường hoạt động"}
            </span>
            {/* Data date tag: hiển thị ngày data STOCK/CW */}
            {atcQuick && (
              <span
                title={atcQuick.long_text || ""}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  padding: "0.12rem 0.45rem",
                  borderRadius: "999px",
                  background: `${atcQuick.badge_color || "#10b981"}15`,
                  color: atcQuick.badge_color || "#10b981",
                  border: `1px solid ${(atcQuick.badge_color || "#10b981")}33`,
                  fontWeight: "700",
                  letterSpacing: "0.1px",
                }}
              >
                {atcQuick.is_up_to_date
                  ? (language === "en"
                      ? `Data ${atcQuick.expected_trading_day_fmt || ""}`
                      : `Data ${atcQuick.expected_trading_day_fmt || ""}`)
                  : (atcQuick.stock_latest_fmt && atcQuick.cw_latest_fmt
                      ? (language === "en"
                          ? `CK ${atcQuick.stock_latest_fmt} · CW ${atcQuick.cw_latest_fmt}`
                          : `CK ${atcQuick.stock_latest_fmt} · CW ${atcQuick.cw_latest_fmt}`)
                      : (language === "en" ? "Outdated" : "Cũ"))}
              </span>
            )}
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button onClick={() => setPage("settings")} style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", padding: 0 }} title="Settings & Help"><HelpCircle size={15} /></button>
              <a href="mailto:support@finvista.vn" style={{ color: "inherit" }} title="Support Email"><Mail size={15} /></a>
            </div>
          </div>
        </div>
      </aside>

      {/* RIGHT WORKSPACE */}
      <div style={{ display: "flex", flexDirection: "column", background: "transparent", minHeight: "100vh", overflowX: "hidden" }}>
        
        {/* HEADER STRIP */}
        <header className="header-strip" style={{
          minHeight: "64px",
          borderBottom: `1px solid ${headerBorder}`,
          padding: "0.5rem 1.5rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
          background: isDark ? "var(--surface-bg, #0b0f19)" : "#ffffff",
          position: "sticky",
          top: 0,
          zIndex: 10
        }}>

          {/* Global Search Bar */}
          <div style={{ position: "relative", flexShrink: 0 }}>
            <input
              type="text"
              placeholder={language === "en" ? "Search CW, stocks, indices..." : "Tìm kiếm mã CW, cổ phiếu..."}
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && selectedSymbol.trim()) {
                  setSelectedSymbol(selectedSymbol.trim().toUpperCase());
                  setPage("detail");
                }
              }}
              style={{
                background: searchBg,
                border: `1px solid ${searchBorder}`,
                borderRadius: "0.375rem",
                padding: "0.4rem 0.75rem",
                fontSize: "0.82rem",
                color: searchColor,
                width: "220px"
              }}
            />
          </div>

          {/* Market Index Animated Ticker Ribbon */}
          <div style={{ flex: 1, overflow: "hidden", position: "relative", margin: "0 1rem", minWidth: 0 }}>
            <style>{`
              @keyframes tickerMarquee {
                0% { transform: translateX(0%); }
                100% { transform: translateX(-50%); }
              }
              .ticker-track:hover {
                animation-play-state: paused;
              }
            `}</style>
            <div 
              className="ticker-track"
              style={{ 
                display: "flex", 
                gap: "2.5rem", 
                fontSize: "0.8rem", 
                fontWeight: "700", 
                alignItems: "center", 
                whiteSpace: "nowrap",
                width: "max-content",
                animation: "tickerMarquee 25s linear infinite"
              }}
            >
              {[1, 2].map((loop) => (
                <React.Fragment key={loop}>
                  {/* VN-INDEX */}
                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>VN-INDEX</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.VNINDEX?.close ?? marketIndices?.vnindex?.close ?? 1284.50).toLocaleString()}</span>
                    <span style={{ color: ((marketIndices?.VNINDEX?.change ?? marketIndices?.vnindex?.change) ?? 0.41) >= 0 ? "#10b981" : "#ef4444" }}>
                      {((marketIndices?.VNINDEX?.change ?? marketIndices?.vnindex?.change) ?? 0.41) >= 0 ? "▲" : "▼"} {Math.abs((marketIndices?.VNINDEX?.change ?? marketIndices?.vnindex?.change) ?? 0.41).toFixed(2)} ({((marketIndices?.VNINDEX?.pct ?? marketIndices?.vnindex?.pct) ?? 0.41).toFixed(2)}%)
                    </span>
                  </div>
                  {/* VN30 */}
                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>VN30</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.VN30?.close ?? marketIndices?.vn30?.close ?? 1312.80).toLocaleString()}</span>
                    <span style={{ color: ((marketIndices?.VN30?.change ?? marketIndices?.vn30?.change) ?? 0.47) >= 0 ? "#10b981" : "#ef4444" }}>
                      {((marketIndices?.VN30?.change ?? marketIndices?.vn30?.change) ?? 0.47) >= 0 ? "▲" : "▼"} {Math.abs((marketIndices?.VN30?.change ?? marketIndices?.vn30?.change) ?? 0.47).toFixed(2)} ({((marketIndices?.VN30?.pct ?? marketIndices?.vn30?.pct) ?? 0.47).toFixed(2)}%)
                    </span>
                  </div>
                  {/* HNX */}
                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>HNX</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.HNXINDEX?.close ?? marketIndices?.hnx?.close ?? 242.15).toLocaleString()}</span>
                    <span style={{ color: ((marketIndices?.HNXINDEX?.change ?? marketIndices?.hnx?.change) ?? -0.60) >= 0 ? "#10b981" : "#ef4444" }}>
                      {((marketIndices?.HNXINDEX?.change ?? marketIndices?.hnx?.change) ?? -0.60) >= 0 ? "▲" : "▼"} {Math.abs((marketIndices?.HNXINDEX?.change ?? marketIndices?.hnx?.change) ?? 0.60).toFixed(2)} ({((marketIndices?.HNXINDEX?.pct ?? marketIndices?.hnx?.pct) ?? -0.60).toFixed(2)}%)
                    </span>
                  </div>
                  {/* UPCOM */}
                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>UPCOM</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.UPCOM?.close ?? marketIndices?.upcom?.close ?? 98.20).toLocaleString()}</span>
                    <span style={{ color: ((marketIndices?.UPCOM?.change ?? marketIndices?.upcom?.change) ?? 0.24) >= 0 ? "#10b981" : "#ef4444" }}>
                      {((marketIndices?.UPCOM?.change ?? marketIndices?.upcom?.change) ?? 0.24) >= 0 ? "▲" : "▼"} {typeof (marketIndices?.UPCOM?.change ?? marketIndices?.upcom?.change) === 'number' ? Math.abs((marketIndices?.UPCOM?.change ?? marketIndices?.upcom?.change)).toFixed(2) : (marketIndices?.UPCOM?.change ?? marketIndices?.upcom?.change ?? "-")} ({typeof (marketIndices?.UPCOM?.pct ?? marketIndices?.upcom?.pct) === 'number' ? ((marketIndices?.UPCOM?.pct ?? marketIndices?.upcom?.pct)).toFixed(2) : (marketIndices?.UPCOM?.pct ?? marketIndices?.upcom?.pct ?? "-")}%)
                    </span>
                  </div>
                  {/* CW-INDEX */}
                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>CW-INDEX</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.CWINDEX?.close ?? marketIndices?.cwindex?.close ?? 108.45).toLocaleString()}</span>
                    <span style={{ color: ((marketIndices?.CWINDEX?.change ?? marketIndices?.cwindex?.change) ?? 1.35) >= 0 ? "#10b981" : "#ef4444" }}>
                      {((marketIndices?.CWINDEX?.change ?? marketIndices?.cwindex?.change) ?? 1.35) >= 0 ? "▲" : "▼"} {typeof (marketIndices?.CWINDEX?.change ?? marketIndices?.cwindex?.change) === 'number' ? Math.abs((marketIndices?.CWINDEX?.change ?? marketIndices?.cwindex?.change)).toFixed(2) : (marketIndices?.CWINDEX?.change ?? marketIndices?.cwindex?.change ?? "-")} ({typeof (marketIndices?.CWINDEX?.pct ?? marketIndices?.cwindex?.pct) === 'number' ? ((marketIndices?.CWINDEX?.pct ?? marketIndices?.cwindex?.pct)).toFixed(2) : (marketIndices?.CWINDEX?.pct ?? marketIndices?.cwindex?.pct ?? "-")}%)
                    </span>
                  </div>
                  {/* US Market Indices - Removed per user request */}
                  {/* S&P 500 */}
                  {/* <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>S&P 500</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.SP500?.close ?? 5560.80).toLocaleString()}</span>
                    <span style={{ color: (marketIndices?.SP500?.change ?? 18.5) >= 0 ? "#10b981" : "#ef4444" }}>
                      {(marketIndices?.SP500?.change ?? 18.5) >= 0 ? "▲" : "▼"} {Math.abs(marketIndices?.SP500?.change ?? 18.5).toFixed(2)} ({(marketIndices?.SP500?.pct ?? 0.33).toFixed(2)}%)
                    </span>
                  </div> */}
                  {/* NASDAQ */}
                  {/* <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>NASDAQ</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.NASDAQ?.close ?? 17872.40).toLocaleString()}</span>
                    <span style={{ color: (marketIndices?.NASDAQ?.change ?? 95.1) >= 0 ? "#10b981" : "#ef4444" }}>
                      {(marketIndices?.NASDAQ?.change ?? 95.1) >= 0 ? "▲" : "▼"} {Math.abs(marketIndices?.NASDAQ?.change ?? 95.1).toFixed(2)} ({(marketIndices?.NASDAQ?.pct ?? 0.54).toFixed(2)}%)
                    </span>
                  </div> */}
                  {/* USD/VND */}
                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>USD/VND</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.USDVND?.close ?? 25450).toLocaleString()}</span>
                    <span style={{ color: (marketIndices?.USDVND?.change ?? 15) >= 0 ? "#10b981" : "#ef4444" }}>
                      {(marketIndices?.USDVND?.change ?? 15) >= 0 ? "▲" : "▼"} {Math.abs(marketIndices?.USDVND?.change ?? 15).toFixed(2)} ({(marketIndices?.USDVND?.pct ?? 0.06).toFixed(2)}%)
                    </span>
                  </div>
                  {/* VÀNG SJC */}
                  <div style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
                    <span style={{ opacity: 0.6, color: headerTextColor }}>VÀNG SJC</span>
                    <span style={{ color: headerTextColor }}>{(marketIndices?.SJC?.close ?? "88.50M")}</span>
                    <span style={{ color: (marketIndices?.SJC?.change ?? -0.5) >= 0 ? "#10b981" : "#ef4444" }}>
                      {(marketIndices?.SJC?.change ?? -0.5) >= 0 ? "▲" : "▼"} {Math.abs(marketIndices?.SJC?.change ?? 0.5)} ({(marketIndices?.SJC?.pct ?? -0.56).toFixed(2)}%)
                    </span>
                  </div>
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Right Header actions */}
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            {/* Notification Badge */}
            <div style={{ position: "relative" }}>
              <button 
                onClick={() => setShowAlertsDropdown(v => !v)} 
                style={{ background: "none", border: "none", color: headerTextColor, cursor: "pointer", position: "relative", padding: "0.25rem", display: "flex", alignItems: "center" }}
                title="Cảnh báo & Tín hiệu"
              >
                <Bell size={18} />
                {notifications.length > 0 && (
                  <span style={{ position: "absolute", top: "1px", right: "1px", background: "#ef4444", color: "#fff", fontSize: "0.6rem", borderRadius: "50%", width: "12px", height: "12px", display: "grid", placeItems: "center", fontWeight: "bold" }}>
                    {notifications.length}
                  </span>
                )}
              </button>

              {/* Popup Dropdown */}
              {showAlertsDropdown && (
                <div 
                  style={{
                    position: "absolute",
                    top: "calc(100% + 0.6rem)",
                    right: 0,
                    width: "320px",
                    background: isDark ? "#131b2e" : "#ffffff",
                    border: `1px solid ${headerBorder}`,
                    borderRadius: "0.75rem",
                    boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
                    zIndex: 100,
                    overflow: "hidden"
                  }}
                >
                  <div style={{ padding: "0.85rem 1rem", borderBottom: `1px solid ${headerBorder}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: "800", fontSize: "0.85rem", color: isDark ? "#f8fafc" : "#0f172a", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                      <Bell size={15} style={{ color: "#f59e0b" }} /> {language === "en" ? "Notifications" : "Cảnh báo"}
                    </span>
                    <span style={{ fontSize: "0.7rem", background: "rgba(100,116,139,0.15)", color: isDark ? "#94a3b8" : "#64748b", padding: "0.1rem 0.4rem", borderRadius: "0.25rem", fontWeight: "700" }}>
                      {notifications.length} {language === "en" ? "active" : "hoạt động"}
                    </span>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column" }}>
                    {notifications.length === 0 ? (
                      <div style={{ padding: "1.5rem", textAlign: "center", color: isDark ? "#64748b" : "#94a3b8", fontSize: "0.82rem" }}>
                        <BellOff size={24} style={{ marginBottom: "0.5rem", opacity: 0.4 }} />
                        <p style={{ margin: 0 }}>{language === "en" ? "No alerts yet" : "Chưa có cảnh báo"}</p>
                      </div>
                    ) : notifications.map(n => (
                      <div
                        key={n.id}
                        onClick={() => { setShowAlertsDropdown(false); setPage("alerts"); }}
                        style={{ padding: "0.75rem 1rem", borderBottom: `1px solid ${headerBorder}`, cursor: "pointer", transition: "background 0.15s", background: "transparent" }}
                        onMouseEnter={e => e.currentTarget.style.background = isDark ? "rgba(255,255,255,0.04)" : "#f8fafc"}
                        onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.2rem" }}>
                          <strong style={{ fontSize: "0.82rem", color: "#60a5fa" }}>{n.symbol}</strong>
                          <span style={{ fontSize: "0.68rem", color: isDark ? "#94a3b8" : "#64748b" }}>{n.time}</span>
                        </div>
                        <p style={{ margin: 0, fontSize: "0.78rem", color: isDark ? "#e2e8f0" : "#334155" }}>{n.message}</p>
                      </div>
                    ))}
                  </div>

                  <div style={{ padding: "0.65rem", textAlign: "center", background: isDark ? "#0b0f19" : "#f1f5f9" }}>
                    <button 
                      onClick={() => { setShowAlertsDropdown(false); setPage("alerts"); }} 
                      style={{ background: "none", border: "none", color: "#2563eb", fontSize: "0.78rem", fontWeight: "800", cursor: "pointer" }}
                    >
                      {language === "en" ? "Manage alerts →" : "Quản lý cảnh báo →"}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Dark Mode Toggle */}
            <button onClick={toggleColorMode} style={{ background: "none", border: "none", color: headerTextColor, cursor: "pointer", padding: "0.25rem" }}>
              {preferences.colorMode === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>

            {/* User Profile */}
            <div style={{ borderLeft: `1px solid ${headerBorder}`, paddingLeft: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <ProfileMenu
                auth={auth}
                language={language}
                page={page}
                setPage={setPage}
              />
            </div>
          </div>
        </header>

        {/* CONTENT VIEWPORT */}
        <main style={{ flex: 1, width: "100%", maxWidth: "100%", padding: "1.5rem 2rem 3rem", margin: 0 }}>
          {/* key={page} triggers CSS re-animation on every page switch for smooth transitions */}
          <div key={page} className="page-enter">
            {page === "intro" ? (
              <HomePage
                setPage={setPage}
                setSelectedSymbol={setSelectedSymbol}
                health={health}
                healthLoading={healthLoading}
                healthError={healthError}
                language={language}
                preferences={preferences}
                strategy={strategy}
                setStrategy={setStrategy}
              />
            ) : null}

            {page === "cw" ? (
              <OpportunitiesPage
                setPage={setPage}
                setSelectedSymbol={setSelectedSymbol}
                language={language}
                preferences={preferences}
                strategy={strategy}
                setStrategy={setStrategy}
              />
            ) : null}

            {page === "market" ? (
              <MarketPage
                setPage={setPage}
                setSelectedSymbol={setSelectedSymbol}
                language={language}
                preferences={preferences}
                strategy={strategy}
                setStrategy={setStrategy}
              />
            ) : null}


            {page === "watchlist" ? (
              <WatchlistPage
                language={language}
                preferences={preferences}
              />
            ) : null}

            {page === "learning" ? (
              <LearningPage
                language={language}
                preferences={preferences}
              />
            ) : null}

            {page === "alerts" ? (
              <AlertsPage
                language={language}
                preferences={preferences}
              />
            ) : null}

            {page === "products" ? (
              <ProductsPage
                language={language}
                preferences={preferences}
              />
            ) : null}

            {page === "news" ? (
              <NewsPage
                language={language}
                preferences={preferences}
                setPage={setPage}
                setSelectedSymbol={setSelectedSymbol}
              />
            ) : null}

            {page === "detail" ? (
              <WarrantDetailPage
                selectedSymbol={selectedSymbol}
                setSelectedSymbol={setSelectedSymbol}
                language={language}
                preferences={preferences}
                strategy={strategy}
                setStrategy={setStrategy}
              />
            ) : null}

            {page === "settings" ? (
              <SettingsPage
                health={health}
                healthLoading={healthLoading}
                healthError={healthError}
                refreshHealth={refreshHealth}
                language={language}
                setLanguage={setLanguage}
                preferences={preferences}
                setPreferences={setPreferences}
              />
            ) : null}

            {(page === "portfolio" || page === "backtest") ? (
              <PortfolioPage 
                language={language} 
                preferences={preferences}
                initialTab={page === "backtest" ? "backtest" : "danh_sach"}
                prepopulatedSymbol={selectedSymbol}
                clearPrepopulatedSymbol={() => setSelectedSymbol("")}
              />
            ) : null}
          </div>
        </main>
      </div>

      {!auth.profile && page === "intro" ? (
        <GlobalFooter language={language} setPage={setPage} />
      ) : null}
      <AIChatWidget language={language} currentPage={page} />
    </div>
  );
}

function RegimeBadge({ regime, onClick }) {
  const r = regime?.regime || "";
  const conf = regime?.confidence ? Math.round(regime.confidence * 100) : 0;
  const bias = regime?.bias || "";

  const isBullish = r.toLowerCase().includes("bullish");
  const isBearish = r.toLowerCase().includes("bearish") || r.toLowerCase().includes("crisis");

  const color = isBullish ? "#008b7a" : isBearish ? "#d94a6f" : "#c9952f";
  const label = isBullish ? "BULL" : isBearish ? "BEAR" : "SIDE";

  return (
    <button
      className="regime-badge"
      onClick={onClick}
      title={`${r} · ${bias} · ${conf}% confidence`}
      style={{ "--regime-color": color }}
    >
      <span className="regime-dot" />
      <span className="regime-label">{label}</span>
      <span className="regime-conf">{conf}%</span>
    </button>
  );
}

function GlobalFooter({ language, setPage }) {
  const isEnglish = language === "en";
  const cols = [
    {
      heading: isEnglish ? "Explore" : "Khám Phá",
      links: [
        { label: isEnglish ? "CW Scanner" : "Bộ lọc CW", page: "cw" },
        { label: isEnglish ? "Market overview" : "Tổng quan thị trường", page: "market" },
        { label: isEnglish ? "Portfolio" : "Danh mục", page: "portfolio" },
        { label: isEnglish ? "Credit health" : "Sức khỏe tín dụng", page: "credit" },
      ],
    },
    {
      heading: isEnglish ? "Analytics" : "Phân Tích",
      links: [
        { label: "G-Score", page: "cw" },
        { label: "HMM Regime", page: "market" },
        { label: "IV / HV", page: "cw" },
        { label: "Altman Z-Score", page: "credit" },
      ],
    },
    {
      heading: isEnglish ? "About" : "Thông Tin",
      links: [
        { label: isEnglish ? "Settings" : "Cài đặt", page: "settings" },
      ],
    },
  ];

  return (
    <footer className="home-footer global-footer" style={{ gridColumn: "1 / -1", zIndex: 10 }}>
      <div className="home-footer-inner">
        <div className="home-footer-brand">
          <div className="home-footer-logo">
            <span className="brand-mark" style={{ width: 32, height: 32, fontSize: "0.85rem" }}>F</span>
            <strong>Finvista</strong>
          </div>
          <p>{isEnglish ? "Quantitative covered warrant analytics for Vietnamese markets." : "Phân tích định lượng chứng quyền thị trường Việt Nam."}</p>
          <p style={{ fontSize: "0.72rem", opacity: 0.7, marginTop: "-0.5rem" }}>
            {isEnglish ? "For analytics only, not investment advice." : "Chỉ dùng cho mục đích phân tích, không phải khuyến nghị đầu tư."}
          </p>
        </div>
        {cols.map((col) => (
          <div key={col.heading} className="home-footer-col">
            <h4>{col.heading}</h4>
            <ul>
              {col.links.map((link) => (
                <li key={link.label}>
                  <button className="home-footer-link" onClick={() => link.page && setPage(link.page)}>
                    {link.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="home-footer-bottom">
        <span>© 2026 Finvista. All rights reserved.</span>
        <span className="home-footer-tag">
          {isEnglish ? "Built with Black-Scholes · HMM · XGBoost · Gemini AI" : "Phát triển dựa trên Black-Scholes · HMM · XGBoost · Gemini AI"}
        </span>
      </div>
    </footer>
  );
}
