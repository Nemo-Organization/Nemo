"use client";

import { useTranslations } from "next-intl";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Notice } from "../types/transfer.types";

export function NoticesList({ notices }: { notices: Notice[] }) {
  const t = useTranslations("transfer.notices");
  const formatDateTime = useDateTimeFormatter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {notices.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("empty")}</p>
        )}
        {notices.map((n) => (
          <div key={n.id} className="space-y-1 border p-4">
            <p className="text-xs font-medium uppercase text-muted-foreground">
              {t(`kind.${n.kind}`)}
            </p>
            <p className="text-sm">{t(`items.${n.key}`)}</p>
            <p className="text-xs text-muted-foreground">
              {formatDateTime(n.createdAt)}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
