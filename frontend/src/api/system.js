import { request } from "./client.js";

export function getHealth() {
  return request("/api/health");
}

export function getCreditHealth(ticker) {
  return request(`/api/credit-health/${ticker.trim().toUpperCase()}`);
}

export function getMarketMetadata({ forceRefresh = false } = {}) {
  const params = new URLSearchParams();
  if (forceRefresh) params.set("force_refresh", "true");
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/api/market/metadata${suffix}`);
}

export function triggerDataSync() {
  return request("/api/admin/scraper/run/ohlcv", { method: "POST" });
}

export function getDbLastUpdated() {
  return request("/api/admin/scraper/status?scraper_type=ohlcv_stock&limit=5");
}
