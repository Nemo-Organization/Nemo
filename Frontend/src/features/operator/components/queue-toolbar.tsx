"use client";

import type { ReactTable, RowData } from "@tanstack/react-table";

import { DataTableFacetedFilter } from "@/components/data-table/data-table-faceted-filter";
import type { FacetedFilterOption } from "@/components/data-table/data-table-faceted-filter";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { DataTableViewOptions } from "@/components/data-table/data-table-view-options";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function QueueToolbar<TData extends RowData>({
  table,
  filterPlaceholder,
  statusTitle,
  statusOptions,
  resetLabel,
}: {
  table: ReactTable<DataTableFeatures, TData>;
  filterPlaceholder: string;
  statusTitle: string;
  statusOptions: FacetedFilterOption[];
  resetLabel: string;
}) {
  const idColumn = table.getColumn("id");
  const isFiltered = table.state.columnFilters.length > 0;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-1 flex-wrap items-center gap-2">
        <Input
          placeholder={filterPlaceholder}
          value={(idColumn?.getFilterValue() as string) ?? ""}
          onChange={(event) => idColumn?.setFilterValue(event.target.value)}
          className="h-8 max-w-xs"
        />
        <DataTableFacetedFilter
          column={table.getColumn("status")}
          title={statusTitle}
          options={statusOptions}
        />
        {isFiltered && (
          <Button variant="ghost" size="sm" onClick={() => table.resetColumnFilters()}>
            {resetLabel}
          </Button>
        )}
      </div>
      <DataTableViewOptions table={table} />
    </div>
  );
}
