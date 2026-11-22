"use client";

import { useTranslations } from "next-intl";
import { XIcon } from "@phosphor-icons/react/ssr";
import type { ReactTable } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTableFacetedFilter } from "@/components/data-table/data-table-faceted-filter";
import type { DataTableFeatures } from "@/components/data-table/data-table-features";
import { DataTableViewOptions } from "@/components/data-table/data-table-view-options";
import type { Endpoint, Lead } from "../types/leads.types";

export function LeadsTableToolbar({
  table,
  endpoints,
}: {
  table: ReactTable<DataTableFeatures, Lead>;
  endpoints: Endpoint[];
}) {
  const t = useTranslations("leads.toolbar");
  const endpointOptions = endpoints.map((endpoint) => ({
    value: endpoint.name,
    label: endpoint.name,
  }));
  const hasActiveFilters = table.state.columnFilters.length > 0;

  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-1 items-center gap-2">
        <Input
          placeholder={t("filterPlaceholder")}
          value={(table.getColumn("id")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("id")?.setFilterValue(event.target.value)
          }
          className="h-8 w-37.5 lg:w-62.5"
        />
        {table.getColumn("endpointName") && (
          <DataTableFacetedFilter
            column={table.getColumn("endpointName")}
            title={t("endpoints")}
            options={endpointOptions}
          />
        )}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            onClick={() => table.resetColumnFilters()}
            className="h-8 px-2 lg:px-3"
          >
            {t("reset")}
            <XIcon data-icon="inline-end" />
          </Button>
        )}
      </div>
      <DataTableViewOptions table={table} />
    </div>
  );
}
