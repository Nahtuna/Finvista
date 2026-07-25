import { useEffect, useState } from "react";

import { DEFAULT_PREFERENCES, STORAGE_KEYS } from "./config.js";


export function usePreferences() {
  const [language, setLanguage] = useState(
    () => localStorage.getItem(STORAGE_KEYS.language) || "vi"
  );
  const [preferences, setPreferences] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.preferences);
    if (!saved) return DEFAULT_PREFERENCES;
    try {
      return { ...DEFAULT_PREFERENCES, ...JSON.parse(saved) };
    } catch {
      return DEFAULT_PREFERENCES;
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.language, language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.preferences, JSON.stringify(preferences));
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", preferences.colorMode);
      if (preferences.colorMode === "light") {
        document.documentElement.classList.remove("dark");
        document.documentElement.classList.add("light");
        document.body.style.backgroundColor = "#f8fafc";
      } else {
        document.documentElement.classList.remove("light");
        document.documentElement.classList.add("dark");
        document.body.style.backgroundColor = "#0b0f19";
      }
    }
  }, [preferences]);

  return { language, setLanguage, preferences, setPreferences };
}
