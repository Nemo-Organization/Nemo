import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { DetailSkeleton, getReport, ReportDetailView } from "@/features/operator";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("operator");
  return { title: t("name") };
}

// Await params inside Suspense so the layout shell renders immediately.
async function ReportDetailContent({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: SearchParams;
}) {
  const { id } = await params;
  const { tab } = await searchParams;
  const report = getReport(id); // TODO: fetch from the report service.
  if (!report) notFound();

  // Pass URL tab to SSR to avoid default-tab flash on reload.
  return (
    <ReportDetailView
      report={report}
      initialTab={typeof tab === "string" ? tab : undefined}
    />
  );
}

export default function ReportDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: SearchParams;
}) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <ReportDetailContent params={params} searchParams={searchParams} />
    </Suspense>
  );
}
