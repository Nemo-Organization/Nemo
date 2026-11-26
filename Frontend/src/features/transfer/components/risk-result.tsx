"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { AnimatePresence, m } from "motion/react";

import { Collapse } from "@/components/motion/collapse";
import { MotionCard } from "@/components/motion/motion-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { formatVnd } from "@/lib/format";
import { cardVariants, itemVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type {
  RiskResult as RiskResultType,
  RiskSignal,
  TransferStatus,
} from "../types/transfer.types";

const CARD_MOTION = {
  variants: cardVariants,
  initial: "hidden",
  animate: "visible",
  exit: "exit",
} as const;

const TONE: Record<RiskResultType["level"], string> = {
  ALLOW: "border-l-primary",
  WARN: "border-l-amber-500",
  HOLD: "border-l-destructive",
};

function SignalGroup({ title, signals }: { title: string; signals: RiskSignal[] }) {
  const t = useTranslations("transfer.risk");
  return (
    <div className="space-y-2 border p-3.5">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      {signals.length ? (
        <ul className="list-disc space-y-1 pl-4 text-sm">
          {signals.map((s) => (
            <li key={s.code}>{t(`signals.${s.code}`)}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">{t("none")}</p>
      )}
    </div>
  );
}

export function RiskResult({
  risk,
  status,
  onContinue,
  onCancel,
}: {
  risk: RiskResultType | null;
  status: TransferStatus | null;
  onContinue: () => void;
  onCancel: () => void;
}) {
  const t = useTranslations("transfer.risk");
  const [ackedTransferId, setAckedTransferId] = useState<string | null>(null);

  // initial={false}: no entrance when the tab remounts; only new results animate.
  return (
    <AnimatePresence mode="wait" initial={false}>
      {risk && status ? (
        <ResultCard
          key={risk.transferId}
          risk={risk}
          status={status}
          acknowledged={ackedTransferId === risk.transferId}
          onAcknowledge={(checked) =>
            setAckedTransferId(checked ? risk.transferId : null)
          }
          onContinue={onContinue}
          onCancel={onCancel}
        />
      ) : (
        <MotionCard key="empty" {...CARD_MOTION}>
          <CardHeader>
            <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
            <CardDescription>{t("empty")}</CardDescription>
          </CardHeader>
        </MotionCard>
      )}
    </AnimatePresence>
  );
}

function ResultCard({
  risk,
  status,
  acknowledged,
  onAcknowledge,
  onContinue,
  onCancel,
}: {
  risk: RiskResultType;
  status: TransferStatus;
  acknowledged: boolean;
  onAcknowledge: (checked: boolean) => void;
  onContinue: () => void;
  onCancel: () => void;
}) {
  const t = useTranslations("transfer.risk");
  const locale = useLocale();
  const formatDateTime = useDateTimeFormatter();
  const levelKey = risk.level.toLowerCase() as "allow" | "warn" | "hold";

  return (
    <MotionCard {...CARD_MOTION} className={cn("border-l-4", TONE[risk.level])}>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-base font-semibold">
              {t(`${levelKey}.title`)}
            </CardTitle>
            <CardDescription>{t(`${levelKey}.description`)}</CardDescription>
          </div>
          <Badge variant="secondary">{risk.level}</Badge>
        </div>
      </CardHeader>

      <CardContent>
        {/* Fixed for a given result; revealed one after another. */}
        <div className="space-y-4">
          {risk.level !== "ALLOW" && (
            <m.div
              variants={itemVariants}
              className="grid grid-cols-1 gap-4 sm:grid-cols-2"
            >
              <SignalGroup
                title={t("recipientWarnings")}
                signals={risk.recipientSignals}
              />
              <SignalGroup
                title={t("behavioralWarnings")}
                signals={risk.behavioralSignals}
              />
            </m.div>
          )}

          {risk.level === "HOLD" && (
            <m.div
              variants={itemVariants}
              className="space-y-1 border border-destructive/30 bg-destructive/5 p-3.5 text-sm"
            >
              <p className="font-medium tabular-nums">
                {t("reservedAmount", { amount: formatVnd(risk.amount, locale) })}
              </p>
              {risk.holdDeadline && (
                <p className="text-xs text-muted-foreground">
                  {t("deadline", { date: formatDateTime(risk.holdDeadline) })}
                </p>
              )}
            </m.div>
          )}

          {risk.level === "ALLOW" && (
            <m.p variants={itemVariants} className="text-xs text-muted-foreground">
              {t("allowDisclaimer")}
            </m.p>
          )}
        </div>

        {/* Changes with status. Spacing sits inside Collapse so it shrinks too. */}
        <AnimatePresence initial={false}>
          {status === "awaiting_decision" && (
            <Collapse key="acknowledge">
              <div className="pt-4">
                <label className="flex cursor-pointer items-start gap-2.5 border bg-secondary/40 p-3 text-sm">
                  <input
                    type="checkbox"
                    checked={acknowledged}
                    onChange={(e) => onAcknowledge(e.target.checked)}
                    className="mt-1 size-4 accent-primary"
                  />
                  <span>{t("acknowledge")}</span>
                </label>
              </div>
            </Collapse>
          )}

          {(status === "completed" || status === "cancelled") && (
            <Collapse key={`status-${status}`}>
              <div className="pt-4">
                <p className="border bg-secondary/45 p-3 text-sm font-medium">
                  {t(`status.${status}`)}
                </p>
              </div>
            </Collapse>
          )}
        </AnimatePresence>
      </CardContent>

      <AnimatePresence initial={false}>
        {status === "awaiting_decision" && (
          <Collapse key="decision-footer">
            <CardFooter className="gap-2 border-t pt-4">
              <Button variant="outline" onClick={onCancel}>
                {t("cancel")}
              </Button>
              <Button disabled={!acknowledged} onClick={onContinue}>
                {t("continue")}
              </Button>
            </CardFooter>
          </Collapse>
        )}
        {status === "held" && (
          <Collapse key="held-footer">
            <CardFooter className="border-t pt-4">
              <Button variant="outline" onClick={onCancel}>
                {t("cancelHold")}
              </Button>
            </CardFooter>
          </Collapse>
        )}
      </AnimatePresence>
    </MotionCard>
  );
}
