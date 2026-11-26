"use client";

import { useTranslations } from "next-intl";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  RiskResult as RiskResultType,
  RiskSignal,
  TransferStatus,
} from "../types/transfer.types";

const TONE: Record<RiskResultType["level"], string> = {
  ALLOW: "border-l-primary",
  WARN: "border-l-amber-500",
  HOLD: "border-l-destructive",
};

function SignalGroup({ title, signals }: { title: string; signals: RiskSignal[] }) {
  const t = useTranslations("transfer.risk");
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      {signals.length ? (
        <ul className="list-disc space-y-1 pl-5 text-sm">
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
  const formatDateTime = useDateTimeFormatter();

  if (!risk || !status) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
          <CardDescription>{t("empty")}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const levelKey = risk.level.toLowerCase() as "allow" | "warn" | "hold";

  return (
    <Card className={cn("border-l-4", TONE[risk.level])}>
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

      <CardContent className="space-y-5">
        {risk.level !== "ALLOW" && (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <SignalGroup title={t("recipientWarnings")} signals={risk.recipientSignals} />
            <SignalGroup title={t("behavioralWarnings")} signals={risk.behavioralSignals} />
          </div>
        )}

        {risk.level === "HOLD" && risk.holdDeadline && (
          <p className="text-sm">
            {t("deadline", {
              date: formatDateTime(risk.holdDeadline),
            })}
          </p>
        )}

        {risk.level === "ALLOW" && (
          <p className="text-xs text-muted-foreground">{t("allowDisclaimer")}</p>
        )}

        {(status === "completed" || status === "cancelled") && (
          <p className="text-sm font-medium">{t(`status.${status}`)}</p>
        )}
      </CardContent>

      {status === "awaiting_decision" && (
        <CardFooter className="gap-2 border-t pt-4">
          <Button variant="outline" onClick={onCancel}>
            {t("cancel")}
          </Button>
          <Button onClick={onContinue}>{t("continue")}</Button>
        </CardFooter>
      )}
      {status === "held" && (
        <CardFooter className="border-t pt-4">
          <Button variant="outline" onClick={onCancel}>
            {t("cancelHold")}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
