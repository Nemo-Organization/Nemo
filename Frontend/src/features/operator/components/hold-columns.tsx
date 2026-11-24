"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { DateTime } from "@/components/shared/date-time";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { operatorHoldRoute } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { formatVnd } from "@/lib/format";
import { filterByAnyOf } from "../lib/queue-filters";
import type { HoldItem, HoldStatus } from "../types/operator.types";

type ColumnLabelKey = "id" | "customer" | "amount" | "status" | "deadline" | "actions";

function ColumnLabel({ labelKey }: { labelKey: ColumnLabelKey }) {
  const t = useTranslations("operator.holds.columns");
  return t(labelKey);
}

function AmountCell({ amount }: { amount: number }) {
  const locale = useLocale();
  return <span className="tabular-nums">{formatVnd(amount, locale)}</span>;
}

function StatusCell({ status }: { status: HoldStatus }) {
  const t = useTranslations("operator.holds.status");
  return <Badge variant="secondary">{t(status)}</Badge>;
}

function OpenLink({ holdId }: { holdId: string }) {
  const t = useTranslations("operator.holds");
  return (
    <Link
      href={operatorHoldRoute(holdId)}
      className={buttonVariants({ variant: "outline", size: "sm" })}
    >
      {t("open")}
    </Link>
  );
}

export const holdColumns: ColumnDef<DataTableFeatures, HoldItem>[] = [
  {
    accessorKey: "id",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="id" />} />
    ),
  },
  {
    accessorKey: "customerName",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="customer" />} />
    ),
  },
  {
    accessorKey: "amount",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="amount" />} />
    ),
    cell: ({ row }) => <AmountCell amount={row.original.amount} />,
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
    accessorKey: "deadline",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title={<ColumnLabel labelKey="deadline" />} />
    ),
    cell: ({ row }) => (
      <DateTime iso={row.original.deadline} className="text-xs tabular-nums" />
    ),
  },
  {
    id: "actions",
    header: () => <ColumnLabel labelKey="actions" />,
    cell: ({ row }) => <OpenLink holdId={row.original.id} />,
    enableSorting: false,
  },
];
