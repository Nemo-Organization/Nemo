"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AnimatePresence, m } from "motion/react";

import { Collapse } from "@/components/motion/collapse";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { fadeMotion } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type {
  RecipientAccount,
  Restriction,
  RestrictionHistoryEntry,
  RestrictionLevel,
} from "../types/operator.types";

const selectClass =
  "h-9 w-full border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50";

const LEVEL_TONE: Record<RestrictionLevel, { box: string; text: string }> = {
  HOLD: { box: "border-destructive/30 bg-destructive/5", text: "text-destructive" },
  WARN: {
    box: "border-amber-500/40 bg-amber-500/5",
    text: "text-amber-700 dark:text-amber-400",
  },
};

export function RecipientDecisionCard({
  recipient,
  restriction,
  history,
  onCreate,
  onRevoke,
}: {
  recipient: RecipientAccount;
  restriction: Restriction | null;
  history: RestrictionHistoryEntry[];
  onCreate: (level: RestrictionLevel, reason: string) => void;
  onRevoke: () => void;
}) {
  const t = useTranslations("operator.decision");
  const formatDateTime = useDateTimeFormatter();
  const [level, setLevel] = useState<RestrictionLevel>("WARN");
  const [reason, setReason] = useState("");
  const [reasonMissing, setReasonMissing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const formatDate = (iso: string) => formatDateTime(iso, { dateStyle: "medium" });

  const handleCreate = () => {
    if (!reason.trim()) {
      setReasonMissing(true);
      return;
    }
    onCreate(level, reason.trim());
    setReason("");
    setReasonMissing(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-0.5 border p-4">
          <p className="text-xs text-muted-foreground">{t("recipient")}</p>
          <p className="text-sm font-semibold">{recipient.name}</p>
          <p className="font-mono text-xs text-muted-foreground">
            {recipient.bankCode} · {recipient.maskedAccount}
          </p>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          {restriction ? (
            <m.div
              key={restriction.id}
              {...fadeMotion}
              className={cn("space-y-2 border p-4 text-sm", LEVEL_TONE[restriction.level].box)}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium">{t("active")}</p>
                <span
                  className={cn(
                    "font-mono text-xs font-semibold",
                    LEVEL_TONE[restriction.level].text,
                  )}
                >
                  {restriction.level} · ACTIVE
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {[
                  t("metaCreated", {
                    createdAt: formatDate(restriction.createdAt),
                    by: restriction.createdBy,
                  }),
                  restriction.evidenceReportIds.length > 0 &&
                    t("metaEvidence", { evidence: restriction.evidenceReportIds.join(", ") }),
                  t("metaExpires", { expiresAt: formatDate(restriction.expiresAt) }),
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              <p>{t("reasonLine", { reason: restriction.reason })}</p>
            </m.div>
          ) : (
            <m.div key="create" {...fadeMotion} className="space-y-4">
              <p className="text-sm text-muted-foreground">{t("none")}</p>
              <div className="space-y-1.5">
                <label htmlFor="restriction-level" className="text-sm font-medium">
                  {t("level")}
                </label>
                <select
                  id="restriction-level"
                  className={selectClass}
                  value={level}
                  onChange={(e) => setLevel(e.target.value as RestrictionLevel)}
                >
                  <option value="WARN">{t("warn")}</option>
                  <option value="HOLD">{t("hold")}</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label htmlFor="restriction-reason" className="text-sm font-medium">
                  {t("reason")}
                </label>
                <textarea
                  id="restriction-reason"
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
            </m.div>
          )}
        </AnimatePresence>

        {/* Avoid space-y so history collapse does not jump */}
        <div>
          <div className="flex flex-wrap items-center gap-2">
            {restriction ? (
              <Button
                variant="outline"
                className="text-destructive hover:text-destructive"
                onClick={onRevoke}
              >
                {t("revoke")}
              </Button>
            ) : (
              <Button onClick={handleCreate}>{t("create")}</Button>
            )}
            {history.length > 0 && (
              <Button
                variant="ghost"
                className="text-primary hover:text-primary"
                aria-expanded={showHistory}
                onClick={() => setShowHistory((value) => !value)}
              >
                {showHistory ? t("hideHistory") : t("history", { count: history.length })}
              </Button>
            )}
          </div>

          <AnimatePresence initial={false}>
            {showHistory && (
              <Collapse key="history">
                <ul className="mt-3 divide-y border">
                  {history.map((entry) => (
                    <li key={entry.id} className="space-y-0.5 px-4 py-2.5 text-sm">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium">
                          {t(`historyAction.${entry.action}`, { level: entry.level })}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(entry.at)}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {entry.by}
                        {entry.reason && ` · ${entry.reason}`}
                      </p>
                    </li>
                  ))}
                </ul>
              </Collapse>
            )}
          </AnimatePresence>
        </div>

        <p className="text-xs text-muted-foreground">{t("footnote")}</p>
      </CardContent>
    </Card>
  );
}
