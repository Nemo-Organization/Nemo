import { useTranslations } from "next-intl";
import {
  ArrowRightIcon,
  ArrowsLeftRightIcon,
  ReceiptIcon,
  ShieldCheckIcon,
  SparkleIcon,
} from "@phosphor-icons/react/ssr";

import { PageContainer } from "@/components/layout/page-container";
import { buttonVariants } from "@/components/ui/button";
import { ROUTES } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

const FEATURES = [
  { key: "transfer", icon: ArrowsLeftRightIcon, iconClass: "text-teal-600 dark:text-teal-400" },
  { key: "risk", icon: ShieldCheckIcon, iconClass: "text-emerald-600 dark:text-emerald-400" },
  { key: "check", icon: SparkleIcon, iconClass: "text-sky-600 dark:text-sky-400" },
  { key: "refund", icon: ReceiptIcon, iconClass: "text-amber-600 dark:text-amber-400" },
] as const;

export function HomeView() {
  const t = useTranslations("home");
  const app = useTranslations("common.app");

  return (
    <PageContainer className="space-y-8">
      <section className="relative overflow-hidden border bg-card px-6 py-12 shadow-2xs sm:px-12 sm:py-16">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 -right-24 size-80 rounded-full bg-primary/10 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-28 -left-16 size-72 rounded-full bg-chart-2/10 blur-3xl"
        />

        <div className="relative max-w-2xl space-y-5">
          <p className="inline-flex items-center gap-2 border border-primary/25 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            <ShieldCheckIcon className="size-3.5" weight="duotone" aria-hidden />
            {t("hero.eyebrow")}
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            {app("name")}
          </h1>
          <p className="text-lg font-medium text-foreground">{t("hero.title")}</p>
          <p className="text-base leading-relaxed text-muted-foreground">
            {t("hero.description")}
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Link
              href={ROUTES.transfer}
              className={cn(buttonVariants({ size: "lg" }), "group")}
            >
              {t("hero.cta")}
              <ArrowRightIcon
                data-icon="inline-end"
                className="transition-transform group-hover:translate-x-1"
                aria-hidden
              />
            </Link>
            <Link
              href={ROUTES.operator}
              className={buttonVariants({ variant: "outline", size: "lg" })}
            >
              {t("hero.operatorCta")}
            </Link>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight text-foreground">
          {t("features.title")}
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ key, icon: Icon, iconClass }) => (
            <div
              key={key}
              className="space-y-3 border bg-card p-5 shadow-2xs transition-colors hover:border-primary/60 hover:bg-accent/35"
            >
              <Icon className={cn("size-7", iconClass)} weight="duotone" aria-hidden />
              <h3 className="font-semibold text-foreground">
                {t(`features.items.${key}.title`)}
              </h3>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {t(`features.items.${key}.description`)}
              </p>
            </div>
          ))}
        </div>
      </section>
    </PageContainer>
  );
}
