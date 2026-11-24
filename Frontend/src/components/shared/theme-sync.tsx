"use client";

import { useLayoutEffect } from "react";

import { readThemeCookie } from "@/lib/theme";

// Re-apply saved theme before paint when layout remounts (e.g. locale switch).
export function ThemeSync() {
  useLayoutEffect(() => {
    document.documentElement.classList.toggle("dark", readThemeCookie() === "dark");
  }, []);

  return null;
}