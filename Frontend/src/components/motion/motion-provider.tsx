"use client";

import { LazyMotion, MotionConfig } from "motion/react";

import { TRANSITION_BASE } from "@/lib/motion";

const loadFeatures = () => import("./features").then((mod) => mod.default);

export function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <MotionConfig reducedMotion="user" transition={TRANSITION_BASE}>
      <LazyMotion features={loadFeatures} strict>
        {children}
      </LazyMotion>
    </MotionConfig>
  );
}
