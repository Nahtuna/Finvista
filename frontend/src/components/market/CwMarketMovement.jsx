import React from "react";
import { RefreshCw } from "lucide-react";

import { VN30_UNDERLYINGS } from "../../app/config.js";
import { formatMoney, formatNumber } from "../../lib/formatters.js";
import { Button } from "../ui/button.jsx";
import { CursorTooltip, useCursorTooltip } from "../ui/cursor-tooltip.jsx";

function formatCurrencyLabel(value, isEnglish) {
  return `${formatMoney(value)}${isEnglish ? " VND" : "đ"}`;
}

export function CwMarketMovement({
  rows = [],
  marketMeta = null,
  isEnglish = false,
  loading = false,
  onOpenDetail,
  onRefresh
}) {
  const [basket, setBasket] = React.useState("all");

  const vn30Set = new Set(
    (marketMeta?.vn30_symbols?.length ? marketMeta.vn30_symbols : [...VN30_UNDERLYINGS])
      .map((symbol) => String(symbol).toUpperCase())
  );
  const vn30Rows = rows.filter((row) =>
    row.is_vn30_underlying || vn30Set.has((row.underlying_symbol || "").toUpperCase())
  );
  const scopedRows = basket === "vn30" ? vn30Rows : rows;
  const activeRows = scopedRows.filter((row) => Number(row.days_to_maturity) > 0);
  const safeRows = activeRows.length ? activeRows : scopedRows;
  const buyRows = safeRows.filter((row) => row.recommendation_signal?.toUpperCase().includes("BUY"));
  const skipRows = safeRows.filter((row) => row.recommendation_signal?.toUpperCase().includes("SKIP"));
  const neutralRows = safeRows.filter((row) => {
    const signal = row.recommendation_signal?.toUpperCase() || "";
    return !signal.includes("BUY") && !signal.includes("SKIP");
  });
  const flowValue = (row) =>
    Math.max(0, Number(row.volume) || 0) * Math.max(0, Number(row.market_price) || 0);
  const totalFlow = safeRows.reduce((sum, row) => sum + flowValue(row), 0) || 1;
  const flowGroups = [
    { key: "buy", label: isEnglish ? "Buy" : "Mua", rows: buyRows, color: "#008b7a" },
    { key: "skip", label: isEnglish ? "Skip" : "Bỏ qua", rows: skipRows, color: "#d94a6f" },
    { key: "neutral", label: isEnglish ? "Neutral" : "Trung tính", rows: neutralRows, color: "#c9952f" }
  ].map((item) => ({
    ...item,
    flow: item.rows.reduce((sum, row) => sum + flowValue(row), 0)
  }));
  const pieTotal = Math.max(1, buyRows.length + skipRows.length + neutralRows.length);
  const topFlow = Math.max(...flowGroups.map((item) => item.flow), 1);
  const underlyingMap = safeRows.reduce((map, row) => {
    const key = row.underlying_symbol || "N/A";
    const current = map.get(key) || {
      key,
      flow: 0,
      count: 0,
      change: 0,
      best: row
    };
    current.flow += flowValue(row);
    current.count += 1;
    current.change += Number(row.price_change_pct) || 0;
    if ((Number(row.composite_g_score) || 0) > (Number(current.best?.composite_g_score) || 0)) {
      current.best = row;
    }
    map.set(key, current);
    return map;
  }, new Map());
  const heatTiles = [...underlyingMap.values()]
    .map((item) => ({
      ...item,
      avgChange: item.count ? item.change / item.count : 0
    }))
    .sort((a, b) => b.flow - a.flow)
    .slice(0, 30);
  const maxHeatFlow = Math.max(...heatTiles.map((item) => item.flow), 1);


  return (
    <section className="cw-movement-panel underlying-cw-pulse" aria-label={isEnglish ? "CW market movement" : "Biến động thị trường CW"}>
      <div className="movement-header">
        <div>
          <span className="eyebrow">{isEnglish ? "Market movement" : "Biến động thị trường"}</span>
          <h2>{isEnglish ? "Covered warrant pulse" : "Nhịp thị trường CW"}</h2>
          <small style={{ display: "block", marginTop: "2px" }}>
            {basket === "vn30"
              ? (isEnglish ? "VN30 underlying warrants only" : "Chỉ hiển thị CW có mã cơ sở thuộc VN30")
              : (isEnglish ? "All active warrants" : "Hiển thị toàn bộ mã CW đang hoạt động")}
          </small>
        </div>
        <div className="header-controls" style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <div className="segment-control" style={{ display: "flex", background: "var(--bg-card, rgba(0,0,0,0.06))", padding: "3px", borderRadius: "8px", border: "1px solid var(--border-light, rgba(0,0,0,0.08))" }}>
            <Button
              variant={basket === "all" ? "primary" : "ghost"}
              size="sm"
              onClick={() => setBasket("all")}
              style={{ padding: "0.25rem 0.75rem", fontSize: "0.78rem", height: "26px", borderRadius: "6px", fontWeight: 600 }}
            >
              {isEnglish ? "All" : "Toàn thị trường"}
            </Button>
            <Button
              variant={basket === "vn30" ? "primary" : "ghost"}
              size="sm"
              onClick={() => setBasket("vn30")}
              style={{ padding: "0.25rem 0.75rem", fontSize: "0.78rem", height: "26px", borderRadius: "6px", fontWeight: 600 }}
            >
              VN30
            </Button>
          </div>
          <Button variant="secondary" onClick={onRefresh} disabled={loading} style={{ height: "32px", padding: "0 0.75rem" }}>
            <RefreshCw size={14} />
            {isEnglish ? "Refresh CW" : "Làm mới CW"}
          </Button>
        </div>
      </div>

      <div className="movement-grid">
        <article className="movement-card breadth-card">
          <div className="movement-card-title">
            <span>{isEnglish ? "Signal breadth" : "Độ rộng tín hiệu"}</span>
            <strong>{formatMoney(safeRows.length)} CW</strong>
          </div>
          <SignalPie
            isEnglish={isEnglish}
            items={[
              { label: isEnglish ? "Buy" : "Mua", value: buyRows.length, color: "#008b7a" },
              { label: isEnglish ? "Skip" : "Bỏ qua", value: skipRows.length, color: "#d94a6f" },
              { label: isEnglish ? "Neutral" : "Trung tính", value: neutralRows.length, color: "#c9952f" }
            ]}
            total={pieTotal}
          />
        </article>

        <article className="movement-card flow-card">
          <div className="movement-card-title">
            <span>{isEnglish ? "CW traded value" : "Giá trị giao dịch CW"}</span>
            <strong>{formatMoney(totalFlow)}đ</strong>
          </div>
          <div className="flow-bars">
            {flowGroups.map((item) => (
              <FlowRow
                key={item.key}
                item={item}
                topFlow={topFlow}
                totalFlow={totalFlow}
                isEnglish={isEnglish}
              />
            ))}
          </div>
        </article>

        <article className="movement-card heatmap-card">
          <div className="movement-card-title">
            <span>{isEnglish ? "VN30 CW heatmap" : "Heatmap CW VN30"}</span>
            <strong>{formatMoney(heatTiles.length)} CPCS</strong>
          </div>
          <div className="cw-heatmap">
            {heatTiles.map((item) => (
              <HeatTile
                key={item.key}
                item={item}
                maxHeatFlow={maxHeatFlow}
                isEnglish={isEnglish}
                onOpenDetail={onOpenDetail}
              />
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}


function FlowRow({ item, topFlow, totalFlow, isEnglish }) {
  const { tooltip, showTooltip, hideTooltip } = useCursorTooltip();
  const share = (item.flow / Math.max(totalFlow, 1)) * 100;

  function showFlowTooltip(event) {
    showTooltip(event, {
      title: item.label,
      detail: `${formatCurrencyLabel(item.flow, isEnglish)} · ${formatNumber(share, 1)}%`
    });
  }

  return (
    <div className="flow-row">
      <span>{item.label}</span>
      <div
        className="flow-track"
        aria-label={`${item.label}: ${formatCurrencyLabel(item.flow, isEnglish)}`}
        onPointerEnter={showFlowTooltip}
        onPointerMove={showFlowTooltip}
        onPointerLeave={hideTooltip}
        onFocus={showFlowTooltip}
        onBlur={hideTooltip}
        tabIndex={0}
      >
        <i style={{ width: `${Math.max(4, (item.flow / topFlow) * 100)}%`, background: item.color }} />
      </div>
      <strong>{formatMoney(item.flow)}đ</strong>
      <CursorTooltip tooltip={tooltip} />
    </div>
  );
}


function HeatTile({ item, maxHeatFlow, isEnglish, onOpenDetail }) {
  const { tooltip, showTooltip, hideTooltip } = useCursorTooltip();

  function showHeatTooltip(event) {
    showTooltip(event, {
      title: item.key,
      detail: `${isEnglish ? "Avg change" : "Biến động TB"} ${formatNumber(item.avgChange, 1)}% · ${formatCurrencyLabel(item.flow, isEnglish)}`
    });
  }

  return (
    <button
      className={item.avgChange > 0 ? "up" : item.avgChange < 0 ? "down" : "flat"}
      style={{
        flexBasis: `${Math.max(18, (item.flow / maxHeatFlow) * 42)}%`,
        "--change-strength": Math.max(0.18, Math.min(0.72, Math.abs(item.avgChange) / 8))
      }}
      aria-label={`${item.key}: ${formatNumber(item.avgChange, 1)}%, ${formatCurrencyLabel(item.flow, isEnglish)}`}
      onClick={() => onOpenDetail(item.best?.warrant_symbol)}
      onPointerEnter={showHeatTooltip}
      onPointerMove={showHeatTooltip}
      onPointerLeave={hideTooltip}
      onFocus={showHeatTooltip}
      onBlur={hideTooltip}
    >
      <strong>{item.key}</strong>
      <span>{formatNumber(item.avgChange, 1)}%</span>
      <small>{formatMoney(item.flow)}đ</small>
      <CursorTooltip tooltip={tooltip} />
    </button>
  );
}


function SignalPie({ items, total, isEnglish }) {
  const { tooltip, showTooltip, hideTooltip } = useCursorTooltip();
  let offset = 0;
  return (
    <div className="signal-pie-wrap">
      <svg className="signal-pie" viewBox="0 0 42 42" aria-hidden="true">
        <circle cx="21" cy="21" r="15.9" fill="none" stroke="#f1e8d9" strokeWidth="8" />
        {items.map((item) => {
          const pct = Math.max(0, item.value / total) * 100;
          const detail = `${item.value} CW · ${formatNumber(pct, 1)}%`;
          function showSignalTooltip(event) {
            showTooltip(event, {
              title: item.label,
              detail
            });
          }
          const circle = (
            <circle
              key={item.label}
              className="cw-signal-segment"
              cx="21"
              cy="21"
              r="15.9"
              fill="none"
              stroke={item.color}
              strokeDasharray={`${pct} ${100 - pct}`}
              strokeDashoffset={-offset}
              strokeWidth="8"
              onPointerEnter={showSignalTooltip}
              onPointerMove={showSignalTooltip}
              onPointerLeave={hideTooltip}
            />
          );
          offset += pct;
          return circle;
        })}
      </svg>
      <div className="pie-legend">
        {items.map((item) => (
          <span key={item.label}>
            <i style={{ background: item.color }} />
            {item.label} <strong>{item.value}</strong>
          </span>
        ))}
      </div>
      <CursorTooltip tooltip={tooltip} />
    </div>
  );
}
