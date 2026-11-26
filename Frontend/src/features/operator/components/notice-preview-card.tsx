"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { AudienceEntry } from "../types/operator.types";

type Phase = "idle" | "confirming" | "published";

export function NoticePreviewCard({ audience }: { audience: AudienceEntry[] }) {
  const t = useTranslations("operator.notice");
  const [phase, setPhase] = useState<Phase>("idle");

  // TODO: call notice publish API.
  const handlePublish = () => {
    setPhase("published");
    toast.success(t("published", { count: audience.length }));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1 border bg-secondary/45 p-3">
          <p className="text-xs text-muted-foreground">{t("template")}</p>
          <p className="text-sm">{t("templateBody")}</p>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium">{t("audience", { count: audience.length })}</p>
          {audience.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("empty")}</p>
          ) : (
            <ul className="max-h-64 divide-y overflow-y-auto border">
              {audience.map((entry) => (
                <li key={entry.customerId} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
                  <span>
                    {entry.customerName}
                    <span className="ml-2 text-xs text-muted-foreground">{entry.customerId}</span>
                  </span>
                  <Badge variant="secondary">{t(`reason.${entry.reason}`)}</Badge>
                </li>
              ))}
            </ul>
          )}
        </div>

        {phase === "published" ? (
          <p className="text-sm font-medium">{t("published", { count: audience.length })}</p>
        ) : phase === "confirming" ? (
          <div className="space-y-3 border border-primary/25 bg-primary/5 p-4">
            <p className="text-sm">{t("confirm", { count: audience.length })}</p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setPhase("idle")}>
                {t("back")}
              </Button>
              <Button onClick={handlePublish}>{t("confirmPublish")}</Button>
            </div>
          </div>
        ) : (
          <Button disabled={audience.length === 0} onClick={() => setPhase("confirming")}>
            {t("publish")}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
