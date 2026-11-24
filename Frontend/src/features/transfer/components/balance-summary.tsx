import { useLocale, useTranslations } from "next-intl";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { AccountBalance } from "../types/transfer.types";

export function BalanceSummary({ account }: { account: AccountBalance }) {
  const t = useTranslations("transfer.balance");
  const locale = useLocale();
  const fmt = (v: number) =>
    new Intl.NumberFormat(locale, { style: "currency", currency: "VND" }).format(v);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("availableHint")}</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1 border p-4">
          <p className="text-xs text-muted-foreground">{t("balance")}</p>
          <p className="text-2xl font-bold tabular-nums">{fmt(account.balance)}</p>
        </div>
        <div className="space-y-1 border border-primary/25 bg-primary/5 p-4">
          <p className="text-xs text-muted-foreground">{t("available")}</p>
          <p className="text-2xl font-bold tabular-nums text-primary">
            {fmt(account.available)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
