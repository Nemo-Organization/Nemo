"use client";

import { useTranslations } from "next-intl";
import { XIcon } from "@phosphor-icons/react/ssr";
import type { ReactTable } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTableFacetedFilter } from "@/components/data-table/data-table-faceted-filter";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { DataTableViewOptions } from "@/components/data-table/data-table-view-options";
import type { ApiLog } from "../types/logs.types";

export function LogsTableToolbar({
  table,
  endpointNames,
}: {
  table: ReactTable<DataTableFeatures, ApiLog>;
  endpointNames: string[];
}) {
  const t = useTranslations("logs");
  const levelOptions = [
    { value: "success", label: t("level.success") },
    { value: "warning", label: t("level.warning") },
    { value: "error", label: t("level.error") },
  ];
  const endpointOptions = endpointNames.map((name) => ({
    value: name,
    label: name,
  }));
  const hasActiveFilters = table.state.columnFilters.length > 0;

  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-1 items-center gap-2">
        <Input
          placeholder={t("toolbar.filterPlaceholder")}
          value={(table.getColumn("message")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("message")?.setFilterValue(event.target.value)
          }
          className="h-8 w-37.5 lg:w-62.5"
        />
        {table.getColumn("level") && (
          <DataTableFacetedFilter
            column={table.getColumn("level")}
            title={t("toolbar.level")}
            options={levelOptions}
          />
        )}
        {table.getColumn("endpointName") && (
          <DataTableFacetedFilter
            column={table.getColumn("endpointName")}
            title={t("toolbar.endpoints")}
            options={endpointOptions}
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
