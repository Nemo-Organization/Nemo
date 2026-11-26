import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { OperatorView } from "@/features/operator";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("operator");
  return { title: t("name") };
}

export default function OperatorPage() {
  return <OperatorView />;
}
