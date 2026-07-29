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

// =============================
// ATC (End-of-Session Close Price) — QUICK STATUS + SYNC
// =============================

export function getAtcQuickStatus() {
  /**
   * Gọi /api/atc/quick-status trả thông tin độ tươi data STOCK/CW:
   *  - is_up_to_date, severity (ok|warning|danger), badge_color
   *  - stock_latest (YYYY-MM-DD), stock_latest_fmt (DD/MM), stock_days_behind
   *  - cw_latest, cw_latest_fmt, cw_days_behind
   *  - expected_trading_day_fmt (ngày cần có)
   *  - short_text, long_text (tự dịch tiếng Việt)
   *  - suggest_sync (true = nên tải lại)
   */
  return request("/api/atc/quick-status");
}

export function triggerAtcSync({ syncType = "ALL", blocking = false, force = false } = {}) {
  /**
   * Gọi /api/atc/sync POST để trigger sync thủ công
   *  - syncType  : ALL | STOCK | CW
   *  - blocking  : true = đợi xong mới trả (chậm); false = chạy background (recommend)
   *  - force     : true = đồng bộ lại dù đã up-to-date
   */
  const params = new URLSearchParams();
  params.set("sync_type", syncType);
  params.set("blocking", blocking ? "true" : "false");
  params.set("force", force ? "true" : "false");
  return request(`/api/atc/sync?${params.toString()}`, { method: "POST" });
}

export function getAtcStatusFull({ limitLogs = 10 } = {}) {
  return request(`/api/atc/status?limit_logs=${limitLogs}`);
}
