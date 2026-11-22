import Image from "next/image";
import { useTranslations } from "next-intl";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Skeleton } from "@/components/ui/skeleton";
import { ROUTES } from "@/config/routes";
import { Link } from "@/i18n/navigation";

export function PageBreadcrumbs({
  currentPageLabel,
  isLoading,
}: {
  currentPageLabel: string;
  isLoading?: boolean;
}) {
  const t = useTranslations("common.navigation");

  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6 sm:px-8">
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink
                render={<Link href={ROUTES.home} />}
                className="text-muted-foreground transition-colors hover:text-primary"
              >
                {t("home")}
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              {isLoading ? (
                <Skeleton className="h-5 w-20" />
              ) : (
                <BreadcrumbPage className="font-medium text-foreground">
                  {currentPageLabel}
                </BreadcrumbPage>
              )}
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
        <Link
          href={ROUTES.home}
          aria-label={t("home")}
          className="flex items-center transition-opacity hover:opacity-80"
        >
          <Image
            src="/icon.png"
            alt=""
            width={24}
            height={24}
            className="size-6 object-contain dark:invert"
          />
        </Link>
      </div>
    </header>
  );
}
