"use client";

import { useLocale, useTranslations } from "next-intl";
import { FlagIcon } from "@phosphor-icons/react/ssr";
import { AnimatePresence, m } from "motion/react";

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
import { cardMotion, itemVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { AnalysisResult, AnalysisVerdict } from "../types/transfer.types";

const VERDICT_TONE: Record<AnalysisVerdict, string> = {
  MISMATCH: "border-l-destructive",
  UNCERTAIN: "border-l-amber-500",
  CONSISTENT: "border-l-primary",
};

const VERDICT_BADGE: Record<AnalysisVerdict, string> = {
  MISMATCH: "border-destructive/40 bg-destructive/10 text-destructive",
  UNCERTAIN: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  CONSISTENT: "border-primary/40 bg-primary/10 text-primary",
};

export function AnalysisResultCard({
  result,
  onCreateReport,
}: {
  result: AnalysisResult | null;
  onCreateReport: (analysis: AnalysisResult) => void;
}) {
  const t = useTranslations("transfer.analysis");

  // Animate new results only; skip on tab remount.
  return (
    <AnimatePresence mode="wait" initial={false}>
      {result ? (
        <ResultCard key={result.id} result={result} onCreateReport={onCreateReport} />
      ) : (
        <MotionCard key="empty" {...cardMotion}>
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
  result,
  onCreateReport,
}: {
  result: AnalysisResult;
  onCreateReport: (analysis: AnalysisResult) => void;
}) {
  const t = useTranslations("transfer.analysis");
  const locale = useLocale();
  const formatDateTime = useDateTimeFormatter();

  return (
    <MotionCard
      {...cardMotion}
      className={cn("border-l-4", VERDICT_TONE[result.verdict])}
    >
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
            <CardDescription>
              {result.id} · {formatDateTime(result.analyzedAt)}
            </CardDescription>
          </div>
          <Badge variant="outline" className={VERDICT_BADGE[result.verdict]}>
            {t(`verdict.${result.verdict}`)}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        <m.div variants={itemVariants} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="space-y-1 border p-3">
            <p className="text-xs text-muted-foreground">{t("requestedAction")}</p>
            <p className="font-medium">{result.requestedAction}</p>
          </div>
          <div className="space-y-1 border p-3">
            <p className="text-xs text-muted-foreground">{t("claimedPurpose")}</p>
            <p className="font-medium">{result.claimedPurpose}</p>
          </div>
        </m.div>

        <m.div variants={itemVariants} className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">{t("references")}</p>
          {result.extractedReferences.length ? (
            <div className="flex flex-wrap gap-1.5">
              {result.extractedReferences.map((ref) => (
                <Badge key={ref} variant="secondary" className="font-mono text-xs">
                  {ref}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">{t("noReferences")}</p>
          )}
        </m.div>

        {result.orderComparison && (
          <m.div
            variants={itemVariants}
            className="space-y-1 border border-primary/25 bg-primary/5 p-3"
          >
            <p className="text-xs font-semibold text-primary">
              {t("orderCheck")} · {result.orderComparison.orderLabel}
            </p>
            <p className="text-xs">
              {t("orderAmount", {
                amount: formatVnd(result.orderComparison.orderAmount, locale),
              })}
            </p>
            <p className="text-xs">
              {t("orderFee", {
                fee:
                  result.orderComparison.feeVnd === null
                    ? t("feeUnknown")
                    : result.orderComparison.feeVnd === 0
                      ? t("feeZero")
                      : formatVnd(result.orderComparison.feeVnd, locale),
              })}
            </p>
          </m.div>
        )}

        {result.sourceExcerpts.length > 0 && (
          <m.div variants={itemVariants} className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">{t("excerpts")}</p>
            <div className="space-y-1.5">
              {result.sourceExcerpts.map((excerpt) => (
                <blockquote
                  key={excerpt}
                  className="border-l-2 border-primary/40 bg-secondary/40 px-3 py-2 text-xs"
                >
                  {excerpt}
                </blockquote>
              ))}
            </div>
          </m.div>
        )}

        {result.missingInfo.length > 0 && (
          <m.div variants={itemVariants} className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">{t("missingInfo")}</p>
            <ul className="list-disc space-y-0.5 pl-4 text-xs text-muted-foreground">
              {result.missingInfo.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </m.div>
        )}

        <m.p variants={itemVariants} className="text-xs text-muted-foreground">
          {t("disclaimer")}
        </m.p>
      </CardContent>

      <CardFooter className="border-t pt-4">
        <Button variant="outline" onClick={() => onCreateReport(result)}>
          <FlagIcon data-icon="inline-start" aria-hidden />
          {t("reportCta")}
        </Button>
      </CardFooter>
    </MotionCard>
  );
}
