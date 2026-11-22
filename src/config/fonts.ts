import { Inter_Tight } from "next/font/google";

/** Project typeface. Exposed as CSS variable `--font-inter-tight` (see globals.css). */
export const fontSans = Inter_Tight({
  subsets: ["latin", "vietnamese"],
  variable: "--font-inter-tight",
  display: "swap",
});
