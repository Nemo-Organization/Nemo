"use client";

import { useSyncExternalStore } from "react";
import { useTranslations } from "next-intl";

import {
  DEFAULT_THEME,
  getThemeSnapshot,
  subscribeTheme,
  THEME_COOKIE,
  THEME_COOKIE_MAX_AGE,
  type Theme,
} from "@/lib/theme";

export function ThemeToggle() {
  const t = useTranslations("common.navigation");
  const theme = useSyncExternalStore(
    subscribeTheme,
    getThemeSnapshot,
    () => DEFAULT_THEME,
  );
  const isDark = theme === "dark";

  const toggleTheme = () => {
    const next: Theme = isDark ? "light" : "dark";
    document.documentElement.classList.toggle("dark", next === "dark");
    document.cookie = `${THEME_COOKIE}=${next}; path=/; max-age=${THEME_COOKIE_MAX_AGE}; samesite=lax`;
  };

  return (
    <label className="theme-switch" title={t("theme")}>
      <input
        type="checkbox"
        aria-label={t("theme")}
        checked={isDark}
        onChange={toggleTheme}
        className="theme-switch-input"
      />
      <span className="theme-switch-slider" aria-hidden />
    </label>
  );
}
