"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { HoldStatus } from "../types/operator.types";

const STATUS_CODE: Record<HoldStatus, string> = {
  pending: "RISK_HELD",
  approved: "READY",
  rejected: "REJECTED",
};

const STATUS_TONE: Record<HoldStatus, string> = {
  pending: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  approved: "border-primary/40 bg-primary/10 text-primary",
  rejected: "border-destructive/40 bg-destructive/10 text-destructive",
};

// "RISK_HELD · Awaiting review". The queue table shows the label only.
export function HoldStatusBadge({ status }: { status: HoldStatus }) {
  const t = useTranslations("operator.holds.status");
  return (
    <Badge variant="outline" className={cn(STATUS_TONE[status])}>
      {STATUS_CODE[status]} · {t(status)}
    </Badge>
  );
}
