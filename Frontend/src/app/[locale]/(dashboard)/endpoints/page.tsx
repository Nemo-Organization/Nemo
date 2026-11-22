import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { EndpointsView } from "@/features/endpoints";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("endpoints");
  return { title: t("name") };
}

export default function EndpointsPage() {
  return <EndpointsView />;
}
