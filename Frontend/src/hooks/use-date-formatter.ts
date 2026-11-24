"use client";

import { useSyncExternalStore } from "react";
import { useLocale } from "next-intl";

const subscribe = () => () => {};
const useIsClient = () =>
  useSyncExternalStore(subscribe, () => true, () => false);

const DEFAULT_OPTIONS: Intl.DateTimeFormatOptions = {
  dateStyle: "medium",
  timeStyle: "short",
};

// Formats ISO dates in UTC during SSR/hydration, then local timezone on client.
export function useDateTimeFormatter() {
  const locale = useLocale();
  const isClient = useIsClient();

  return (iso: string, options: Intl.DateTimeFormatOptions = DEFAULT_OPTIONS) =>
    new Date(iso).toLocaleString(locale, {
      ...options,
      timeZone: isClient ? undefined : "UTC",
    });
}
