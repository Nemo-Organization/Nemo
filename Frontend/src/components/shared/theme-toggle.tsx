"use client";

import { useTranslations } from "next-intl";
import { MoonIcon, SunIcon } from "@phosphor-icons/react/ssr";

import { THEME_COOKIE, THEME_COOKIE_MAX_AGE, type Theme } from "@/lib/theme";

export function ThemeToggle() {
  const t = useTranslations("common.navigation");

  const toggleTheme = () => {
    const root = document.documentElement;
    const next: Theme = root.classList.contains("dark") ? "light" : "dark";

    root.classList.toggle("dark", next === "dark");
    document.cookie = `${THEME_COOKIE}=${next}; path=/; max-age=${THEME_COOKIE_MAX_AGE}; samesite=lax`;
  };

  return (
    <button
      type="button"
      aria-label={t("theme")}
      title={t("theme")}
      onClick={toggleTheme}
      className="flex size-8 items-center justify-center border border-border bg-background text-muted-foreground transition-colors hover:text-foreground"
    >
      {/* CSS-driven swap avoids hydration mismatch */}
      <SunIcon className="hidden size-4 dark:block" aria-hidden />
      <MoonIcon className="size-4 dark:hidden" aria-hidden />
    </button>
  );
}