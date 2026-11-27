"use client";

import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "motion/react";

import { EASE_OUT } from "@/lib/motion";

// Animates numeric transitions on client; SSR renders final value.
export function AnimatedNumber({
  value,
  format,
  className,
}: {
  value: number;
  format: (value: number) => string;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = useState(value);
  const current = useRef(value);

  useEffect(() => {
    if (current.current === value) return;
    const controls = animate(current.current, value, {
      duration: reduceMotion ? 0 : 0.5,
      ease: EASE_OUT,
      onUpdate: (latest) => {
        current.current = latest;
        setDisplay(latest);
      },
    });
    return () => controls.stop();
  }, [value, reduceMotion]);

  return <span className={className}>{format(Math.round(display))}</span>;
}
