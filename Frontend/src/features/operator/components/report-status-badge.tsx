"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ReportStatus } from "../types/operator.types";

const STATUS_CODE: Record<ReportStatus, string> = {
  new: "RECEIVED",
  inReview: "IN_REVIEW",
  resolved: "RESOLVED",
  dismissed: "DISMISSED",
};

const STATUS_TONE: Record<ReportStatus, string> = {
  new: "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-400",
  inReview: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  resolved: "border-primary/40 bg-primary/10 text-primary",
  dismissed: "border-border bg-muted text-muted-foreground",
};

// "RECEIVED · New". Set withLabel={false} for the code only.
export function ReportStatusBadge({
  status,
  withLabel = true,
  className,
}: {
  status: ReportStatus;
  withLabel?: boolean;
  className?: string;
}) {
  const t = useTranslations("operator.reports.status");
  return (
    <Badge variant="outline" className={cn(STATUS_TONE[status], className)}>
      {STATUS_CODE[status]}
      {withLabel && ` · ${t(status)}`}
    </Badge>
  );
}
