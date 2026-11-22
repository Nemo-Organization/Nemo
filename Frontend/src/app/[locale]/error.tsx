"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

// Next.js 16 error boundaries receive `retry` (not `reset`).
export default function LocaleError({
  error,
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  const t = useTranslations("common.errors");

  useEffect(() => {
    // TODO: send to an error reporting service (e.g. Sentry).
    console.error(error);
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-4 text-center">
      <h1 className="text-3xl font-semibold tracking-tight">{t("title")}</h1>
      <p className="text-muted-foreground">{t("description")}</p>
      <Button onClick={() => retry()}>{t("retry")}</Button>
    </main>
  );
}
