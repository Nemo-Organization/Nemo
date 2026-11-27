"use client";

import { m } from "motion/react";

import type { TabDirection } from "@/hooks/use-tab-param";

// Slides tab panel in by direction (0 skips entrance).
export function TabPanelMotion({
  direction,
  children,
}: {
  direction: TabDirection;
  children: React.ReactNode;
}) {
  return (
    <m.div
      initial={direction === 0 ? false : { opacity: 0, x: direction * 8 }}
      animate={{ opacity: 1, x: 0 }}
    >
      {children}
    </m.div>
  );
}
