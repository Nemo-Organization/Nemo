"use client";

import { DataTable } from "@/components/data-table/data-table";
import type { ApiLog } from "../types/logs.types";
import { logsTableColumns } from "./logs-table-columns";
import { LogsTableToolbar } from "./logs-table-toolbar";

export function LogsTable({ logs }: { logs: ApiLog[] }) {
  const endpointNames = Array.from(
    new Set(logs.map((log) => log.endpointName)),
  ).sort();

  return (
    <DataTable
      columns={logsTableColumns}
      data={logs}
      renderToolbar={(table) => (
        <LogsTableToolbar table={table} endpointNames={endpointNames} />
      )}
    />
  );
}
