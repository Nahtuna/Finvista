export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8008";

let authTokenProvider = null;

export function setAuthTokenProvider(provider) {
  authTokenProvider = provider;
}

// In-memory deduplication + sessionStorage-backed TTL cache
const pendingRequests = new Map();
const responseCache = new Map();
const DEFAULT_TTL_MS = parseInt(import.meta.env.VITE_DEFAULT_TTL_MS || "30000"); // 30s default, configurable

// Per-endpoint TTL overrides (longer = less critical freshness)
// Optimized based on data freshness requirements and update frequency
// Can be overridden via environment variables
const ENDPOINT_TTL = {
  "/api/regime/market": parseInt(import.meta.env.VITE_REGIME_TTL_MS || "120000"),      // regime: 120s (regime changes infrequently)
  "/api/warrants/opportunities": parseInt(import.meta.env.VITE_WARRANTS_TTL_MS || "60000"), // scanner: 60s (reasonable for market scan)
  "/api/market/underlyings": parseInt(import.meta.env.VITE_MARKET_TTL_MS || "45000"),  // market: 45s (slightly longer for underlying data)
  "/api/market/macro": parseInt(import.meta.env.VITE_MACRO_TTL_MS || "60000"),        // macro (USD/Gold/Oil): 60s (reasonable for macro data)
  "/api/portfolio": parseInt(import.meta.env.VITE_PORTFOLIO_TTL_MS || "5000"),            // portfolio: 5s (realtime P&L - needs to be fresh)
  "/api/credit-health": parseInt(import.meta.env.VITE_CREDIT_TTL_MS || "120000"),      // credit health: 120s (credit metrics change slowly)
  "/api/news-impact": parseInt(import.meta.env.VITE_NEWS_TTL_MS || "180000"),        // news impact: 180s (news analysis less frequent)
};

function getTTL(path) {
  for (const [prefix, ttl] of Object.entries(ENDPOINT_TTL)) {
    if (path.startsWith(prefix)) return ttl;
  }
  return DEFAULT_TTL_MS;
}

// Hydrate in-memory cache from sessionStorage on first load
try {
  const stored = sessionStorage.getItem("fv_cache");
  if (stored) {
    const entries = JSON.parse(stored);
    for (const [k, v] of Object.entries(entries)) {
      responseCache.set(k, v);
    }
  }
} catch (_) {}

export async function request(path, options = {}, retries = 2) {
  const isGet = !options.method || options.method.toUpperCase() === "GET";
  const forceRefresh = options.forceRefresh === true;
  const cacheKey = `${path}_${options.body || ""}`;
  const ttl = getTTL(path);

  // 1. Return from TTL cache if valid (in-memory, seeded from sessionStorage)
  if (isGet && !forceRefresh && responseCache.has(cacheKey)) {
    const { timestamp, data } = responseCache.get(cacheKey);
    if (Date.now() - timestamp < ttl) {
      return data;
    }
    responseCache.delete(cacheKey);
  }

  // 2. Request Deduplication: Reuse pending promise if identical GET request is in-flight
  if (isGet && !forceRefresh && pendingRequests.has(cacheKey)) {
    return pendingRequests.get(cacheKey);
  }

  const token = authTokenProvider ? await authTokenProvider() : "";
  const requestPromise = (async () => {
    let lastErr;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const fetchOptions = { ...options };
        delete fetchOptions.forceRefresh;

        const response = await fetch(`${API_BASE_URL}${path}`, {
          ...fetchOptions,
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(fetchOptions.headers || {})
          }
        });

        const data = await response.json().catch(() => null);
        if (!response.ok) {
          // For 401 auth errors, return null instead of throwing to allow graceful handling
          if (response.status === 401 || data?.detail?.includes('Not authenticated')) {
            console.warn(`Auth required for ${path}`);
            return null;
          }
          throw new Error(
            data?.detail ||
              data?.message ||
              `HTTP ${response.status}: ${response.statusText}`
          );
        }

        // Cache successful GET responses in memory + sessionStorage
        if (isGet && data) {
          const entry = { timestamp: Date.now(), data };
          responseCache.set(cacheKey, entry);
          try {
            const all = {};
            responseCache.forEach((v, k) => { all[k] = v; });
            sessionStorage.setItem("fv_cache", JSON.stringify(all));
          } catch (_) {} // quota exceeded — silently skip
        }

        return data;
      } catch (err) {
        lastErr = err;
        if (err.name === "TypeError" && attempt < retries) {
          await new Promise(r => setTimeout(r, 600 * (attempt + 1)));
          continue;
        }
        // GET: network errors return null (backend starting up / down) — never throw
        if (isGet && err.name === "TypeError") return null;
        throw err;
      }
    }
    // GET: all retries exhausted → return null instead of throw
    if (isGet) return null;
    throw lastErr;
  })();

  if (isGet && !forceRefresh) {
    pendingRequests.set(cacheKey, requestPromise);
    // Suppress unhandled rejection for deduped callers that share this promise
    requestPromise.catch(() => {}).finally(() => {
      pendingRequests.delete(cacheKey);
    });
  }

  return requestPromise;
}
