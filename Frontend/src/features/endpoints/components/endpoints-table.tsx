"use client";

import { DataTable } from "@/components/data-table/data-table";
import type { EndpointItem } from "../types/endpoints.types";
import { endpointsTableColumns } from "./endpoints-table-columns";
import { EndpointsTableToolbar } from "./endpoints-table-toolbar";

export function EndpointsTable({ endpoints }: { endpoints: EndpointItem[] }) {
  return (
    <DataTable
      columns={endpointsTableColumns}
      data={endpoints}
      renderToolbar={(table) => <EndpointsTableToolbar table={table} />}
    />
  );
}
