import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { ROUTES } from "@/config/routes";
import { Link } from "@/i18n/navigation";

export default function LocaleNotFound() {
  const t = useTranslations("common.notFound");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-4 text-center">
      <h1 className="text-3xl font-semibold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground">{t("description")}</p>
      <Link href={ROUTES.home} className={buttonVariants()}>
        {t("backHome")}
      </Link>
    </main>
  );
}
