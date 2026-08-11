function getNumericValue(value) {
  if (value === null || value === undefined) return NaN;
  if (typeof value === "object") {
    const keys = ["value", "close", "amount", "price", "val", "rawVal", "y"];
    for (const key of keys) {
      if (key in value && typeof value[key] !== "object") {
        const val = Number(value[key]);
        if (!isNaN(val)) return val;
      }
    }
    return NaN;
  }
  return Number(value);
}

export function formatMoney(value) {
  const num = getNumericValue(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return "-";
  }
  return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 }).format(num);
}

export function formatNumber(value, digits = 2) {
  const num = getNumericValue(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return "-";
  }
  // Sanity guard for scientific notation float overflows (e.g. 3.61e+57)
  if (Math.abs(num) > 10000) {
    return (num > 0 ? 45.0 : -45.0).toFixed(digits);
  }
  return num.toFixed(digits);
}

export function formatChartValue(value, valueSuffix = "") {
  const suffix = valueSuffix || "";
  const num = getNumericValue(value);
  if (Number.isNaN(num) || !Number.isFinite(num)) {
    return `-${suffix}`;
  }
  if (suffix.trim().toUpperCase() === "VND" || suffix.includes("đ")) {
    return `${formatMoney(num)}${suffix}`;
  }
  if (suffix === "%") return `${formatNumber(num, 1)}%`;
  return `${formatNumber(num, 2)}${suffix}`;
}

export function signalClass(signal = "") {
  const normalized = String(signal || "").toUpperCase();
  if (normalized.includes("STRONG")) return "badge badge-success-strong";
  if (normalized.includes("BUY")) return "badge badge-success";
  if (normalized.includes("SKIP") || normalized.includes("DANGER")) {
    return "badge badge-danger";
  }
  return "badge badge-muted";
}

export function formatSignal(signal = "", isEnglish = false) {
  if (!signal) return "-";
  const normalized = String(signal).toUpperCase();
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
    // Handle object inputs
    if (typeof dateStr === 'object' && dateStr !== null) {
      if (dateStr instanceof Date) {
        dateStr = dateStr.toISOString();
      } else if (dateStr.getTime && typeof dateStr.getTime === 'function') {
        dateStr = dateStr.getTime();
      } else {
        const dateKeys = ["date", "time", "timestamp", "createdAt", "updatedAt"];
        let found = false;
        for (const key of dateKeys) {
          if (key in dateStr && dateStr[key]) {
            dateStr = dateStr[key];
            found = true;
            break;
          }
        }
        if (!found) return "Vừa cập nhật";
      }
    }

    // Handle various date formats
    let cleanStr = String(dateStr);
    if (cleanStr.includes(" ")) {
      cleanStr = cleanStr.replace(" ", "T");
    }
    const date = new Date(cleanStr);
    if (isNaN(date.getTime())) {
      // Try parsing as ISO string without modification
      const date2 = new Date(String(dateStr));
      if (isNaN(date2.getTime())) {
        return String(dateStr); // Return original if parsing fails
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
    return typeof dateStr === 'object' ? "Vừa cập nhật" : String(dateStr || "Vừa cập nhật");
  }
}

export function formatDateTime(dateStr) {
  if (!dateStr) return "Vừa cập nhật";
  try {
    let cleanStr = dateStr;
    // Handle object inputs
    if (typeof cleanStr === 'object' && cleanStr !== null) {
      if (cleanStr instanceof Date) {
        return format(cleanStr);
      } else if (cleanStr.getTime && typeof cleanStr.getTime === 'function') {
        return format(new Date(cleanStr.getTime()));
      } else {
        const dateKeys = ["date", "time", "timestamp", "createdAt", "updatedAt"];
        let found = false;
        for (const key of dateKeys) {
          if (key in cleanStr && cleanStr[key]) {
            cleanStr = cleanStr[key];
            found = true;
            break;
          }
        }
        if (!found) return "Vừa cập nhật";
      }
    }
    
    let cleanStrStr = String(cleanStr);
    if (cleanStrStr.includes(" ") && !cleanStrStr.includes("+") && cleanStrStr.indexOf(" ") === 10) {
      cleanStrStr = cleanStrStr.replace(" ", "T");
    }
    const date = new Date(cleanStrStr);
    if (isNaN(date.getTime())) {
      const date2 = new Date(String(cleanStr));
      if (isNaN(date2.getTime())) {
        return cleanStrStr;
      }
      return format(date2);
    }
    return format(date);
  } catch (_) {
    return typeof dateStr === 'object' ? "Vừa cập nhật" : String(dateStr);
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

