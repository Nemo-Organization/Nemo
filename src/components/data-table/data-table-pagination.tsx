"use client";

import { useTranslations } from "next-intl";
import type { ReactTable, RowData } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import type { DataTableFeatures } from "./data-table-features";

export function DataTablePagination<TData extends RowData>({
  table,
}: {
  table: ReactTable<DataTableFeatures, TData>;
}) {
  const t = useTranslations("data-table");
  const { pageIndex } = table.state.pagination;

  return (
    <div className="flex items-center justify-between px-2">
      <p className="text-xs text-muted-foreground tabular-nums">
        {t("page", {
          page: pageIndex + 1,
          total: Math.max(1, table.getPageCount()),
        })}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          {t("previous")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          {t("next")}
        </Button>
      </div>
    </div>
  );
}
