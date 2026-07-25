export const NAV_ITEMS = {
  vi: [
    { id: "intro", label: "Tổng quan" },
    { id: "market", label: "Thị trường & Vĩ mô" },
    { id: "cw", label: "Scanner & Phân tích" },
    { id: "portfolio", label: "Danh mục & Watchlist" },
    { id: "news", label: "Tin tức & Phân tích" },
    { id: "alerts", label: "Tiện ích & Cảnh báo" },
    { id: "settings", label: "Cài đặt" }
  ],
  en: [
    { id: "intro", label: "Overview" },
    { id: "market", label: "Market & Macro" },
    { id: "cw", label: "Scanner & Analytics" },
    { id: "portfolio", label: "Portfolio & Watchlist" },
    { id: "news", label: "News & Analysis" },
    { id: "alerts", label: "Utilities & Alerts" },
    { id: "settings", label: "Settings" }
  ]
};

export const DEFAULT_PREFERENCES = {
  theme: "soft",
  colorMode: "dark",
  density: "comfortable",
  smoothMotion: true,
  tableHints: true,
  zoomSpeed: "normal",
  panSpeed: "normal"
};

export const STORAGE_KEYS = {
  language: "finvista-language",
  preferences: "finvista-preferences",
  filterPresets: "finvista-cw-filter-presets",
  strategy: "finvista-strategy"
};

export const VN30_UNDERLYINGS = new Set([
  "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
  "LPB", "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI",
  "STB", "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]);

