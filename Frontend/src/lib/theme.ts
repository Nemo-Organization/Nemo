export const THEMES = ["light", "dark"] as const;
export type Theme = (typeof THEMES)[number];

export const THEME_COOKIE = "theme";
export const THEME_COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 year (s)
export const DEFAULT_THEME: Theme = "light";

export function parseTheme(value: string | undefined): Theme {
  return THEMES.find((theme) => theme === value) ?? DEFAULT_THEME;
}

export function readThemeCookie(): Theme {
  const entry = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${THEME_COOKIE}=`));
  return parseTheme(entry?.slice(THEME_COOKIE.length + 1));
}

export function subscribeTheme(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });
  return () => observer.disconnect();
}

export function getThemeSnapshot(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

// Inlined in <head> to apply theme before first paint (no external deps).
export const THEME_INIT_SCRIPT = `(function(){try{var m=document.cookie.match(/(?:^|; )${THEME_COOKIE}=(light|dark)/);var t=m?m[1]:"${DEFAULT_THEME}";if(t==="dark")document.documentElement.classList.add("dark")}catch(e){}})();`;