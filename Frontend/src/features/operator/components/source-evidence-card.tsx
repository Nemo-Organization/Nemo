"use client";

import { useTranslations } from "next-intl";
import { ImageIcon } from "@phosphor-icons/react/ssr";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import type { Evidence } from "../types/operator.types";

export function SourceEvidenceCard({ evidence }: { evidence: Evidence | null }) {
  const t = useTranslations("operator.evidence");
  const formatDateTime = useDateTimeFormatter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!evidence ? (
          <p className="text-sm text-muted-foreground">{t("empty")}</p>
        ) : (
          <>
            {evidence.kind === "screenshot" && (
              <div className="flex items-center gap-3 border border-dashed p-4 text-sm text-muted-foreground">
                <ImageIcon className="size-6 shrink-0" aria-hidden />
                <span>{t("screenshotMock", { name: evidence.fileName ?? "" })}</span>
              </div>
            )}
            {evidence.text && (
              <blockquote className="border-l-4 border-primary/40 bg-secondary/45 p-3 text-sm">
                {evidence.text}
              </blockquote>
            )}
            <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-xs text-muted-foreground">{t("submittedAt")}</dt>
                <dd>{formatDateTime(evidence.submittedAt)}</dd>
              </div>
              {evidence.linkedDraftLabel && (
                <div>
                  <dt className="text-xs text-muted-foreground">{t("linkedDraft")}</dt>
                  <dd>{evidence.linkedDraftLabel}</dd>
                </div>
              )}
              {evidence.linkedOrderLabel && (
                <div>
                  <dt className="text-xs text-muted-foreground">{t("linkedOrder")}</dt>
                  <dd>{evidence.linkedOrderLabel}</dd>
                </div>
              )}
            </dl>
          </>
        )}
      </CardContent>
    </Card>
  );
}
