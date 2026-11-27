"use client";

import { m, useReducedMotion, type HTMLMotionProps } from "motion/react";

// Height + opacity reveal inside AnimatePresence (keep padding inside).
export function Collapse({ style, ...props }: HTMLMotionProps<"div">) {
  const reduceMotion = useReducedMotion();
  const collapsed = reduceMotion ? "auto" : 0;

  return (
    <m.div
      initial={{ height: collapsed, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: collapsed, opacity: 0 }}
      style={{ overflow: "hidden", ...style }}
      {...props}
    />
  );
}
