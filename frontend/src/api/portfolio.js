import { request } from "./client.js";

export function getPortfolio() {
  return request("/api/portfolio");
}

export function placeOrder({ symbol, side, qty, quantity, price, reason }) {
  const finalQty = qty !== undefined ? qty : quantity;
  return request("/api/portfolio/orders", {
    method: "POST",
    body: JSON.stringify({
      symbol: (symbol || "").trim().toUpperCase(),
      side: (side || "BUY").toUpperCase(),
      qty: finalQty ? Number(finalQty) : 1000,
      price: price ? Number(price) : undefined,
      reason: reason || "Manual User Order"
    })
  });
}

export function resetPortfolio() {
  return request("/api/portfolio/reset", { method: "POST" });
}

export function scanPortfolio(force = false) {
  const params = new URLSearchParams({ force: String(force) });
  return request(`/api/portfolio/scan?${params.toString()}`, { method: "POST" });
}

export function runBacktestApi(
  strategy = "vol_arb",
  periodDays = 60,
  capital = 100000000,
  stopLossPct = 15,
  takeProfitPct = 35,
  underlyingSymbol = "ALL"
) {
  const params = new URLSearchParams({
    strategy,
    period_days: String(periodDays),
    capital: String(capital),
    stop_loss_pct: String(stopLossPct),
    take_profit_pct: String(takeProfitPct),
    underlying_symbol: underlyingSymbol
  });
  return request(`/api/portfolio/backtest?${params.toString()}`, { method: "POST" });
}

export function runCsvBacktestApi({
  strategy = "vol_arb",
  capital = 100000000,
  stopLossPct = 15,
  takeProfitPct = 35,
  ivEntryThreshold = 5,
  deltaEntryMin = 0.25,
  symbols = "ALL",
} = {}) {
  const params = new URLSearchParams({
    strategy,
    capital: String(capital),
    stop_loss_pct: String(stopLossPct),
    take_profit_pct: String(takeProfitPct),
    iv_entry_threshold: String(ivEntryThreshold),
    delta_entry_min: String(deltaEntryMin),
    symbols,
  });
  return request(`/api/portfolio/backtest/csv?${params.toString()}`, { method: "POST" });
}

export function getCsvDatasets() {
  return request("/api/portfolio/backtest/csv/available");
}

export function runLongtermBacktestApi({
  strategy = "momentum",
  years = 3,
  capital = 100000000,
  stopLossPct = 15,
  takeProfitPct = 35,
  underlyingFilter = "ALL",
} = {}) {
  const params = new URLSearchParams({
    strategy,
    years: String(years),
    capital: String(capital),
    stop_loss_pct: String(stopLossPct),
    take_profit_pct: String(takeProfitPct),
    underlying_filter: underlyingFilter,
  });
  return request(`/api/portfolio/backtest/longterm?${params.toString()}`, { method: "POST" });
}
