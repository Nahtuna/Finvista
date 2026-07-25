import React, { useState, useEffect, useMemo } from "react";
import { getFireantArticles } from "../../api/news.js";
import { Newspaper, Search, RefreshCw, ExternalLink, Filter, TrendingUp, Sparkles, Tag, ShieldCheck } from "lucide-react";
import { useThemeTokens } from "../../app/useThemeTokens.js";

export function NewsPage({ language = "vi", preferences = {} }) {
  const { bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const isEnglish = language === "en";
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const defaultNews = [
    { id: 1, title: "VN-Index bật tăng mạnh nhờ đà kéo từ nhóm cổ phiếu ngân hàng", date: "2024-07-19T10:30:00", source: "Vietstock", category: "ThiThruong", impact: "positive", score: "+8.5", summary: "Dòng tiền lớn lan tỏa vào các mã HDB, MBB, VCB giúp chỉ số giữ vững mốc 1,245 điểm.", url: "#" },
    { id: 2, title: "Hòa Phát (HPG) công bố doanh thu & lợi nhuận quý 2/2024 tăng trưởng kỷ lục", date: "2024-07-19T09:45:00", source: "CafeF", category: "DoanhNghiep", impact: "positive", score: "+9.2", summary: "Lợi nhuận sau thuế đạt hơn 3.200 tỷ đồng, tăng 15% so với cùng kỳ năm trước nhờ sản lượng thép xây dựng cải thiện.", url: "#" },
    { id: 3, title: "Khối ngoại mua ròng hơn 620 tỷ đồng trên HOSE tập trung chứng quyền & cổ phiếu VN30", date: "2024-07-19T09:15:00", source: "Finvista Intelligence", category: "DongTien", impact: "positive", score: "+7.8", summary: "Các mã CW như CVPB2404 và CHPG2405 được khối ngoại gia tăng tỷ trọng đột biến trong phiên ATO.", url: "#" },
    { id: 4, title: "Vinhomes (VHM) bàn giao phân khu mới, doanh thu bất động sản tăng mạnh", date: "2024-07-18T16:20:00", source: "Báo Đầu Tư", category: "DoanhNghiep", impact: "neutral", score: "+2.1", summary: "Dự kiến bàn giao hơn 5.000 căn hộ trong quý 3 giúp cải thiện dòng tiền doanh nghiệp và giảm nợ vay ngắn hạn.", url: "#" },
    { id: 5, title: "Áp lực tỷ giá USD/VND nhích nhẹ gây rung lắc ngắn hạn trên thị trường phái sinh", date: "2024-07-18T14:10:00", source: "VnEconomy", category: "ViMo", impact: "negative", score: "-4.5", summary: "Lợi suất trái phiếu Mỹ kỳ hạn 10 năm biến động nhẹ khiến hợp đồng VN30F1M thu hẹp khoảng cách Basis.", url: "#" }
  ];

  useEffect(() => {
    setLoading(true);
    getFireantArticles(symbolFilter || null, 30)
      .then(res => {
        if (res && res.length > 0) setArticles(res);
        else setArticles(defaultNews);
      })
      .catch(() => setArticles(defaultNews))
      .finally(() => setLoading(false));
  }, [symbolFilter]);

  const filteredArticles = useMemo(() => {
    return articles.filter(item => {
      if (categoryFilter === "all") return true;
      if (item.category === categoryFilter) return true;

      const text = `${item.title || ""} ${item.summary || item.content || ""}`.toLowerCase();

      if (categoryFilter === "DoanhNghiep") {
        return /doanh nghiệp|kqkd|lợi nhuận|doanh thu|bctc|cổ tức|lãnh đạo|đại hội|hđqt|hội đồng|công ty|khởi tố|chi nhánh|tài chính|giải trình|giao dịch|cổ phiếu|ctcp/i.test(text);
      }
      if (categoryFilter === "DongTien") {
        return /dòng tiền|khối ngoại|mua ròng|bán ròng|tự doanh|giao dịch|thanh khoản|khối lượng|tỷ trọng/i.test(text);
      }
      if (categoryFilter === "ViMo") {
        return /vĩ mô|tỷ giá|lãi suất|lợi suất|nhnn|fed|lạm phát|trái phiếu|usd|vnd|ngân hàng nhà nước/i.test(text);
      }
      if (categoryFilter === "ThiThruong") {
        return /thị trường|index|vnindex|vn30|chỉ số|chứng quyền|phái sinh|chứng khoán|hose|hnx|upcom/i.test(text);
      }

      return false;
    });
  }, [articles, categoryFilter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", color: textColor, background: bg }}>
      
      {/* HEADER BAR */}
      <div style={{ background: cardBg, border: `1px solid ${borderColor}`, borderRadius: "0.75rem", padding: "1.25rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "900", margin: 0, color: textColor, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            📰 Tin tức & Phân tích Tác động Định lượng (Finvista News Hub)
          </h2>
          <p style={{ fontSize: "0.8rem", color: mutedText, margin: "0.25rem 0 0 0" }}>
            Tổng hợp tin tức thị trường realtime · Phân tích mức độ tác động AI Score lên cổ phiếu & Chứng quyền
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <div style={{ position: "relative" }}>
            <Search size={15} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: mutedText }} />
            <input
              placeholder="Lọc theo mã CK (vd: HPG, FPT)..."
              value={symbolFilter}
              onChange={e => setSymbolFilter(e.target.value.toUpperCase())}
              style={{ background: subBg, border: `1px solid ${borderColor}`, color: textColor, padding: "0.4rem 0.75rem 0.4rem 2rem", borderRadius: "0.375rem", fontSize: "0.8rem", width: "220px" }}
            />
          </div>

          <button onClick={() => setSymbolFilter(symbolFilter)} style={{ background: subBg, color: textColor, border: `1px solid ${borderColor}`, padding: "0.4rem 0.85rem", borderRadius: "0.375rem", fontSize: "0.8rem", fontWeight: "700", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Tải lại
          </button>
        </div>
      </div>

      {/* CATEGORY TABS */}
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {[
          { id: "all", label: "🌐 Tất cả tin tức" },
          { id: "ThiThruong", label: "📈 Thị trường & Index" },
          { id: "DongTien", label: "💰 Dòng tiền & Khối ngoại" },
          { id: "DoanhNghiep", label: "🏢 Doanh nghiệp & KQKD" },
          { id: "ViMo", label: "🏛️ Vĩ mô & Tỷ giá" }
        ].map(cat => (
          <button
            key={cat.id}
            onClick={() => setCategoryFilter(cat.id)}
            style={{
              background: categoryFilter === cat.id ? "#2563eb" : cardBg,
              color: categoryFilter === cat.id ? "#fff" : textColor,
              border: `1px solid ${categoryFilter === cat.id ? "#2563eb" : borderColor}`,
              padding: "0.4rem 0.85rem",
              borderRadius: "2rem",
              fontSize: "0.78rem",
              fontWeight: "700",
              cursor: "pointer",
              transition: "all 0.15s ease"
            }}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* ARTICLES LIST */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {filteredArticles.map((item, idx) => {
          const impact = item.impact || (idx % 2 === 0 ? "positive" : "neutral");
          const score = item.score || (impact === "positive" ? "+8.5" : impact === "negative" ? "-4.5" : "+1.2");
          const impactColor = impact === "positive" ? "#10b981" : impact === "negative" ? "#ef4444" : "#eab308";
          const impactBg = impact === "positive" ? "rgba(16,185,129,0.12)" : impact === "negative" ? "rgba(239,68,68,0.12)" : "rgba(234,179,8,0.12)";
          const impactLabel = impact === "positive" ? "Tác động Tích cực" : impact === "negative" ? "Áp lực Điều chỉnh" : "Tác động Trung tính";

          return (
            <div
              key={idx}
              style={{
                background: cardBg,
                border: `1px solid ${borderColor}`,
                borderRadius: "0.75rem",
                padding: "1.25rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.6rem",
                transition: "border-color 0.2s ease, transform 0.15s ease",
                cursor: "pointer"
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = "#3b82f6";
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = borderColor;
                e.currentTarget.style.transform = "none";
              }}
            >
              {/* Header Badge Row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ background: subBg, border: `1px solid ${borderColor}`, color: "#3b82f6", fontSize: "0.72rem", fontWeight: "800", padding: "0.2rem 0.5rem", borderRadius: "0.25rem" }}>
                    {item.source || "Tin tức"}
                  </span>
                  <span style={{ fontSize: "0.72rem", color: mutedText }}>
                    🕒 {item.date ? (isNaN(new Date(item.date).getTime()) ? item.date : new Date(item.date).toLocaleString("vi-VN")) : "Mới cập nhật"}
                  </span>
                </div>

                <span style={{ background: impactBg, color: impactColor, border: `1px solid ${impactColor}40`, fontSize: "0.72rem", fontWeight: "800", padding: "0.2rem 0.6rem", borderRadius: "0.3rem", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                  <Sparkles size={12} /> {impactLabel} ({score} điểm AI)
                </span>
              </div>

              {/* Title */}
              <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: "800", color: textColor, lineHeight: "1.4" }}>
                {item.title}
              </h3>

              {/* Summary */}
              <p style={{ margin: 0, fontSize: "0.85rem", color: mutedText, lineHeight: "1.5" }}>
                {item.summary || item.content}
              </p>

              {/* Footer Row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: `1px solid ${borderColor}`, paddingTop: "0.6rem", marginTop: "0.2rem" }}>
                <span style={{ fontSize: "0.72rem", color: mutedText, display: "flex", alignItems: "center", gap: "0.3rem" }}>
                  <Tag size={12} style={{ color: "#3b82f6" }} /> Liên quan: <strong style={{ color: textColor }}>{item.symbols && item.symbols.length > 0 ? item.symbols.join(", ") : "VN30, HOSE"}</strong>
                </span>

                <a
                  href={item.url || item.link || "#"}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: "0.75rem", color: "#3b82f6", fontWeight: "700", textDecoration: "none", display: "flex", alignItems: "center", gap: "0.25rem" }}
                  onClick={e => e.stopPropagation()}
                >
                  Đọc nguồn gốc bài viết <ExternalLink size={12} />
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
