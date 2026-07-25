export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8008`
    : "http://127.0.0.1:8008");

let authTokenProvider = null;

export function setAuthTokenProvider(provider) {
  authTokenProvider = provider;
}

// In-memory request deduplication and 2000ms TTL response cache
const pendingRequests = new Map();
const responseCache = new Map();
const TTL_MS = 2000; // 2 seconds TTL

export async function request(path, options = {}, retries = 2) {
  const isGet = !options.method || options.method.toUpperCase() === "GET";
  const forceRefresh = options.forceRefresh === true;
  const cacheKey = `${path}_${options.body || ""}`;

  // 1. Return from 2-second TTL cache if valid and GET request
  if (isGet && !forceRefresh && responseCache.has(cacheKey)) {
    const { timestamp, data } = responseCache.get(cacheKey);
    if (Date.now() - timestamp < TTL_MS) {
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
          throw new Error(
            data?.detail ||
              data?.message ||
              `HTTP ${response.status}: ${response.statusText}`
          );
        }

        // Cache successful GET responses
        if (isGet && data) {
          responseCache.set(cacheKey, { timestamp: Date.now(), data });
        }

        return data;
      } catch (err) {
        lastErr = err;
        if (err.name === "TypeError" && attempt < retries) {
          await new Promise(r => setTimeout(r, 600 * (attempt + 1)));
          continue;
        }
        throw err;
      }
    }
    throw lastErr;
  })();

  if (isGet && !forceRefresh) {
    pendingRequests.set(cacheKey, requestPromise);
    requestPromise.finally(() => {
      pendingRequests.delete(cacheKey);
    });
  }

  return requestPromise;
}
