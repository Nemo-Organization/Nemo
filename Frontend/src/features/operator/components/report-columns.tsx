"use client";

import { useTranslations } from "next-intl";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { DateTime } from "@/components/shared/date-time";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { operatorReportRoute } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { filterByAnyOf } from "../lib/queue-filters";
import type {
  Priority,
  ReportItem,
  ReportStatus,
  ReportType,
} from "../types/operator.types";

type ColumnLabelKey = "id" | "type" | "status" | "priority" | "createdAt" | "actions";

function ColumnLabel({ labelKey }: { labelKey: ColumnLabelKey }) {
  const t = useTranslations("operator.reports.columns");
  return t(labelKey);
}

function TypeCell({ type }: { type: ReportType }) {
  const t = useTranslations("operator.reports.type");
  return t(type);
}

function StatusCell({ status }: { status: ReportStatus }) {
  const t = useTranslations("operator.reports.status");
  return <Badge variant="secondary">{t(status)}</Badge>;
}

function PriorityCell({ priority }: { priority: Priority }) {
  const t = useTranslations("operator.reports.priority");
  return t(priority);
}

function OpenLink({ reportId }: { reportId: string }) {
  const t = useTranslations("operator.reports");
  return (
    <Link
      href={operatorReportRoute(reportId)}
      className={buttonVariants({ variant: "outline", size: "sm" })}
    >
      {t("open")}
    </Link>
  );
}

export const reportColumns: ColumnDef<DataTableFeatures, ReportItem>[] = [
  {
    accessorKey: "id",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="id" />} />
    ),
  },
  {
    accessorKey: "type",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="type" />} />
    ),
    cell: ({ row }) => <TypeCell type={row.original.type} />,
  },
  {
    accessorKey: "status",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="status" />} />
    ),
    cell: ({ row }) => <StatusCell status={row.original.status} />,
    filterFn: filterByAnyOf,
  },
  {
    accessorKey: "priority",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="priority" />} />
    ),
    cell: ({ row }) => <PriorityCell priority={row.original.priority} />,
  },
  {
    accessorKey: "createdAt",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="createdAt" />} />
    ),
    cell: ({ row }) => (
      <DateTime iso={row.original.createdAt} className="text-xs tabular-nums" />
    ),
  },
  {
    id: "actions",
    header: () => <ColumnLabel labelKey="actions" />,
    cell: ({ row }) => <OpenLink reportId={row.original.id} />,
    enableSorting: false,
  },
];
