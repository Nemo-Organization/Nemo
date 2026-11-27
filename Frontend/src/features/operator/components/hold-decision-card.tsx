"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { CheckCircleIcon, InfoIcon, XCircleIcon } from "@phosphor-icons/react/ssr";
import { AnimatePresence, m } from "motion/react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { formatVnd } from "@/lib/format";
import { fadeMotion } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { HoldDecision } from "../types/operator.types";

// Transfer-only decision; does not change global recipient restriction.
export function HoldDecisionCard({
  decision,
  customerName,
  amount,
  deadline,
  onDecide,
}: {
  decision?: HoldDecision;
  customerName: string;
  amount: number;
  deadline: string;
  onDecide: (action: HoldDecision["action"], reason: string) => void;
}) {
  const t = useTranslations("operator.holds.decision");
  const locale = useLocale();
  const formatDateTime = useDateTimeFormatter();
  const [reason, setReason] = useState("");
  const [reasonMissing, setReasonMissing] = useState(false);

  const formatTime = (iso: string) => formatDateTime(iso, { timeStyle: "short" });

  const decide = (action: HoldDecision["action"]) => {
    if (!reason.trim()) {
      setReasonMissing(true);
      return;
    }
    onDecide(action, reason.trim());
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <AnimatePresence mode="wait" initial={false}>
          {decision ? (
            <m.div
              key={decision.action}
              {...fadeMotion}
              className={cn(
                "space-y-1.5 border p-4 text-sm",
                decision.action === "approved"
                  ? "border-primary/25 bg-primary/5"
                  : "border-destructive/30 bg-destructive/5",
              )}
            >
              <p
                className={cn(
                  "flex items-center gap-2 font-medium",
                  decision.action === "approved" ? "text-primary" : "text-destructive",
                )}
              >
                {decision.action === "approved" ? (
                  <CheckCircleIcon className="size-4 shrink-0" aria-hidden />
                ) : (
                  <XCircleIcon className="size-4 shrink-0" aria-hidden />
                )}
                {t(`${decision.action}Title`, { by: decision.by, time: formatTime(decision.at) })}
              </p>
              <p>
                {decision.action === "approved"
                  ? t("approvedBody", { customer: customerName, deadline: formatTime(deadline) })
                  : t("rejectedBody", {
                      customer: customerName,
                      amount: formatVnd(amount, locale),
                    })}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("reasonLine", { reason: decision.reason })}
              </p>
            </m.div>
          ) : (
            <m.div key="pending" {...fadeMotion} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="hold-decision-reason" className="text-sm font-medium">
                  {t("reason")}
                </label>
                <textarea
                  id="hold-decision-reason"
                  rows={3}
                  value={reason}
                  onChange={(e) => {
                    setReason(e.target.value);
                    if (reasonMissing) setReasonMissing(false);
                  }}
                  placeholder={t("reasonPlaceholder")}
                  aria-invalid={reasonMissing}
                  className="w-full border border-input bg-card p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                />
                {reasonMissing && (
                  <p className="text-xs text-destructive">{t("reasonRequired")}</p>
                )}
              </div>

              <div className="space-y-1 border border-sky-500/30 bg-sky-500/5 p-3">
                <p className="flex items-center gap-1.5 text-xs font-semibold text-sky-700 dark:text-sky-400">
                  <InfoIcon className="size-4" aria-hidden />
                  {t("infoTitle")}
                </p>
                <p className="text-xs">{t("infoBody", { deadline: formatTime(deadline) })}</p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button onClick={() => decide("approved")}>{t("approve")}</Button>
                <Button
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => decide("rejected")}
                >
                  {t("reject")}
                </Button>
              </div>
            </m.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}
