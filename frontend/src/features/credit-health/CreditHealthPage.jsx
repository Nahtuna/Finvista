import React, { useEffect, useState } from "react";
import { RefreshCw, Search } from "lucide-react";

import { getCreditHealth } from "../../api.js";
import { Button } from "../../components/ui/button.jsx";
import { Input } from "../../components/ui/input.jsx";
import { ErrorBox, LoadingBox, MetricCard } from "../../components/ui/status.jsx";
import { formatNumber } from "../../lib/formatters.js";

// Set to true to show the AI (SHAP) model explanations section during presentations
const SHOW_SHAP_EXPLANATION = false;

function Ratio({ label, value }) {
  return (
    <div className="ratio-item">
      <span>{label}</span>
      <strong>{formatNumber(value, 4)}</strong>
    </div>
  );
}

function RatioText({ label, value, tone = "" }) {
  return (
    <div className={`ratio-item ${tone}`}>
      <span>{label}</span>
      <strong>{value || "-"}</strong>
    </div>
  );
}

function KpiGroup({ title, description, children }) {
  return (
    <section className="kpi-group">
      <div className="kpi-group-heading">
        <span>{title}</span>
        {description ? <p>{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

function formatRiskZone(zone, isEnglish) {
  const normalized = String(zone || "").toUpperCase();
  if (!zone) return "-";
  if (isEnglish) return zone;
  if (normalized.includes("DANGER")) return "NGUY HIỂM (ĐỎ)";
  if (normalized.includes("WARNING")) return "CẢNH BÁO (XÁM)";
  if (normalized.includes("SAFE")) return "AN TOÀN (XANH)";
  return zone;
}

function formatStatusDescription(description, zone, isEnglish) {
  if (isEnglish) return description || "";
  const normalized = String(zone || "").toUpperCase();
  if (normalized.includes("DANGER")) {
    return "Doanh nghiệp có dấu hiệu suy yếu tài chính nghiêm trọng. Cần tránh chiến lược rủi ro cao.";
  }
  if (normalized.includes("WARNING")) {
    return "Tình hình tài chính chưa ổn định. Nên dùng chiến lược phòng thủ và kiểm tra thêm dữ liệu.";
  }
  if (normalized.includes("SAFE")) {
    return "Điểm tín dụng doanh nghiệp tốt. Nền tảng tài chính đang ổn định.";
  }
  return description || "";
}

function formatDistressFlag(value, isEnglish) {
  return value ? (isEnglish ? "Distressed" : "Có rủi ro") : (isEnglish ? "Normal" : "Bình thường");
}


export function CreditHealthPage({ language = "vi" }) {
  const isEnglish = language === "en";
  const [ticker, setTicker] = useState("HPG");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function searchTicker() {
    if (!ticker.trim()) return;
    setLoading(true);
    setError("");
    try {
      setData(await getCreditHealth(ticker));
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    searchTicker();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const metrics = data?.credit_metrics || {};
  const ratios = data?.financial_ratios || {};
  const scores = data?.distress_scores || {};
  const zoneTone = metrics.risk_zone?.includes("DANGER")
    ? "danger"
    : metrics.risk_zone?.includes("WARNING") ? "warning" : "success";

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isEnglish ? "Enterprise risk" : "Rủi ro doanh nghiệp"}</p>
          <h2>{isEnglish ? "Credit Health" : "Sức khỏe tín dụng"}</h2>
        </div>
      </div>

      <div className="search-row">
        <Input
          value={ticker}
          onChange={(event) => setTicker(event.target.value.toUpperCase())}
          onKeyDown={(event) => event.key === "Enter" && searchTicker()}
          placeholder={isEnglish ? "Enter ticker: HPG, FPT, VIC..." : "Nhập mã cổ phiếu: HPG, FPT, VIC..."}
        />
        <Button onClick={searchTicker}><Search size={16} />{isEnglish ? "Search" : "Tra cứu"}</Button>
        <Button variant="secondary" onClick={searchTicker}><RefreshCw size={16} />{isEnglish ? "Refresh" : "Làm mới"}</Button>
      </div>

      {error ? <ErrorBox message={error} language={language} /> : null}
      {loading ? <LoadingBox message={isEnglish ? "Loading credit health..." : "Đang tải sức khỏe tín dụng..."} /> : null}

      {data ? (
        <>
          {data.is_bank ? (
            <>
              <KpiGroup
                title={isEnglish ? "Risk snapshot" : "Tóm tắt rủi ro"}
                description={isEnglish ? "Read this first to decide whether the bank is safe enough for CW strategies." : "Đọc nhóm này trước để biết ngân hàng có đủ an toàn cho chiến lược CW không."}
              >
                <div className="metric-grid">
                  <MetricCard label={isEnglish ? "Ticker" : "Mã cổ phiếu"} value={data.ticker} detail={`${isEnglish ? "Year" : "Năm"} ${data.reported_year}`} />
                  <MetricCard label={isEnglish ? "Capital Adequacy (CAR)" : "An toàn vốn (CAR)"} value={`${formatNumber((ratios.car || 0) * 100, 2)}%`} tone={zoneTone} />
                  <MetricCard label={isEnglish ? "Risk zone" : "Vùng rủi ro"} value={formatRiskZone(metrics.risk_zone, isEnglish)} tone={zoneTone} />
                  <MetricCard label={isEnglish ? "Risk probability" : "Xác suất rủi ro"} value={`${formatNumber((metrics.bankruptcy_probability || 0) * 100, 1)}%`} tone={zoneTone} />
                </div>
              </KpiGroup>

              <KpiGroup
                title={isEnglish ? "CAMELS Quality Metrics" : "Chất lượng CAMELS"}
                description={isEnglish ? "Capital adequacy, asset quality, earnings, liquidity, and sensitivity." : "Độ an toàn vốn, chất lượng tài sản, năng lực quản lý, hiệu quả sinh lời và thanh khoản."}
              >
                <div className="ratio-grid">
                  <Ratio label={isEnglish ? "Capital Adequacy (CAR)" : "An toàn vốn (CAR)"} value={ratios.car} />
                  <Ratio label={isEnglish ? "Bad Debt Ratio (NPL)" : "Tỷ lệ nợ xấu (NPL)"} value={ratios.npl} />
                  <Ratio label={isEnglish ? "Bad Debt Coverage (LLR)" : "Bao phủ nợ xấu (LLR)"} value={ratios.llr} />
                  <Ratio label={isEnglish ? "Cost-to-Income (CIR)" : "Hiệu quả chi phí (CIR)"} value={ratios.cir} />
                  <Ratio label={isEnglish ? "Net Interest Margin (NIM)" : "Biên lãi ròng (NIM)"} value={ratios.nim} />
                  <Ratio label={isEnglish ? "Loan-to-Deposit (LDR)" : "Tỷ lệ dư nợ/huy động (LDR)"} value={ratios.ldr} />
                  <Ratio label="ROE" value={ratios.roe} />
                </div>
              </KpiGroup>

              <KpiGroup
                title={isEnglish ? "Bank Risk Assessment" : "Đánh giá rủi ro ngân hàng"}
                description={isEnglish ? "Specialized financial institution risk parameters." : "Các chỉ báo rủi ro định chế tài chính chuyên biệt."}
              >
                <div className="ratio-grid distress-score-grid">
                  <RatioText label={isEnglish ? "CAMELS Rating" : "Xếp hạng CAMELS"} value={formatRiskZone(metrics.risk_zone, isEnglish)} tone={zoneTone} />
                  <RatioText label={isEnglish ? "Market Sensitivity" : "Độ nhạy thị trường"} value={isEnglish ? "Low / Stable" : "Thấp / An toàn"} tone="success" />
                  <RatioText label={isEnglish ? "ML Distress Alert" : "ML Cảnh báo"} value={formatDistressFlag(metrics.is_ml_distressed, isEnglish)} tone={metrics.is_ml_distressed ? "danger" : "success"} />
                </div>
              </KpiGroup>

              {SHOW_SHAP_EXPLANATION && data.shap_contributions && Object.keys(data.shap_contributions).length ? (
                <KpiGroup
                  title={isEnglish ? "XAI Model Explanations (SHAP)" : "Giải thích mô hình AI (SHAP)"}
                  description={isEnglish ? "Key drivers pushing the bank rating towards Safe (green/negative) or Distress (red/positive)." : "Các chỉ báo chính đóng góp đẩy điểm tín dụng ngân hàng về Safe (xanh/âm) hoặc Distress (đỏ/dương)."}
                >
                  <div className="shap-container" style={{ display: "flex", flexDirection: "column", gap: "0.75rem", padding: "1rem", background: "rgba(255, 255, 255, 0.03)", borderRadius: "6px" }}>
                    {Object.entries(data.shap_contributions).map(([feature, val]) => {
                      const maxVal = Math.max(...Object.values(data.shap_contributions).map(Math.abs)) || 1.0;
                      const percentage = Math.min(50, (Math.abs(val) / maxVal) * 50);
                      const isDanger = val > 0;
                      return (
                        <div key={feature} style={{ display: "grid", gridTemplateColumns: "150px 1fr 60px", alignItems: "center", gap: "1rem" }}>
                          <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--text-muted)" }}>
                            {feature.toUpperCase()}
                          </span>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", height: "16px", background: "rgba(255,255,255,0.02)", borderRadius: "4px", overflow: "hidden" }}>
                            <div style={{ display: "flex", justifyContent: "flex-end" }}>
                              {!isDanger ? (
                                <div style={{ width: `${percentage * 2}%`, background: "rgba(46, 196, 182, 0.85)", height: "100%", borderTopLeftRadius: "4px", borderBottomLeftRadius: "4px" }} />
                              ) : null}
                            </div>
                            <div style={{ display: "flex", justifyContent: "flex-start" }}>
                              {isDanger ? (
                                <div style={{ width: `${percentage * 2}%`, background: "rgba(230, 57, 70, 0.85)", height: "100%", borderTopRightRadius: "4px", borderBottomRightRadius: "4px" }} />
                              ) : null}
                            </div>
                          </div>
                          <span style={{ fontSize: "0.8rem", fontWeight: "600", textAlign: "right", color: isDanger ? "#e63946" : "#2ec4b6" }}>
                            {val > 0 ? "+" : ""}{val.toFixed(4)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </KpiGroup>
              ) : null}
              <p className="description-box">{metrics.status_description}</p>
            </>
          ) : (
            <>
              <KpiGroup
                title={isEnglish ? "Risk snapshot" : "Tóm tắt rủi ro"}
                description={isEnglish ? "Read this first to decide whether the ticker is safe enough for CW strategies." : "Đọc nhóm này trước để biết mã có đủ an toàn cho chiến lược CW không."}
              >
                <div className="metric-grid">
                  <MetricCard label={isEnglish ? "Ticker" : "Mã cổ phiếu"} value={data.ticker} detail={`${isEnglish ? "Year" : "Năm"} ${data.reported_year}`} />
                  <MetricCard label="Altman Z-score" value={formatNumber(metrics.altman_z_score, 2)} tone={zoneTone} />
                  <MetricCard label={isEnglish ? "Risk zone" : "Vùng rủi ro"} value={formatRiskZone(metrics.risk_zone, isEnglish)} tone={zoneTone} />
                  <MetricCard label={isEnglish ? "Risk probability" : "Xác suất rủi ro"} value={`${formatNumber((metrics.bankruptcy_probability || 0) * 100, 1)}%`} tone={zoneTone} />
                </div>
              </KpiGroup>

              <KpiGroup
                title={isEnglish ? "Financial quality" : "Chất lượng tài chính"}
                description={isEnglish ? "Liquidity, leverage, profitability, and debt-service capacity." : "Thanh khoản, đòn bẩy, khả năng sinh lời và khả năng trả lãi/nợ."}
              >
                <div className="ratio-grid">
                  <Ratio label={isEnglish ? "Debt ratio" : "Tỷ lệ nợ"} value={ratios.leverage_debt_ratio} />
                  <Ratio label={isEnglish ? "Liquidity" : "Thanh khoản"} value={ratios.liquidity_current_ratio} />
                  <Ratio label="ROA" value={ratios.roa} />
                  <Ratio label="ROE" value={ratios.roe} />
                  <Ratio label="EBIT/assets" value={ratios.ebit_to_assets} />
                  <Ratio label="ICR" value={ratios.icr} />
                  <Ratio label="OCF/debt" value={ratios.ocf_to_total_debt} />
                </div>
              </KpiGroup>

              <KpiGroup
                title={isEnglish ? "Distress models" : "Mô hình cảnh báo"}
                description={isEnglish ? "Cross-check statistical and rule-based distress signals before trusting a setup." : "Đối chiếu nhiều mô hình cảnh báo trước khi tin một setup."}
              >
                <div className="ratio-grid distress-score-grid">
                  <RatioText label={isEnglish ? "Altman zone" : "Vùng Altman"} value={formatRiskZone(scores.altman_zone, isEnglish)} tone={zoneTone} />
                  <Ratio label="Springate S-score" value={scores.springate_s_score} />
                  <Ratio label="Zmijewski X-score" value={scores.zmijewski_x_score} />
                  <RatioText label={isEnglish ? "Springate signal" : "Tín hiệu Springate"} value={formatDistressFlag(scores.springate_distressed, isEnglish)} tone={scores.springate_distressed ? "danger" : "success"} />
                  <RatioText label={isEnglish ? "Zmijewski signal" : "Tín hiệu Zmijewski"} value={formatDistressFlag(scores.zmijewski_distressed, isEnglish)} tone={scores.zmijewski_distressed ? "danger" : "success"} />
                  <RatioText label={isEnglish ? "ML distress" : "ML cảnh báo"} value={formatDistressFlag(metrics.is_ml_distressed, isEnglish)} tone={metrics.is_ml_distressed ? "danger" : "success"} />
                </div>
              </KpiGroup>

              {SHOW_SHAP_EXPLANATION && data.shap_contributions && Object.keys(data.shap_contributions).length ? (
                <KpiGroup
                  title={isEnglish ? "XAI Model Explanations (SHAP)" : "Giải thích mô hình AI (SHAP)"}
                  description={isEnglish ? "Key drivers pushing the XGBoost rating towards Safe (green/negative) or Distress (red/positive)." : "Các chỉ báo chính đóng góp đẩy điểm XGBoost về Safe (xanh/âm) hoặc Distress (đỏ/dương)."}
                >
                  <div className="shap-container" style={{ display: "flex", flexDirection: "column", gap: "0.75rem", padding: "1rem", background: "rgba(255, 255, 255, 0.03)", borderRadius: "6px" }}>
                    {Object.entries(data.shap_contributions).map(([feature, val]) => {
                      const maxVal = Math.max(...Object.values(data.shap_contributions).map(Math.abs)) || 1.0;
                      const percentage = Math.min(50, (Math.abs(val) / maxVal) * 50);
                      const isDanger = val > 0;
                      return (
                        <div key={feature} style={{ display: "grid", gridTemplateColumns: "150px 1fr 60px", alignItems: "center", gap: "1rem" }}>
                          <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--text-muted)" }}>
                            {feature}
                          </span>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", height: "16px", background: "rgba(255,255,255,0.02)", borderRadius: "4px", overflow: "hidden" }}>
                            <div style={{ display: "flex", justifyContent: "flex-end" }}>
                              {!isDanger ? (
                                <div style={{ width: `${percentage * 2}%`, background: "rgba(46, 196, 182, 0.85)", height: "100%", borderTopLeftRadius: "4px", borderBottomLeftRadius: "4px" }} />
                              ) : null}
                            </div>
                            <div style={{ display: "flex", justifyContent: "flex-start" }}>
                              {isDanger ? (
                                <div style={{ width: `${percentage * 2}%`, background: "rgba(230, 57, 70, 0.85)", height: "100%", borderTopRightRadius: "4px", borderBottomRightRadius: "4px" }} />
                              ) : null}
                            </div>
                          </div>
                          <span style={{ fontSize: "0.8rem", fontWeight: "600", textAlign: "right", color: isDanger ? "#e63946" : "#2ec4b6" }}>
                            {val > 0 ? "+" : ""}{val.toFixed(4)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </KpiGroup>
              ) : null}
              <p className="description-box">{formatStatusDescription(metrics.status_description, metrics.risk_zone, isEnglish)}</p>
            </>
          )}
        </>
      ) : null}
    </section>
  );
}
