"use client";

import {
  CaretDownIcon,
  CaretUpDownIcon,
  CaretUpIcon,
} from "@phosphor-icons/react/ssr";
import type { Column, RowData } from "@tanstack/react-table";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { DataTableFeatures } from "./data-table-features";

export function DataTableColumnHeader<TData extends RowData, TValue>({
  column,
  title,
  className,
}: {
  column: Column<DataTableFeatures, TData, TValue>;
  title: React.ReactNode;
  className?: string;
}) {
  if (!column.getCanSort()) {
    return <div className={cn(className)}>{title}</div>;
  }

  const sortDirection = column.getIsSorted();

  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn("-ml-3 h-8", className)}
      onClick={() => column.toggleSorting(sortDirection === "asc")}
    >
      <span>{title}</span>
      {sortDirection === "desc" ? (
        <CaretDownIcon />
      ) : sortDirection === "asc" ? (
        <CaretUpIcon />
      ) : (
        <CaretUpDownIcon />
      )}
    </Button>
  );
}
