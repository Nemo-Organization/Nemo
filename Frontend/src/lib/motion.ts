import type { Transition, Variants } from "motion/react";

export const EASE_OUT = [0.22, 1, 0.36, 1] as const;

export const TRANSITION_BASE: Transition = { duration: 0.22, ease: EASE_OUT };
export const TRANSITION_EXIT: Transition = { duration: 0.12, ease: "easeIn" };

// Card fades in, then staggers children using itemVariants.
export const cardVariants: Variants = {
  hidden: { opacity: 0, y: 6 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { ...TRANSITION_BASE, delayChildren: 0.05, staggerChildren: 0.04 },
  },
  exit: { opacity: 0, transition: TRANSITION_EXIT },
};

export const cardMotion = {
  variants: cardVariants,
  initial: "hidden",
  animate: "visible",
  exit: "exit",
} as const;

export const fadeMotion = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0, transition: TRANSITION_EXIT },
} as const;

export const itemVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  visible: { opacity: 1, y: 0, transition: TRANSITION_BASE },
};

export const listItemMotion = {
  initial: { opacity: 0, y: -6 },
  animate: { opacity: 1, y: 0 },
} as const;
