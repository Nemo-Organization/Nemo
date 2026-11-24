import { useLocale, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  const fmt = (v: number) =>
    new Intl.NumberFormat(locale, { style: "currency", currency: "VND" }).format(v);

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
                  {t("refundAmount", { amount: fmt(refund.amount) })}
                  {order ? ` · ${t("orderAmount", { amount: fmt(order.amount) })}` : ""}
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(refund.updatedAt).toLocaleString(locale)}
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
