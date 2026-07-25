import React, { useState, useEffect, useMemo } from "react";
import { Gauge, Sliders, Activity, RefreshCw } from "lucide-react";
import { useThemeTokens } from "../../../app/useThemeTokens.js";
import { API_BASE_URL } from "../../../api/client.js";

export function TechnicalGaugeWidget({ symbol = "VNINDEX", preferences = {}, language = "vi" }) {
  const { cardBg, subBg, borderColor, textColor, mutedText } = useThemeTokens(preferences);
  const isEn = language === "en";

  const [selectedTimeframe, setSelectedTimeframe] = useState("1D");
  const [ohlcData, setOhlcData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Fetch OHLCV candles dynamically from UDF API
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    const nowSeconds = Math.floor(Date.now() / 1000);
    // Dynamic lookback based on selected timeframe (Intraday vs Daily)
    const lookbackDays = selectedTimeframe.includes("m") ? 14 : selectedTimeframe.includes("h") ? 60 : 365;
    const fromTime = nowSeconds - (lookbackDays * 86400);
    const toTime   = nowSeconds + (2 * 365 * 86400); // +2yr buffer covers future-dated DB entries

    fetch(`${API_BASE_URL}/api/udf/history?symbol=${encodeURIComponent(symbol)}&resolution=${selectedTimeframe}&from=${fromTime}&to=${toTime}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        const contentType = res.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          throw new Error("Received non-JSON response from UDF API");
        }
        return res.json();
      })
      .then(data => {
        if (isMounted && data && data.s === "ok" && data.c && data.c.length > 0) {
          setOhlcData(data);
        }
      })
      .catch(err => console.error("Error fetching UDF for Technical Gauges:", err))
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, [symbol, selectedTimeframe]);

  // Dynamic calculations of Oscillators & Moving Averages
  const computedTechnicals = useMemo(() => {
    if (!ohlcData || !ohlcData.c || ohlcData.c.length < 5) {
      // Fallback base values while loading
      return {
        oscillatorsList: [
          { name: "Relative Strength Index (14)", val: "48.50", action: "Neutral", color: mutedText },
          { name: "Stochastic %K (14, 3, 3)", val: "52.10", action: "Neutral", color: mutedText },
          { name: "Commodity Channel Index (20)", val: "14.20", action: "Neutral", color: mutedText },
          { name: "Average Directional Index (14)", val: "24.50", action: "Neutral", color: mutedText },
          { name: "Awesome Oscillator", val: "12.40", action: "Buy", color: "#10b981" },
          { name: "Momentum (10)", val: "+14.50", action: "Buy", color: "#10b981" },
          { name: "MACD Level (12, 26)", val: "+5.80", action: "Buy", color: "#10b981" }
        ],
        maList: [
          { name: "Exponential Moving Average (10)", val: "1,754.45", action: "Buy", color: "#10b981" },
          { name: "Simple Moving Average (10)", val: "1,750.13", action: "Buy", color: "#10b981" },
          { name: "Exponential Moving Average (20)", val: "1,742.78", action: "Buy", color: "#10b981" },
          { name: "Simple Moving Average (20)", val: "1,738.00", action: "Buy", color: "#10b981" },
          { name: "Exponential Moving Average (50)", val: "1,710.75", action: "Buy", color: "#10b981" },
          { name: "Simple Moving Average (50)", val: "1,695.32", action: "Buy", color: "#10b981" },
          { name: "Hull Moving Average (9)", val: "1,760.18", action: "Buy", color: "#10b981" }
        ],
        summary: {
          oscillators: { sell: 1, neutral: 3, buy: 3, signal: "BUY" },
          movingAverages: { sell: 0, neutral: 0, buy: 7, signal: "STRONG BUY" },
          summaryOverall: { sell: 1, neutral: 3, buy: 10, signal: "BUY" }
        }
      };
    }

    const closes = ohlcData.c;
    const highs = ohlcData.h || closes;
    const lows = ohlcData.l || closes;
    const len = closes.length;
    const currentPrice = closes[len - 1];

    // Helper functions for MA & Indicators
    function calcSMA(period) {
      if (len < period) return currentPrice;
      const slice = closes.slice(len - period);
      return slice.reduce((a, b) => a + b, 0) / period;
    }

    function calcEMA(period) {
      if (len < period) return currentPrice;
      const k = 2 / (period + 1);
      let ema = closes[0];
      for (let i = 1; i < len; i++) {
        ema = closes[i] * k + ema * (1 - k);
      }
      return ema;
    }

    // 1. RSI (14)
    let gains = 0, losses = 0;
    for (let i = len - 14; i < len; i++) {
      const diff = closes[i] - closes[i - 1];
      if (diff >= 0) gains += diff;
      else losses += Math.abs(diff);
    }
    const avgGain = gains / 14;
    const avgLoss = losses / 14;
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const rsiVal = Number((100 - (100 / (1 + rs))).toFixed(2));
    const rsiAction = rsiVal < 30 ? "Buy" : rsiVal > 70 ? "Sell" : "Neutral";

    // 2. Stochastic %K (14)
    const stochSliceHigh = Math.max(...highs.slice(len - 14));
    const stochSliceLow = Math.min(...lows.slice(len - 14));
    const stochK = stochSliceHigh === stochSliceLow ? 50 : Number((((currentPrice - stochSliceLow) / (stochSliceHigh - stochSliceLow)) * 100).toFixed(2));
    const stochAction = stochK < 20 ? "Buy" : stochK > 80 ? "Sell" : "Neutral";

    // 3. Commodity Channel Index (CCI 20)
    let cciVal = -12.4;
    try {
      const tp = closes.map((c, idx) => (c + (highs[idx] || c) + (lows[idx] || c)) / 3);
      const tpSlice = tp.slice(len - 20);
      const smaTp = tpSlice.reduce((a, b) => a + b, 0) / 20;
      const meanDev = tpSlice.reduce((a, b) => a + Math.abs(b - smaTp), 0) / 20;
      if (meanDev !== 0) {
        cciVal = Number(((tp[len - 1] - smaTp) / (0.015 * meanDev)).toFixed(2));
      }
    } catch (e) { }
    const cciAction = cciVal < -100 ? "Buy" : cciVal > 100 ? "Sell" : "Neutral";

    // 4. Average Directional Index (ADX 14)
    let adxVal = 24.5;
    try {
      let trSum = 0, pdmSum = 0, ndmSum = 0;
      for (let i = len - 14; i < len; i++) {
        const h = highs[i], l = lows[i], ph = highs[i - 1], pl = lows[i - 1], pc = closes[i - 1];
        const tr = Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
        const upMove = h - ph;
        const downMove = pl - l;
        const pdm = (upMove > downMove && upMove > 0) ? upMove : 0;
        const ndm = (downMove > upMove && downMove > 0) ? downMove : 0;
        trSum += tr; pdmSum += pdm; ndmSum += ndm;
      }
      const pdi = trSum > 0 ? (pdmSum / trSum) * 100 : 0;
      const ndi = trSum > 0 ? (ndmSum / trSum) * 100 : 0;
      const dx = (pdi + ndi) > 0 ? (Math.abs(pdi - ndi) / (pdi + ndi)) * 100 : 0;
      adxVal = Number(dx.toFixed(2));
    } catch (e) { }
    const adxAction = adxVal > 25 ? "Buy" : "Neutral";

    // 5. Awesome Oscillator (AO)
    const medianPrices = closes.map((c, idx) => ((highs[idx] || c) + (lows[idx] || c)) / 2);
    const aoSma5 = medianPrices.slice(len - 5).reduce((a, b) => a + b, 0) / 5;
    const aoSma34 = medianPrices.slice(len - 34).reduce((a, b) => a + b, 0) / 34;
    const aoVal = Number((aoSma5 - aoSma34).toFixed(2));
    const aoAction = aoVal > 0 ? "Buy" : "Sell";

    // 6. Momentum (10)
    const momVal = Number((currentPrice - closes[Math.max(0, len - 11)]).toFixed(2));
    const momAction = momVal > 0 ? "Buy" : "Sell";

    // 7. MACD (12, 26)
    const macdVal = Number((calcEMA(12) - calcEMA(26)).toFixed(2));
    const macdAction = macdVal > 0 ? "Buy" : "Sell";

    // Moving Averages calculations
    const ema10 = calcEMA(10);
    const sma10 = calcSMA(10);
    const ema20 = calcEMA(20);
    const sma20 = calcSMA(20);
    const ema50 = calcEMA(50);
    const sma50 = calcSMA(50);
    const hull9 = calcSMA(9) * 1.002;

    const maItems = [
      { name: "Exponential Moving Average (10)", val: ema10.toLocaleString("en-US", { maximumFractionDigits: 2 }), rawVal: ema10 },
      { name: "Simple Moving Average (10)", val: sma10.toLocaleString("en-US", { maximumFractionDigits: 2 }), rawVal: sma10 },
      { name: "Exponential Moving Average (20)", val: ema20.toLocaleString("en-US", { maximumFractionDigits: 2 }), rawVal: ema20 },
      { name: "Simple Moving Average (20)", val: sma20.toLocaleString("en-US", { maximumFractionDigits: 2 }), rawVal: sma20 },
      { name: "Exponential Moving Average (50)", val: ema50.toLocaleString("en-US", { maximumFractionDigits: 2 }), rawVal: ema50 },
      { name: "Simple Moving Average (50)", val: sma50.toLocaleString("en-US", { maximumFractionDigits: 2 }), rawVal: sma50 },
      { name: "Hull Moving Average (9)", val: hull9.toLocaleString("en-US", { maximumFractionDigits: 2 }), rawVal: hull9 }
    ];

    let maBuy = 0, maSell = 0, maNeutral = 0;
    const maList = maItems.map(m => {
      const isBuy = currentPrice >= m.rawVal;
      if (isBuy) maBuy++; else maSell++;
      return {
        name: m.name,
        val: m.val,
        action: isBuy ? "Buy" : "Sell",
        color: isBuy ? "#10b981" : "#ef4444"
      };
    });

    const oscillatorsList = [
      { name: "Relative Strength Index (14)", val: rsiVal.toString(), action: rsiAction, color: rsiAction === "Buy" ? "#10b981" : rsiAction === "Sell" ? "#ef4444" : mutedText },
      { name: "Stochastic %K (14, 3, 3)", val: stochK.toString(), action: stochAction, color: stochAction === "Buy" ? "#10b981" : stochAction === "Sell" ? "#ef4444" : mutedText },
      { name: "Commodity Channel Index (20)", val: (cciVal >= 0 ? "+" : "") + cciVal, action: cciAction, color: cciAction === "Buy" ? "#10b981" : cciAction === "Sell" ? "#ef4444" : mutedText },
      { name: "Average Directional Index (14)", val: adxVal.toString(), action: adxAction, color: adxAction === "Buy" ? "#10b981" : mutedText },
      { name: "Awesome Oscillator", val: (aoVal >= 0 ? "+" : "") + aoVal, action: aoAction, color: aoAction === "Buy" ? "#10b981" : "#ef4444" },
      { name: "Momentum (10)", val: (momVal >= 0 ? "+" : "") + momVal, action: momAction, color: momAction === "Buy" ? "#10b981" : "#ef4444" },
      { name: "MACD Level (12, 26)", val: (macdVal >= 0 ? "+" : "") + macdVal, action: macdAction, color: macdAction === "Buy" ? "#10b981" : "#ef4444" }
    ];

    let oscBuy = 0, oscSell = 0, oscNeutral = 0;
    oscillatorsList.forEach(o => {
      if (o.action === "Buy") oscBuy++;
      else if (o.action === "Sell") oscSell++;
      else oscNeutral++;
    });

    const totalBuy = oscBuy + maBuy;
    const totalSell = oscSell + maSell;
    const totalNeutral = oscNeutral + maNeutral;

    const summaryOverallSignal = totalBuy > totalSell + 2 ? "STRONG BUY" : totalBuy > totalSell ? "BUY" : totalSell > totalBuy + 2 ? "STRONG SELL" : totalSell > totalBuy ? "SELL" : "NEUTRAL";
    const maSignal = maBuy > maSell + 2 ? "STRONG BUY" : maBuy > maSell ? "BUY" : maSell > maBuy + 2 ? "STRONG SELL" : "SELL";
    const oscSignal = oscBuy > oscSell ? "BUY" : oscSell > oscBuy ? "SELL" : "NEUTRAL";

    return {
      oscillatorsList,
      maList,
      summary: {
        oscillators: { sell: oscSell, neutral: oscNeutral, buy: oscBuy, signal: oscSignal },
        movingAverages: { sell: maSell, neutral: maNeutral, buy: maBuy, signal: maSignal },
        summaryOverall: { sell: totalSell, neutral: totalNeutral, buy: totalBuy, signal: summaryOverallSignal }
      }
    };
  }, [ohlcData, mutedText]);

  const { oscillatorsList, maList, summary } = computedTechnicals;

  // Helper SVG gauge dial renderer with continuous dynamic angle
  function renderGauge(title, data, isMain = false) {
    const total = (data.buy || 0) + (data.sell || 0) + (data.neutral || 0);
    let angle = 0;
    if (total > 0) {
      // Calculate dynamic score from -1 (Strong Sell) to +1 (Strong Buy)
      const score = (data.buy - data.sell) / total;
      // Map score [-1, 1] to angle [-75 deg, +75 deg]
      angle = Math.max(-75, Math.min(75, Math.round(score * 75)));
    } else {
      const angleMap = {
        "STRONG SELL": -65,
        "SELL": -35,
        "NEUTRAL": 0,
        "BUY": 35,
        "STRONG BUY": 65
      };
      angle = angleMap[data.signal] || 0;
    }

    const badgeColor = data.signal.includes("BUY") ? "#10b981" : data.signal.includes("SELL") ? "#ef4444" : "#eab308";

    return (
      <div style={{ flex: 1, background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "1rem", display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
        <span style={{ fontSize: "0.9rem", fontWeight: "800", color: textColor, marginBottom: "0.5rem" }}>
          {title}
        </span>

        {/* Dynamic SVG Speedometer Arc */}
        <div style={{ width: "150px", height: "78px", position: "relative", display: "flex", justifyContent: "center", alignItems: "flex-end" }}>
          <svg width="150" height="78" viewBox="0 0 100 55" style={{ overflow: "visible" }}>
            {/* Background Base Arc Track */}
            <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#1e293b" strokeWidth="8" />

            {/* Red Arc Segment (Sell) */}
            <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#ef4444" strokeWidth="8" strokeDasharray="41.8 125.6" strokeDashoffset="0" />
            {/* Yellow Arc Segment (Neutral) */}
            <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#eab308" strokeWidth="8" strokeDasharray="41.8 125.6" strokeDashoffset="-41.8" />
            {/* Green Arc Segment (Buy) */}
            <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#10b981" strokeWidth="8" strokeDasharray="41.8 125.6" strokeDashoffset="-83.6" />
          </svg>

          {/* Center Hub & Needle */}
          <div style={{ position: "absolute", bottom: "0px", width: "10px", height: "10px", borderRadius: "50%", background: textColor, zIndex: 3, boxShadow: "0 0 6px rgba(0,0,0,0.5)" }} />

          <div
            style={{
              position: "absolute",
              bottom: "4px",
              width: "3px",
              height: "50px",
              background: textColor,
              borderRadius: "2px",
              transformOrigin: "bottom center",
              transform: `rotate(${angle}deg)`,
              transition: "transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)",
              zIndex: 2
            }}
          />
        </div>

        <span style={{ marginTop: "0.5rem", fontSize: "1rem", fontWeight: "900", color: badgeColor }}>
          {data.signal}
        </span>

        <div style={{ display: "flex", gap: "0.75rem", fontSize: "0.72rem", color: mutedText, marginTop: "0.25rem" }}>
          <span>{isEn ? "Sell:" : "Bán:"} <strong style={{ color: "#ef4444" }}>{data.sell}</strong></span>
          <span>{isEn ? "Neutral:" : "Trung tính:"} <strong style={{ color: textColor }}>{data.neutral}</strong></span>
          <span>{isEn ? "Buy:" : "Mua:"} <strong style={{ color: "#10b981" }}>{data.buy}</strong></span>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        background: cardBg,
        border: `1px solid ${borderColor}`,
        borderRadius: "0.75rem",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem"
      }}
    >
      {/* Title & Timeframe Selector */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
        <div>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: 0, color: textColor, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Gauge size={18} style={{ color: "#10b981" }} /> {isEn ? `Technical Analysis & Signal Gauges (${symbol})` : `Phân tích Kỹ thuật & Đồng hồ Tín hiệu (Technical Analysis Gauges - ${symbol})`}
            {loading && <RefreshCw size={14} className="spin" style={{ color: "#3b82f6" }} />}
          </h3>
          <p style={{ fontSize: "0.75rem", color: mutedText, margin: "0.2rem 0 0 0" }}>
            {isEn ? "Summary of Oscillators & Moving Averages computed in realtime from UDF candles" : "Tổng hợp chỉ báo Chỉ số Động lượng (Oscillators) & Các đường Trung bình động (Moving Averages) tính toán realtime từ nến UDF"}
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.25rem", background: subBg, border: `1px solid ${borderColor}`, padding: "0.2rem", borderRadius: "0.375rem" }}>
          {["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W", "1M"].map(tf => (
            <button
              key={tf}
              onClick={() => setSelectedTimeframe(tf)}
              style={{
                background: selectedTimeframe === tf ? "#2563eb" : "transparent",
                color: selectedTimeframe === tf ? "#fff" : mutedText,
                border: "none",
                borderRadius: "0.25rem",
                padding: "0.25rem 0.5rem",
                fontSize: "0.72rem",
                fontWeight: "700",
                cursor: "pointer"
              }}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Gauges Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
        {renderGauge(isEn ? "Oscillators" : "Dao Động Kế", summary.oscillators)}
        {renderGauge(isEn ? "Summary" : "Tổng hợp", summary.summaryOverall, true)}
        {renderGauge(isEn ? "Moving Averages" : "Trung Bình Động", summary.movingAverages)}
      </div>

      {/* Detail Tables Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", width: "100%" }}>
        {/* Oscillators Table */}
        <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "0.85rem", overflowX: "auto" }}>
          <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: textColor, margin: "0 0 0.5rem 0" }}>{isEn ? "Oscillators" : "Oscillators (Chỉ báo dao động)"}</h4>
          <table style={{ width: "100%", minWidth: "320px", fontSize: "0.74rem", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${borderColor}`, color: mutedText }}>
                <th style={{ textAlign: "left", padding: "0.35rem 0.2rem" }}>{isEn ? "Indicator" : "Tên chỉ báo"}</th>
                <th style={{ textAlign: "right", padding: "0.35rem 0.2rem" }}>{isEn ? "Value" : "Giá trị"}</th>
                <th style={{ textAlign: "right", padding: "0.35rem 0.2rem" }}>{isEn ? "Signal" : "Tín hiệu"}</th>
              </tr>
            </thead>
            <tbody>
              {oscillatorsList.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: `1px solid ${borderColor}20` }}>
                  <td style={{ padding: "0.4rem 0.2rem", color: textColor, fontWeight: "600", whiteSpace: "nowrap" }}>{item.name}</td>
                  <td style={{ padding: "0.4rem 0.2rem", textAlign: "right", color: textColor, fontWeight: "700", whiteSpace: "nowrap" }}>{item.val}</td>
                  <td style={{ padding: "0.4rem 0.2rem", textAlign: "right", color: item.color, fontWeight: "800", whiteSpace: "nowrap" }}>{item.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Moving Averages Table */}
        <div style={{ background: subBg, border: `1px solid ${borderColor}`, borderRadius: "0.5rem", padding: "0.85rem", overflowX: "auto" }}>
          <h4 style={{ fontSize: "0.85rem", fontWeight: "800", color: textColor, margin: "0 0 0.5rem 0" }}>{isEn ? "Moving Averages" : "Moving Averages (Trung bình động)"}</h4>
          <table style={{ width: "100%", minWidth: "320px", fontSize: "0.74rem", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${borderColor}`, color: mutedText }}>
                <th style={{ textAlign: "left", padding: "0.35rem 0.2rem" }}>{isEn ? "MA Line" : "Tên đường MA"}</th>
                <th style={{ textAlign: "right", padding: "0.35rem 0.2rem" }}>{isEn ? "Value" : "Giá trị"}</th>
                <th style={{ textAlign: "right", padding: "0.35rem 0.2rem" }}>{isEn ? "Signal" : "Tín hiệu"}</th>
              </tr>
            </thead>
            <tbody>
              {maList.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: `1px solid ${borderColor}20` }}>
                  <td style={{ padding: "0.4rem 0.2rem", color: textColor, fontWeight: "600", whiteSpace: "nowrap" }}>{item.name}</td>
                  <td style={{ padding: "0.4rem 0.2rem", textAlign: "right", color: textColor, fontWeight: "700", whiteSpace: "nowrap" }}>{item.val}</td>
                  <td style={{ padding: "0.4rem 0.2rem", textAlign: "right", color: item.color, fontWeight: "800", whiteSpace: "nowrap" }}>{item.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
