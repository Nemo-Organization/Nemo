"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { endpointLeadsRoute } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { ApiLog, LogLevel } from "../types/logs.types";

type ColumnLabelKey =
  | "id"
  | "endpoint"
  | "status"
  | "level"
  | "latency"
  | "message"
  | "createdAt";

function ColumnLabel({ labelKey }: { labelKey: ColumnLabelKey }) {
  const t = useTranslations("logs.columns");
  return t(labelKey);
}

const LEVEL_STYLES: Record<LogLevel, string> = {
  success: "border border-primary/25 bg-secondary text-primary",
  warning: "border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  error: "border border-destructive/30 bg-destructive/10 text-destructive",
};

function LevelBadge({ level }: { level: LogLevel }) {
  const t = useTranslations("logs.level");
  return (
    <Badge variant="outline" className={cn("font-medium", LEVEL_STYLES[level])}>
      {t(level)}
    </Badge>
  );
}

function CreatedAtCell({ isoDate }: { isoDate: string }) {
  const locale = useLocale();
  return (
    <p className="text-xs tabular-nums text-muted-foreground">
      {new Date(isoDate).toLocaleString(locale, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: "UTC",
      })}
    </p>
  );
}

export const logsTableColumns: ColumnDef<DataTableFeatures, ApiLog>[] = [
  {
    accessorKey: "id",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="id" />}
      />
    ),
    cell: ({ row }) => (
      <code className="text-xs font-medium text-foreground">
        {row.original.id}
      </code>
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
        href={endpointLeadsRoute(row.original.endpointId)}
        className="underline underline-offset-4 transition-opacity hover:opacity-70"
      >
        {row.original.endpointName}
      </Link>
    ),
    filterFn: (row, columnId, selectedNames) =>
      (selectedNames as string[]).includes(row.getValue(columnId)),
  },
  {
    accessorKey: "statusCode",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="status" />}
      />
    ),
    cell: ({ row }) => (
      <span className="font-mono text-xs tabular-nums">
        {row.original.method} {row.original.statusCode}
      </span>
    ),
  },
  {
    accessorKey: "level",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="level" />}
      />
    ),
    cell: ({ row }) => <LevelBadge level={row.original.level} />,
    filterFn: (row, columnId, selectedLevels) =>
      (selectedLevels as string[]).includes(row.getValue(columnId)),
  },
  {
    accessorKey: "latencyMs",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title={<ColumnLabel labelKey="latency" />}
      />
    ),
    cell: ({ row }) => (
      <span className="font-mono text-xs tabular-nums text-muted-foreground">
        {row.original.latencyMs}ms
      </span>
    ),
  },
  {
    accessorKey: "message",
    header: () => <ColumnLabel labelKey="message" />,
    cell: ({ row }) => (
      <span className="block max-w-xs truncate text-xs text-muted-foreground">
        {row.original.message}
      </span>
    ),
    enableSorting: false,
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
];
