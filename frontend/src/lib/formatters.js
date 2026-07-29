export function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 }).format(
    Number(value)
  );
}

export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(digits);
}

export function formatChartValue(value, valueSuffix = "") {
  const suffix = valueSuffix || "";
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return `-${suffix}`;
  }
  if (suffix.trim().toUpperCase() === "VND" || suffix.includes("đ")) {
    return `${formatMoney(value)}${suffix}`;
  }
  if (suffix === "%") return `${formatNumber(value, 1)}%`;
  return `${formatNumber(value, 2)}${suffix}`;
}

export function signalClass(signal = "") {
  const normalized = signal.toUpperCase();
  if (normalized.includes("STRONG")) return "badge badge-success-strong";
  if (normalized.includes("BUY")) return "badge badge-success";
  if (normalized.includes("SKIP") || normalized.includes("DANGER")) {
    return "badge badge-danger";
  }
  return "badge badge-muted";
}

export function formatSignal(signal = "", isEnglish = false) {
  if (!signal) return "-";
  const normalized = signal.toUpperCase();
  if (!isEnglish) return signal;
  if (normalized.includes("STRONG")) return "STRONG BUY";
  if (normalized.includes("BUY")) return "BUY";
  if (normalized.includes("THANH KHOẢN") || normalized.includes("LIQUID")) {
    return "SKIP (LOW LIQUIDITY)";
  }
  if (normalized.includes("SKIP")) return "SKIP";
  return signal;
}

export function formatRelativeTime(dateStr) {
  if (!dateStr) return "Vừa cập nhật";
  try {
    let cleanStr = dateStr;
    // Handle various date formats
    if (dateStr.includes(" ")) {
      cleanStr = dateStr.replace(" ", "T");
    }
    const date = new Date(cleanStr);
    if (isNaN(date.getTime())) {
      // Try parsing as ISO string without modification
      const date2 = new Date(dateStr);
      if (isNaN(date2.getTime())) {
        return dateStr; // Return original if parsing fails
      }
    }

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60_000);

    if (diffMins < 1) return "Vừa cập nhật";
    if (diffMins < 60) return `${diffMins} phút trước`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} giờ trước`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return "Hôm qua";
    if (diffDays < 7) return `${diffDays} ngày trước`;

    return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
  } catch (_) {
    return dateStr;
  }
}

export function formatDateTime(dateStr) {
  if (!dateStr) return "Vừa cập nhật";
  try {
    let cleanStr = dateStr;
    // Handle standard database and rss date strings
    if (dateStr.includes(" ") && !dateStr.includes("+") && dateStr.indexOf(" ") === 10) {
      cleanStr = dateStr.replace(" ", "T");
    }
    const date = new Date(cleanStr);
    if (isNaN(date.getTime())) {
      const date2 = new Date(dateStr);
      if (isNaN(date2.getTime())) {
        return dateStr;
      }
      return format(date2);
    }
    return format(date);
  } catch (_) {
    return dateStr;
  }

  function format(d) {
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    return `${hours}:${minutes} ${day}/${month}/${year}`;
  }
}

