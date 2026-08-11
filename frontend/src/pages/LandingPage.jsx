import React, { useEffect, useRef, useState } from "react";

// Cumulative Standard Normal Distribution (approximation)
function cnd(x) {
  const a1 = 0.319381530;
  const a2 = -0.356563782;
  const a3 = 1.781477937;
  const a4 = -1.821255978;
  const a5 = 1.330274429;
  const L = Math.abs(x);
  const K = 1.0 / (1.0 + 0.2316419 * L);
  let w = 1.0 - 1.0 / Math.sqrt(2.0 * Math.PI) * Math.exp(-L * L / 2.0) * (a1 * K + a2 * K * K + a3 * Math.pow(K, 3) + a4 * Math.pow(K, 4) + a5 * Math.pow(K, 5));
  if (x < 0) {
    w = 1.0 - w;
  }
  return w;
}

// Probability Density Function
function ndf(x) {
  return (1.0 / Math.sqrt(2.0 * Math.PI)) * Math.exp(-x * x / 2.0);
}

function calculateBlackScholes(S, K, T_days, r_percent, sigma_percent, conversionRatio = 5) {
  const T = T_days / 365;
  const r = r_percent / 100;
  const sigma = sigma_percent / 100;

  if (T <= 0) return { price: 0, delta: 0, gamma: 0, vega: 0, theta: 0 };

  const d1 = (Math.log(S / K) + (r + (sigma * sigma) / 2.0) * T) / (sigma * Math.sqrt(T));
  const d2 = d1 - sigma * Math.sqrt(T);

  const nd1 = cnd(d1);
  const nd2 = cnd(d2);
  const npd1 = ndf(d1);

  // Call option price
  const optionPrice = S * nd1 - K * Math.exp(-r * T) * nd2;
  const delta = nd1;
  const gamma = npd1 / (S * sigma * Math.sqrt(T));
  const vega = S * Math.sqrt(T) * npd1;
  const theta = (- (S * npd1 * sigma) / (2 * Math.sqrt(T)) - r * K * Math.exp(-r * T) * nd2) / 365;

  // Adjusted for Conversion Ratio for Covered Warrants (CW)
  return {
    optionPrice: Math.max(0, optionPrice),
    cwPrice: Math.max(0, optionPrice / conversionRatio),
    delta: delta / conversionRatio,
    gamma: gamma / (conversionRatio * conversionRatio), // Gamma scales quadratically
    vega: vega / (conversionRatio * 100), // per 1% change in vol
    theta: theta / conversionRatio // per day decay
  };
}

function Sparkline({ data, color = "#2563eb", height = 40, width = 120 }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 6) - 3;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} fill="none" style={{ filter: "drop-shadow(0 2px 8px rgba(37,99,235,0.15))" }}>
      <polyline points={pts} stroke={color} strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={`${pts} ${width},${height} 0,${height}`} fill={`${color}12`} stroke="none" />
    </svg>
  );
}

function useCountUp(target, duration = 1500, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime = null;
    const step = (ts) => {
      if (!startTime) startTime = ts;
      const progress = Math.min((ts - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 4); // Quartic ease out
      setCount(Math.floor(ease * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [start, target, duration]);
  return count;
}

function useInView(threshold = 0.1) {
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
  const [ref, inView] = useInView(0.2);
  const count = useCountUp(target, 1500, inView);
  return (
    <div ref={ref} className="lp-stat-counter-card">
      <div className="lp-stat-number">
        {prefix}{count.toLocaleString()}{suffix}
      </div>
      <div className="lp-stat-label">{label}</div>
    </div>
  );
}

function FeatureCard({ icon, title, desc, delay = 0 }) {
  const [ref, inView] = useInView(0.05);
  const [hovered, setHovered] = useState(false);
  return (
    <div
      ref={ref}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`lp-feature-card ${inView ? "visible" : ""}`}
      style={{
        transitionDelay: `${delay}ms`,
        transform: inView ? `translateY(${hovered ? "-8px" : "0"})` : "translateY(40px)"
      }}
    >
      <div className="lp-feature-icon-container">{icon}</div>
      <h3 className="lp-feature-card-title">{title}</h3>
      <p className="lp-feature-card-desc">{desc}</p>
    </div>
  );
}

function TechPill({ icon, name, desc }) {
  return (
    <div className="lp-tech-pill-card">
      <div className="lp-tech-pill-header">
        <span className="lp-tech-pill-icon">{icon}</span>
        <span className="lp-tech-pill-name">{name}</span>
      </div>
      <p className="lp-tech-pill-desc">{desc}</p>
    </div>
  );
}

export function LandingPage({ onEnterApp }) {
  const [scrolled, setScrolled] = useState(false);
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);

  // Black-Scholes Simulator State
  const [spotPrice, setSpotPrice] = useState(52000);
  const [strikePrice, setStrikePrice] = useState(50000);
  const [volatility, setVolatility] = useState(45); // %
  const [daysToExpiry, setDaysToExpiry] = useState(60);
  const [conversionRatio, setConversionRatio] = useState(5);

  const bs = calculateBlackScholes(spotPrice, strikePrice, daysToExpiry, 5.0, volatility, conversionRatio);

  const [faqOpen, setFaqOpen] = useState({});
  const toggleFaq = (idx) => setFaqOpen(prev => ({ ...prev, [idx]: !prev[idx] }));

  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactMsg, setContactMsg] = useState("");
  const [contactSuccess, setContactSuccess] = useState(false);

  const handleContactSubmit = (e) => {
    e.preventDefault();
    setContactSuccess(true);
    setTimeout(() => {
      setContactSuccess(false);
      setContactName("");
      setContactEmail("");
      setContactMsg("");
    }, 3000);
  };

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleSubscribe = (e) => {
    e.preventDefault();
    if (email.trim().includes("@")) {
      setSubscribed(true);
      setTimeout(() => {
        setSubscribed(false);
        setEmail("");
      }, 3000);
    }
  };

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
    { icon: "📊", title: "Định giá Chứng quyền", desc: "SABR Volatility Smile Calibration & Black-Scholes nâng cao. Tính toán chính xác 5 chỉ số Greeks cơ bản (Delta, Gamma, Vega, Theta, Rho). Backtest chiến lược Delta-Adaptive toàn lịch sử.", delay: 0 },
    { icon: "🌊", title: "Phát hiện chế độ thị trường", desc: "Mô hình HMM (Hidden Markov Model) 4 trạng thái phát hiện chế độ thị trường. Giao thoa dự báo biến động qua GARCH và Machine Learning xu hướng XGBoost.", delay: 100 },
    { icon: "📰", title: "Tin tức & Phân tích Tác động", desc: "Hệ thống AI xử lý ngôn ngữ tự nhiên Tiếng Việt phân tích tâm lý tin tức tài chính. Cảnh báo biến động real-time tức thời qua Telegram và WebSockets.", delay: 200 },
    { icon: "🛡️", title: "Rủi ro tín dụng cơ sở", desc: "Đánh giá sức khỏe tài chính thông qua khoảng cách vỡ nợ Merton Model. Quy trình ETL 8 bước tự động và phân tích rủi ro hệ thống DebtRank.", delay: 0 },
    { icon: "🤖", title: "Hội đồng AI Trading", desc: "Đồng thuận đa tác nhân Gemini AI đưa ra các khuyến nghị giao dịch chuẩn xác. Paper trading mô phỏng sát sao luật khớp lệnh HOSE kèm stress-test kịch bản.", delay: 100 },
    { icon: "⚡", title: "Bảng dữ liệu Real-time", desc: "Cập nhật giá và chỉ số < 50ms qua WebSockets kết nối trực tiếp. Trải nghiệm đồ thị dạng TradingView-style mượt mà và trực quan nhất.", delay: 200 },
  ];

  const TECH_PILLS = [
    { icon: "📐", name: "SABR Model", desc: "Hiệu chuẩn nụ cười biến động (volatility smile calibration) cho cấu trúc kỳ hạn." },
    { icon: "📈", name: "Black-Scholes", desc: "Công cụ định giá quyền chọn và phân tích rủi ro Greeks chuẩn mực." },
    { icon: "🔮", name: "H Markov Model", desc: "Nhận diện chế độ thị trường (Bull/Bear/Sideways) tự động qua xác suất." },
    { icon: "📉", name: "GARCH Model", desc: "Dự báo độ biến động chuỗi thời gian của tài sản cơ sở." },
    { icon: "🌳", name: "XGBoost ML", desc: "Dự báo xu hướng giá và tối ưu hóa phân bổ tỷ trọng danh mục." },
    { icon: "🏦", name: "Merton Model", desc: "Đo lường khoảng cách vỡ nợ (Distance-to-Default) của tổ chức phát hành." },
    { icon: "🤖", name: "Gemini AI", desc: "Hệ thống AI đa tác nhân phân tích mẫu hình kỹ thuật và báo cáo tài chính." },
    { icon: "⚡", name: "WebSockets", desc: "Luồng dữ liệu realtime độ trễ thấp kết nối trực tiếp với backend FastAPI." },
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
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    /* Global Overrides */
    .lp-wrapper {
      background-color: #080c16;
      color: #f1f5f9;
      font-family: 'Outfit', sans-serif;
      overflow-x: hidden;
      min-height: 100vh;
      line-height: 1.5;
    }
    
    .lp-wrapper *, .lp-wrapper *::before, .lp-wrapper *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    
    /* Animations */
    @keyframes drift-orb-1 {
      0%, 100% { transform: translate(0, 0) scale(1); }
      33% { transform: translate(80px, -60px) scale(1.15); }
      66% { transform: translate(-50px, 80px) scale(0.9); }
    }
    @keyframes drift-orb-2 {
      0%, 100% { transform: translate(0, 0) scale(1.1); }
      33% { transform: translate(-90px, 90px) scale(0.95); }
      66% { transform: translate(60px, -40px) scale(1.05); }
    }
    @keyframes ticker-scroll {
      from { transform: translateX(0); }
      to { transform: translateX(-50%); }
    }
    .lp-ticker-wrap {
      overflow: hidden;
      white-space: nowrap;
      position: relative;
    }
    .lp-ticker-inner {
      display: inline-flex;
      animation: ticker-scroll 50s linear infinite;
    }
    @keyframes pulse-soft {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.6; transform: scale(0.96); }
    }
    @keyframes fade-in-up {
      from { opacity: 0; transform: translateY(30px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Grid Overlay */
    .lp-grid-overlay {
      position: absolute;
      inset: 0;
      background-image: linear-gradient(rgba(37,99,235,0.035) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(37,99,235,0.035) 1px, transparent 1px);
      background-size: 50px 50px;
      mask-image: radial-gradient(ellipse 60% 50% at 50% 50%, #000 70%, transparent 100%);
      -webkit-mask-image: radial-gradient(ellipse 60% 50% at 50% 50%, #000 70%, transparent 100%);
      pointer-events: none;
    }

    /* Glowing Orbs */
    .lp-glow-orb {
      position: absolute;
      border-radius: 50%;
      filter: blur(120px);
      opacity: 0.25;
      pointer-events: none;
      z-index: 0;
    }

    /* Buttons */
    .lp-btn-glow {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #ffffff;
      border: none;
      border-radius: 12px;
      padding: 0.85rem 2rem;
      font-weight: 700;
      font-size: 0.95rem;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4);
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
    }
    .lp-btn-glow:hover {
      transform: translateY(-3px);
      box-shadow: 0 12px 30px rgba(37, 99, 235, 0.6);
      background: linear-gradient(135deg, #3b82f6, #2563eb);
    }
    .lp-btn-glow:active {
      transform: translateY(-1px);
    }

    .lp-btn-border-glow {
      background: rgba(13, 22, 43, 0.6);
      color: #f1f5f9;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 0.85rem 2rem;
      font-weight: 600;
      font-size: 0.95rem;
      cursor: pointer;
      transition: all 0.3s;
      backdrop-filter: blur(8px);
    }
    .lp-btn-border-glow:hover {
      border-color: #2563eb;
      color: #60a5fa;
      background: rgba(37, 99, 235, 0.08);
      box-shadow: 0 0 15px rgba(37, 99, 235, 0.15);
    }

    /* Nav Link */
    .lp-nav-link-btn {
      color: #94a3b8;
      font-size: 0.92rem;
      font-weight: 500;
      transition: color 0.25s;
      cursor: pointer;
      background: none;
      border: none;
      font-family: inherit;
    }
    .lp-nav-link-btn:hover {
      color: #f1f5f9;
    }

    /* Option Simulator Dashboard */
    .lp-sim-dashboard {
      background: rgba(19, 27, 46, 0.75);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid rgba(37, 99, 235, 0.25);
      border-radius: 20px;
      padding: 1.75rem;
      box-shadow: 0 30px 70px rgba(8, 12, 22, 0.8),
                  inset 0 1px 0 rgba(255, 255, 255, 0.08);
      position: relative;
      overflow: hidden;
      z-index: 2;
    }
    .lp-sim-dashboard::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.6), transparent);
    }

    .lp-sim-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
    }

    .lp-sim-price-main {
      font-family: 'JetBrains Mono', monospace;
      font-size: 2.2rem;
      font-weight: 800;
      color: #10b981;
      text-shadow: 0 0 20px rgba(16, 185, 129, 0.25);
      line-height: 1.1;
    }

    .lp-sim-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      background: rgba(16, 185, 129, 0.12);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 99px;
      padding: 0.25rem 0.75rem;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .lp-sim-badge.otm {
      background: rgba(239, 68, 68, 0.12);
      color: #ef4444;
      border-color: rgba(239, 68, 68, 0.25);
    }
    
    .lp-sim-badge.atm {
      background: rgba(245, 158, 11, 0.12);
      color: #f59e0b;
      border-color: rgba(245, 158, 11, 0.25);
    }

    .lp-sim-sliders {
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      margin-bottom: 1.5rem;
      background: rgba(8, 12, 22, 0.4);
      padding: 1rem;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.03);
    }

    .lp-slider-group {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }

    .lp-slider-label-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.78rem;
      color: #94a3b8;
    }

    .lp-slider-val {
      font-family: 'JetBrains Mono', monospace;
      color: #f1f5f9;
      font-weight: 700;
    }

    .lp-slider-input {
      -webkit-appearance: none;
      appearance: none;
      width: 100%;
      height: 5px;
      border-radius: 99px;
      background: #1e293b;
      outline: none;
      cursor: pointer;
    }
    .lp-slider-input::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 15px;
      height: 15px;
      border-radius: 50%;
      background: #2563eb;
      border: 2px solid #ffffff;
      box-shadow: 0 0 10px rgba(37, 99, 235, 0.5);
      transition: transform 0.1s;
    }
    .lp-slider-input::-webkit-slider-thumb:hover {
      transform: scale(1.2);
    }

    .lp-greek-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.5rem;
    }

    .lp-greek-card {
      background: rgba(30, 41, 59, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 10px;
      padding: 0.6rem 0.25rem;
      text-align: center;
      transition: all 0.25s;
    }
    .lp-greek-card:hover {
      background: rgba(30, 41, 59, 0.7);
      border-color: rgba(37, 99, 235, 0.2);
    }

    .lp-greek-name {
      font-size: 0.65rem;
      font-weight: 700;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.2px;
      margin-bottom: 0.2rem;
    }
    
    .lp-greek-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.88rem;
      font-weight: 700;
      color: #f1f5f9;
    }

    /* Stats Grid */
    .lp-stat-counter-card {
      background: rgba(19, 27, 46, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 16px;
      padding: 2.2rem 1.5rem;
      text-align: center;
      backdrop-filter: blur(8px);
      transition: all 0.3s;
    }
    .lp-stat-counter-card:hover {
      border-color: rgba(37, 99, 235, 0.2);
      transform: translateY(-4px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    .lp-stat-number {
      font-size: 3.2rem;
      font-weight: 800;
      background: linear-gradient(135deg, #60a5fa, #06b6d4);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      line-height: 1.1;
      margin-bottom: 0.6rem;
    }
    .lp-stat-label {
      color: #94a3b8;
      font-size: 0.95rem;
      font-weight: 500;
    }

    /* Feature Card Grid */
    .lp-feature-card {
      background: rgba(19, 27, 46, 0.55);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 18px;
      padding: 2rem;
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
      opacity: 0;
    }
    .lp-feature-card.visible {
      opacity: 1;
    }
    .lp-feature-card:hover {
      border-color: rgba(37, 99, 235, 0.35);
      box-shadow: 0 16px 40px rgba(8, 12, 22, 0.6), 
                  0 0 25px rgba(37, 99, 235, 0.12);
    }
    .lp-feature-icon-container {
      font-size: 2rem;
      background: rgba(37, 99, 235, 0.08);
      width: 60px;
      height: 60px;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(37, 99, 235, 0.18);
      margin-bottom: 1.25rem;
      transition: transform 0.3s;
    }
    .lp-feature-card:hover .lp-feature-icon-container {
      transform: scale(1.08) rotate(5deg);
      background: rgba(37, 99, 235, 0.15);
      border-color: rgba(37, 99, 235, 0.4);
    }
    .lp-feature-card-title {
      font-size: 1.15rem;
      fontWeight: 700;
      color: #f8fafc;
      margin-bottom: 0.75rem;
    }
    .lp-feature-card-desc {
      font-size: 0.88rem;
      color: #94a3b8;
      line-height: 1.65;
    }

    /* Tech Pills Grid */
    .lp-tech-pill-card {
      background: rgba(19, 27, 46, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.04);
      border-radius: 14px;
      padding: 1.5rem;
      transition: all 0.3s;
    }
    .lp-tech-pill-card:hover {
      border-color: rgba(37, 99, 235, 0.25);
      background: rgba(19, 27, 46, 0.6);
      transform: translateY(-2px);
    }
    .lp-tech-pill-header {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      margin-bottom: 0.6rem;
    }
    .lp-tech-pill-icon {
      font-size: 1.5rem;
    }
    .lp-tech-pill-name {
      font-size: 0.95rem;
      font-weight: 700;
      color: #f1f5f9;
    }
    .lp-tech-pill-desc {
      font-size: 0.78rem;
      color: #64748b;
      line-height: 1.5;
    }

    /* Index Card */
    .lp-index-card {
      background: rgba(19, 27, 46, 0.65);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 16px;
      padding: 1.5rem 1.25rem;
      text-align: center;
      transition: all 0.3s;
    }
    .lp-index-card:hover {
      border-color: rgba(255, 255, 255, 0.12);
      transform: scale(1.03);
    }
    .lp-index-name {
      font-size: 0.8rem;
      color: #64748b;
      font-weight: 600;
      margin-bottom: 0.4rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .lp-index-price {
      font-family: 'JetBrains Mono', monospace;
      font-size: 1.6rem;
      font-weight: 800;
      color: #f8fafc;
      margin-bottom: 0.25rem;
    }
    .lp-index-change {
      font-size: 0.88rem;
      font-weight: 700;
      margin-bottom: 0.85rem;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.2rem;
    }

    /* Subscription Inputs */
    .lp-sub-form {
      display: flex;
      gap: 0.75rem;
      max-width: 450px;
      margin: 0 auto 1.5rem;
    }
    .lp-sub-input {
      flex: 1;
      background: rgba(8, 12, 22, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 0.85rem 1.25rem;
      color: #f1f5f9;
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
      transition: all 0.3s;
    }
    .lp-sub-input:focus {
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
    }
    .lp-success-msg {
      color: #10b981;
      font-size: 0.9rem;
      font-weight: 600;
      margin-top: 0.5rem;
      animation: pulse-soft 2s infinite;
    }

    /* Headings */
    .lp-title-section {
      font-size: clamp(2rem, 4vw, 2.5rem);
      font-weight: 800;
      color: #f8fafc;
      text-align: center;
      margin-bottom: 0.75rem;
      letter-spacing: -0.5px;
    }
    .lp-subtitle-section {
      font-size: 1rem;
      color: #64748b;
      text-align: center;
      max-width: 600px;
      margin: 0 auto 3rem;
      line-height: 1.7;
    }
  `;

  // Determine Moneyness for Simulator Badge
  const moneynessRatio = spotPrice / strikePrice;
  let moneynessLabel = "ATM (Ngang giá)";
  let moneynessClass = "atm";
  if (moneynessRatio > 1.02) {
    moneynessLabel = `ITM (Trong vị thế +${Math.round((moneynessRatio - 1) * 100)}%)`;
    moneynessClass = "itm";
  } else if (moneynessRatio < 0.98) {
    moneynessLabel = `OTM (Ngoài vị thế -${Math.round((1 - moneynessRatio) * 100)}%)`;
    moneynessClass = "otm";
  }

  return (
    <div className="lp-wrapper">
      <style>{CSS}</style>

      {/* NAVBAR */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100, padding: "0 2rem",
        background: scrolled ? "rgba(8,12,22,0.9)" : "transparent",
        backdropFilter: scrolled ? "blur(20px)" : "none",
        borderBottom: scrolled ? "1px solid rgba(255,255,255,0.06)" : "none",
        transition: "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        display: "flex", alignItems: "center", justifyContent: "space-between", height: 68,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div style={{ width: 36, height: 36, borderRadius: "0.6rem", background: "linear-gradient(135deg,#ef4444,#2563eb)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: "1.2rem", color: "#fff" }}>F</div>
          <span style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 900, fontSize: "1.3rem", letterSpacing: "0.5px" }}>
            <span style={{ color: "#2563eb" }}>FIN</span><span style={{ color: "#f1f5f9" }}>VISTA</span>
          </span>
        </div>
        <div style={{ display: "flex", gap: "2.5rem", alignItems: "center" }}>
          {["Tính năng", "Công nghệ", "Thị trường", "Liên hệ"].map(l => (
            <button key={l} className="lp-nav-link-btn">{l}</button>
          ))}
        </div>
        <button className="lp-btn-glow" onClick={onEnterApp} style={{ padding: "0.5rem 1.25rem", fontSize: "0.85rem", borderRadius: "10px" }}>
          Dùng thử ngay
        </button>
      </nav>

      {/* HERO SECTION */}
      <section style={{ position: "relative", minHeight: "100vh", display: "flex", flexDirection: "column", overflow: "hidden", justifyContent: "center" }}>
        {/* Glow Blobs */}
        <div className="lp-glow-orb" style={{ width: 650, height: 650, background: "#2563eb", top: -200, left: -200, animation: "drift-orb-1 20s ease-in-out infinite" }} />
        <div className="lp-glow-orb" style={{ width: 500, height: 500, background: "#06b6d4", bottom: -100, right: -100, animation: "drift-orb-2 25s ease-in-out infinite" }} />
        <div className="lp-grid-overlay" />

        {/* Ticker tape */}
        <div style={{ marginTop: 68, background: "rgba(13,22,43,0.5)", borderBottom: "1px solid rgba(255,255,255,0.04)", padding: "0.6rem 0", position: "relative", zIndex: 1, backdropFilter: "blur(10px)" }}>
          <div className="lp-ticker-wrap">
            <div className="lp-ticker-inner">
              {tickerItems.map((t, i) => (
                <span key={i} style={{ marginRight: "3.5rem", fontSize: "0.82rem", fontWeight: 600, color: t.up ? "#10b981" : "#ef4444", display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
                  <span style={{ color: "#94a3b8", fontWeight: 500 }}>{t.sym}</span>
                  {t.up ? "▲" : "▼"} {t.val}
                  <span style={{ opacity: 0.85, fontFamily: "'JetBrains Mono', monospace" }}>({t.pct})</span>
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Hero body */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", position: "relative", zIndex: 1, maxWidth: 1280, margin: "0 auto", padding: "4rem 2rem", width: "100%", gap: "5rem", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 450px", animation: "fade-in-up 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards" }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", background: "rgba(37,99,235,0.1)", border: "1px solid rgba(37,99,235,0.25)", borderRadius: "99px", padding: "0.4rem 1.1rem", fontSize: "0.8rem", fontWeight: 600, color: "#60a5fa", marginBottom: "1.75rem" }}>
              <span className="lp-dot-blink" style={{ width: 7, height: 7, borderRadius: "50%", background: "#10b981", display: "inline-block", animation: "pulse-soft 2s infinite" }} />
              Nền tảng định lượng số 1 thị trường Chứng quyền Việt Nam
            </div>
            <h1 style={{ fontSize: "clamp(2.4rem, 5.5vw, 4rem)", fontWeight: 900, lineHeight: 1.1, color: "#f8fafc", marginBottom: "1.5rem", letterSpacing: "-1px" }}>
              Định Giá Chứng Quyền<br />
              <span style={{ background: "linear-gradient(135deg,#2563eb 20%,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
                Chuẩn Xác. Thông Minh.
              </span>
            </h1>
            <p style={{ fontSize: "1.08rem", color: "#94a3b8", lineHeight: 1.8, marginBottom: "2.5rem", maxWidth: 540 }}>
              Sử dụng các mô hình định lượng hiện đại <strong style={{ color: "#f1f5f9" }}>SABR · Black-Scholes · HMM Regime · Gemini AI</strong> để tối ưu hóa quyết định đầu tư chứng quyền có bảo đảm.
            </p>
            <div style={{ display: "flex", gap: "1.25rem", flexWrap: "wrap" }}>
              <button className="lp-btn-glow" onClick={onEnterApp}>Vào ứng dụng ngay →</button>
              <button className="lp-btn-border-glow" onClick={onEnterApp}>Xem Demo</button>
            </div>
          </div>

          {/* Interactive Calculator Dashboard */}
          <div style={{ flex: "1 1 400px", maxWidth: "100%", animation: "fade-in-up 1s cubic-bezier(0.16, 1, 0.3, 1) 0.15s both" }}>
            <div className="lp-sim-dashboard">
              <div className="lp-sim-header">
                <div>
                  <span style={{ fontSize: "1.15rem", fontWeight: 800, color: "#f8fafc" }}>HPG/5M/SSI (Mô phỏng)</span>
                  <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.15rem" }}>Underlying Strike: 50.000đ · Ratio 5:1</div>
                </div>
                <span className={`lp-sim-badge ${moneynessClass}`}>{moneynessLabel}</span>
              </div>

              {/* Price Display */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
                <div style={{ background: "rgba(8, 12, 22, 0.4)", padding: "0.75rem 1rem", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.03)" }}>
                  <div style={{ fontSize: "0.7rem", color: "#64748b", textTransform: "uppercase", fontWeight: 600 }}>Fair Value Call (1:1)</div>
                  <div className="lp-sim-price-main" style={{ color: "#3b82f6" }}>{Math.round(bs.optionPrice).toLocaleString()}đ</div>
                </div>
                <div style={{ background: "rgba(8, 12, 22, 0.4)", padding: "0.75rem 1rem", borderRadius: "12px", border: "1px solid rgba(255, 255, 255, 0.03)" }}>
                  <div style={{ fontSize: "0.7rem", color: "#64748b", textTransform: "uppercase", fontWeight: 600 }}>CW Fair Value (5:1)</div>
                  <div className="lp-sim-price-main">{Math.round(bs.cwPrice).toLocaleString()}đ</div>
                </div>
              </div>

              {/* Interactive Sliders */}
              <div className="lp-sim-sliders">
                {/* Spot Price Slider */}
                <div className="lp-slider-group">
                  <div className="lp-slider-label-row">
                    <span>Giá tài sản cơ sở (HPG)</span>
                    <span className="lp-slider-val">{spotPrice.toLocaleString()}đ</span>
                  </div>
                  <input
                    type="range"
                    min="35000"
                    max="65000"
                    step="500"
                    value={spotPrice}
                    onChange={(e) => setSpotPrice(Number(e.target.value))}
                    className="lp-slider-input"
                  />
                </div>

                {/* Volatility Slider */}
                <div className="lp-slider-group">
                  <div className="lp-slider-label-row">
                    <span>Độ biến động kỳ vọng (Volatility)</span>
                    <span className="lp-slider-val">{volatility}%</span>
                  </div>
                  <input
                    type="range"
                    min="15"
                    max="100"
                    step="1"
                    value={volatility}
                    onChange={(e) => setVolatility(Number(e.target.value))}
                    className="lp-slider-input"
                  />
                </div>

                {/* Days to Expiry Slider */}
                <div className="lp-slider-group">
                  <div className="lp-slider-label-row">
                    <span>Thời hạn còn lại (Expiry)</span>
                    <span className="lp-slider-val">{daysToExpiry} ngày</span>
                  </div>
                  <input
                    type="range"
                    min="2"
                    max="180"
                    step="1"
                    value={daysToExpiry}
                    onChange={(e) => setDaysToExpiry(Number(e.target.value))}
                    className="lp-slider-input"
                  />
                </div>
              </div>

              {/* Calculated Greeks Grid */}
              <div style={{ marginBottom: "0.6rem", fontSize: "0.72rem", color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>Các chỉ số nhạy cảm (Greeks)</div>
              <div className="lp-greek-grid">
                {[
                  { name: "Δ Delta", val: bs.delta.toFixed(4), desc: "Tốc độ thay đổi giá CW" },
                  { name: "Γ Gamma", val: bs.gamma.toFixed(5), desc: "Gia tốc của Delta" },
                  { name: "Θ Theta", val: `${bs.theta.toFixed(1)}đ`, desc: "Hao mòn thời gian/ngày" },
                  { name: "ν Vega", val: `${bs.vega.toFixed(1)}đ`, desc: "Nhạy cảm biến động +1%" }
                ].map(g => (
                  <div key={g.name} className="lp-greek-card" title={g.desc}>
                    <div className="lp-greek-name">{g.name}</div>
                    <div className="lp-greek-val">{g.val}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom stats strip */}
        <div style={{ position: "relative", zIndex: 1, padding: "1.5rem 2rem", borderTop: "1px solid rgba(255,255,255,0.05)", background: "rgba(8,12,22,0.7)", backdropFilter: "blur(12px)" }}>
          <div style={{ maxWidth: 1280, margin: "0 auto", display: "flex", justifyContent: "space-between", gap: "2rem", flexWrap: "wrap" }}>
            {[{ n: "389+ CW", l: "theo dõi liên tục" }, { n: "6 mô hình", l: "định lượng cao cấp" }, { n: "< 50ms", l: "độ trễ dữ liệu" }, { n: "100%", l: "đồng bộ sàn HOSE" }].map(({ n, l }) => (
              <div key={n} style={{ flex: "1 1 180px", textAlign: "center" }}>
                <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "#f8fafc" }}>{n}</div>
                <div style={{ fontSize: "0.78rem", color: "#64748b", marginTop: "0.15rem" }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* INSTITUTIONAL MONEY FLOW SHOWCASE */}
      <section style={{ padding: "7rem 2rem", background: "rgba(19, 27, 46, 0.2)", borderTop: "1px solid rgba(255,255,255,0.03)", position: "relative", zIndex: 1 }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "3.5rem", alignItems: "center" }}>
          <div>
            <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "#3b82f6", letterSpacing: "1.5px", textTransform: "uppercase", background: "rgba(59,130,246,0.1)", padding: "0.3rem 0.75rem", borderRadius: "2rem" }}>
              Dấu chân dòng tiền lớn
            </span>
            <h2 style={{ fontSize: "clamp(2rem, 4vw, 2.6rem)", fontWeight: 900, color: "#ffffff", marginTop: "1.25rem", lineHeight: 1.15, fontFamily: "'Outfit', sans-serif" }}>
              Ai đang gom, ai đang xả — theo từng nhóm nhà đầu tư
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "1rem", marginTop: "1rem", lineHeight: 1.75 }}>
              Mỗi giao dịch của tổ chức lớn đều để lại dấu vết. Finvista bóc tách giá trị mua & bán ròng của khối ngoại, tự doanh, tổ chức và cá nhân trong nước theo thời gian thực — để bạn nhận ra đâu là dòng tiền đang thật sự dẫn dắt thị trường, ngay trong một màn hình.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "2rem", fontSize: "0.85rem", color: "#e2e8f0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ color: "#10b981", fontWeight: "700" }}>✓</span> Đầy đủ 6 nhóm nhà đầu tư
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ color: "#10b981", fontWeight: "700" }}>✓</span> Biểu đồ nhiệt VN100 trực quan
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ color: "#10b981", fontWeight: "700" }}>✓</span> Lịch sử dòng tiền chi tiết
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ color: "#10b981", fontWeight: "700" }}>✓</span> Dữ liệu cập nhật từng phiên
              </div>
            </div>

            <button onClick={onEnterApp} className="lp-btn-glow" style={{ marginTop: "2.5rem", padding: "0.85rem 2rem" }}>
              Xem dòng tiền ngay
            </button>
          </div>

          {/* Mini Interactive Heatmap Preview */}
          <div style={{ background: "#0b0f19", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "0.75rem", padding: "1.5rem", boxShadow: "0 20px 40px rgba(0,0,0,0.4)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#f8fafc" }}>Biểu đồ nhiệt · VN100</span>
              <span style={{ fontSize: "0.75rem", color: "#10b981", background: "rgba(16,185,129,0.1)", padding: "0.15rem 0.4rem", borderRadius: "0.25rem" }}>Khối Ngoại</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "6px", height: "240px", fontSize: "0.85rem", color: "#ffffff", fontWeight: "800" }}>
              <div style={{ background: "rgba(16, 185, 129, 0.8)", borderRadius: "6px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
                <span>FPT</span>
                <span style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.9)", fontWeight: "500" }}>+865 tỷ</span>
              </div>
              <div style={{ display: "grid", gridTemplateRows: "1fr 1fr", gap: "6px" }}>
                <div style={{ background: "rgba(16, 185, 129, 0.65)", borderRadius: "6px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
                  <span>VIC</span>
                  <span style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.9)", fontWeight: "500" }}>+727 tỷ</span>
                </div>
                <div style={{ background: "rgba(239, 68, 68, 0.7)", borderRadius: "6px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
                  <span>TCB</span>
                  <span style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.9)", fontWeight: "500" }}>-769 tỷ</span>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateRows: "1.2fr 0.8fr", gap: "6px" }}>
                <div style={{ background: "rgba(239, 68, 68, 0.85)", borderRadius: "6px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
                  <span>VPB</span>
                  <span style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.9)", fontWeight: "500" }}>-746 tỷ</span>
                </div>
                <div style={{ background: "rgba(16, 185, 129, 0.5)", borderRadius: "6px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" }}>
                  <span>HPG</span>
                  <span style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.9)", fontWeight: "500" }}>+440 tỷ</span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "center", gap: "1rem", marginTop: "1rem", fontSize: "0.7rem", color: "#64748b" }}>
              <span>● Xanh - Mua ròng</span>
              <span>● Đỏ - Bán ròng</span>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section style={{ padding: "7rem 2rem", position: "relative", zIndex: 1 }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <h2 className="lp-title-section">Toàn bộ công cụ của một Quant Trader</h2>
          <p className="lp-subtitle-section">Từ định giá quyền chọn nâng cao đến quản trị rủi ro toàn hệ thống — mọi thứ tích hợp trong một nền tảng duy nhất.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
            {FEATURES.map((f) => <FeatureCard key={f.title} {...f} />)}
          </div>
        </div>
      </section>

      {/* LIVE MARKET SECTION */}
      <section style={{ padding: "6rem 2rem", background: "rgba(19, 27, 46, 0.4)", position: "relative", zIndex: 1, borderTop: "1px solid rgba(255,255,255,0.03)", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <h2 className="lp-title-section">Dữ liệu thị trường trực tiếp</h2>
          <p className="lp-subtitle-section">Các chỉ số chứng khoán chính của thị trường Việt Nam cập nhật tức thì trong phiên giao dịch.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "1.25rem", marginBottom: "2rem" }}>
            {MARKET_DATA.map(({ name, price, pct, up, data }) => (
              <div key={name} className="lp-index-card">
                <div className="lp-index-name">{name}</div>
                <div className="lp-index-price">{price}</div>
                <div className="lp-index-change" style={{ color: up ? "#10b981" : "#ef4444" }}>
                  <span>{up ? "▲" : "▼"}</span>
                  <span>{pct}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "center", marginTop: "0.5rem" }}>
                  <Sparkline data={data} color={up ? "#10b981" : "#ef4444"} width={160} height={40} />
                </div>
              </div>
            ))}
          </div>
          <p style={{ textAlign: "center", fontSize: "0.75rem", color: "#475569" }}>Cập nhật tự động · Nguồn dữ liệu: HOSE · Vietstock · VPS</p>
        </div>
      </section>

      {/* TECH STACK SECTION */}
      <section style={{ padding: "7rem 2rem", position: "relative", zIndex: 1 }}>
        <div className="lp-grid-overlay" style={{ opacity: 0.3 }} />
        <div style={{ maxWidth: 1280, margin: "0 auto", position: "relative", zIndex: 1 }}>
          <h2 className="lp-title-section">Được xây dựng trên nền tảng toán tin vững chắc</h2>
          <p className="lp-subtitle-section">Kết hợp hài hòa giữa các thuật toán định lượng cổ điển và công nghệ trí tuệ nhân tạo đột phá.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1.25rem" }}>
            {TECH_PILLS.map(p => <TechPill key={p.name} {...p} />)}
          </div>
        </div>
      </section>

      {/* STATS SECTION */}
      <section style={{ padding: "6rem 2rem", position: "relative", zIndex: 1 }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <h2 className="lp-title-section">Những con số nổi bật</h2>
          <p className="lp-subtitle-section" style={{ marginBottom: "4rem" }}>Khối lượng dữ liệu xử lý khổng lồ phục vụ công việc phân tích định lượng chuyên sâu.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1.5rem" }}>
            <StatCounter target={389} label="Chứng quyền đang theo dõi" />
            <StatCounter target={6} label="Mô hình định lượng cốt lõi" />
            <StatCounter target={1467} label="Doanh nghiệp niêm yết cơ sở" />
            <StatCounter target={100} label="Độ khớp dữ liệu HOSE" suffix="%" />
          </div>
        </div>
      </section>

      {/* FAQ SECTION */}
      <section style={{ padding: "7rem 2rem", position: "relative", zIndex: 1 }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <h2 className="lp-title-section" style={{ textAlign: "center" }}>Chưa rõ điều gì?</h2>
          <p className="lp-subtitle-section" style={{ textAlign: "center", marginBottom: "4rem" }}>Câu trả lời cho những băn khoăn phổ biến nhất về dữ liệu và tính năng định lượng.</p>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {[
              {
                q: '"Dấu chân dòng tiền lớn" nghĩa là gì?',
                a: "Là toàn bộ giá trị mua/bán ròng mà các nhóm nhà đầu tư lớn (như khối ngoại, tự doanh, tổ chức trong nước) để lại trên từng cổ phiếu. Finvista bóc tách tự động dữ liệu khớp lệnh và thỏa thuận để bạn thấy rõ tiền lớn đang tích lũy (gom) hay phân phối (xả)."
              },
              {
                q: "Biểu đồ nhiệt (heatmap) dòng tiền hoạt động thế nào?",
                a: "Biểu đồ nhiệt hiển thị toàn bộ 100 cổ phiếu lớn nhất rổ VN100 dưới dạng các ô hình chữ nhật. Màu sắc (Xanh: mua ròng, Đỏ: bán ròng) và diện tích ô tương ứng với độ lớn của dòng tiền ròng trong kỳ báo cáo để bạn nhận ra ngay tiêu điểm thị trường."
              },
              {
                q: "Finvista có hỗ trợ cập nhật dữ liệu tự động không?",
                a: "Có, hệ thống tự động đồng bộ dữ liệu giao dịch trong ngày và dữ liệu cuối ngày trực tiếp từ sàn HOSE và các nguồn uy tín qua hệ thống API Gateway để phân tích Greeks và Dòng tiền thời gian thực."
              }
            ].map((faq, idx) => {
              const isOpen = !!faqOpen[idx];
              return (
                <div key={idx} style={{ background: "rgba(19, 27, 46, 0.4)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "0.5rem", overflow: "hidden" }}>
                  <button
                    onClick={() => toggleFaq(idx)}
                    style={{
                      width: "100%",
                      padding: "1.25rem 1.5rem",
                      background: "none",
                      border: "none",
                      textAlign: "left",
                      color: "#f8fafc",
                      fontSize: "1rem",
                      fontWeight: "700",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      cursor: "pointer"
                    }}
                  >
                    <span>{faq.q}</span>
                    <span style={{ fontSize: "1.25rem", color: "#3b82f6" }}>{isOpen ? "−" : "+"}</span>
                  </button>
                  {isOpen && (
                    <div style={{ padding: "0 1.5rem 1.25rem", color: "#94a3b8", fontSize: "0.88rem", lineHeight: 1.6, borderTop: "1px solid rgba(255,255,255,0.03)", paddingTop: "1rem" }}>
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CONTACT SECTION */}
      <section style={{ padding: "7rem 2rem", background: "rgba(19, 27, 46, 0.2)", borderTop: "1px solid rgba(255,255,255,0.03)", position: "relative", zIndex: 1 }}>
        <div style={{ maxWidth: 1000, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: "4rem", alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: "2rem", fontWeight: 900, color: "#ffffff", fontFamily: "'Outfit', sans-serif" }}>Liên hệ với chúng tôi</h2>
            <p style={{ color: "#94a3b8", fontSize: "0.95rem", marginTop: "0.75rem", lineHeight: 1.6 }}>Bạn cần hỗ trợ kỹ thuật, hợp tác phát triển hoặc muốn tìm hiểu sâu hơn về các gói cước dữ liệu định lượng của Finvista?</p>

            <div style={{ marginTop: "2rem", display: "flex", flexDirection: "column", gap: "1rem", fontSize: "0.88rem", color: "#94a3b8" }}>
              <div>✉ Email: <span style={{ color: "#ffffff" }}>support@finvista.vn</span></div>
              <div>☏ Hotline: <span style={{ color: "#ffffff" }}>038 703 9960</span></div>
              <div>📍 Địa chỉ: <span style={{ color: "#ffffff" }}>Số 22, đường Tố Hữu, Tp. Hà Nội, Việt Nam</span></div>
            </div>
          </div>

          {/* Form */}
          <div style={{ background: "#131b2e", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "0.75rem", padding: "2rem", boxShadow: "0 10px 30px rgba(0,0,0,0.2)" }}>
            <form onSubmit={handleContactSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "0.35rem" }}>Họ tên</label>
                <input
                  type="text"
                  value={contactName}
                  required
                  onChange={e => setContactName(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.85rem", background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "0.375rem", color: "#ffffff", fontSize: "0.85rem", outline: "none" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "0.35rem" }}>Email</label>
                <input
                  type="email"
                  value={contactEmail}
                  required
                  onChange={e => setContactEmail(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.85rem", background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "0.375rem", color: "#ffffff", fontSize: "0.85rem", outline: "none" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "0.35rem" }}>Nội dung tin nhắn</label>
                <textarea
                  rows={4}
                  value={contactMsg}
                  required
                  onChange={e => setContactMsg(e.target.value)}
                  style={{ width: "100%", padding: "0.55rem 0.85rem", background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "0.375rem", color: "#ffffff", fontSize: "0.85rem", outline: "none", resize: "none" }}
                />
              </div>

              <button type="submit" className="lp-btn-glow" style={{ padding: "0.7rem 1rem", width: "100%", marginTop: "0.5rem" }}>
                Gửi tin nhắn
              </button>
            </form>

            {contactSuccess && (
              <div style={{ color: "#10b981", fontSize: "0.8rem", textAlign: "center", marginTop: "1rem", fontWeight: "600" }}>
                ✓ Gửi thành công! Chúng tôi sẽ liên hệ lại qua email sớm nhất.
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Call To Action (CTA) SECTION */}
      <section style={{ background: "linear-gradient(135deg, #091326 0%, #150f38 50%, #080c16 100%)", padding: "7rem 2rem", position: "relative", zIndex: 1, borderTop: "1px solid rgba(37,99,235,0.15)" }}>
        <div style={{ maxWidth: 620, margin: "0 auto", textAlign: "center" }}>
          <h2 style={{ fontSize: "clamp(2rem, 5vw, 2.6rem)", fontWeight: 900, color: "#f8fafc", marginBottom: "1rem", lineHeight: 1.15, letterSpacing: "-0.5px" }}>
            Trở thành Quant Trader chuyên nghiệp ngay hôm nay
          </h2>
          <p style={{ color: "#94a3b8", fontSize: "1.05rem", marginBottom: "2.5rem", lineHeight: 1.75 }}>
            Bắt đầu phân tích, lọc vị thế tối ưu, và nhận cảnh báo thị trường hoàn toàn miễn phí.
          </p>

          <form onSubmit={handleSubscribe} className="lp-sub-form">
            <input
              type="email"
              value={email}
              required
              onChange={e => setEmail(e.target.value)}
              placeholder="Nhập địa chỉ email của bạn..."
              className="lp-sub-input"
            />
            <button type="submit" className="lp-btn-glow" style={{ padding: "0.85rem 1.75rem" }}>Đăng ký</button>
          </form>

          {subscribed && (
            <div className="lp-success-msg">✓ Cảm ơn bạn đã đăng ký! Chúng tôi sẽ gửi thông tin sớm nhất.</div>
          )}

          <div style={{ marginTop: "2rem" }}>
            <button onClick={onEnterApp} className="lp-btn-border-glow" style={{ fontSize: "0.9rem", padding: "0.75rem 1.75rem" }}>
              Vào thẳng ứng dụng →
            </button>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ background: "#060910", borderTop: "1px solid rgba(255,255,255,0.04)", padding: "2.5rem 2rem", display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: "1.5rem", position: "relative", zIndex: 1, width: "100%", boxSizing: "border-box" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", justifyContent: "flex-start" }}>
          <div style={{ width: 28, height: 28, borderRadius: "0.5rem", background: "linear-gradient(135deg,#ef4444,#2563eb)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: "0.9rem", color: "#fff" }}>F</div>
          <span style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 900, fontSize: "1rem", color: "#94a3b8" }}>FINVISTA</span>
        </div>
        <div style={{ display: "flex", gap: "2rem", justifyContent: "center", alignItems: "center" }}>
          {["Tính năng", "Tài liệu", "Chính sách", "Liên hệ"].map(l => (
            <span key={l} style={{ fontSize: "0.85rem", color: "#475569", cursor: "pointer", transition: "color 0.2s" }} onMouseEnter={e => e.currentTarget.style.color = '#94a3b8'} onMouseLeave={e => e.currentTarget.style.color = '#475569'}>{l}</span>
          ))}
        </div>
        <div style={{ fontSize: "0.82rem", color: "#334155", textAlign: "right" }}>
          © 2026 Finvista · Quantitative Covered Warrants Edge.
        </div>
      </footer>
    </div>
  );
}
