"use client";

import { useLocale, useTranslations } from "next-intl";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatVnd } from "@/lib/format";
import type { Order, Refund } from "../types/transfer.types";

export function RefundContext({
  refunds,
  orders,
}: {
  refunds: Refund[];
  orders: Order[];
}) {
  const t = useTranslations("transfer.refund");
  const locale = useLocale();
  const formatDateTime = useDateTimeFormatter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {refunds.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("empty")}</p>
        )}
        {refunds.map((refund) => {
          const order = orders.find((o) => o.id === refund.orderId);
          return (
            <div key={refund.id} className="flex items-start justify-between gap-3 border p-4">
              <div className="space-y-1">
                <p className="text-sm font-medium">{order?.label ?? refund.orderId}</p>
                <p className="text-xs text-muted-foreground">
                  {t("refundAmount", { amount: formatVnd(refund.amount, locale) })}
                  {order ? ` · ${t("orderAmount", { amount: formatVnd(order.amount, locale) })}` : ""}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDateTime(refund.updatedAt)}
                </p>
              </div>
              <Badge variant="secondary">{t(`status.${refund.status}`)}</Badge>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
