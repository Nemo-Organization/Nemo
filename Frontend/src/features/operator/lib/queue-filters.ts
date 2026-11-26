// Multi-select (string[]) column filter for faceted filters.
export function filterByAnyOf(
  row: { getValue: (columnId: string) => unknown },
  columnId: string,
  filterValue: string[],
) {
  return !filterValue?.length || filterValue.includes(String(row.getValue(columnId)));
}
