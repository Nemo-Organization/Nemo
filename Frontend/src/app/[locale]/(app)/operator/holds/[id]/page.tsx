import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { DetailSkeleton, getHold, HoldDetailView } from "@/features/operator";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("operator");
  return { title: t("name") };
}

// Await params inside Suspense so the layout shell renders immediately.
async function HoldDetailContent({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const hold = getHold(id); // TODO: fetch from the hold service.
  if (!hold) notFound();

  return <HoldDetailView hold={hold} />;
}

export default function HoldDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <HoldDetailContent params={params} />
    </Suspense>
  );
}