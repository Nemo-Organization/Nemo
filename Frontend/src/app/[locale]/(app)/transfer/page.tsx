import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { TransferView } from "@/features/transfer";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("transfer");
  return { title: t("name") };
}

export default function TransferPage() {
  return <TransferView />;
}
