"use client";

import { useLocale, useTranslations } from "next-intl";
import { FileTextIcon, ImageIcon } from "@phosphor-icons/react/ssr";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { formatVnd } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Evidence, EvidenceVerdict } from "../types/operator.types";
import { StateBox } from "./state-box";

const VERDICT_BADGE: Record<EvidenceVerdict, string> = {
  MISMATCH: "border-destructive/40 bg-destructive/10 text-destructive",
  UNCERTAIN: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  CONSISTENT: "border-primary/40 bg-primary/10 text-primary",
};

// Source evidence for a report or a held transfer. `context` picks the copy.
export function EvidenceCard({
  evidence,
  context,
}: {
  evidence: Evidence | null;
  context: "report" | "hold";
}) {
  const t = useTranslations("operator.evidence");
  const locale = useLocale();
  const formatDateTime = useDateTimeFormatter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t(`description.${context}`)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!evidence ? (
          <StateBox
            icon={FileTextIcon}
            title={t(`empty.${context}`)}
            hint={context === "hold" ? t("emptyHint") : undefined}
          />
        ) : (
          <>
            {evidence.fileName && (
              <div className="flex flex-col items-center gap-1.5 border border-dashed border-input bg-secondary/25 px-4 py-6 text-center">
                <ImageIcon className="size-5 text-muted-foreground" aria-hidden />
                <p className="text-sm font-medium">{evidence.fileName}</p>
                <p className="text-xs text-muted-foreground">{t("openOriginal")}</p>
              </div>
            )}

            <figure className="space-y-1 border-l-2 border-primary/40 bg-secondary/40 px-3 py-2.5">
              <blockquote className="text-sm font-medium">{evidence.text}</blockquote>
              <figcaption className="text-xs text-muted-foreground">
                {t(`textSource.${evidence.textSource}`)}
              </figcaption>
            </figure>

            <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-xs text-muted-foreground">{t("submittedAt")}</dt>
                <dd>{formatDateTime(evidence.submittedAt)}</dd>
              </div>
              {evidence.linkedTransfer && (
                <div>
                  <dt className="text-xs text-muted-foreground">{t("linkedTransfer")}</dt>
                  <dd className="tabular-nums">
                    {formatVnd(evidence.linkedTransfer.amount, locale)} ·{" "}
                    {evidence.linkedTransfer.status}
                  </dd>
                </div>
              )}
              {evidence.linkedOrder && (
                <div>
                  <dt className="text-xs text-muted-foreground">{t("linkedOrder")}</dt>
                  <dd>{evidence.linkedOrder}</dd>
                </div>
              )}
            </dl>

            {evidence.customerAnalysis && (
              <div className="space-y-1.5 border p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-medium text-muted-foreground">
                    {t("customerAnalysis")}
                  </p>
                  <Badge
                    variant="outline"
                    className={cn(VERDICT_BADGE[evidence.customerAnalysis.verdict])}
                  >
                    {evidence.customerAnalysis.verdict}
                  </Badge>
                </div>
                <p className="text-sm">{evidence.customerAnalysis.summary}</p>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
