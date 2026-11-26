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
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import type {
  RecipientInfo,
  Restriction,
  RestrictionLevel,
} from "../types/operator.types";

const selectClass =
  "h-9 w-full border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50";

export function RecipientDecisionCard({
  recipient,
  initialRestriction,
}: {
  recipient: RecipientInfo;
  initialRestriction: Restriction | null;
}) {
  const t = useTranslations("operator.decision");
  const formatDateTime = useDateTimeFormatter();
  const [restriction, setRestriction] = useState(initialRestriction);
  const [level, setLevel] = useState<RestrictionLevel>("WARN");
  const [reason, setReason] = useState("");
  const [reasonMissing, setReasonMissing] = useState(false);

  // TODO: call restriction API.
  const handleCreate = () => {
    if (!reason.trim()) {
      setReasonMissing(true);
      return;
    }
    setRestriction({
      id: `rs-${Date.now()}`,
      level,
      reason: reason.trim(),
      createdAt: new Date().toISOString(),
    });
    setReason("");
    setReasonMissing(false);
    toast.success(t("created"));
  };

  const handleRevoke = () => {
    setRestriction(null);
    toast.success(t("revoked"));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="border p-4 text-sm">
          <p className="text-xs text-muted-foreground">{t("recipient")}</p>
          <p className="font-medium">{recipient.name}</p>
          <p className="text-xs text-muted-foreground">{recipient.accountNumber}</p>
        </div>

        {restriction ? (
          <div className="space-y-3">
            <div className="space-y-2 border border-primary/25 bg-primary/5 p-4 text-sm">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium">{t("current")}</p>
                <Badge variant="secondary">{restriction.level}</Badge>
              </div>
              <p>{restriction.reason}</p>
              <p className="text-xs text-muted-foreground">
                {formatDateTime(restriction.createdAt)}
              </p>
            </div>
            <Button variant="outline" onClick={handleRevoke}>
              {t("revoke")}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
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
            <Button onClick={handleCreate}>{t("create")}</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
