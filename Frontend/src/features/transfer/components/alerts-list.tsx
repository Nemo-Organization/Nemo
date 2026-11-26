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
import { cn } from "@/lib/utils";
import type { AlertItem, AlertKind } from "../types/transfer.types";

const KIND_STYLE: Record<AlertKind, string> = {
  risk: "border-destructive/30 bg-destructive/10 text-destructive",
  refund: "border-primary/30 bg-primary/10 text-primary",
  info: "border-border bg-secondary text-secondary-foreground",
};

export function AlertsList({ alerts }: { alerts: AlertItem[] }) {
  const t = useTranslations("transfer.alerts");
  const formatDateTime = useDateTimeFormatter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("empty")}</p>
        )}
        {alerts.map((item) => (
          <div key={item.id} className="space-y-2 border p-4">
            <div className="flex items-center justify-between gap-2">
              <Badge variant="outline" className={cn("text-xs", KIND_STYLE[item.kind])}>
                {t(`kind.${item.kind}`)}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {formatDateTime(item.createdAt)}
              </span>
            </div>
            <p className="text-sm leading-relaxed">{t(`items.${item.key}`)}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
