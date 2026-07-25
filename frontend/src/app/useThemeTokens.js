// Centralized Design System Theme Tokens hook
// Reduces boilerplate across all feature pages and components
export function useThemeTokens(preferences = {}) {
  const isDark = preferences.colorMode !== "light";
  return {
    isDark,
    bg: "var(--surface-bg, " + (isDark ? "#0b0f19" : "#f8fafc") + ")",
    cardBg: "var(--surface-panel, " + (isDark ? "#131b2e" : "#ffffff") + ")",
    subBg: "var(--surface-muted, " + (isDark ? "#1e293b" : "#f1f5f9") + ")",
    textColor: "var(--text-main, " + (isDark ? "#f8fafc" : "#0f172a") + ")",
    mutedText: "var(--text-muted, " + (isDark ? "#94a3b8" : "#64748b") + ")",
    borderColor: "var(--border-soft, " + (isDark ? "#1e293b" : "#e2e8f0") + ")",
  };
}
