"use client";

import { useTranslations } from "next-intl";
import {
  type ColumnDef,
  type ReactTable,
  type RowData,
  useTable,
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  dataTableFeatures,
  type DataTableFeatures,
} from "./data-table-features";
import { DataTablePagination } from "./data-table-pagination";

type DataTableProps<TData extends RowData> = {
  columns: ColumnDef<DataTableFeatures, TData>[];
  data: TData[];
  renderToolbar?: (
    table: ReactTable<DataTableFeatures, TData>,
  ) => React.ReactNode;
};

export function DataTable<TData extends RowData>({
  columns,
  data,
  renderToolbar,
}: DataTableProps<TData>) {
  const t = useTranslations("data-table");
  const table = useTable({ features: dataTableFeatures, columns, data });

  return (
    <div className="space-y-4">
      {renderToolbar?.(table)}
      <div className="border bg-card shadow-2xs">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : (
                      <table.FlexRender header={header} />
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      <table.FlexRender cell={cell} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  {t("noResults")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <DataTablePagination table={table} />
    </div>
  );
}
