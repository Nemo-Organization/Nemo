"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { m } from "motion/react";

import { AnimatedNumber } from "@/components/motion/animated-number";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatVnd } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AccountBalance } from "../types/transfer.types";

export function BalanceSummary({ account }: { account: AccountBalance }) {
  const t = useTranslations("transfer.balance");
  const locale = useLocale();
  const format = (value: number) => formatVnd(value, locale);

  // Bump a key each time held funds increase so the highlight replays.
  const [prevHeld, setPrevHeld] = useState(account.held);
  const [heldPulse, setHeldPulse] = useState(0);
  if (account.held !== prevHeld) {
    setPrevHeld(account.held);
    if (account.held > prevHeld) setHeldPulse((n) => n + 1);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("availableHint")}</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="space-y-1 border p-4">
          <p className="text-xs text-muted-foreground">{t("balance")}</p>
          <AnimatedNumber
            value={account.balance}
            format={format}
            className="block text-2xl font-bold tabular-nums"
          />
        </div>
        <div
          className={cn(
            "relative isolate space-y-1 border p-4 transition-colors duration-300",
            account.held > 0 && "border-amber-500/40 bg-amber-500/5",
          )}
        >
          {heldPulse > 0 && (
            <m.span
              key={heldPulse}
              aria-hidden
              className="pointer-events-none absolute inset-0 -z-10 bg-amber-500/15"
              initial={{ opacity: 1 }}
              animate={{ opacity: 0 }}
              transition={{ duration: 1.2, ease: "easeOut" }}
            />
          )}
          <p className="text-xs text-muted-foreground">{t("held")}</p>
          <AnimatedNumber
            value={account.held}
            format={format}
            className={cn(
              "block text-2xl font-bold tabular-nums transition-colors duration-300",
              account.held > 0 ? "text-amber-600 dark:text-amber-400" : "text-foreground",
            )}
          />
        </div>
        <div className="space-y-1 border border-primary/25 bg-primary/5 p-4">
          <p className="text-xs text-muted-foreground">{t("available")}</p>
          <AnimatedNumber
            value={account.available}
            format={format}
            className="block text-2xl font-bold tabular-nums text-primary"
          />
        </div>
      </CardContent>
    </Card>
  );
}
