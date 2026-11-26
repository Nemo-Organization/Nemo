"use client";

import Image from "next/image";
import { useLocale, useTranslations } from "next-intl";

import { ROUTES } from "@/config/routes";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { key: "dashboard", href: ROUTES.home },
  { key: "endpoints", href: ROUTES.endpoints },
  { key: "leads", href: ROUTES.leads },
  { key: "logs", href: ROUTES.logs },
] as const;

export function DashboardTopbar() {
  const t = useTranslations("common.navigation");
  const pathname = usePathname();
  const locale = useLocale();
  const router = useRouter();

  const isActive = (href: string) =>
    href === ROUTES.home
      ? pathname === ROUTES.home
      : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-6 sm:px-8">
        <div className="flex items-center gap-6">
          <Link
            href={ROUTES.home}
            aria-label={t("home")}
            className="flex items-center gap-2 transition-opacity hover:opacity-80"
          >
            <Image
              src="/icon.png"
              alt=""
              width={24}
              height={24}
              className="size-6 object-contain dark:invert"
            />
            <span className="text-sm font-semibold tracking-tight text-foreground">
              Nemo
            </span>
          </Link>

          <nav
            aria-label={t("main")}
            className="flex items-center gap-1 overflow-x-auto"
          >
            {NAV_ITEMS.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.key}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "px-3 py-1.5 text-xs font-medium transition-colors",
                    active
                      ? "bg-secondary text-primary"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                  )}
                >
                  {t(item.key)}
                </Link>
              );
            })}
          </nav>
        </div>

        <div
          className="flex items-center border border-border bg-background"
          role="group"
          aria-label={t("language")}
        >
          {routing.locales.map((targetLocale) => {
            const selected = locale === targetLocale;
            return (
              <button
                key={targetLocale}
                type="button"
                onClick={() => router.replace(pathname, { locale: targetLocale })}
                className={cn(
                  "px-2 py-1 text-xs font-medium uppercase transition-colors",
                  selected
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {targetLocale}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
