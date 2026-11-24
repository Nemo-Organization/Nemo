import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { HomeView } from "@/features/home";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("home");
  return { title: t("name") };
}

export default function HomePage() {
  return <HomeView />;
}
