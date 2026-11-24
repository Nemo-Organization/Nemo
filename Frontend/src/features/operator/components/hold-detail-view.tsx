"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ArrowLeftIcon } from "@phosphor-icons/react/ssr";
import { toast } from "sonner";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ROUTES } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { formatVnd } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { HoldItem, HoldSignal, HoldStatus } from "../types/operator.types";
import { CaseSections } from "./case-sections";

function SignalGroup({ title, signals }: { title: string; signals: HoldSignal[] }) {
  const t = useTranslations("transfer.risk");
  const tOp = useTranslations("operator.holds");
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
        <p className="text-sm text-muted-foreground">{tOp("noSignals")}</p>
      )}
    </div>
  );
}

export function HoldDetailView({ hold }: { hold: HoldItem }) {
  const t = useTranslations("operator");
  const locale = useLocale();
  const formatDateTime = useDateTimeFormatter();
  const [status, setStatus] = useState<HoldStatus>(hold.status);

  // TODO: call hold decision API.
  const decide = (next: "approved" | "rejected") => {
    setStatus(next);
    toast.success(t(`holds.actions.${next}Done`));
  };

  return (
    <PageContainer className="space-y-6">
      <Link
        href={ROUTES.operator}
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-3")}
      >
        <ArrowLeftIcon data-icon="inline-start" aria-hidden />
        {t("back")}
      </Link>

      <PageHeader
        title={t("holds.detailTitle", { id: hold.id })}
        description={t("holds.detailDescription", { transferId: hold.transferId })}
      />

      <Card>
        <CardContent className="space-y-5 pt-6">
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground">{t("holds.columns.customer")}</dt>
              <dd>{hold.customerName}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{t("holds.columns.amount")}</dt>
              <dd className="tabular-nums">{formatVnd(hold.amount, locale)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{t("holds.columns.status")}</dt>
              <dd><Badge variant="secondary">{t(`holds.status.${status}`)}</Badge></dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{t("holds.columns.deadline")}</dt>
              <dd>{formatDateTime(hold.deadline)}</dd>
            </div>
          </dl>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <SignalGroup
              title={t("holds.recipientSignals")}
              signals={hold.signals.filter((s) => s.kind === "recipient")}
            />
            <SignalGroup
              title={t("holds.behavioralSignals")}
              signals={hold.signals.filter((s) => s.kind === "behavioral")}
            />
          </div>

          {status === "pending" ? (
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => decide("approved")}>{t("holds.actions.approved")}</Button>
              <Button variant="outline" onClick={() => decide("rejected")}>
                {t("holds.actions.rejected")}
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("holds.decidedNote")}</p>
          )}
        </CardContent>
      </Card>

      <CaseSections caseFile={hold.caseFile} />
    </PageContainer>
  );
}
