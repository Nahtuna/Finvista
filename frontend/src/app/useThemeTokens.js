// Centralized Design System Theme Tokens hook
// Reduces boilerplate across all feature pages and components
export function useThemeTokens(preferences = {}) {
  const isDark = preferences.colorMode !== "light";
  return {
    isDark,
    // Background colors
    bg: "var(--surface-bg, " + (isDark ? "#0b0f19" : "#f8fafc") + ")",
    cardBg: "var(--surface-panel, " + (isDark ? "#131b2e" : "#ffffff") + ")",
    subBg: "var(--surface-muted, " + (isDark ? "#1e293b" : "#f1f5f9") + ")",
    
    // Text colors
    textColor: "var(--text-main, " + (isDark ? "#f8fafc" : "#0f172a") + ")",
    mutedText: "var(--text-muted, " + (isDark ? "#94a3b8" : "#64748b") + ")",
    
    // Border colors
    borderColor: "var(--border-soft, " + (isDark ? "#1e293b" : "#e2e8f0") + ")",
    
    // Semantic colors (status)
    success: "#059669",  // Green for success/safe
    warning: "#d97706",  // Yellow/amber for warning
    error: "#dc2626",   // Red for error/danger
    info: "#0284c7",    // Blue for info
    
    // Button colors
    primaryBtn: "#059669",     // Green primary button (consistent with "Làm mới" button)
    secondaryBtn: "#64748b",  // Gray secondary button
    dangerBtn: "#dc2626",      // Red danger button
    
    // Status indicators
    positive: "#059669",  // Green for positive changes
    negative: "#dc2626",  // Red for negative changes
    neutral: "#64748b",   // Gray for neutral/unchanged
  };
}
