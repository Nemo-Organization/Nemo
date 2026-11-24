"use client";

import { useLayoutEffect, useSyncExternalStore } from "react";

import { readThemeCookie, THEME_INIT_SCRIPT } from "@/lib/theme";

const subscribe = () => () => {};

// Applies saved theme before first paint (SSR script) and on locale remount.
export function ThemeSync() {
  const isClient = useSyncExternalStore(subscribe, () => true, () => false);

  useLayoutEffect(() => {
    document.documentElement.classList.toggle("dark", readThemeCookie() === "dark");
  }, []);

  if (isClient) return null;

  return <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />;
}