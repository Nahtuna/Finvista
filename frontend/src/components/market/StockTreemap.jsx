import React from "react";

/**
 * Simple treemap visualization for stocks.
 * Props:
 *   stocks: array of objects { key, flow, avgChange }
 */
export default function StockTreemap({ stocks = [] }) {
  if (!stocks.length) return null;
  const maxFlow = Math.max(...stocks.map(s => Math.abs(s.flow)), 1);
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
      {stocks.map(stock => {
        const size = Math.round((Math.abs(stock.flow) / maxFlow) * 100) + 40;
        const bg = stock.avgChange > 0 ? "#4caf50" : stock.avgChange < 0 ? "#f44336" : "#9e9e9e";
        return (
          <div
            key={stock.key}
            style={{
              width: size,
              height: size,
              backgroundColor: bg,
              color: "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.8rem",
              textAlign: "center",
              borderRadius: "4px",
            }}
            title={`${stock.key}\nFlow: ${stock.flow}\nAvg: ${stock.avgChange}%`}
          >
            {stock.key}
          </div>
        );
      })}
    </div>
  );
}
