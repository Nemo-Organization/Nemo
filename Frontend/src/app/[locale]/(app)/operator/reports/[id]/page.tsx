import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { DetailSkeleton, getReport, ReportDetailView } from "@/features/operator";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("operator");
  return { title: t("name") };
}

// Await params inside Suspense so the layout shell renders immediately.
async function ReportDetailContent({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const report = getReport(id); // TODO: fetch from the report service.
  if (!report) notFound();

  return <ReportDetailView report={report} />;
}

export default function ReportDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <ReportDetailContent params={params} />
    </Suspense>
  );
}