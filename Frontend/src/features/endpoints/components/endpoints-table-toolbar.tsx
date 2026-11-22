"use client";

import { useTranslations } from "next-intl";
import { XIcon } from "@phosphor-icons/react/ssr";
import type { ReactTable } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTableFacetedFilter } from "@/components/data-table/data-table-faceted-filter";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { DataTableViewOptions } from "@/components/data-table/data-table-view-options";
import type { EndpointItem } from "../types/endpoints.types";

export function EndpointsTableToolbar({
  table,
}: {
  table: ReactTable<DataTableFeatures, EndpointItem>;
}) {
  const t = useTranslations("endpoints");
  const statusOptions = [
    { value: "active", label: t("status.active") },
    { value: "paused", label: t("status.paused") },
  ];
  const hasActiveFilters = table.state.columnFilters.length > 0;

  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-1 items-center gap-2">
        <Input
          placeholder={t("toolbar.filterPlaceholder")}
          value={(table.getColumn("name")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("name")?.setFilterValue(event.target.value)
          }
          className="h-8 w-37.5 lg:w-62.5"
        />
        {table.getColumn("status") && (
          <DataTableFacetedFilter
            column={table.getColumn("status")}
            title={t("toolbar.status")}
            options={statusOptions}
          />
        )}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            onClick={() => table.resetColumnFilters()}
            className="h-8 px-2 lg:px-3"
          >
            {t("toolbar.reset")}
            <XIcon data-icon="inline-end" />
          </Button>
        )}
      </div>
      <DataTableViewOptions table={table} />
    </div>
  );
}
