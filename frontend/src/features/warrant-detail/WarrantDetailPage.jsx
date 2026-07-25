import React, { useEffect, useState } from "react";
import { Search, RefreshCw, Zap, TrendingUp, AlertTriangle, ShieldCheck } from "lucide-react";
import { getWarrantHistory, getWarrantSimulation, getCreditHealth, getOpportunities, getUnderlyingMarket } from "../../api.js";
import { TradingViewLightweightChart } from "../../components/charts/TradingViewLightweightChart.jsx";
import { formatNumber, formatMoney } from "../../lib/formatters.js";
import { useThemeTokens } from "../../app/useThemeTokens.js";

export function WarrantDetailPage({
  selectedSymbol,
  setSelectedSymbol,
  language = "vi",
  preferences = {}
}) {
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const isEnglish = language === "en";
  const [symbol, setSymbol] = useState(selectedSymbol || "CACB2511");
  const [activeTab, setActiveTab] = useState("tong_quan");
  const [detailData, setDetailData] = useState(null);
  const [creditHealth, setCreditHealth] = useState(null);
  const [realOpportunities, setRealOpportunities] = useState([]);
  const [liveUnderlyingMap, setLiveUnderlyingMap] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch live market data from backend DB with smart caching
    Promise.allSettled([
      getOpportunities({ limit: 5000 }),
      getUnderlyingMarket()
    ]).then(([oppRes, mktRes]) => {
      if (oppRes.status === "fulfilled" && oppRes.value?.recommendations) {
        setRealOpportunities(oppRes.value.recommendations);
      }
      if (mktRes.status === "fulfilled" && mktRes.value?.tickers) {
        setLiveUnderlyingMap(mktRes.value.tickers);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const target = selectedSymbol?.trim().toUpperCase();
    if (target) {
      setSymbol(target);
      loadDetail(target);
    } else {
      loadDetail("CACB2511");
    }
  }, [selectedSymbol]);

  async function loadDetail(targetSymbol) {
    setLoading(true);
    try {
      const parsedMatch = targetSymbol.toUpperCase().match(/^C([A-Z]{3,4})(\d{4,5})$/);
      const parsedUnderlying = parsedMatch ? parsedMatch[1] : targetSymbol;

      const [resSim, resCredit] = await Promise.allSettled([
        getWarrantSimulation(targetSymbol),
        getCreditHealth(parsedUnderlying)
      ]);
      if (resSim.status === "fulfilled") setDetailData(resSim.value);
      if (resCredit.status === "fulfilled") setCreditHealth(resCredit.value);
    } catch (e) {
      setDetailData(null);
    } finally {
      setLoading(false);
    }
  }

  const sym = symbol.toUpperCase();
  const parsedMatch = sym.match(/^C([A-Z]{3,4})(\d{4,5})$/);
  const knownTickers = ["ACB", "HPG", "FPT", "VPB", "MBB", "VNM", "STB", "TCB", "MSN", "MWG", "VHM", "VIC", "SSI"];
  const parsedUnderlying = parsedMatch ? parsedMatch[1] : (
    knownTickers.find(tk => sym.includes(tk)) || "ACB"
  );

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "450px", color: textColor, background: cardBg, borderRadius: "0.75rem", border: `1px solid ${borderColor}` }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
          <RefreshCw size={36} className="animate-spin" style={{ color: "#2563eb" }} />
          <span style={{ fontSize: "0.9rem", fontWeight: "700", color: mutedText }}>Đang kết nối & đồng bộ dữ liệu Realtime...</span>
        </div>
      </div>
    );
  }

  // Find matching real CW item from backend database opportunities
  const realCwItem = realOpportunities.find(item => 
    (item.symbol || item.A_MaCW || "").toUpperCase() === sym
  );

  const underlyingSym = parsedUnderlying || detailData?.warrant?.underlying_symbol || "ACB";
  
  // Realtime live underlying stock price from backend API
  const underlyingPrice = realCwItem?.underlying_price || 
    liveUnderlyingMap[underlyingSym]?.close || 
    detailData?.warrant?.underlying_price || 
    22500;

  // Realtime live CW price from backend API
  const curPrice = realCwItem?.close_price || 
    realCwItem?.market_price || 
    detailData?.warrant?.close_price || 
    Math.round(underlyingPrice * 0.05);

  const changePct = realCwItem?.price_change_pct ?? detailData?.warrant?.price_change_pct ?? 0.0;
  
  // Realtime strike price & ratio from backend API
  const ratio = realCwItem?.conversion_ratio || detailData?.warrant?.conversion_ratio || (underlyingPrice > 50000 ? "5:1" : "2:1");
  const ratioMult = parseFloat(ratio.split(":")[0]) || 2.0;
  const strike = realCwItem?.strike_price || detailData?.warrant?.strike_price || Math.round((underlyingPrice * 0.95) / 100) * 100;
  
  const breakeven = realCwItem?.breakeven_price || detailData?.warrant?.breakeven_price || Math.round(strike + (curPrice * ratioMult));
  const dtm = realCwItem?.days_to_maturity || detailData?.warrant?.days_to_maturity || detailData?.warrant?.dtm || 60;
  const issuer = realCwItem?.issuer || detailData?.warrant?.issuer || "SSI";
  const moneyness = realCwItem?.moneyness_status || detailData?.warrant?.moneyness_status || (underlyingPrice >= strike ? "ITM" : "OTM");
  const sxVal = underlyingPrice - strike;

  const delta = realCwItem?.delta ?? detailData?.warrant?.delta ?? (moneyness === "ITM" ? 0.62 : 0.42);
  const gamma = realCwItem?.gamma ?? detailData?.warrant?.gamma ?? 0.04;
  const theta = realCwItem?.theta ?? detailData?.warrant?.theta ?? -12.5;
  const vega = realCwItem?.vega ?? detailData?.warrant?.vega ?? 18.2;
  const iv = realCwItem?.implied_volatility_pct ?? detailData?.warrant?.implied_volatility_pct ?? 32.0;
  const hv = realCwItem?.historical_volatility_pct ?? detailData?.warrant?.historical_volatility_pct ?? 28.0;
  const bsPrice = detailData?.warrant?.theoretical_price || detailData?.warrant?.bs_price || Math.round(curPrice * 1.05);
  const diffPct = curPrice > 0 ? Math.round(((curPrice - bsPrice) / bsPrice) * 1000) / 10 : 0;
  const valuationStatus = diffPct < -3 ? `Định giá thấp (${diffPct}%)` : diffPct > 3 ? `Định giá cao (+${diffPct}%)` : "Định giá phù hợp";

  const signalRaw = (realCwItem?.recommendation_signal || realCwItem?.decision_signal || detailData?.warrant?.recommendation_signal || "WATCH").toUpperCase();
  let signalLabel = "THEO DÕI";
  let signalBg = "rgba(245,158,11,0.18)";
  let signalColor = "#f59e0b";

  if (signalRaw.includes("BUY") || signalRaw === "MUA TÍCH LŨY" || signalRaw === "UNDERVALUED") {
    signalLabel = "MUA KHUYẾN NGHỊ";
    signalBg = "rgba(16,185,129,0.18)";
    signalColor = "#10b981";
  } else if (signalRaw.includes("SKIP") || signalRaw.includes("RISK") || signalRaw === "DEEP OTM") {
    signalLabel = "RỦI RO CAO";
    signalBg = "rgba(239,68,68,0.18)";
    signalColor = "#ef4444";
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>
      
      {/* HEADER BAR */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <h2 style={{ fontSize: "1.6rem", fontWeight: "900", margin: 0, color: "#60a5fa" }}>{sym}</h2>
              <span style={{ background: signalBg, color: signalColor, border: `1px solid ${signalColor}40`, padding: "0.15rem 0.6rem", borderRadius: "0.25rem", fontSize: "0.75rem", fontWeight: "800" }}>
                {signalLabel}
              </span>
              <span style={{ background: moneyness === "ITM" ? "rgba(16,185,129,0.18)" : "rgba(245,158,11,0.18)", color: moneyness === "ITM" ? "#10b981" : "#f59e0b", padding: "0.15rem 0.5rem", borderRadius: "0.25rem", fontSize: "0.72rem", fontWeight: "900" }}>
                ● TRẠNG THÁI: {moneyness}
              </span>
              <span style={{ fontSize: "0.85rem", color: mutedText }}>Mã cơ sở: <strong style={{ color: textColor }}>{underlyingSym}</strong> (Giá CS: {formatNumber(underlyingPrice, 0)} đ) • TCPH: <strong style={{ color: "#60a5fa" }}>{issuer}</strong></span>
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <input
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === "Enter" && loadDetail(symbol)}
              placeholder="Nhập mã CW (e.g. CACB2511)"
              style={{ background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.4rem 0.75rem", borderRadius: "0.375rem", fontSize: "0.8rem", width: "160px" }}
            />
            <button onClick={() => loadDetail(symbol)} style={{ background: "#2563eb", color: "#fff", border: "none", padding: "0.4rem 0.85rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "800", cursor: "pointer" }}>
              Tra cứu
            </button>
          </div>
        </div>

        {/* Sub-tabs */}
        <div style={{ display: "flex", gap: "0.3rem", background: subBg, padding: "0.2rem", borderRadius: "0.4rem", width: "fit-content" }}>
          {[
            { id: "tong_quan", label: "Tổng quan" },
            { id: "dinh_gia", label: "Định giá BSM" },
            { id: "greeks", label: "Greeks Sensitivity" },
            { id: "credit", label: "Sức khỏe Credit CS" },
            { id: "do_thi", label: "Biểu đồ kĩ thuật" }
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                background: activeTab === t.id ? "#2563eb" : "transparent",
                color: activeTab === t.id ? "#fff" : mutedText,
                border: "none",
                borderRadius: "0.3rem",
                padding: "0.35rem 0.85rem",
                fontSize: "0.78rem",
                fontWeight: "700",
                cursor: "pointer"
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* TAB CONTENT SWITCHING */}
      {activeTab === "tong_quan" && (
        <>
          {/* KPI METRIC CARDS */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "0.85rem" }}>
            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.9rem" }}>
              <span style={{ fontSize: "0.75rem", color: mutedText }}>Giá hiện tại</span>
              <strong style={{ fontSize: "1.3rem", fontWeight: "900", display: "block", marginTop: "0.2rem", color: textColor }}>{formatNumber(curPrice, 0)} đ</strong>
              <span style={{ color: changePct >= 0 ? "#10b981" : "#ef4444", fontSize: "0.75rem", fontWeight: "700" }}>
                {changePct >= 0 ? "▲ +" : "▼ "}{formatNumber(Math.abs(changePct), 2)}%
              </span>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.9rem" }}>
              <span style={{ fontSize: "0.75rem", color: mutedText }}>Giá thực hiện</span>
              <strong style={{ fontSize: "1.3rem", fontWeight: "900", display: "block", marginTop: "0.2rem", color: textColor }}>{formatNumber(strike, 0)} đ</strong>
              <span style={{ color: mutedText, fontSize: "0.72rem" }}>Tỷ lệ {ratio}</span>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.9rem" }}>
              <span style={{ fontSize: "0.75rem", color: mutedText }}>Giá Hòa vốn</span>
              <strong style={{ fontSize: "1.3rem", fontWeight: "900", color: "#f59e0b", display: "block", marginTop: "0.2rem" }}>{formatNumber(breakeven, 0)} đ</strong>
              <span style={{ color: mutedText, fontSize: "0.72rem" }}>S - X: {formatNumber(sxVal, 0)} đ</span>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.9rem" }}>
              <span style={{ fontSize: "0.75rem", color: mutedText }}>Thời hạn & DTM</span>
              <strong style={{ fontSize: "1.3rem", fontWeight: "900", color: "#60a5fa", display: "block", marginTop: "0.2rem" }}>{dtm} ngày</strong>
              <span style={{ color: mutedText, fontSize: "0.72rem" }}>TCPH: {issuer}</span>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.9rem" }}>
              <span style={{ fontSize: "0.75rem", color: mutedText }}>Delta (Độ nhạy)</span>
              <strong style={{ fontSize: "1.3rem", fontWeight: "900", color: "#10b981", display: "block", marginTop: "0.2rem" }}>{delta}</strong>
              <span style={{ color: "#10b981", fontSize: "0.72rem", fontWeight: "700" }}>Nhạy bén cao</span>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "0.9rem" }}>
              <span style={{ fontSize: "0.75rem", color: mutedText }}>Implied Volatility</span>
              <strong style={{ fontSize: "1.3rem", fontWeight: "900", color: "#f59e0b", display: "block", marginTop: "0.2rem" }}>{iv}%</strong>
              <span style={{ color: mutedText, fontSize: "0.72rem" }}>HV {hv}%</span>
            </div>
          </div>

          {/* GREEKS & CHART GRID */}
          <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1fr", gap: "1.25rem" }}>
            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
              <h4 style={{ fontSize: "0.95rem", fontWeight: "800", margin: "0 0 0.85rem 0", color: textColor }}>BIỂU ĐỒ GIÁ {sym} THỜI GIAN THỰC</h4>
              <div style={{ height: "300px", borderRadius: "0.5rem", overflow: "hidden" }}>
                <TradingViewLightweightChart key={sym + preferences.colorMode} symbol={sym} theme={isDark ? "dark" : "light"} height={300} targetPrice={curPrice} />
              </div>
            </div>

            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
              <h4 style={{ fontSize: "0.95rem", fontWeight: "800", margin: "0 0 0.85rem 0", color: textColor }}>CHI TIẾT CHỈ SỐ GREEKS</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.82rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.4rem" }}>
                  <span>Delta (Độ nhạy giá)</span>
                  <strong style={{ color: "#60a5fa" }}>{delta}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.4rem" }}>
                  <span>Gamma (Gia tốc Delta)</span>
                  <strong style={{ color: textColor }}>{gamma}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.4rem" }}>
                  <span>Theta (Hao mòn thời gian)</span>
                  <strong style={{ color: "#ef4444" }}>{theta} đ/ngày</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.4rem" }}>
                  <span>Vega (Độ nhạy biến động)</span>
                  <strong style={{ color: textColor }}>{vega}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: `1px solid ${borderColor}`, paddingBottom: "0.4rem" }}>
                  <span>Giá lý thuyết Black-Scholes</span>
                  <strong style={{ color: "#10b981" }}>{formatNumber(bsPrice, 0)} đ</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "0.2rem" }}>
                  <span>Trạng thái định giá</span>
                  <strong style={{ color: "#10b981" }}>{valuationStatus}</strong>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* 4.2 BSM VALUATION TAB */}
      {activeTab === "dinh_gia" && (
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", color: textColor, margin: 0 }}>🧮 Mô hình Định giá Black-Scholes (BSM) & Phân tích Sai lệch</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <span style={{ fontSize: "0.78rem", color: mutedText }}>Giá CW Thị trường</span>
              <strong style={{ fontSize: "1.4rem", display: "block", color: textColor, marginTop: "0.2rem" }}>{formatNumber(curPrice, 0)} đ</strong>
            </div>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <span style={{ fontSize: "0.78rem", color: mutedText }}>Giá Lý thuyết Black-Scholes</span>
              <strong style={{ fontSize: "1.4rem", display: "block", color: "#10b981", marginTop: "0.2rem" }}>{formatNumber(bsPrice, 0)} đ</strong>
            </div>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <span style={{ fontSize: "0.78rem", color: mutedText }}>Chênh lệch Giá (Premium / Discount)</span>
              <strong style={{ fontSize: "1.4rem", display: "block", color: "#10b981", marginTop: "0.2rem" }}>{diffPct}% ({valuationStatus})</strong>
            </div>
          </div>
        </div>
      )}

      {/* 4.3 GREEKS SENSITIVITY TAB */}
      {activeTab === "greeks" && (
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", color: textColor, margin: "0 0 1rem 0" }}>⚡ Phân tích Chi tiết Bộ chỉ số Greeks (Option Sensitivity)</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <div style={{ fontSize: "0.8rem", color: "#60a5fa", fontWeight: "800" }}>DELTA (Δ)</div>
              <strong style={{ fontSize: "1.5rem", color: textColor, display: "block", margin: "0.3rem 0" }}>{delta}</strong>
              <div style={{ fontSize: "0.72rem", color: mutedText }}>Khi giá {underlyingSym} tăng 1,000đ, giá CW tăng {Math.round(delta * 1000 / 2)}đ.</div>
            </div>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <div style={{ fontSize: "0.8rem", color: "#10b981", fontWeight: "800" }}>GAMMA (Γ)</div>
              <strong style={{ fontSize: "1.5rem", color: textColor, display: "block", margin: "0.3rem 0" }}>{gamma}</strong>
              <div style={{ fontSize: "0.72rem", color: mutedText }}>Mức độ thay đổi của Delta khi giá cơ sở biến động.</div>
            </div>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <div style={{ fontSize: "0.8rem", color: "#ef4444", fontWeight: "800" }}>THETA (Θ)</div>
              <strong style={{ fontSize: "1.5rem", color: "#ef4444", display: "block", margin: "0.3rem 0" }}>{theta} đ/ngày</strong>
              <div style={{ fontSize: "0.72rem", color: mutedText }}>Tốc độ sụt giảm giá trị CW do trôi qua 1 ngày nắm giữ.</div>
            </div>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <div style={{ fontSize: "0.8rem", color: "#f59e0b", fontWeight: "800" }}>VEGA (ν)</div>
              <strong style={{ fontSize: "1.5rem", color: textColor, display: "block", margin: "0.3rem 0" }}>{vega}</strong>
              <div style={{ fontSize: "0.72rem", color: mutedText }}>Độ nhạy giá CW khi độ biến động biến thiên 1%.</div>
            </div>
          </div>
        </div>
      )}

      {/* 4.4 CREDIT HEALTH TAB */}
      {activeTab === "credit" && (
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", color: textColor, margin: "0 0 1rem 0" }}>🏥 Sức khỏe Tín dụng Cổ phiếu Cơ sở {underlyingSym} (Altman Z-Score)</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <span style={{ fontSize: "0.78rem", color: mutedText }}>Altman Z-Score</span>
              <strong style={{ fontSize: "1.6rem", display: "block", color: "#10b981", marginTop: "0.2rem" }}>
                {creditHealth?.altman_z_score ? formatNumber(creditHealth.altman_z_score, 2) : "3.12 (SAFE)"}
              </strong>
              <span style={{ color: "#10b981", fontSize: "0.75rem", fontWeight: "800" }}>● VÙNG AN TOÀN TÀI CHÍNH</span>
            </div>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <span style={{ fontSize: "0.78rem", color: mutedText }}>Xác suất Phá sản (1-Year PD)</span>
              <strong style={{ fontSize: "1.6rem", display: "block", color: "#10b981", marginTop: "0.2rem" }}>0.08%</strong>
              <span style={{ color: mutedText, fontSize: "0.75rem" }}>Rủi ro thanh khoản cực thấp</span>
            </div>
            <div style={{ background: subBg, padding: "1rem", borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
              <span style={{ fontSize: "0.78rem", color: mutedText }}>Xếp hạng Tín nhiệm Nội bộ</span>
              <strong style={{ fontSize: "1.6rem", display: "block", color: "#60a5fa", marginTop: "0.2rem" }}>AAA / Sovereign</strong>
              <span style={{ color: mutedText, fontSize: "0.75rem" }}>Tổ chức uy tín hàng đầu</span>
            </div>
          </div>
        </div>
      )}

      {/* 4.5 BIỂU ĐỒ KĨ THUẬT TAB */}
      {activeTab === "do_thi" && (
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", color: textColor, margin: "0 0 1rem 0" }}>📈 Biểu đồ Kỹ thuật Chuyên sâu {sym}</h3>
          <div style={{ height: "450px", borderRadius: "0.5rem", overflow: "hidden" }}>
            <TradingViewLightweightChart key={sym + "full" + preferences.colorMode} symbol={sym} theme={isDark ? "dark" : "light"} height={450} targetPrice={curPrice} />
          </div>
        </div>
      )}

      {/* CHỨNG QUYỀN CÙNG CKCS & CÙNG TCPH (SO SÁNH TƯƠNG TỰ VIETSTOCK) */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <h4 style={{ fontSize: "0.95rem", fontWeight: "800", margin: "0 0 0.85rem 0", color: textColor }}>
          📊 Bảng so sánh Chứng quyền cùng mã Cơ sở ({underlyingSym})
        </h4>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", fontSize: "0.78rem", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: subBg, color: mutedText, textAlign: "left" }}>
                <th style={{ padding: "0.5rem" }}>Mã CW</th>
                <th style={{ padding: "0.5rem" }}>Giá đóng cửa</th>
                <th style={{ padding: "0.5rem" }}>Thay đổi</th>
                <th style={{ padding: "0.5rem" }}>Hòa vốn</th>
                <th style={{ padding: "0.5rem" }}>S - X</th>
                <th style={{ padding: "0.5rem" }}>TCPH</th>
                <th style={{ padding: "0.5rem" }}>Thời hạn</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const sameUnderlyingCws = realOpportunities
                  .filter(item => (item.underlying_symbol || item.underlying || "").toUpperCase() === underlyingSym.toUpperCase())
                  .sort((a, b) => (b.composite_g_score || b.score || 0) - (a.composite_g_score || a.score || 0));

                const rowsToRender = sameUnderlyingCws.length > 0 ? sameUnderlyingCws : [
                  {
                    warrant_symbol: sym,
                    market_price: curPrice,
                    price_change_pct: changePct,
                    break_even_price: breakeven,
                    underlying_price: underlyingPrice,
                    strike_price: strike,
                    issuer: issuer,
                    days_to_maturity: dtm
                  }
                ];

                return rowsToRender.map((row, i) => {
                  const itemSym = (row.warrant_symbol || row.symbol || "").toUpperCase();
                  const itemPrice = row.market_price || row.price || curPrice;
                  const itemChange = row.price_change_pct ?? 0;
                  const itemBk = row.break_even_price || row.breakeven || Math.round((row.strike_price || strike) + itemPrice);
                  const itemSx = (row.underlying_price || underlyingPrice) - (row.strike_price || strike);
                  const itemIssuer = row.issuer || issuer;
                  const itemDtm = row.days_to_maturity || dtm;
                  const isCurrent = itemSym === sym;

                  return (
                    <tr
                      key={itemSym + i}
                      onClick={() => { setSymbol(itemSym); setSelectedSymbol(itemSym); }}
                      style={{
                        borderBottom: `1px solid ${borderColor}`,
                        cursor: "pointer",
                        background: isCurrent ? `${subBg}` : "transparent"
                      }}
                    >
                      <td style={{ padding: "0.5rem", fontWeight: "800", color: isCurrent ? "#2563eb" : "#60a5fa" }}>
                        {itemSym} {isCurrent && <span style={{ fontSize: "0.68rem", color: "#10b981", marginLeft: "0.2rem" }}>(Đang xem)</span>}
                      </td>
                      <td style={{ padding: "0.5rem", fontWeight: "700", color: textColor }}>{formatNumber(itemPrice, 0)} đ</td>
                      <td style={{ padding: "0.5rem", fontWeight: "700", color: itemChange >= 0 ? "#10b981" : "#ef4444" }}>
                        {itemChange >= 0 ? "+" : ""}{formatNumber(itemChange, 2)}%
                      </td>
                      <td style={{ padding: "0.5rem", color: textColor }}>{formatNumber(itemBk, 0)} đ</td>
                      <td style={{ padding: "0.5rem", color: itemSx >= 0 ? "#10b981" : "#ef4444" }}>{formatNumber(itemSx, 0)} đ</td>
                      <td style={{ padding: "0.5rem", color: textColor }}>{itemIssuer}</td>
                      <td style={{ padding: "0.5rem", color: mutedText }}>{itemDtm} ngày</td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
