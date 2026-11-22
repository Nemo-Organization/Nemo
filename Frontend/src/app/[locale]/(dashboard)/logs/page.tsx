import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { LogsView } from "@/features/logs";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("logs");
  return { title: t("name") };
}

export default function LogsPage() {
  return <LogsView />;
}
