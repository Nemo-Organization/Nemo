import { useTranslations } from "next-intl";
import { CircleNotchIcon } from "@phosphor-icons/react/ssr";

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
        {/* TODO: replace with the brand icon (public/icon.svg) once provided */}
        <CircleNotchIcon
          className="size-5 text-primary transition-transform duration-500 hover:rotate-180"
          aria-hidden
        />
      </div>
    </header>
  );
}
