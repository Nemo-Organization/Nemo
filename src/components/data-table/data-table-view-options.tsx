"use client";

import { useTranslations } from "next-intl";
import { SlidersHorizontalIcon } from "@phosphor-icons/react/ssr";
import type { ReactTable, RowData } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { DataTableFeatures } from "./data-table-features";

export function DataTableViewOptions<TData extends RowData>({
  table,
}: {
  table: ReactTable<DataTableFeatures, TData>;
}) {
  const t = useTranslations("data-table");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={<Button variant="outline" className="hidden lg:flex" />}
      >
        <SlidersHorizontalIcon data-icon="inline-start" />
        {t("view")}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-62.5">
        <DropdownMenuGroup>
          <DropdownMenuLabel>{t("toggleColumns")}</DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        {table
          .getAllColumns()
          .filter(
            (column) =>
              typeof column.accessorFn !== "undefined" && column.getCanHide(),
          )
          .map((column) => (
            <DropdownMenuCheckboxItem
              key={column.id}
              className="capitalize"
              checked={column.getIsVisible()}
              onCheckedChange={(isVisible) =>
                column.toggleVisibility(!!isVisible)
              }
            >
              {column.id}
            </DropdownMenuCheckboxItem>
          ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
