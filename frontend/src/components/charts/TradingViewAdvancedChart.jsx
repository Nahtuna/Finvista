import React, { useEffect, useRef } from "react";
import { TradingViewLightweightChart } from "./TradingViewLightweightChart.jsx";

export function TradingViewAdvancedChart({ symbol = "CACB2511", theme = "dark", height = 450 }) {
  // Fallback to lightweight chart since advanced TradingView library is not available
  return (
    <TradingViewLightweightChart 
      symbol={symbol} 
      theme={theme} 
      height={height}
      resolution="1D"
    />
  );
}
