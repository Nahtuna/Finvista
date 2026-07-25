import React, { useEffect, useRef } from "react";

export function TradingViewChart({ 
  symbol = "HOSE:VNINDEX", 
  theme = "dark", 
  height = 420,
  allowSymbolChange = false,
  regimeData = null
}) {
  const containerRef = useRef(null);

  // Normalize symbol with proper Exchange prefix for TradingView Advanced Widget
  const cleanSym = symbol.replace("HOSE:", "").replace("HNX:", "").replace("AMEX:", "").toUpperCase();
  const tvSymbol = cleanSym.includes("HNX") ? `HNX:${cleanSym}` : (cleanSym === "SPX" ? "INDEX:SPX" : `HOSE:${cleanSym}`);

  const widgetId = useRef(`tradingview_${Math.random().toString(36).substring(2, 9)}`).current;

  useEffect(() => {
    if (!containerRef.current) return;

    let isMounted = true;

    const initWidget = () => {
      if (window.TradingView && containerRef.current && isMounted) {
        containerRef.current.innerHTML = "";
        new window.TradingView.widget({
          width: "100%",
          height: height,
          symbol: tvSymbol,
          interval: "D",
          timezone: "Asia/Ho_Chi_Minh",
          theme: theme === "dark" ? "dark" : "light",
          style: "1",
          locale: "vi",
          toolbar_bg: theme === "dark" ? "#0f172a" : "#f8fafc",
          enable_publishing: false,
          hide_side_toolbar: false,
          allow_symbol_change: allowSymbolChange,
          container_id: widgetId,
        });
      }
    };

    if (window.TradingView) {
      initWidget();
    } else {
      let script = document.getElementById("tradingview-widget-script");
      if (!script) {
        script = document.createElement("script");
        script.id = "tradingview-widget-script";
        script.src = "https://s3.tradingview.com/tv.js";
        script.type = "text/javascript";
        script.async = true;
        document.head.appendChild(script);
      }
      script.addEventListener("load", initWidget);
    }

    return () => {
      isMounted = false;
    };
  }, [tvSymbol, theme, height, allowSymbolChange, widgetId]);

  // Derive Phase & Layer from regimeData
  const phase = regimeData?.phase || (regimeData?.regime?.includes("BEAR") ? "BEAR" : "BULL");
  const layer = regimeData?.layer || (regimeData?.bias === "SKIP_CW" ? "PAUSE" : "ACTIVATE");

  return (
    <div style={{ position: "relative", width: "100%", borderRadius: "8px", overflow: "hidden", border: "1px solid var(--border-color, rgba(255,255,255,0.08))" }}>
      {/* Floating PHASE / Layer Overlay Badge matching TradingView Creed Grid screenshot */}
      <div style={{
        position: "absolute",
        top: "42px",
        right: "65px",
        zIndex: 10,
        background: theme === "dark" ? "rgba(15, 23, 42, 0.88)" : "rgba(255, 255, 255, 0.92)",
        backdropFilter: "blur(6px)",
        border: `1px solid ${theme === "dark" ? "rgba(255, 255, 255, 0.15)" : "rgba(0, 0, 0, 0.12)"}`,
        borderRadius: "4px",
        padding: "4px 8px",
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
        fontSize: "11px",
        fontWeight: "700",
        color: theme === "dark" ? "#cbd5e1" : "#334155",
        boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
        display: "grid",
        gridTemplateColumns: "auto auto",
        gap: "4px 10px",
        alignItems: "center",
        pointerEvents: "none"
      }}>
        <span style={{ color: "#94a3b8", textTransform: "uppercase", fontSize: "10px" }}>PHASE</span>
        <span style={{ 
          color: phase === "BEAR" ? "#ef4444" : "#10b981", 
          fontWeight: "900", 
          fontSize: "12px",
          letterSpacing: "0.5px"
        }}>
          {phase}
        </span>
        <span style={{ color: "#94a3b8", fontSize: "10px" }}>Layer</span>
        <span style={{ 
          color: layer === "ACTIVATE" ? "#10b981" : (layer === "PAUSE" ? "#ef4444" : "#f59e0b"), 
          fontWeight: "900", 
          fontSize: "12px",
          letterSpacing: "0.5px"
        }}>
          {layer}
        </span>
      </div>

      <div id={widgetId} ref={containerRef} style={{ height: `${height}px`, width: "100%" }} />
    </div>
  );
}
