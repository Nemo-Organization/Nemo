"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

const CHANGE_EVENT = "tabparamchange";

function subscribe(onChange: () => void) {
  window.addEventListener("popstate", onChange);
  window.addEventListener(CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener("popstate", onChange);
    window.removeEventListener(CHANGE_EVENT, onChange);
  };
}

const readParam = (param: string) => new URLSearchParams(window.location.search).get(param);

// Use replaceState to avoid polluting browser history.
function writeParam(param: string, value: string) {
  const url = new URL(window.location.href);
  url.searchParams.set(param, value);
  window.history.replaceState(null, "", url);
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export type TabDirection = -1 | 0 | 1;

// Syncs active tab with ?tab= via window.location (keeps static pages prerenderable).
export function useTabParam<T extends string>(
  tabs: readonly T[],
  {
    fallback,
    serverValue,
    param = "tab",
  }: { fallback: T; serverValue?: string; param?: string },
) {
  const raw = useSyncExternalStore(
    subscribe,
    () => readParam(param),
    () => serverValue ?? null,
  );
  const active = tabs.find((tab) => tab === raw) ?? fallback;
  const [direction, setDirection] = useState<TabDirection>(0);

  // Normalize missing/invalid param to fallback on mount.
  useEffect(() => {
    const current = readParam(param);
    if (!tabs.some((tab) => tab === current)) writeParam(param, fallback);
  }, [tabs, fallback, param]);

  const setActive = (next: T) => {
    if (next === active) return;
    setDirection(tabs.indexOf(next) > tabs.indexOf(active) ? 1 : -1);
    writeParam(param, next);
  };

  return { active, setActive, direction };
}
