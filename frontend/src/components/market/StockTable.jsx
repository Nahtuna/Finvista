import React from "react";

/**
 * Simple table for displaying stock information.
 * Expects `stocks` prop with the same shape as heatTiles:
 * [{ key, flow, avgChange, best?, ... }]
 */
export function StockTable({ stocks = [] }) {
  if (!stocks.length) return null;
  return (
    <table className="stock-table" style={{ width: "100%", marginTop: "1rem", borderCollapse: "collapse" }}>
      <thead>
        <tr>
          <th style={{ borderBottom: "1px solid #ddd", textAlign: "left", padding: "4px" }}>Symbol</th>
          <th style={{ borderBottom: "1px solid #ddd", textAlign: "right", padding: "4px" }}>Flow</th>
          <th style={{ borderBottom: "1px solid #ddd", textAlign: "right", padding: "4px" }}>Avg Change %</th>
        </tr>
      </thead>
      <tbody>
        {stocks.map(item => (
          <tr key={item.key}>
            <td style={{ borderBottom: "1px solid #eee", padding: "4px" }}>{item.key}</td>
            <td style={{ borderBottom: "1px solid #eee", padding: "4px", textAlign: "right" }}>{(item.flow ?? 0).toLocaleString()}&#160;đ</td>
            <td style={{ borderBottom: "1px solid #eee", padding: "4px", textAlign: "right" }}>{item.avgChange.toFixed(1)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
