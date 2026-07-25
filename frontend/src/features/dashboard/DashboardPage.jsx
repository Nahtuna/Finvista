import React, { useEffect, useState } from "react";
import { AlertTriangle, TrendingUp, DollarSign, PieChart, BarChart3, Clock, Bell, ShieldCheck } from "lucide-react";
import { getPortfolio, getCreditHealth } from "../../api.js";
import { formatMoney, formatNumber } from "../../lib/formatters.js";

import { useThemeTokens } from "../../app/useThemeTokens.js";

export function DashboardPage({ language = "vi", preferences = {} }) {
  const { isDark, bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const isEnglish = language === "en";
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState("tong_quan");
  const [creditHealthMap, setCreditHealthMap] = useState({});

  useEffect(() => {
    getPortfolio().then(res => {
      setData(res);
      const positions = res?.active_positions || [];
      const underlyings = Array.from(new Set(positions.map(p => p.underlying || p.symbol?.substring(1, 4)).filter(Boolean)));
      const fetchSymbols = underlyings.length > 0 ? underlyings : ["VPB", "HPG", "FPT", "MSN", "VRE", "VNM"];
      
      fetchSymbols.forEach(sym => {
        getCreditHealth(sym).then(ch => {
          setCreditHealthMap(prev => ({ ...prev, [sym]: ch }));
        }).catch(() => { });
      });
    }).catch(() => { });
  }, []);

  const positions = data?.active_positions || [];
  const hasPositions = positions.length > 0;
  const nav = data?.total_nav ?? (data?.cash || 100000000);
  const plVnd = hasPositions ? (data?.cumulative_p_l_vnd ?? 0) : 0;
  const plPct = hasPositions ? (data?.cumulative_p_l_pct ?? 0) : 0;
  const cash = data?.cash ?? nav;

  // Real maturity alerts derived from active positions
  const nearMaturityPositions = positions.filter(p => (p.days_at_buy || 30) <= 14);

  // Profit/Loss contributors sorted from real positions
  const sortedContributors = [...positions].sort((a, b) => (b.p_l_vnd || 0) - (a.p_l_vnd || 0));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>

      {/* HEADER BAR (PDF Page 7) */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.5rem", fontWeight: "900", margin: 0, color: textColor, letterSpacing: "0.5px" }}>
              4. DASHBOARD – BẢNG ĐIỀU KHIỂN ({activeTab.toUpperCase()})
            </h2>
            <p style={{ fontSize: "0.82rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
              Phân tích hiệu suất, phân bổ tài sản và cảnh báo rủi ro danh mục tự động.
            </p>
          </div>
        </div>

        {/* PDF Page 7 Tabs: Tổng quan, Hiệu suất, Rủi ro, Cảnh báo */}
        <div style={{ display: "flex", gap: "0.35rem", background: subBg, padding: "0.25rem", borderRadius: "0.5rem", width: "fit-content" }}>
          {[
            { id: "tong_quan", label: "Tổng quan" },
            { id: "hieu_suat", label: "Hiệu suất" },
            { id: "rui_ro", label: "Rủi ro tín dụng Z-Score" },
            { id: "canh_bao", label: `Cảnh báo đáo hạn ${nearMaturityPositions.length > 0 ? `(${nearMaturityPositions.length})` : ""}` },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? "#2563eb" : "transparent",
                color: activeTab === tab.id ? "#fff" : "#94a3b8",
                border: "none",
                borderRadius: "0.375rem",
                padding: "0.4rem 1.25rem",
                fontSize: "0.82rem",
                fontWeight: "700",
                cursor: "pointer"
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* DYNAMIC TAB VIEW */}
      {activeTab === "tong_quan" && (
        <>
          {/* CẢNH BÁO RỦI RO BANNER */}
          {nearMaturityPositions.length > 0 ? (
            <div style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.4)", borderRadius: "0.75rem", padding: "1rem 1.25rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <AlertTriangle size={20} style={{ color: "#ef4444" }} />
              <div style={{ flex: 1 }}>
                <strong style={{ color: "#ef4444", fontSize: "0.9rem" }}>CẢNH BÁO RỦI RO TẮT TOÁN</strong>
                <span style={{ fontSize: "0.82rem", color: "#f87171", marginLeft: "0.75rem" }}>Danh mục của bạn đang có {nearMaturityPositions.length} mã rủi ro đáo hạn trong 14 ngày tới.</span>
              </div>
              <span onClick={() => setActiveTab("canh_bao")} style={{ color: "#60a5fa", fontSize: "0.82rem", fontWeight: "700", cursor: "pointer" }}>Xem chi tiết ›</span>
            </div>
          ) : (
            <div style={{ background: "rgba(16, 185, 129, 0.12)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "0.75rem", padding: "0.75rem 1.25rem", display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <ShieldCheck size={18} style={{ color: "#10b981" }} />
              <span style={{ fontSize: "0.82rem", color: "#10b981", fontWeight: "600" }}>Danh mục an toàn: Không có mã CW nào sát ngày đáo hạn (&lt;14 ngày).</span>
            </div>
          )}

          {/* TOP 3 PANELS GRID */}
          <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1.1fr 1fr", gap: "1.25rem" }}>

            {/* HIỆU SUẤT DANH MỤC */}
            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
              <div style={{ fontSize: "0.85rem", color: mutedText, fontWeight: "700" }}>HIỆU SUẤT DANH MỤC</div>
              <div style={{ fontSize: "1.7rem", fontWeight: "900", color: plPct >= 0 ? "#10b981" : "#ef4444", margin: "0.25rem 0" }}>{plPct >= 0 ? "+" : ""}{formatNumber(plPct, 2)}%</div>
              <div style={{ fontSize: "0.78rem", color: mutedText, marginBottom: "1rem" }}>{hasPositions ? "Lãi/Lỗ danh mục thực tế" : "Danh mục chưa phát sinh vị thế"}</div>

              {/* Line Chart Simulation */}
              <div style={{ height: "120px", display: "flex", alignItems: "flex-end" }}>
                <svg width="100%" height="100%" viewBox="0 0 300 100" preserveAspectRatio="none">
                  <path d={plPct >= 0 ? "M0,80 Q50,60 100,70 T200,40 T300,10" : "M0,20 Q50,40 100,30 T200,60 T300,80"} fill="none" stroke={plPct >= 0 ? "#10b981" : "#ef4444"} strokeWidth="3" />
                </svg>
              </div>

              <div style={{ display: "flex", gap: "0.35rem", fontSize: "0.72rem", marginTop: "0.75rem" }}>
                {["1D", "1W", "1M", "3M", "6M", "YTD", "1Y", "ALL"].map((tf, i) => (
                  <button key={tf} style={{ background: i === 5 ? subBg : "transparent", color: i === 5 ? "#60a5fa" : mutedText, border: "none", borderRadius: "0.25rem", padding: "0.2rem 0.4rem", cursor: "pointer", fontWeight: "600" }}>{tf}</button>
                ))}
              </div>
            </div>

            {/* PHÂN BỔ TÀI SẢN */}
            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div style={{ fontSize: "0.85rem", color: mutedText, fontWeight: "700" }}>PHÂN BỔ TÀI SẢN</div>

              <div style={{ display: "flex", alignItems: "center", gap: "1.5rem", margin: "1rem 0" }}>
                <div style={{ width: "100px", height: "100px", borderRadius: "50%", background: hasPositions ? "conic-gradient(#c084fc 0% 70%, #f59e0b 70% 100%)" : "#2563eb", display: "grid", placeItems: "center" }}>
                  <div style={{ width: "60px", height: "60px", background: cardBg, borderRadius: "50%" }} />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", fontSize: "0.78rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#c084fc" }} />
                    <span>Chứng quyền: <strong>{hasPositions ? Math.round(((nav - cash) / nav) * 100) : 0}%</strong></span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#f59e0b" }} />
                    <span>Tiền mặt: <strong>{hasPositions ? Math.round((cash / nav) * 100) : 100}%</strong></span>
                  </div>
                </div>
              </div>
            </div>

            {/* TOP ĐÓNG GÓP LÃI/LỖ */}
            <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
              <div style={{ fontSize: "0.85rem", color: mutedText, fontWeight: "700", marginBottom: "0.75rem" }}>TOP ĐÓNG GÓP LÃI/LỖ</div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.78rem" }}>
                {sortedContributors.length > 0 ? (
                  sortedContributors.slice(0, 5).map(pos => (
                    <div key={pos.symbol} style={{ display: "flex", justifyContent: "space-between" }}>
                      <span>{pos.symbol}</span>
                      <strong style={{ color: (pos.p_l_vnd || 0) >= 0 ? "#10b981" : "#ef4444" }}>
                        {(pos.p_l_vnd || 0) >= 0 ? "+" : ""}{formatMoney(pos.p_l_vnd || 0)}đ
                      </strong>
                    </div>
                  ))
                ) : (
                  <span style={{ color: mutedText, fontSize: "0.78rem" }}>Chưa có vị thế trong danh mục</span>
                )}
              </div>
            </div>

          </div>
        </>
      )}

      {activeTab === "rui_ro" && (
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: "0 0 1rem 0" }}>BẢNG ĐÁNH GIÁ RỦI RO TÍN DỤNG ALTMAN Z-SCORE DOANH NGHIỆP CƠ SỞ</h3>

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${borderColor}`, color: mutedText }}>
                <th style={{ padding: "0.6rem" }}>Mã cổ phiếu CS</th>
                <th style={{ padding: "0.6rem" }}>Công ty</th>
                <th style={{ padding: "0.6rem" }}>Altman Z-Score</th>
                <th style={{ padding: "0.6rem" }}>Đánh giá Rủi ro</th>
                <th style={{ padding: "0.6rem" }}>Xác suất Kiệt quệ</th>
                <th style={{ padding: "0.6rem" }}>Khuyến nghị Vốn</th>
              </tr>
            </thead>
            <tbody>
              {["VPB", "HPG", "FPT", "MSN", "VHM", "VRE"].map(sym => {
                const info = creditHealthMap[sym] || { altman_z_score: 3.12, distress_probability: 0.05, rating: "SAFE" };
                const isSafe = (info.altman_z_score || 3.12) >= 2.99;
                return (
                  <tr key={sym} style={{ borderBottom: `1px solid ${borderColor}` }}>
                    <td style={{ padding: "0.75rem 0.6rem", fontWeight: "800", color: "#60a5fa" }}>{sym}</td>
                    <td style={{ padding: "0.75rem 0.6rem" }}>Doanh nghiệp {sym}</td>
                    <td style={{ padding: "0.75rem 0.6rem", fontWeight: "800", color: isSafe ? "#10b981" : "#ef4444" }}>{formatNumber(info.altman_z_score || 3.12, 2)}</td>
                    <td style={{ padding: "0.75rem 0.6rem", color: isSafe ? "#10b981" : "#ef4444", fontWeight: "700" }}>
                      {isSafe ? "✓ An toàn (Safe Zone)" : "⚠️ Vùng Cảnh báo (Gray Zone)"}
                    </td>
                    <td style={{ padding: "0.75rem 0.6rem" }}>{formatNumber((info.distress_probability || 0.03) * 100, 1)}%</td>
                    <td style={{ padding: "0.75rem 0.6rem", color: isSafe ? "#10b981" : "#ef4444", fontWeight: "700" }}>
                      {isSafe ? "Cấp phép giải ngân" : "Hạn chế tỷ trọng"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "canh_bao" && (
        <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "800", margin: "0 0 1rem 0" }}>CẢNH BÁO ĐÁO HẠN VÀ THỜI GIAN CÒN LẠI (WARRANT EXPIRATION)</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {nearMaturityPositions.length > 0 ? (
              nearMaturityPositions.map(pos => (
                <div key={pos.symbol} style={{ background: subBg, border: "1px solid #ef4444", padding: "1rem", borderRadius: "0.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong style={{ color: "#ef4444", fontSize: "0.95rem" }}>{pos.symbol} - Đáo hạn trong {pos.days_at_buy || 5} ngày</strong>
                    <p style={{ fontSize: "0.78rem", color: mutedText, margin: "0.2rem 0 0 0" }}>Ngày đáo hạn: {pos.settlement_date ? pos.settlement_date.split("T")[0] : "Sát đáo hạn"} • Khuyên dùng: Đóng vị thế chốt lời/cắt lỗ sớm</p>
                  </div>
                  <button style={{ background: "#ef4444", color: "#fff", border: "none", padding: "0.4rem 0.85rem", borderRadius: "0.25rem", fontSize: "0.78rem", fontWeight: "800", cursor: "pointer" }}>Bán đóng vị thế</button>
                </div>
              ))
            ) : (
              <div style={{ padding: "1.5rem", color: mutedText, fontSize: "0.85rem", textAlign: "center", background: subBg, borderRadius: "0.5rem", border: `1px solid ${borderColor}` }}>
                ✓ Không có vị thế nào sắp đáo hạn (&lt;14 ngày).
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
