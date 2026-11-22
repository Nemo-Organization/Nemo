"use client";

import { useTranslations } from "next-intl";

import { useTemplateItems } from "../hooks/use-template-items";

export function TemplateList() {
  // TODO: create i18n files `template.json` (en + vi) and use that namespace.
  const t = useTranslations("template");
  const { items, isLoading } = useTemplateItems();

  // TODO: render a skeleton / empty state.
  if (isLoading) return null;

  // TODO: build the real UI with components from `@/components/ui` and `@/components/layout`.
  return (
    <section aria-label={t("title")}>
      <h2>{t("title")}</h2>
      <ul>
        {items.map((item) => (
          <li key={item.id}>{item.name}</li>
        ))}
      </ul>
    </section>
  );
}
