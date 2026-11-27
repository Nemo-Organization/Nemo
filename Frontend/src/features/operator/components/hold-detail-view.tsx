"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ArrowLeftIcon } from "@phosphor-icons/react/ssr";
import { toast } from "sonner";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ROUTES } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { formatVnd } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useRecipientRestriction } from "../hooks/use-recipient-restriction";
import { formatTransferRef } from "../lib/transfer-ref";
import type { HoldDecision, HoldItem, HoldStatus } from "../types/operator.types";
import { EvidenceCard } from "./evidence-card";
import { HoldDecisionCard } from "./hold-decision-card";
import { HoldSignalBoxes } from "./hold-signal-boxes";
import { HoldStatusBadge } from "./hold-status-badge";
import { RecipientDecisionCard } from "./recipient-decision-card";

export function HoldDetailView({ hold }: { hold: HoldItem }) {
  const t = useTranslations("operator");
  const locale = useLocale();
  const formatDateTime = useDateTimeFormatter();
  // TODO(API): wire useReviewOpsHoldMutation & GET /ops/holds/{id} once available.
  const [status, setStatus] = useState<HoldStatus>(hold.status);
  const [decision, setDecision] = useState(hold.decision);
  const restriction = useRecipientRestriction({
    restriction: hold.restriction,
    history: hold.restrictionHistory,
    evidenceReportIds: [],
  });

  // TODO: call hold review API (approval clears hold, does not send funds).
  const decide = (action: HoldDecision["action"], reason: string) => {
    setDecision({ action, reason, by: "OPS", at: new Date().toISOString() });
    setStatus(action);
    toast.success(t(`holds.decision.${action}Done`));
  };

  const fields = [
    { label: t("holds.fields.customer"), value: hold.customerName },
    { label: t("holds.fields.recipient"), value: hold.recipient.name },
    { label: t("holds.fields.amount"), value: formatVnd(hold.amount, locale), numeric: true },
  ];

  return (
    <PageContainer className="space-y-6">
      <Link
        href={{ pathname: ROUTES.operator, query: { queue: "holds" } }}
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-3")}
      >
        <ArrowLeftIcon data-icon="inline-start" aria-hidden />
        {t("back")}
      </Link>

      <PageHeader
        title={t("holds.detailTitle")}
        description={t(`holds.description.${status}`, {
          transferId: formatTransferRef(hold.transferId),
        })}
      />

      <Card>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-3 lg:grid-cols-5">
            {fields.map((field) => (
              <div key={field.label} className="space-y-0.5">
                <dt className="text-xs text-muted-foreground">{field.label}</dt>
                <dd className={cn("font-medium", field.numeric && "tabular-nums")}>
                  {field.value}
                </dd>
              </div>
            ))}
            <div className="space-y-0.5">
              <dt className="text-xs text-muted-foreground">{t("holds.fields.status")}</dt>
              <dd>
                <HoldStatusBadge status={status} />
              </dd>
            </div>
            <div className="space-y-0.5">
              <dt className="text-xs text-muted-foreground">{t("holds.fields.deadline")}</dt>
              <dd className="font-medium">{formatDateTime(hold.deadline)}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <HoldSignalBoxes signals={hold.signals} />

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <HoldDecisionCard
            decision={decision}
            customerName={hold.customerName}
            amount={hold.amount}
            deadline={hold.deadline}
            onDecide={decide}
          />
          <EvidenceCard evidence={hold.evidence} context="hold" />
        </div>
        <RecipientDecisionCard
          recipient={hold.recipient}
          restriction={restriction.restriction}
          history={restriction.history}
          onCreate={restriction.create}
          onRevoke={restriction.revoke}
        />
      </div>
    </PageContainer>
  );
}
