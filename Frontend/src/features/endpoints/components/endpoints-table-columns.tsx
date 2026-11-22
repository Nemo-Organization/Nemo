"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { endpointLeadsRoute } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import type { EndpointItem, EndpointStatus } from "../types/endpoints.types";
import { EndpointRowActions } from "./endpoint-row-actions";

type ColumnLabelKey =
  | "name"
  | "url"
  | "status"
  | "leadsCount"
  | "errorRate"
  | "createdAt"
  | "actions";

function ColumnLabel({ labelKey }: { labelKey: ColumnLabelKey }) {
  const t = useTranslations("endpoints.columns");
  return t(labelKey);
}

function StatusBadge({ status }: { status: EndpointStatus }) {
  const t = useTranslations("endpoints.status");
  return (
    <Badge
      variant={status === "active" ? "secondary" : "outline"}
      className={
        status === "active"
          ? "border border-primary/25 text-primary"
          : "text-muted-foreground"
      }
    >
      {t(status)}
    </Badge>
  );
}

function CreatedAtCell({ isoDate }: { isoDate: string }) {
  const locale = useLocale();
  return (
    <p className="text-xs tabular-nums text-muted-foreground">
      {new Date(isoDate).toLocaleDateString(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      })}
    </p>
  );
}

export const endpointsTableColumns: ColumnDef<
  DataTableFeatures,
  EndpointItem
>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="name" />}
      />
    ),
    cell: ({ row }) => (
      <div className="space-y-0.5">
        <Link
          href={endpointLeadsRoute(row.original.id)}
          className="font-medium text-foreground underline-offset-4 hover:text-primary hover:underline"
        >
          {row.original.name}
        </Link>
        <p className="font-mono text-xs text-muted-foreground">
          {row.original.id}
        </p>
      </div>
    ),
  },
  {
    accessorKey: "url",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="url" />}
      />
    ),
    cell: ({ row }) => (
      <code className="text-xs text-muted-foreground">{row.original.url}</code>
    ),
  },
  {
    accessorKey: "status",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="status" />}
      />
    ),
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
    filterFn: (row, columnId, selectedStatuses) =>
      (selectedStatuses as string[]).includes(row.getValue(columnId)),
  },
  {
    accessorKey: "leadsCount",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="leadsCount" />}
      />
    ),
    cell: ({ row }) => (
      <span className="font-medium tabular-nums">
        {row.original.leadsCount.toLocaleString("en-US")}
      </span>
    ),
  },
  {
    accessorKey: "errorRate",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="errorRate" />}
      />
    ),
    cell: ({ row }) => (
      <span className="text-xs tabular-nums text-muted-foreground">
        {row.original.errorRate.toFixed(1)}%
      </span>
    ),
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
    cell: ({ row }) => <EndpointRowActions endpoint={row.original} />,
    enableSorting: false,
  },
];
