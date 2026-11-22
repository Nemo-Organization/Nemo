"use client";

import { DataTable } from "@/components/data-table/data-table";
import type { Endpoint, Lead } from "../types/leads.types";
import { leadsTableColumns } from "./leads-table-columns";
import { LeadsTableToolbar } from "./leads-table-toolbar";

export function LeadsTable({
  leads,
  endpoints,
}: {
  leads: Lead[];
  endpoints: Endpoint[];
}) {
  return (
    <DataTable
      columns={leadsTableColumns}
      data={leads}
      renderToolbar={(table) => (
        <LeadsTableToolbar table={table} endpoints={endpoints} />
      )}
    />
  );
}
