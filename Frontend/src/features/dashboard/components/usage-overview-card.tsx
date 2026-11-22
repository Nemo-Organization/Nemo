import { useTranslations } from "next-intl";
import { ArrowUpIcon, InfoIcon } from "@phosphor-icons/react/ssr";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ROUTES } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import type { PlanUsage } from "../types/dashboard.types";

const formatNumber = (value: number) => value.toLocaleString("en-US");

export function UsageOverviewCard({ planUsage }: { planUsage: PlanUsage }) {
  const t = useTranslations("dashboard.usage");
  const { tier, tierLabel, leadsUsed, leadsLimit, daysUntilReset } = planUsage;

  const leadsRemaining = Math.max(0, leadsLimit - leadsUsed);
  const usagePercent = leadsLimit > 0 ? (leadsUsed / leadsLimit) * 100 : 100;
  const canUpgrade = tier === "free" || tier === "lite";

  return (
    <Card className="flex w-full flex-col py-0">
      <CardHeader className="border-b px-6 py-5">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-base font-semibold">
              {t("title")}
            </CardTitle>
            <CardDescription>{t("description")}</CardDescription>
          </div>
          <Badge
            variant={tier === "free" ? "secondary" : "default"}
            className="border border-primary/20 font-medium text-primary"
          >
            {tierLabel}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex flex-grow flex-col justify-center px-6 py-6">
        <div className="space-y-4 border border-primary/15 bg-secondary/45 p-4">
          <div className="flex items-baseline justify-between gap-2">
            <p className="text-xl font-bold tracking-tight text-foreground tabular-nums">
              {formatNumber(leadsUsed)}
              <span className="text-sm font-normal text-muted-foreground">
                {" "}
                / {formatNumber(leadsLimit)}
              </span>
            </p>
            <span className="text-xs font-medium text-primary tabular-nums">
              {Math.round(usagePercent)}%
            </span>
          </div>

          <Progress value={Math.min(100, usagePercent)} />

          <div className="space-y-1.5 pt-1">
            <p className="text-xs text-muted-foreground">
              {t("leadsCaptured")} ·{" "}
              <span className="font-medium text-foreground">
                {t("remaining", { count: formatNumber(leadsRemaining) })}
              </span>
            </p>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <InfoIcon className="size-3.5 shrink-0 text-primary" />
              <span>{t("resetsIn", { days: daysUntilReset })}</span>
            </p>
          </div>
        </div>
      </CardContent>

      {canUpgrade && (
        <CardFooter className="mt-auto border-t bg-card px-6 py-4">
          <Link
            href={ROUTES.upgrade}
            className="group flex w-full items-center justify-between gap-3 border border-primary/25 bg-primary/5 px-4 py-2.5 text-foreground transition-colors hover:border-primary hover:bg-primary hover:text-primary-foreground"
          >
            <span className="text-xs font-medium">{t("upgrade")}</span>
            <span className="flex size-6 shrink-0 items-center justify-center border border-primary/30 bg-card text-primary transition-transform group-hover:-translate-y-0.5">
              <ArrowUpIcon className="size-3.5" />
            </span>
          </Link>
        </CardFooter>
      )}
    </Card>
  );
}
