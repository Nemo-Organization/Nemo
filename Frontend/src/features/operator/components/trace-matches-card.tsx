"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import type { TraceMatch } from "../types/operator.types";

export function TraceMatchesCard({ matches }: { matches: TraceMatch[] }) {
  const t = useTranslations("operator.trace");
  const formatDateTime = useDateTimeFormatter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {matches.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("empty")}</p>
        )}
        {matches.map((m) => (
          <div key={m.id} className="flex items-start justify-between gap-3 border p-4">
            <div className="space-y-1">
              <p className="text-sm font-medium">{m.reference}</p>
              <p className="text-xs text-muted-foreground">
                {t(`recordType.${m.recordType}`)} · {m.recordId}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatDateTime(m.matchedAt)}
              </p>
            </div>
            <Badge variant="secondary">{t(`match.${m.match}`)}</Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
