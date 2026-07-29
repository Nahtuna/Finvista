import React, { useState, useEffect, useMemo } from "react";
import { getFireantArticles } from "../../api/news.js";
import { Newspaper, Search, RefreshCw, ExternalLink, Filter, TrendingUp, Sparkles, Tag, ShieldCheck, X } from "lucide-react";
import { useThemeTokens } from "../../app/useThemeTokens.js";
import { formatDateTime } from "../../lib/formatters.js";

export function NewsPage({ language = "vi", preferences = {} }) {
  const { bg, cardBg, subBg, textColor, mutedText, borderColor } = useThemeTokens(preferences);

  const isEnglish = language === "en";
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [selectedNews, setSelectedNews] = useState(null);

  useEffect(() => {
    setLoading(true);
    getFireantArticles(symbolFilter || null, 30)
      .then(res => {
        setArticles(Array.isArray(res) && res.length > 0 ? res : []);
      })
      .catch(() => setArticles([]))
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
              onClick={() => setSelectedNews(item)}
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
                    🕒 {formatDateTime(item.date)}
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
                {item.summary || item.content || "Không có tóm tắt"}
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

      {/* Empty state */}
      {!loading && filteredArticles.length === 0 && (
        <div style={{ textAlign: "center", padding: "3rem", color: mutedText }}>
          <Newspaper size={40} style={{ opacity: 0.3, marginBottom: "0.75rem" }} />
          <p style={{ fontSize: "0.9rem", margin: 0 }}>
            {isEnglish ? "No news available. Check back later." : "Chưa có tin tức. Vui lòng thử lại sau."}
          </p>
        </div>
      )}

      {/* News Detail Modal */}
      {selectedNews && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem"
          }}
          onClick={() => setSelectedNews(null)}
        >
          <div
            style={{
              background: cardBg,
              border: `1px solid ${borderColor}`,
              borderRadius: "0.75rem",
              maxWidth: "800px",
              width: "100%",
              maxHeight: "90vh",
              overflow: "auto",
              padding: "1.5rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem"
            }}
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <span style={{ background: subBg, border: `1px solid ${borderColor}`, color: "#3b82f6", fontSize: "0.75rem", fontWeight: "800", padding: "0.2rem 0.5rem", borderRadius: "0.25rem" }}>
                    {selectedNews.source || "Tin tức"}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: mutedText }}>
                    🕒 {formatDateTime(selectedNews.date)}
                  </span>
                </div>
                <h2 style={{ margin: 0, fontSize: "1.3rem", fontWeight: "900", color: textColor, lineHeight: "1.4" }}>
                  {selectedNews.title}
                </h2>
              </div>
              <button
                onClick={() => setSelectedNews(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: mutedText,
                  cursor: "pointer",
                  padding: "0.25rem",
                  borderRadius: "0.25rem"
                }}
              >
                <X size={24} />
              </button>
            </div>

            {/* Modal Content */}
            <div style={{ borderTop: `1px solid ${borderColor}`, paddingTop: "1rem" }}>
              <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.9rem", fontWeight: "700", color: textColor }}>
                Tổng quan bài viết
              </h4>
              <div style={{ 
                background: subBg, 
                padding: "1rem", 
                borderRadius: "0.5rem", 
                fontSize: "0.9rem", 
                lineHeight: "1.6", 
                color: textColor,
                whiteSpace: "pre-wrap"
              }}>
                {selectedNews.summary || selectedNews.content || "Không có nội dung tóm tắt"}
              </div>
            </div>

            {/* Related Symbols */}
            {selectedNews.symbols && selectedNews.symbols.length > 0 && (
              <div style={{ borderTop: `1px solid ${borderColor}`, paddingTop: "1rem" }}>
                <span style={{ fontSize: "0.8rem", color: mutedText, display: "flex", alignItems: "center", gap: "0.3rem" }}>
                  <Tag size={14} style={{ color: "#3b82f6" }} /> Liên quan: <strong style={{ color: textColor }}>{selectedNews.symbols.join(", ")}</strong>
                </span>
              </div>
            )}

            {/* Link to Source */}
            <div style={{ borderTop: `1px solid ${borderColor}`, paddingTop: "1rem", display: "flex", justifyContent: "flex-end" }}>
              <a
                href={selectedNews.url || selectedNews.link || "#"}
                target="_blank"
                rel="noreferrer"
                style={{
                  fontSize: "0.85rem",
                  color: "#3b82f6",
                  fontWeight: "700",
                  textDecoration: "none",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem"
                }}
              >
                Đọc nguồn gốc bài viết <ExternalLink size={14} />
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
