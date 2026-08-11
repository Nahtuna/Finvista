import React, { useEffect, useRef, useState } from "react";
import { createChart } from "lightweight-charts";

function calculateVolatility(bars) {
  if (!bars || bars.length < 2) return 0.015;
  const returns = [];
  for (let i = 1; i < bars.length; i++) {
    const prev = bars[i - 1].close;
    const curr = bars[i].close;
    if (prev > 0) {
      returns.push(Math.log(curr / prev));
    }
  }
  if (returns.length === 0) return 0.015;
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const variance = returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / returns.length;
  return Math.sqrt(variance);
}

function getFutureTimes(lastTime, numPeriods, resolution) {
  const result = [];
  let current = lastTime;
  const isNumber = typeof lastTime === 'number';

  const resolutionSecondsMap = {
    "1": 60, "5": 300, "15": 900, "30": 1800, "60": 3600,
    "1D": 86400, "1W": 604800, "1M": 2592000,
  };
  const step = resolutionSecondsMap[resolution] || 86400;

  if (isNumber) {
    for (let i = 1; i <= numPeriods; i++) {
      current += step;
      result.push(current);
    }
  } else {
    const date = new Date(lastTime);
    let tempDate = new Date(date);
    while (result.length < numPeriods) {
      tempDate.setDate(tempDate.getDate() + 1);
      const day = tempDate.getDay();
      if (day !== 0 && day !== 6) {
        const yr = tempDate.getFullYear();
        const mo = String(tempDate.getMonth() + 1).padStart(2, "0");
        const dy = String(tempDate.getDate()).padStart(2, "0");
        result.push(`${yr}-${mo}-${dy}`);
      }
    }
  }
  return result;
}

export function TradingViewLightweightChart({
  symbol,
  theme = "dark",
  height = 350,
  timeframe = "3M",
  resolution = "1D",
  targetPrice: externalTargetPrice,
  onCrosshairMove,
  onDataLoaded,
  forceRefresh = 0,
  showSR = true,
  showForecast = true,
  showRegime = true,
  showStructure = false,
  language = "vi",
}) {
  const chartContainerRef = useRef(null);
  const [forecast, setForecast] = useState(null);
  const [showForecastDetails, setShowForecastDetails] = useState(false);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const isDark = theme === "dark";
    const container = chartContainerRef.current;
    if (container) {
      container.innerHTML = "";
    }
    let isDisposed = false;
    const abortCtrl = new AbortController();

    // Create chart
    const chart = createChart(container, {
      width: container.clientWidth || 600,
      height: height,
      layout: {
        background: { color: isDark ? "#131722" : "#ffffff" },
        textColor: isDark ? "#d1d4dc" : "#333333",
      },
      grid: {
        vertLines: { color: isDark ? "rgba(42,46,57,0.4)" : "rgba(42,46,57,0.1)" },
        horzLines: { color: isDark ? "rgba(42,46,57,0.4)" : "rgba(42,46,57,0.1)" },
      },
      timeScale: {
        borderColor: isDark ? "rgba(42,46,57,0.4)" : "rgba(42,46,57,0.1)",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: isDark ? "rgba(42,46,57,0.4)" : "rgba(42,46,57,0.1)",
      },
      crosshair: { mode: 0 },
      handleScroll: true,
      handleScale: {
        mouseWheel: false,
        pinch: true,
        axisPressedMouseMove: true,
      },
    });

    // Force a dynamic width recalculation after rendering completes
    setTimeout(() => {
      if (!isDisposed && container) {
        try { chart.applyOptions({ width: container.clientWidth }); } catch (_) { }
      }
    }, 100);

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: "#00c897",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#00c897",
      wickDownColor: "#ef4444",
    });

    const trendLineSeries = chart.addLineSeries({
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      title: "Ensemble Master Trend",
    });

    const upperForecastSeries = chart.addLineSeries({
      color: "#10b981",
      lineWidth: 2,
      lineStyle: 2, // dashed
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      title: "+1 SD Upper Limit",
    });

    const lowerForecastSeries = chart.addLineSeries({
      color: "#f43f5e",
      lineWidth: 2,
      lineStyle: 2, // dashed
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      title: "-1 SD Lower Limit",
    });

    const medianForecastSeries = chart.addLineSeries({
      color: "#f59e0b",
      lineWidth: 2.5,
      lineStyle: 0, // solid
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      title: "Median Path",
    });

    // S/R Diagonal Trendline Series
    const resTrendLine1 = chart.addLineSeries({
      color: "rgba(239, 68, 68, 0.65)", // red
      lineWidth: 1.5,
      lineStyle: 2, // dashed
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      title: "Resistance Trend",
    });
    const resTrendLine2 = chart.addLineSeries({
      color: "rgba(239, 68, 68, 0.65)",
      lineWidth: 1.5,
      lineStyle: 2,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      title: "Resistance Trend",
    });
    const supTrendLine1 = chart.addLineSeries({
      color: "rgba(16, 185, 129, 0.65)", // green
      lineWidth: 1.5,
      lineStyle: 2,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      title: "Support Trend",
    });
    const supTrendLine2 = chart.addLineSeries({
      color: "rgba(16, 185, 129, 0.65)",
      lineWidth: 1.5,
      lineStyle: 2,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      title: "Support Trend",
    });

    // BOS (Break of Structure) line series list for cleanup and redraw
    const bosSeriesList = [];

    const regimeSeries = chart.addHistogramSeries({
      priceScaleId: "regime-scale",
      priceFormat: { type: "volume" },
      lastValueVisible: false,
      priceLineVisible: false,
    });

    chart.priceScale("regime-scale").applyOptions({
      scaleMargins: { top: 0, bottom: 0 },
      visible: false,
    });

    chart.priceScale("right").applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.25 },
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume-scale",
    });

    chart.priceScale("volume-scale").applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      visible: false,
    });

    const volumeMap = {};

    // Calculate continuous Ensemble Master Trend & Regime Phase Bands
    function calculateCreedRegimeBands(bars) {
      if (!bars || bars.length === 0) return { regimeBars: [], trendBars: [] };
      const closes = bars.map(b => b.close);
      const n = closes.length;

      function calcEMA(period) {
        const k = 2 / (period + 1);
        const ema = new Array(n);
        let prev = closes[0];
        ema[0] = prev;
        for (let i = 1; i < n; i++) {
          prev = closes[i] * k + prev * (1 - k);
          ema[i] = prev;
        }
        return ema;
      }

      const trendSpan = Math.min(200, Math.max(20, Math.floor(n / 2)));
      const emaTrend = calcEMA(trendSpan);
      const ema10 = calcEMA(10);
      const ema20 = calcEMA(20);

      const greenColor = isDark ? "rgba(0, 200, 151, 0.08)" : "rgba(16, 185, 129, 0.08)";
      const redColor = isDark ? "rgba(239, 68, 68, 0.08)" : "rgba(239, 68, 68, 0.08)";
      const neutralColor = "transparent";

      const regimeBars = [];
      const trendBars = [];

      for (let i = 0; i < n; i++) {
        const c = closes[i];
        const tr = emaTrend[i];
        const e10 = ema10[i];
        const e20 = ema20[i];

        const isBull = c >= tr && e10 >= e20;
        const isBear = c < tr && e10 < e20;
        const bandColor = isBull ? greenColor : isBear ? redColor : neutralColor;
        const trendColor = isBull ? "#10b981" : isBear ? "#ef4444" : "#3b82f6";

        regimeBars.push({
          time: bars[i].time,
          value: 100,
          color: bandColor
        });

        trendBars.push({
          time: bars[i].time,
          value: tr,
          color: trendColor
        });
      }

      return { regimeBars, trendBars };
    }

    // Safe wrapper — prevents "Object is disposed" crashes
    const srLines = []; // track price lines for cleanup
    const srZoneSeriesList = []; // track candlestick series used for filled zones

    function drawSRLines(srData) {
      // Remove old lines first
      srLines.forEach(line => { try { candlestickSeries.removePriceLine(line); } catch (_) { } });
      srLines.length = 0;

      // Remove old zone series
      srZoneSeriesList.forEach(series => { try { chart.removeSeries(series); } catch (_) { } });
      srZoneSeriesList.length = 0;

      if (isDisposed || !srData || !showSR) return;

      // Detect if we need to normalize S/R prices to match chart scale (thousands vs raw VND)
      let scaleFactor = 1.0;
      const zones = [
        ...(srData.support_zones || []),
        ...(srData.resistance_zones || []),
      ];

      if (loadedBars && loadedBars.length > 0) {
        const lastClose = loadedBars[loadedBars.length - 1].close;
        if (srData.poc && srData.poc.price > 1000 && lastClose < 1000) {
          scaleFactor = 0.001; // divide by 1000
        } else if (zones.length > 0 && zones[0].price > 1000 && lastClose < 1000) {
          scaleFactor = 0.001;
        }
      }

      // POC line (draw separately with distinct dotted amber color to show confluence)
      if (srData.poc) {
        try {
          const l = candlestickSeries.createPriceLine({
            price: srData.poc.price * scaleFactor,
            color: "rgba(251, 191, 36, 0.75)",   // amber
            lineWidth: 1.5,
            lineStyle: 3, // dotted
            axisLabelVisible: true,
            title: "POC",
          });
          srLines.push(l);
        } catch (_) { }
      }

      // Filter support and resistance zones
      const supports = zones.filter(z => z.type === "support");
      const resistances = zones.filter(z => z.type === "resistance");

      // Sort supports descending (closest to price first) and resistances ascending (closest to price first)
      const sortedRes = [...resistances].sort((a, b) => a.price - b.price);
      const sortedSup = [...supports].sort((a, b) => b.price - a.price);

      const supportLabels = {};
      const resistanceLabels = {};

      sortedSup.forEach((z, idx) => {
        supportLabels[z.price * scaleFactor] = `S${idx + 1}`;
      });

      sortedRes.forEach((z, idx) => {
        resistanceLabels[z.price * scaleFactor] = `R${idx + 1}`;
      });

      const displayZones = [...sortedRes, ...sortedSup];

      displayZones.forEach(z => {
        const isSupport = z.type === "support";
        
        // Dynamic opacity and line width based on S/R strength
        let opacity = isDark ? 0.45 : 0.65;
        let lineWidth = isDark ? 1.2 : 1.6;
        let lineStyle = 2; // dashed
        
        if (z.strength === "MAJOR_ATH" || z.strength === "MAJOR_FLOOR") {
          opacity = isDark ? 0.95 : 1.0;
          lineWidth = isDark ? 2.5 : 3.0;
          lineStyle = 0; // solid for historical peak/trough
        } else if (z.strength === "STRONG") {
          opacity = isDark ? 0.8 : 0.95;
          lineWidth = isDark ? 2.0 : 2.4;
          lineStyle = 2; // thick dashed
        } else if (z.strength === "MODERATE") {
          opacity = isDark ? 0.6 : 0.8;
          lineWidth = isDark ? 1.5 : 1.9;
          lineStyle = 2;
        }

        const color = isSupport
          ? (isDark ? `rgba(16, 185, 129, ${opacity})` : `rgba(5, 150, 105, ${opacity})`)
          : (isDark ? `rgba(244, 63, 94, ${opacity})` : `rgba(225, 29, 72, ${opacity})`);
        
        const label = isSupport ? supportLabels[z.price * scaleFactor] : resistanceLabels[z.price * scaleFactor];
        
        try {
          const l = candlestickSeries.createPriceLine({
            price: z.price * scaleFactor,
            color,
            lineWidth,
            lineStyle,
            axisLabelVisible: true,
            title: label,
          });
          srLines.push(l);
        } catch (_) { }
      });
    }

    let loadedBars = [];
    let currentForecast = null;
    let loadedFractals = [];
    let loadedBosLines = [];
    let loadedChochLines = [];

    function drawBosLines(bosDataList, chochDataList = []) {
      // Remove old BOS/CHoCH line series first
      bosSeriesList.forEach(series => {
        try { chart.removeSeries(series); } catch (_) { }
      });
      bosSeriesList.length = 0;

      if (isDisposed || !showStructure) return;

      // Determine scale factor similar to S/R
      let scaleFactor = 1.0;
      if (loadedBars && loadedBars.length > 0) {
        const lastClose = loadedBars[loadedBars.length - 1].close;
        const allLines = [...(bosDataList || []), ...(chochDataList || [])];
        if (allLines.length > 0 && allLines[0].price > 1000 && lastClose < 1000) {
          scaleFactor = 0.001;
        }
      }

      // Render BOS lines (amber/orange = trend continuation)
      (bosDataList || []).forEach(bos => {
        try {
          const s = chart.addLineSeries({
            color: "rgba(245, 158, 11, 0.75)", // amber
            lineWidth: 1.5,
            lineStyle: 3, // dotted
            priceLineVisible: false,
            crosshairMarkerVisible: false,
            title: "BOS",
          });
          s.setData([
            { time: bos.start_time, value: bos.price * scaleFactor },
            { time: bos.end_time, value: bos.price * scaleFactor }
          ]);
          bosSeriesList.push(s);
        } catch (_) {}
      });

      // Render CHoCH lines (red/pink = trend reversal signal)
      (chochDataList || []).forEach(choch => {
        try {
          const s = chart.addLineSeries({
            color: "rgba(239, 68, 68, 0.8)", // red
            lineWidth: 1.5,
            lineStyle: 1, // dashed
            priceLineVisible: false,
            crosshairMarkerVisible: false,
            title: "CHoCH",
          });
          s.setData([
            { time: choch.start_time, value: choch.price * scaleFactor },
            { time: choch.end_time, value: choch.price * scaleFactor }
          ]);
          bosSeriesList.push(s);
        } catch (_) {}
      });
    }

    function updateVisibleMarkers() {
      if (isDisposed || !loadedBars || loadedBars.length === 0) return;
      try {
        if (!showStructure) {
          candlestickSeries.setMarkers([]);
          return;
        }

        const range = chart.timeScale().getVisibleLogicalRange();
        if (!range) return;

        const fromIndex = Math.max(0, Math.floor(range.from));
        const toIndex = Math.min(loadedBars.length - 1, Math.ceil(range.to));

        if (fromIndex >= toIndex) return;

        const visibleBars = loadedBars.slice(fromIndex, toIndex + 1);
        if (visibleBars.length === 0) return;

        // Map visible bar times to rapid lookup
        const visibleTimes = new Set(visibleBars.map(b => b.time));

        // Group loadedFractals by type and sort chronologically
        const sortedFractals = [...loadedFractals].sort((a, b) => (a.date > b.date ? 1 : -1));
        const peaks = sortedFractals.filter(f => f.type === 'resistance');
        const troughs = sortedFractals.filter(f => f.type === 'support');

        const markers = [];

        // Identify HH / LH
        for (let i = 0; i < peaks.length; i++) {
          const curr = peaks[i];
          if (!visibleTimes.has(curr.date)) continue;

          let label = "H";
          if (i > 0) {
            const prev = peaks[i - 1];
            label = curr.price > prev.price ? "HH" : "LH";
          }
          markers.push({
            time: curr.date,
            position: "aboveBar",
            color: label === "HH" ? "#00c897" : "#f43f5e",
            shape: "arrowDown",
            text: label,
          });
        }

        // Identify HL / LL
        for (let i = 0; i < troughs.length; i++) {
          const curr = troughs[i];
          if (!visibleTimes.has(curr.date)) continue;

          let label = "L";
          if (i > 0) {
            const prev = troughs[i - 1];
            label = curr.price > prev.price ? "HL" : "LL";
          }
          markers.push({
            time: curr.date,
            position: "belowBar",
            color: label === "HL" ? "#00c897" : "#f43f5e",
            shape: "arrowUp",
            text: label,
          });
        }

        markers.sort((a, b) => (a.time > b.time ? 1 : -1));
        candlestickSeries.setMarkers(markers);
      } catch (_) { }
    }


    function drawForecast(bars, forecastData) {
      if (isDisposed || !bars || bars.length === 0 || !showForecast) return;
      try {
        const lastBar = bars[bars.length - 1];
        const lastPrice = lastBar.close;
        const vol = calculateVolatility(bars);

        let drift = 0;
        if (forecastData && forecastData.forecast) {
          const bias = forecastData.forecast.current_bias;
          if (bias === "LONG_CW") {
            drift = 0.0015; // +0.15% per day
          } else if (bias === "SKIP_CW" || bias === "CASH_ONLY") {
            drift = -0.002; // -0.2% per day
          }
        }

        const futureTimes = getFutureTimes(lastBar.time, 15, resolution);
        const upperData = [{ time: lastBar.time, value: lastPrice }];
        const lowerData = [{ time: lastBar.time, value: lastPrice }];
        const medianData = [{ time: lastBar.time, value: lastPrice }];


        futureTimes.forEach((time, index) => {
          const t = index + 1;
          const upperVal = lastPrice * (1 + drift * t + vol * Math.sqrt(t));
          const lowerVal = lastPrice * (1 + drift * t - vol * Math.sqrt(t));
          const medianVal = lastPrice * (1 + drift * t);

          upperData.push({ time, value: Math.round(upperVal * 100) / 100 });
          lowerData.push({ time, value: Math.round(lowerVal * 100) / 100 });
          medianData.push({ time, value: Math.round(medianVal * 100) / 100 });
        });

        upperForecastSeries.setData(upperData);
        lowerForecastSeries.setData(lowerData);
        medianForecastSeries.setData(medianData);
      } catch (_) { }
    }

    function safeSetData(bars) {
      if (isDisposed) return;
      try {
        candlestickSeries.setData(bars);
        loadedBars = bars;

        if (showRegime) {
          const { regimeBars, trendBars } = calculateCreedRegimeBands(bars);
          regimeSeries.setData(regimeBars);
          trendLineSeries.setData(trendBars);
        } else {
          regimeSeries.setData([]);
          trendLineSeries.setData([]);
        }

        const volumeBars = bars.map(b => {
          const vol = volumeMap[b.time] || 0;
          const isUp = b.close >= b.open;
          return {
            time: b.time,
            value: vol,
            color: isUp ? "rgba(0, 200, 151, 0.22)" : "rgba(239, 68, 68, 0.22)"
          };
        });
        volumeSeries.setData(volumeBars);

        // Markers will be handled dynamically via updateVisibleMarkers and subscribeVisibleLogicalRangeChange

        if (showForecast) {
          if (currentForecast) {
            drawForecast(bars, currentForecast);
          } else {
            drawForecast(bars, null);
          }
        } else {
          upperForecastSeries.setData([]);
          lowerForecastSeries.setData([]);
          medianForecastSeries.setData([]);
        }

        chart.timeScale().fitContent();
        try {
          chart.timeScale().subscribeVisibleLogicalRangeChange(updateVisibleMarkers);
          updateVisibleMarkers();
        } catch (_) { }
      } catch (_) { /* chart was disposed between the check and the call */ }
    }

    let cleanSymbol = (symbol || "VNINDEX").replace("HOSE:", "").replace("HNX:", "").toUpperCase();
    if (cleanSymbol === "CW" || cleanSymbol === "CW-INDEX") {
      cleanSymbol = "CWINDEX";
    } else if (cleanSymbol === "HNX" || cleanSymbol === "HNX-INDEX") {
      cleanSymbol = "HNXINDEX";
    }

    const resolutionDaysMap = {
      "1": 30, "5": 60, "15": 90, "30": 180, "60": 365,
      "1D": 1825, "1W": 3650, "1M": 5475,
    };
    const days = resolutionDaysMap[resolution];
    const toTime = Math.floor(Date.now() / 1000);
    const fromTime = days ? toTime - days * 86400 : toTime - 1825 * 86400;

    // Seeded PRNG — deterministic per symbol so each tab looks different
    function seededRnd(seed) {
      let s = seed;
      return () => {
        s = (s * 1103515245 + 12345) & 0x7fffffff;
        return s / 2147483647;
      };
    }

    function generateFallbackBars(tgtPrice) {
      // Realistic fallbacks per symbol
      const DEFAULTS = {
        VNINDEX: 1660.70, VN30: 1828.16, HNXINDEX: 273.84,
        CWINDEX: 108.45, UPINDEX: 124.21,
        SPX: 5420.10, DJI: 38800, NASDAQ: 17200,
      };
      let targetPrice = tgtPrice || externalTargetPrice || DEFAULTS[cleanSymbol];
      if (!targetPrice) {
        targetPrice = cleanSymbol.includes("INDEX") ? 1000.0 : 50.0;
      }

      const rnd = seededRnd(cleanSymbol.split("").reduce((a, c) => a + c.charCodeAt(0), 0) * 7919);
      const volPct = cleanSymbol.includes("HNX") ? 0.014 : cleanSymbol.includes("CW") || cleanSymbol.includes("INDEX") ? 0.018 : 0.012;
      const trendBias = cleanSymbol.includes("HNX") || cleanSymbol === "VN30" ? -0.0005 : 0.0004;

      let baseP = targetPrice * (trendBias >= 0 ? 0.88 : 1.12);
      const bars = [];

      let currTs = fromTime;
      while (currTs <= toTime) {
        const d = new Date(currTs * 1000);
        const dow = d.getUTCDay();
        if (dow !== 0 && dow !== 6) {
          const r1 = rnd() - 0.48;
          const r2 = rnd();
          const cycle = Math.sin(bars.length * 0.08 + (rnd() * 6));
          const change = (r1 * volPct + cycle * 0.003 + trendBias) * baseP;
          baseP = Math.max(5, baseP + change);

          const yr = d.getUTCFullYear();
          const mo = String(d.getUTCMonth() + 1).padStart(2, "0");
          const dy = String(d.getUTCDate()).padStart(2, "0");
          const timeStr = `${yr}-${mo}-${dy}`;

          const open = Math.round((baseP - change * 0.35) * 100) / 100;
          const close = Math.round(baseP * 100) / 100;
          const high = Math.round((Math.max(open, close) + Math.abs(change) * (0.3 + r2 * 0.4)) * 100) / 100;
          const low = Math.round((Math.min(open, close) - Math.abs(change) * (0.3 + (1 - r2) * 0.4)) * 100) / 100;
          const vol = Math.round(3000000 + r2 * 12000000);

          volumeMap[timeStr] = vol;
          bars.push({ time: timeStr, open, high, low, close });
        }
        currTs += 86400;
      }

      // Scale so last bar ends exactly at targetPrice without creating negative values
      if (bars.length > 0) {
        const lastClose = bars[bars.length - 1].close;
        const ratio = lastClose !== 0 ? targetPrice / lastClose : 1;
        for (const b of bars) {
          b.open = Math.round(b.open * ratio * 100) / 100;
          b.high = Math.round(b.high * ratio * 100) / 100;
          b.low = Math.round(b.low * ratio * 100) / 100;
          b.close = Math.round(b.close * ratio * 100) / 100;
        }
      }
      return bars;
    }

    const isIntraday = ["1", "5", "15", "30", "60"].includes(resolution);
    const backendBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8008";
    const url = `${backendBase}/api/udf/history?symbol=${cleanSymbol}&resolution=${resolution}&from=${fromTime}&to=${toTime}&_t=${Date.now()}`;

    // Render initial bars immediately to avoid blank space lag
    const initialFallbackBars = generateFallbackBars();
    safeSetData(initialFallbackBars);

    fetch(url, { signal: abortCtrl.signal, cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (isDisposed) return;
        if (data.s !== "ok" || !data.t || data.t.length === 0) {
          safeSetData(generateFallbackBars());
          return;
        }

        const bars = [];
        const seenDates = new Set();
        for (let i = 0; i < data.t.length; i++) {
          const timestampSec = data.t[i];
          let timeVal;
          if (isIntraday) {
            timeVal = timestampSec; // UNIX epoch timestamp for intraday bars
          } else {
            const dateObj = new Date(timestampSec * 1000);
            const yr = dateObj.getUTCFullYear();
            const mo = String(dateObj.getUTCMonth() + 1).padStart(2, "0");
            const dy = String(dateObj.getUTCDate()).padStart(2, "0");
            timeVal = `${yr}-${mo}-${dy}`;
          }

          if (seenDates.has(timeVal)) {
            continue; // Prevent duplicate time key crash in lightweight-charts
          }
          seenDates.add(timeVal);

          let c = data.c[i], o = data.o[i], h = data.h[i], l = data.l[i];
          // Backend may return raw VND (e.g. 1660700 instead of 1660.70)
          if (["VNINDEX", "VN30", "HNXINDEX"].includes(cleanSymbol) && c > 10000) {
            c /= 1000; o /= 1000; h /= 1000; l /= 1000;
          }

          volumeMap[timeVal] = data.v[i];
          bars.push({ time: timeVal, open: o, high: h, low: l, close: c });
        }

        if (bars.length > 0) {
          safeSetData(bars);
          if (onDataLoaded && !isDisposed) {
            const latest = bars[bars.length - 1];
            const prev = bars[bars.length - 2];
            const change = prev ? latest.close - prev.close : 0;
            const changePct = prev && prev.close ? (change / prev.close) * 100 : 0;
            onDataLoaded({ ...latest, change, changePct, volume: volumeMap[latest.time] || 0 });
          }
          // Fetch and draw S/R zones after real data is loaded
          if (showSR && !isDisposed) {
            const backendBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8008";
            fetch(`${backendBase}/api/regime/${cleanSymbol}/support-resistance?lookback_days=250`, {
              signal: abortCtrl.signal,
              cache: "no-store",
            })
              .then(r => {
                if (!r.ok) {
                  console.warn("⚠️ [Chart] S/R API HTTP error:", r.status, r.statusText);
                  return r.json().then(err => Promise.reject(err));
                }
                return r.json();
              })
              .then(srData => {
                if (!isDisposed && srData.status === "ok") {
                  console.log("✅ [Chart] S/R data loaded successfully");
                  loadedFractals = srData.fractals || [];
                  loadedBosLines = srData.bos_lines || [];
                  loadedChochLines = srData.choch_lines || [];
                  drawSRLines(srData);
                  drawBosLines(loadedBosLines, loadedChochLines);
                  updateVisibleMarkers();
                } else {
                  console.warn("⚠️ [Chart] S/R API returned non-ok status:", srData.status, srData.message || '');
                }
              })
              .catch(err => {
                if (err.name !== 'AbortError') {
                  console.error("❌ [Chart] S/R API error:", err?.message || String(err));
                }
              });
          }

          // Fetch and draw forecast after real data is loaded
          fetch(`${backendBase}/api/regime/forecast/${cleanSymbol}`, {
            signal: abortCtrl.signal,
            cache: "no-store",
          })
            .then(r => r.json())
            .then(forecastData => {
              if (!isDisposed && forecastData.status === "ok") {
                console.log("✅ [Chart] Forecast data loaded successfully");
                currentForecast = forecastData;
                setForecast(forecastData);
                if (loadedBars.length > 0) {
                  drawForecast(loadedBars, forecastData);
                }
              }
            })
            .catch(err => {
              if (err.name !== 'AbortError') {
                console.error("❌ [Chart] Forecast API error:", err?.message || String(err));
              }
            });
        } else {
          safeSetData(generateFallbackBars());
        }
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        safeSetData(generateFallbackBars());
      });

    // Crosshair events
    if (onCrosshairMove) {
      chart.subscribeCrosshairMove((param) => {
        if (isDisposed) return;
        if (!param || param.time === undefined || !param.point) {
          onCrosshairMove(null);
          return;
        }
        const bar = param.seriesData.get(candlestickSeries);
        if (!bar) return;

        let timeStr = "";
        if (typeof param.time === "string") {
          timeStr = param.time;
        } else if (typeof param.time === "number") {
          const d = new Date(param.time * 1000);
          timeStr = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
        } else if (param.time && typeof param.time === "object") {
          timeStr = `${param.time.year}-${String(param.time.month).padStart(2, "0")}-${String(param.time.day).padStart(2, "0")}`;
        }

        onCrosshairMove({ time: param.time, ...bar, volume: volumeMap[timeStr] || 0 });
      });
    }

    const handleResize = () => {
      if (!isDisposed && chartContainerRef.current) {
        try { chart.applyOptions({ width: chartContainerRef.current.clientWidth }); } catch (_) { }
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      isDisposed = true;
      abortCtrl.abort();
      window.removeEventListener("resize", handleResize);
      // Clean up price lines before removing chart
      srLines.forEach(line => { try { candlestickSeries.removePriceLine(line); } catch (_) { } });
      bosSeriesList.forEach(series => { try { chart.removeSeries(series); } catch (_) { } });
      try { chart.remove(); } catch (_) { }
    };
  }, [symbol, theme, height, timeframe, externalTargetPrice, showSR, showForecast, showRegime, !!showStructure]);

  return (
    <div style={{ width: "100%", height: `${height}px`, position: "relative" }}>
      <div
        ref={chartContainerRef}
        style={{ width: "100%", height: "100%" }}
      />
      {showForecast && forecast && forecast.forecast && (() => {
        const isEn = language === "en";
        const bias = forecast.forecast.current_bias;
        const isBull = bias === "LONG_CW";
        const isBear = bias === "SKIP_CW" || bias === "CASH_ONLY";

        const current_confidence = forecast.forecast.current_confidence || 0.65;
        const confidencePctStr = `${(current_confidence * 100).toFixed(1)}%`;
        const statusText = isBull ? (isEn ? `Bullish (${confidencePctStr})` : `Tăng giá (${confidencePctStr})`) : isBear ? (isEn ? `Bearish (${confidencePctStr})` : `Giảm giá (${confidencePctStr})`) : (isEn ? "Sideways" : "Đi ngang");
        const statusColor = isBull ? "#10b981" : isBear ? "#ef4444" : "#f59e0b";
        const arrow = isBull ? "📈" : isBear ? "📉" : "➡️";
        const actionText = isBull ? (isEn ? "BUY" : "MUA VÀO") : (isEn ? "HOLD CASH" : "ĐỨNG NGOÀI");
        const actionColor = isBull ? "#10b981" : "#ef4444";

        const risk = forecast.forecast.transition_risk || "MEDIUM";
        const riskColor = risk === "LOW" ? "#10b981" : risk === "MEDIUM" ? "#f59e0b" : "#ef4444";
        const riskLabel = risk === "LOW" ? (isEn ? "Low" : "Thấp") : risk === "MEDIUM" ? (isEn ? "Medium" : "Trung bình") : (isEn ? "High" : "Cao");

        const regimeMeta = {
          BULLISH_VOL_EXPANSION: { label: isEn ? "Bull Expansion" : "Tăng mạnh (Mở rộng)", color: "#10b981" },
          BULLISH_VOL_CONTRACTION: { label: isEn ? "Bull Accumulation" : "Tăng tích lũy (Bình ổn)", color: "#60a5fa" },
          SIDEWAYS: { label: isEn ? "Sideways" : "Đi ngang (Lưỡng lự)", color: "#f59e0b" },
          BEARISH_HIGH_VOL: { label: isEn ? "Bear High Vol (Panic)" : "Giảm mạnh (Hoảng loạn)", color: "#ef4444" },
          BEARISH_VOL_CONTRACTION: { label: isEn ? "Bear Accumulation" : "Giảm nhẹ (Tích lũy)", color: "#f97316" }
        };

        const biasMeta = {
          LONG_CW: { label: isEn ? "BUY" : "MUA", color: "#10b981" },
          NEUTRAL: { label: isEn ? "WATCH" : "T.DÕI", color: "#f59e0b" },
          CASH_ONLY: { label: isEn ? "CASH" : "BỎ QUA", color: "#ef4444" },
          SKIP_CW: { label: isEn ? "SKIP" : "BỎ QUA", color: "#ef4444" },
        };

        const getBiasBadge = (b) => {
          const m = biasMeta[b] || { label: b || "CASH", color: "#ef4444" };
          return (
            <span style={{ background: `${m.color}22`, border: `1px solid ${m.color}66`, color: m.color, padding: "2px 6px", borderRadius: "4px", fontWeight: "bold", fontSize: "10px", whiteSpace: "nowrap" }}>
              {m.label}
            </span>
          );
        };

        const isDark = theme === "dark";
        const cardBg = isDark ? "rgba(19, 27, 46, 0.95)" : "rgba(255, 255, 255, 0.96)";
        const cardBorder = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(226, 232, 240, 0.9)";
        const textColor = isDark ? "#f8fafc" : "#0f172a";
        const mutedText = isDark ? "#94a3b8" : "#64748b";
        const boxBg = isDark ? "rgba(255,255,255,0.02)" : "rgba(241, 245, 249, 0.8)";
        const boxBorder = isDark ? "rgba(255,255,255,0.04)" : "rgba(203, 213, 225, 0.6)";

        return (
          <div
            style={{
              position: "absolute",
              top: "10px",
              left: "15px",
              background: cardBg,
              backdropFilter: "blur(16px)",
              border: `1px solid ${cardBorder}`,
              borderRadius: "8px",
              padding: "10px 14px",
              color: textColor,
              fontSize: "11px",
              fontFamily: "sans-serif",
              zIndex: 10,
              pointerEvents: "auto",
              boxShadow: isDark ? "0 8px 24px rgba(0, 0, 0, 0.5)" : "0 8px 24px rgba(148, 163, 184, 0.25)",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              width: "320px",
              transition: "all 0.25s ease-in-out",
            }}
          >
            {/* Header summary */}
            <div
              onClick={() => setShowForecastDetails(!showForecastDetails)}
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer", userSelect: "none" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: mutedText, fontWeight: "500" }}>{isEn ? "T+5 Forecast:" : "Dự báo T+5:"}</span>
                <span style={{ color: statusColor, fontWeight: "bold" }}>
                  {arrow} {statusText}
                </span>
              </div>
              <span style={{ color: "#2563eb", fontSize: "10px", fontWeight: "bold" }}>
                {showForecastDetails ? (isEn ? " Collapse ▲" : " Thu gọn ▲") : (isEn ? " Details ▼" : " Chi tiết ▼")}
              </span>
            </div>

            {/* Default actions row */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px", borderBottom: showForecastDetails ? `1px solid ${cardBorder}` : "none", paddingBottom: showForecastDetails ? "6px" : "0" }}>
              <span style={{ color: mutedText }}>{isEn ? "Action:" : "Hành động:"}</span>
              <span style={{ color: actionColor, fontWeight: "bold" }}>{actionText}</span>
              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "4px" }}>
                <span style={{ color: mutedText, fontSize: "10px" }}>{isEn ? "Risk:" : "Rủi ro:"}</span>
                <span style={{ color: riskColor, fontWeight: "bold", fontSize: "10px" }}>{riskLabel}</span>
              </div>
            </div>

            {/* Expanded section */}
            {showForecastDetails && (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px" }}>
                {/* 5-Day recommendation path */}
                <div>
                  <div style={{ color: mutedText, fontSize: "10px", fontWeight: "bold", marginBottom: "4px" }}>{isEn ? "RECOMMENDED PATH (T+1 → T+5)" : "LỘ TRÌNH KHUYẾN NGHỊ (T+1 → T+5)"}</div>
                  <div style={{ display: "flex", justifyContent: "space-between", background: boxBg, padding: "6px 8px", borderRadius: "6px", border: `1px solid ${boxBorder}` }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                      <span style={{ color: mutedText, fontSize: "9px" }}>T+1</span>
                      {getBiasBadge(forecast.forecast.current_bias)}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                      <span style={{ color: mutedText, fontSize: "9px" }}>T+2</span>
                      {getBiasBadge(forecast.forecast.t2_bias)}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                      <span style={{ color: mutedText, fontSize: "9px" }}>T+3</span>
                      {getBiasBadge(forecast.forecast.t3_bias)}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                      <span style={{ color: mutedText, fontSize: "9px" }}>T+4</span>
                      {getBiasBadge(forecast.forecast.t4_bias)}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                      <span style={{ color: mutedText, fontSize: "9px" }}>T+5</span>
                      {getBiasBadge(forecast.forecast.t5_bias)}
                    </div>
                  </div>
                </div>

                {/* Dynamic Scenario Text */}
                <div style={{ background: boxBg, padding: "8px", borderRadius: "6px", border: `1px solid ${boxBorder}`, fontSize: "10px", lineHeight: "1.4" }}>
                  <div style={{ color: mutedText, fontWeight: "bold", marginBottom: "4px" }}>
                    {isEn ? "ANALYSIS & FORECAST SCENARIO" : "KỊCH BẢN PHÂN TÍCH & DỰ BÁO"}
                  </div>
                  <span style={{ color: textColor }}>
                    {(() => {
                      const current_confidence = forecast.forecast.current_confidence || 0.65;
                      if (isBear) {
                        return isEn 
                          ? `The market is in a Bearish regime (${(current_confidence * 100).toFixed(1)}% confidence). Price is currently trading below the Master Trend line. The system forecasts a high probability of consolidation or correction towards local support areas. Action: Hold cash, avoid covered warrants.`
                          : `Thị trường đang ở pha Giảm giá/Rủi ro (Độ tin cậy ${(current_confidence * 100).toFixed(1)}%). Giá đang giao dịch dưới đường Master Trend. Hệ thống dự báo xác suất cao thị trường sẽ đi ngang tích lũy hoặc điều chỉnh về các vùng hỗ trợ cũ. Khuyến nghị: Ưu tiên giữ tiền mặt, tạm dừng mua mới chứng quyền.`;
                      } else if (isBull) {
                        return isEn
                          ? `The market is in a Bullish trend (${(current_confidence * 100).toFixed(1)}% confidence). Price is trading above the Master Trend line with positive momentum. The system forecasts continuation of the upward path. Action: Buy/Long Covered Warrants.`
                          : `Thị trường đang ở pha Tăng giá tích cực (Độ tin cậy ${(current_confidence * 100).toFixed(1)}%). Giá giao dịch trên đường Master Trend với động lực tăng mạnh. Hệ thống dự báo xu hướng tăng tiếp tục được duy trì. Khuyến nghị: Phù hợp mua vào chứng quyền Call.`;
                      } else {
                        return isEn
                          ? `The market is in a Sideways/Neutral phase (${(current_confidence * 100).toFixed(1)}% confidence). Volatility is high but trend direction is unclear. The system recommends waiting for a breakout. Action: Watch/Reduce position size.`
                          : `Thị trường đang ở pha Đi ngang/Lưỡng lự (Độ tin cậy ${(current_confidence * 100).toFixed(1)}%). Biến động cao nhưng xu hướng chưa rõ ràng. Hệ thống khuyến nghị chờ đợi tín hiệu bứt phá. Khuyến nghị: Theo dõi, hạ quy mô vị thế.`;
                      }
                    })()}
                  </span>
                </div>

                {/* Transition Probabilities */}
                {forecast.forecast.transition_probabilities && (
                  <div>
                    <div style={{ color: mutedText, fontSize: "10px", fontWeight: "bold", marginBottom: "6px" }}>{isEn ? "HMM STATE TRANSITION PROBABILITIES" : "XÁC SUẤT DỊCH CHUYỂN TRẠNG THÁI HMM"}</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {Object.entries(forecast.forecast.transition_probabilities)
                        .sort((a, b) => b[1] - a[1])
                        .map(([regimeKey, prob]) => {
                          const meta = regimeMeta[regimeKey] || { label: regimeKey, color: mutedText };
                          const pct = Math.round(prob * 100);
                          return (
                            <div key={regimeKey} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px" }}>
                                <span style={{ color: meta.color, fontWeight: "500" }}>{meta.label}</span>
                                <span style={{ fontWeight: "bold", color: textColor }}>{pct}%</span>
                              </div>
                              <div style={{ width: "100%", height: "4px", background: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.08)", borderRadius: "2px", overflow: "hidden" }}>
                                <div style={{ width: `${pct}%`, height: "100%", background: meta.color, borderRadius: "2px" }} />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
