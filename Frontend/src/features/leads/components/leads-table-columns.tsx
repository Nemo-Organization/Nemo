"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ColumnDef } from "@tanstack/react-table";

import { buttonVariants } from "@/components/ui/button";
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { endpointLeadsRoute, leadDetailRoute } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { Lead } from "../types/leads.types";
import { LeadRowActions } from "./lead-row-actions";

type ColumnLabelKey = "id" | "endpoint" | "createdAt" | "actions";

/** Column headers are plain functions, so translations need a small component. */
function ColumnLabel({ labelKey }: { labelKey: ColumnLabelKey }) {
  const t = useTranslations("leads.columns");
  return t(labelKey);
}

function CreatedAtCell({ isoDate }: { isoDate: string }) {
  const locale = useLocale();
  return (
    <p className="text-xs tabular-nums">
      {new Date(isoDate).toLocaleString(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "numeric",
        timeZone: "UTC",
      })}
    </p>
  );
}

export const leadsTableColumns: ColumnDef<DataTableFeatures, Lead>[] = [
  {
    accessorKey: "id",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="id" />}
      />
    ),
    cell: ({ row }) => (
      <Link
        href={leadDetailRoute(row.original.id)}
        className={cn(buttonVariants({ size: "sm", variant: "outline" }))}
      >
        {row.original.id}
      </Link>
    ),
  },
  {
    accessorKey: "endpointName",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="endpoint" />}
      />
    ),
    cell: ({ row }) => (
      <Link
        className="underline underline-offset-4 transition-opacity hover:opacity-70"
        href={endpointLeadsRoute(row.original.endpointId)}
      >
        {row.original.endpointName}
      </Link>
    ),
    filterFn: (row, columnId, selectedNames) =>
      (selectedNames as string[]).includes(row.getValue(columnId)),
  },
  {
    accessorKey: "createdAt",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="createdAt" />}
      />
    ),
    cell: ({ row }) => <CreatedAtCell isoDate={row.original.createdAt} />,
  },
  {
    id: "actions",
    header: () => <ColumnLabel labelKey="actions" />,
    cell: ({ row }) => <LeadRowActions leadId={row.original.id} />,
    enableSorting: false,
  },
];
