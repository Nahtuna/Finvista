import React, { useEffect, useRef, useState } from "react";

function Sparkline({ data, color = "#2563eb", height = 40, width = 100 }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} fill="none">
      <polyline points={pts} stroke={color} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={`${pts} ${width},${height} 0,${height}`} fill={`${color}20`} stroke="none" />
    </svg>
  );
}

function useCountUp(target, duration = 1800, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime = null;
    const step = (ts) => {
      if (!startTime) startTime = ts;
      const progress = Math.min((ts - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(ease * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [start, target, duration]);
  return count;
}

function useInView(threshold = 0.2) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true); }, { threshold });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, inView];
}

function StatCounter({ target, label, suffix = "", prefix = "" }) {
  const [ref, inView] = useInView(0.3);
  const count = useCountUp(target, 1600, inView);
  return (
    <div ref={ref} style={{ textAlign: "center", padding: "2rem 1rem" }}>
      <div style={{
        fontSize: "3.5rem", fontWeight: 800,
        background: "linear-gradient(135deg, #2563eb, #06b6d4)",
        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        lineHeight: 1.1, marginBottom: "0.5rem"
      }}>
        {prefix}{count.toLocaleString()}{suffix}
      </div>
      <div style={{ color: "#64748b", fontSize: "0.9rem", fontWeight: 500 }}>{label}</div>
    </div>
  );
}

function FeatureCard({ icon, title, desc, delay = 0 }) {
  const [ref, inView] = useInView(0.1);
  const [hovered, setHovered] = useState(false);
  return (
    <div ref={ref} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} style={{
      background: "rgba(19, 27, 46, 0.8)",
      backdropFilter: "blur(12px)",
      border: `1px solid ${hovered ? "rgba(37,99,235,0.6)" : "rgba(255,255,255,0.06)"}`,
      borderRadius: "1rem",
      padding: "1.75rem",
      cursor: "default",
      transition: "all 0.3s ease",
      transform: inView ? `translateY(${hovered ? "-6px" : "0"})` : "translateY(32px)",
      opacity: inView ? 1 : 0,
      transitionDelay: `${delay}ms`,
      boxShadow: hovered ? "0 12px 40px rgba(37,99,235,0.18)" : "none",
    }}>
      <div style={{
        fontSize: "2rem", marginBottom: "1rem",
        background: "rgba(37,99,235,0.12)",
        width: 56, height: 56, borderRadius: "0.75rem",
        display: "flex", alignItems: "center", justifyContent: "center",
        border: "1px solid rgba(37,99,235,0.2)"
      }}>{icon}</div>
      <div style={{ fontSize: "1rem", fontWeight: 700, color: "#f1f5f9", marginBottom: "0.6rem" }}>{title}</div>
      <div style={{ fontSize: "0.83rem", color: "#64748b", lineHeight: 1.6 }}>{desc}</div>
    </div>
  );
}

function TechPill({ icon, name, desc }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} style={{
      background: "rgba(19, 27, 46, 0.7)",
      backdropFilter: "blur(12px)",
      border: `1px solid ${hovered ? "rgba(37,99,235,0.5)" : "rgba(255,255,255,0.06)"}`,
      borderRadius: "0.75rem",
      padding: "1.25rem",
      transition: "all 0.25s ease",
      boxShadow: hovered ? "0 0 20px rgba(37,99,235,0.15)" : "none",
    }}>
      <div style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>{icon}</div>
      <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#f1f5f9" }}>{name}</div>
      <div style={{ fontSize: "0.73rem", color: "#64748b", marginTop: "0.25rem" }}>{desc}</div>
    </div>
  );
}

export function LandingPage({ onEnterApp }) {
  const [scrolled, setScrolled] = useState(false);
  const [email, setEmail] = useState("");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const TICKER_DATA = [
    { sym: "VN-INDEX", val: "1.693,92", pct: "+0.79%", up: true },
    { sym: "VN30", val: "1.832,06", pct: "+0.42%", up: true },
    { sym: "HNX", val: "269.45", pct: "+0.04%", up: true },
    { sym: "UPCOM", val: "105.11", pct: "-0.89%", up: false },
    { sym: "CW-INDEX", val: "108.45", pct: "+1.24%", up: true },
    { sym: "USD/VND", val: "25.450", pct: "+0.06%", up: true },
    { sym: "VANG SJC", val: "88,50M", pct: "-0.56%", up: false },
  ];

  const FEATURES = [
    { icon: "📊", title: "Định giá Chứng quyền", desc: "SABR Volatility Surface + Black-Scholes nâng cao. Tính đủ 5 chỉ số Greeks (Delta, Gamma, Vega, Theta, Rho). Backtest Delta-Adaptive strategy toàn lịch sử.", delay: 0 },
    { icon: "🌊", title: "Phát hiện chế độ thị trường", desc: "HMM 4-state regime detection. GARCH volatility forecasting. XGBoost trend prediction. DRL portfolio optimization theo thị trường.", delay: 100 },
    { icon: "📰", title: "Tin tức & Tác động CW", desc: "AI phân tích sentiment Tiếng Việt. Cảnh báo Telegram real-time. Tương quan sự kiện tin tức => biến động giá CW underlying.", delay: 200 },
    { icon: "🛡️", title: "Rủi ro tín dụng cơ sở", desc: "Merton Model distance-to-default. HistGradientBoosting 8-step ETL. DebtRank systemic risk propagation toàn thị trường.", delay: 0 },
    { icon: "🤖", title: "AI Trading Committee", desc: "Gemini AI đồng thuận đa agent. Paper Trading mô phỏng HOSE. Stress test kịch bản, scenario analysis và phân tích sâu 7 lớp.", delay: 100 },
    { icon: "⚡", title: "Real-time Dashboard", desc: "WebSocket live quotes < 50ms. VNINDEX, VN30, UPCOM, HNX, CW-INDEX. Biểu đồ TradingView-style với chỉ báo kỹ thuật chuyên sâu.", delay: 200 },
  ];

  const TECH_PILLS = [
    { icon: "📐", name: "SABR Model", desc: "Volatility smile calibration" },
    { icon: "📈", name: "Black-Scholes", desc: "Options fair value engine" },
    { icon: "🔮", name: "Hidden Markov Model", desc: "Market regime detection" },
    { icon: "📉", name: "GARCH", desc: "Volatility forecasting" },
    { icon: "🌳", name: "XGBoost", desc: "Trend prediction ML" },
    { icon: "🏦", name: "Merton Model", desc: "Credit distance-to-default" },
    { icon: "🤖", name: "Gemini AI", desc: "Trading committee" },
    { icon: "⚡", name: "FastAPI WebSocket", desc: "< 50ms real-time data" },
  ];

  const MARKET_DATA = [
    { name: "VNINDEX", price: "1.693,92", pct: "+0.79%", up: true, data: [1640, 1650, 1655, 1648, 1660, 1672, 1680, 1678, 1685, 1694] },
    { name: "VN30", price: "1.832,06", pct: "+0.42%", up: true, data: [1800, 1808, 1812, 1810, 1818, 1820, 1825, 1822, 1828, 1832] },
    { name: "UPCOM", price: "105.11", pct: "-0.89%", up: false, data: [108, 107, 107.5, 106.8, 106, 105.8, 106.2, 105.5, 105.2, 105.1] },
    { name: "HNX", price: "269.45", pct: "+0.04%", up: true, data: [268, 268.5, 269, 268.8, 269.2, 269.1, 269.3, 269.2, 269.4, 269.45] },
    { name: "CW-INDEX", price: "108.45", pct: "+1.24%", up: true, data: [104, 105, 105.5, 106, 106.8, 107, 107.5, 107.8, 108, 108.45] },
  ];

  const tickerItems = [...TICKER_DATA, ...TICKER_DATA];

  const CSS = `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    @keyframes drift1 { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(60px,-40px) scale(1.08)} 66%{transform:translate(-40px,60px) scale(0.95)} }
    @keyframes drift2 { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(-50px,70px) scale(1.05)} 66%{transform:translate(70px,-30px) scale(0.98)} }
    @keyframes drift3 { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(40px,50px) scale(1.1)} 66%{transform:translate(-60px,-40px) scale(0.92)} }
    @keyframes ticker { from{transform:translateX(0)} to{transform:translateX(-50%)} }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.5} }
    @keyframes fadeUp { from{opacity:0;transform:translateY(24px)} to{opacity:1;transform:translateY(0)} }
    .lp-blob { position:absolute; border-radius:50%; filter:blur(80px); animation-timing-function:ease-in-out; animation-iteration-count:infinite; }
    .lp-ticker-wrap { overflow:hidden; white-space:nowrap; position:relative; }
    .lp-ticker-inner { display:inline-flex; animation:ticker 50s linear infinite; }
    .lp-dot-blink { animation:blink 2s ease-in-out infinite; }
    .lp-nav-link { color:#94a3b8; font-size:0.88rem; font-weight:500; transition:color 0.2s; cursor:pointer; background:none; border:none; font-family:inherit; padding:0; }
    .lp-nav-link:hover { color:#f1f5f9; }
    .lp-btn-primary { background:linear-gradient(135deg,#2563eb,#1d4ed8); color:#fff; border:none; border-radius:8px; padding:0.7rem 1.5rem; font-weight:700; font-size:0.9rem; cursor:pointer; transition:all 0.25s; font-family:inherit; box-shadow:0 4px 16px rgba(37,99,235,0.35); }
    .lp-btn-primary:hover { transform:translateY(-2px) scale(1.02); box-shadow:0 8px 28px rgba(37,99,235,0.5); }
    .lp-btn-outline { background:transparent; color:#f1f5f9; border:1px solid rgba(255,255,255,0.2); border-radius:8px; padding:0.7rem 1.5rem; font-weight:600; font-size:0.9rem; cursor:pointer; transition:all 0.25s; font-family:inherit; }
    .lp-btn-outline:hover { border-color:#2563eb; color:#60a5fa; background:rgba(37,99,235,0.08); }
    .lp-section-title { font-size:clamp(1.6rem,3vw,2rem); font-weight:800; color:#f1f5f9; text-align:center; margin-bottom:0.75rem; }
    .lp-section-sub { font-size:0.95rem; color:#64748b; text-align:center; max-width:540px; margin:0 auto 2.5rem; line-height:1.7; }
    .lp-grid-bg { background-image:linear-gradient(rgba(37,99,235,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(37,99,235,0.04) 1px,transparent 1px); background-size:40px 40px; }
    .lp-email-input { flex:1; background:rgba(30,41,59,0.7); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:0.7rem 1rem; color:#f1f5f9; font-size:0.9rem; font-family:inherit; outline:none; }
    .lp-email-input:focus { border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,0.2); }
  `;

  return (
    <div style={{ background: "#0b0f19", color: "#f1f5f9", fontFamily: "'Inter', sans-serif", overflowX: "hidden", minHeight: "100vh" }}>
      <style>{CSS}</style>

      {/* NAVBAR */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100, padding: "0 2rem",
        background: scrolled ? "rgba(11,15,25,0.92)" : "transparent",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid rgba(255,255,255,0.06)" : "none",
        transition: "all 0.3s ease",
        display: "flex", alignItems: "center", justifyContent: "space-between", height: 64,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <div style={{ width: 34, height: 34, borderRadius: "0.5rem", background: "linear-gradient(135deg,#ef4444,#2563eb)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: "1.1rem", color: "#fff" }}>F</div>
          <span style={{ fontFamily: "monospace", fontWeight: 800, fontSize: "1.15rem", letterSpacing: "1px" }}>
            <span style={{ color: "#2563eb" }}>FIN</span><span style={{ color: "#f1f5f9" }}>VISTA</span>
          </span>
        </div>
        <div style={{ display: "flex", gap: "2rem", alignItems: "center" }}>
          {["Tính năng", "Công nghệ", "Thị trường", "Liên hệ"].map(l => (
            <button key={l} className="lp-nav-link">{l}</button>
          ))}
        </div>
        <button className="lp-btn-primary" onClick={onEnterApp} style={{ padding: "0.5rem 1.2rem", fontSize: "0.85rem" }}>
          Dùng thử ngay
        </button>
      </nav>

      {/* HERO */}
      <section style={{ position: "relative", minHeight: "100vh", display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div className="lp-blob" style={{ width: 700, height: 700, background: "rgba(37,99,235,0.16)", top: -200, left: -200, animation: "drift1 24s ease-in-out infinite" }} />
        <div className="lp-blob" style={{ width: 500, height: 500, background: "rgba(139,92,246,0.11)", top: 100, right: -150, animation: "drift2 28s ease-in-out infinite" }} />
        <div className="lp-blob" style={{ width: 450, height: 450, background: "rgba(6,182,212,0.09)", bottom: 0, left: "35%", animation: "drift3 32s ease-in-out infinite" }} />
        <div className="lp-grid-bg" style={{ position: "absolute", inset: 0, opacity: 0.45 }} />

        {/* Ticker tape */}
        <div style={{ marginTop: 64, background: "rgba(19,27,46,0.65)", borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "0.45rem 0", position: "relative", zIndex: 1 }}>
          <div className="lp-ticker-wrap">
            <div className="lp-ticker-inner">
              {tickerItems.map((t, i) => (
                <span key={i} style={{ marginRight: "3rem", fontSize: "0.8rem", fontWeight: 600, color: t.up ? "#10b981" : "#ef4444", display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
                  <span style={{ color: "#64748b", fontWeight: 500 }}>{t.sym}</span>
                  {t.up ? "▲" : "▼"} {t.val}
                  <span style={{ opacity: 0.8 }}>({t.pct})</span>
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Hero body */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", position: "relative", zIndex: 1, maxWidth: 1280, margin: "0 auto", padding: "3rem 2rem", width: "100%", gap: "4rem", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 400px", animation: "fadeUp 0.8s ease forwards" }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", background: "rgba(37,99,235,0.12)", border: "1px solid rgba(37,99,235,0.35)", borderRadius: "2rem", padding: "0.35rem 1rem", fontSize: "0.78rem", fontWeight: 600, color: "#60a5fa", marginBottom: "1.5rem" }}>
              <span className="lp-dot-blink" style={{ width: 7, height: 7, borderRadius: "50%", background: "#10b981", display: "inline-block" }} />
              Nền tảng quant số 1 thị trường CW Việt Nam
            </div>
            <h1 style={{ fontSize: "clamp(2.2rem, 5vw, 3.75rem)", fontWeight: 800, lineHeight: 1.15, color: "#f1f5f9", marginBottom: "1.25rem" }}>
              Định Giá Chứng Quyền<br />
              <span style={{ background: "linear-gradient(135deg,#2563eb 30%,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
                Chính Xác. Nhanh Chóng. Thông Minh.
              </span>
            </h1>
            <p style={{ fontSize: "1rem", color: "#94a3b8", lineHeight: 1.8, marginBottom: "2rem", maxWidth: 510 }}>
              Nền tảng quant duy nhất tích hợp <strong style={{ color: "#f1f5f9" }}>SABR · Black-Scholes · HMM Regime · Gemini AI</strong> cho thị trường Chứng quyền có bảo đảm Việt Nam.
            </p>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <button className="lp-btn-primary" onClick={onEnterApp} style={{ fontSize: "1rem", padding: "0.85rem 2.2rem" }}>Bắt đầu ngay →</button>
              <button className="lp-btn-outline" onClick={onEnterApp} style={{ fontSize: "1rem", padding: "0.85rem 2.2rem" }}>Xem demo</button>
            </div>
          </div>

          {/* Mock dashboard card */}
          <div style={{ flex: "0 0 360px", maxWidth: "100%", animation: "fadeUp 1s 0.15s ease both" }}>
            <div style={{ background: "rgba(19,27,46,0.88)", backdropFilter: "blur(20px)", border: "1px solid rgba(37,99,235,0.28)", borderRadius: "1.25rem", padding: "1.5rem", boxShadow: "0 24px 80px rgba(37,99,235,0.22), inset 0 1px 0 rgba(255,255,255,0.05)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <div>
                  <span style={{ fontSize: "1.05rem", fontWeight: 800, color: "#f1f5f9" }}>HPGVPB2327</span>
                  <span style={{ fontSize: "0.7rem", color: "#64748b", marginLeft: "0.5rem" }}>SSI · VN30</span>
                </div>
                <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", background: "rgba(16,185,129,0.12)", color: "#10b981", border: "1px solid rgba(16,185,129,0.3)", borderRadius: "2rem", padding: "0.2rem 0.65rem", fontSize: "0.7rem", fontWeight: 700 }}>
                  <span className="lp-dot-blink" style={{ width: 5, height: 5, borderRadius: "50%", background: "#10b981", display: "inline-block" }} />
                  Live
                </span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.6rem", marginBottom: "1rem" }}>
                {[{ l: "Fair Value", v: "1.850đ", c: "#10b981" }, { l: "Market", v: "1.650đ", c: "#f1f5f9" }, { l: "Discount", v: "-10.8%", c: "#ef4444" }].map(({ l, v, c }) => (
                  <div key={l} style={{ background: "rgba(30,41,59,0.6)", borderRadius: "0.5rem", padding: "0.6rem 0.4rem", textAlign: "center" }}>
                    <div style={{ fontSize: "0.65rem", color: "#64748b", marginBottom: "0.2rem" }}>{l}</div>
                    <div style={{ fontSize: "0.95rem", fontWeight: 700, color: c }}>{v}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginBottom: "1rem", borderRadius: "0.5rem", overflow: "hidden" }}>
                <Sparkline data={[1620, 1635, 1640, 1630, 1648, 1655, 1642, 1658, 1665, 1650]} color="#2563eb" width={316} height={56} />
              </div>
              <div style={{ marginBottom: "0.75rem", fontSize: "0.68rem", color: "#475569", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>Greeks (5 chỉ số)</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.35rem" }}>
                {[
                  { l: "Δ Delta", v: "0.52", c: "#60a5fa" },
                  { l: "Γ Gamma", v: "0.001", c: "#8b5cf6" },
                  { l: "Θ Theta", v: "-4.3", c: "#ef4444" },
                  { l: "ν Vega", v: "10.9", c: "#f59e0b" },
                  { l: "ρ Rho", v: "1412", c: "#ec4899" },
                ].map(({ l, v, c }) => (
                  <div key={l} style={{ textAlign: "center", background: "rgba(30,41,59,0.45)", borderRadius: "0.4rem", padding: "0.4rem 0.15rem", border: `1px solid ${c}20` }}>
                    <div style={{ fontSize: "0.62rem", color: c, fontWeight: 700 }}>{l}</div>
                    <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "0.1rem" }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom stat strip */}
        <div style={{ position: "relative", zIndex: 1, padding: "1.25rem 2rem", borderTop: "1px solid rgba(255,255,255,0.05)", background: "rgba(11,15,25,0.65)", backdropFilter: "blur(8px)" }}>
          <div style={{ maxWidth: 1280, margin: "0 auto", display: "flex", justifyContent: "center", gap: "3rem", flexWrap: "wrap" }}>
            {[{ n: "389+ CW", l: "đang theo dõi" }, { n: "6 mô hình", l: "quant tích hợp" }, { n: "< 50ms", l: "real-time latency" }, { n: "100%", l: "dữ liệu thực HOSE" }].map(({ n, l }) => (
              <div key={n} style={{ textAlign: "center" }}>
                <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "#f1f5f9" }}>{n}</div>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section style={{ padding: "5rem 2rem", background: "#0b0f19" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <h2 className="lp-section-title">Toàn bộ toolkit của một quant trader</h2>
          <p className="lp-section-sub">Từ định giá quyền chọn đến quản trị rủi ro hệ thống — mọi công cụ bạn cần trong một nền tảng duy nhất.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.25rem" }}>
            {FEATURES.map((f) => <FeatureCard key={f.title} {...f} />)}
          </div>
        </div>
      </section>

      {/* LIVE MARKET */}
      <section style={{ padding: "4rem 2rem", background: "#131b2e" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <h2 className="lp-section-title">Dữ liệu thị trường thực</h2>
          <p className="lp-section-sub">Chỉ số chứng khoán Việt Nam cập nhật liên tục trong giờ giao dịch.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "1rem", marginBottom: "1.25rem" }}>
            {MARKET_DATA.map(({ name, price, pct, up, data }) => (
              <div key={name} style={{ background: "rgba(19,27,46,0.8)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "0.875rem", padding: "1.25rem", textAlign: "center" }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600, marginBottom: "0.35rem" }}>{name}</div>
                <div style={{ fontSize: "1.35rem", fontWeight: 800, color: "#f1f5f9", marginBottom: "0.25rem" }}>{price}</div>
                <div style={{ fontSize: "0.82rem", fontWeight: 700, color: up ? "#10b981" : "#ef4444", marginBottom: "0.7rem" }}>{up ? "▲" : "▼"} {pct}</div>
                <Sparkline data={data} color={up ? "#10b981" : "#ef4444"} width={140} height={32} />
              </div>
            ))}
          </div>
          <p style={{ textAlign: "center", fontSize: "0.72rem", color: "#374151" }}>Cập nhật mỗi 15 phút · Nguồn: VPS · Vietstock · HOSE</p>
        </div>
      </section>

      {/* TECH STACK */}
      <section className="lp-grid-bg" style={{ padding: "5rem 2rem", background: "#0b0f19" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <h2 className="lp-section-title">Được xây dựng trên nền tảng khoa học</h2>
          <p className="lp-section-sub">Hội tụ những mô hình định lượng hàng đầu và công nghệ AI tiên tiến nhất.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "1rem" }}>
            {TECH_PILLS.map(p => <TechPill key={p.name} {...p} />)}
          </div>
        </div>
      </section>

      {/* STATS */}
      <section style={{ padding: "5rem 2rem", background: "linear-gradient(180deg, #0d1627 0%, #0b0f19 100%)" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <h2 className="lp-section-title">Con số biết nói</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.5rem" }}>
            <StatCounter target={389} label="Chứng quyền đang phân tích" />
            <StatCounter target={6} label="Mô hình định lượng tích hợp" />
            <StatCounter target={1467} label="Doanh nghiệp niêm yết" />
            <StatCounter target={100} label="Dữ liệu thực từ thị trường" suffix="%" />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ background: "linear-gradient(135deg, #0f1e3c 0%, #1a1040 50%, #0b0f19 100%)", padding: "5rem 2rem" }}>
        <div style={{ maxWidth: 580, margin: "0 auto", textAlign: "center" }}>
          <h2 style={{ fontSize: "clamp(1.8rem,3.5vw,2.25rem)", fontWeight: 800, color: "#f1f5f9", marginBottom: "1rem", lineHeight: 1.2 }}>
            Bắt đầu phân tích thông minh hơn hôm nay
          </h2>
          <p style={{ color: "#64748b", fontSize: "1rem", marginBottom: "2rem", lineHeight: 1.7 }}>
            Miễn phí. Không cần thẻ tín dụng. Setup trong 5 phút.
          </p>
          <div style={{ display: "flex", gap: "0.75rem", maxWidth: 420, margin: "0 auto 1.5rem" }}>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="email@example.com" className="lp-email-input" />
            <button className="lp-btn-primary" onClick={onEnterApp}>Đăng ký</button>
          </div>
          <button onClick={onEnterApp} className="lp-btn-outline" style={{ fontSize: "0.9rem" }}>
            Vào thẳng ứng dụng →
          </button>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ background: "#0b0f19", borderTop: "1px solid rgba(255,255,255,0.05)", padding: "1.75rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.55rem" }}>
          <div style={{ width: 26, height: 26, borderRadius: "0.4rem", background: "linear-gradient(135deg,#ef4444,#2563eb)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: "0.85rem", color: "#fff" }}>F</div>
          <span style={{ fontFamily: "monospace", fontWeight: 800, fontSize: "0.88rem", color: "#475569" }}>FINVISTA</span>
        </div>
        <div style={{ display: "flex", gap: "1.5rem" }}>
          {["Tính năng", "Tài liệu", "Chính sách bảo mật", "Liên hệ"].map(l => (
            <span key={l} style={{ fontSize: "0.78rem", color: "#374151", cursor: "pointer" }}>{l}</span>
          ))}
        </div>
        <div style={{ fontSize: "0.75rem", color: "#1f2937" }}>
          © 2026 Finvista · Quantitative Edge, Smarter Decisions.
        </div>
      </footer>
    </div>
  );
}
