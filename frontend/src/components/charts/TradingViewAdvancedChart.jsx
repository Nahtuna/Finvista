import React, { useEffect, useRef } from "react";

export function TradingViewAdvancedChart({ symbol = "CACB2511", theme = "dark", height = 450 }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.innerHTML = "";
    }

    // Dynamic loading of the local charting library script from the public folder
    const script = document.createElement("script");
    script.src = "/charting_library/charting_library.standalone.js";
    script.type = "text/javascript";
    script.async = true;
    script.onload = () => {
      if (typeof window.TradingView !== "undefined" && containerRef.current) {
        const backendBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8008";
        const datafeedUrl = `${backendBase}/api/udf`;

        new window.TradingView.widget({
          width: "100%",
          height: height,
          symbol: symbol.toUpperCase(),
          interval: "D",
          timezone: "Asia/Ho_Chi_Minh",
          theme: theme,
          style: "1",
          locale: "vi",
          container_id: containerRef.current.id,
          // TradingView Charting Library specific UDF configuration
          library_path: "/charting_library/",
          datafeed: new window.Datafeeds.UDFCompatibleDatafeed(datafeedUrl),
          disabled_features: ["use_localstorage_for_settings_saving"],
          enabled_features: ["study_templates"],
          charts_storage_url: "https://saveload.tradingview.com",
          charts_storage_api_version: "1.1",
          client_id: "finvista_local",
          user_id: "public_user",
        });
      }
    };

    // If script is already in head, trigger onload directly, otherwise append
    const existingScript = document.querySelector(`script[src="${script.src}"]`);
    if (existingScript) {
      if (typeof window.TradingView !== "undefined") {
        script.onload();
      } else {
        existingScript.addEventListener("load", script.onload);
      }
    } else {
      document.head.appendChild(script);
    }

    return () => {
      // Clean up if component unmounts
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [symbol, theme, height]);

  const widgetId = `tv_advanced_chart_${symbol.replace(/[^a-zA-Z0-9]/g, "_")}`;

  return (
    <div style={{ width: "100%", borderRadius: "8px", overflow: "hidden", border: "1px solid var(--border-color, rgba(255,255,255,0.08))" }}>
      <div id={widgetId} ref={containerRef} style={{ height: `${height}px`, width: "100%" }} />
    </div>
  );
}
