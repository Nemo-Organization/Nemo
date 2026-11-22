import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { LeadsView } from "@/features/leads";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("leads");
  return { title: t("name") };
}

export default function LeadsPage() {
  return <LeadsView />;
}
