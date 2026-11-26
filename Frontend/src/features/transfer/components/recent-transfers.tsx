"use client";

import { useLocale, useTranslations } from "next-intl";
import { AnimatePresence, m } from "motion/react";

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
import { formatVnd } from "@/lib/format";
import { listItemMotion, TRANSITION_EXIT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type {
  RecentTransfer,
  RecentTransferStatus,
} from "../types/transfer.types";

const STATUS_STYLE: Record<RecentTransferStatus, string> = {
  completed: "border-primary/30 bg-primary/10 text-primary",
  held: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  cancelled: "border-border bg-muted text-muted-foreground",
};

export function RecentTransfers({
  transfers,
  onCancelHold,
}: {
  transfers: RecentTransfer[];
  onCancelHold: (transferId: string) => void;
}) {
  const t = useTranslations("transfer.history");
  const locale = useLocale();
  const formatDateTime = useDateTimeFormatter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {transfers.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("empty")}</p>
        )}
        {/* initial={false}: rows present on mount stay still; new rows slide in. */}
        <AnimatePresence initial={false}>
          {transfers.map((item) => (
            <m.div
              key={item.id}
              layout
              {...listItemMotion}
              className="flex flex-col justify-between gap-3 border p-4 sm:flex-row sm:items-center"
            >
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">{item.recipientName}</p>
                  <AnimatePresence mode="wait" initial={false}>
                    <m.span
                      key={item.status}
                      className="inline-flex"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, transition: TRANSITION_EXIT }}
                    >
                      <Badge
                        variant="outline"
                        className={cn("text-xs", STATUS_STYLE[item.status])}
                      >
                        {t(`status.${item.status}`)}
                      </Badge>
                    </m.span>
                  </AnimatePresence>
                </div>
                <p className="text-xs text-muted-foreground tabular-nums">
                  {item.id} · {item.accountNumber} · {formatDateTime(item.createdAt)}
                </p>
              </div>
              <div className="flex items-center justify-between gap-3 sm:justify-end">
                <m.p layout="position" className="text-base font-semibold tabular-nums">
                  {formatVnd(item.amount, locale)}
                </m.p>
                <AnimatePresence initial={false}>
                  {item.status === "held" && (
                    <m.div
                      key="cancel-hold"
                      exit={{ opacity: 0, scale: 0.95, transition: TRANSITION_EXIT }}
                    >
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onCancelHold(item.id)}
                      >
                        {t("cancelHold")}
                      </Button>
                    </m.div>
                  )}
                </AnimatePresence>
              </div>
            </m.div>
          ))}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}
