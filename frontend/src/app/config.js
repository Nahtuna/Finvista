// NAV_ITEMS — 11 core nav items theo ARCHITECTURE spec
// Settings is accessed ONLY via Profile Avatar menu (to avoid clutter)
export const NAV_ITEMS = {
  vi: [
    { id: "intro",     label: "Tổng quan",          icon: "LayoutDashboard" },
    { id: "market",    label: "Thị trường",          icon: "BarChart2" },
    { id: "cw",        label: "Scanner & Phân tích", icon: "ScanLine" },
    { id: "portfolio", label: "Danh mục",            icon: "Briefcase" },
    { id: "watchlist", label: "Watchlist",           icon: "Bookmark" },
    { id: "learning",  label: "Learning",            icon: "BookOpen" },
    { id: "news",      label: "Tin tức",             icon: "Newspaper" },
    { id: "alerts",    label: "Cảnh báo",            icon: "Bell" },
    { id: "products",  label: "Sản phẩm",            icon: "Zap" },
  ],
  en: [
    { id: "intro",     label: "Overview",            icon: "LayoutDashboard" },
    { id: "market",    label: "Market",              icon: "BarChart2" },
    { id: "cw",        label: "Scanner & Analytics", icon: "ScanLine" },
    { id: "portfolio", label: "Portfolio",           icon: "Briefcase" },
    { id: "watchlist", label: "Watchlist",           icon: "Bookmark" },
    { id: "learning",  label: "Learning",            icon: "BookOpen" },
    { id: "news",      label: "News",                icon: "Newspaper" },
    { id: "alerts",    label: "Alerts",              icon: "Bell" },
    { id: "products",  label: "Products",            icon: "Zap" },
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

