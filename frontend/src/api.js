// Compatibility surface for existing imports while endpoints live by domain.
export { API_BASE_URL, request, setAuthTokenProvider } from "./api/client.js";
export { getAdminSecretStatus } from "./api/admin.js";
export {
  getCreditHealth,
  getHealth,
  getMarketMetadata,
  triggerDataSync,
  getDbLastUpdated,
  getAtcQuickStatus,
  triggerAtcSync,
  getAtcStatusFull,
} from "./api/system.js";
export { getUnderlyingMarket, getMacroData, refreshAllData } from "./api/market.js";

export {
  getOpportunities,
  getWarrantHistory,
  getWarrantSimulation,
  refreshMarketScan,
  calculateGreeks,
  getWarrantMatrix
} from "./api/warrants.js";
export {
  getPortfolio,
  placeOrder,
  resetPortfolio,
  scanPortfolio
} from "./api/portfolio.js";
export {
  getMarketRegime,
  getTickerRegime,
  getTickerIndicators
} from "./api/regime.js";
export {
  getSystemicNetwork,
  getTopPropagators,
  getTickerSystemicProfile
} from "./api/systemic.js";
export {
  getNewsImpact,
  getNewsMLSignal,
  getNewsSentiment,
  runNewsPipeline,
  getFireantArticles
} from "./api/news.js";
export {
  chatCompletion,
  generateFinancialCommentary,
  getChatContextSummary
} from "./api/chat.js";
