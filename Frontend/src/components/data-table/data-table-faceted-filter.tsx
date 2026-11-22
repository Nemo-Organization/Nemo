"use client";

import { useTranslations } from "next-intl";
import { CheckIcon, PlusCircleIcon } from "@phosphor-icons/react/ssr";
import type { Column, RowData } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { DataTableFeatures } from "./data-table-features";

export type FacetedFilterOption = { label: string; value: string };

export function DataTableFacetedFilter<TData extends RowData, TValue>({
  column,
  title,
  options,
}: {
  column?: Column<DataTableFeatures, TData, TValue>;
  title: string;
  options: FacetedFilterOption[];
}) {
  const t = useTranslations("data-table");
  const facetCounts = column?.getFacetedUniqueValues();
  const selectedValues = new Set(
    column?.getFilterValue() as string[] | undefined,
  );

  const toggleOption = (value: string) => {
    if (selectedValues.has(value)) selectedValues.delete(value);
    else selectedValues.add(value);
    const nextValues = Array.from(selectedValues);
    column?.setFilterValue(nextValues.length ? nextValues : undefined);
  };

  return (
    <Popover>
      <PopoverTrigger
        render={<Button variant="outline" size="sm" className="h-8" />}
      >
        <PlusCircleIcon data-icon="inline-start" />
        {title}
        {selectedValues.size > 0 && (
          <Badge variant="secondary" className="ml-1">
            {selectedValues.size}
          </Badge>
        )}
      </PopoverTrigger>
      <PopoverContent className="w-55 p-0" align="start">
        <Command>
          <CommandInput placeholder={title} />
          <CommandList>
            <CommandEmpty>{t("noResults")}</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                const isSelected = selectedValues.has(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    onSelect={() => toggleOption(option.value)}
                  >
                    <CheckIcon
                      className={cn(
                        "mr-2",
                        isSelected ? "opacity-100" : "opacity-0",
                      )}
                    />
                    <span>{option.label}</span>
                    {facetCounts?.get(option.value) ? (
                      <span className="ml-auto text-xs tabular-nums">
                        {facetCounts.get(option.value)}
                      </span>
                    ) : null}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            {selectedValues.size > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    onSelect={() => column?.setFilterValue(undefined)}
                    className="justify-center text-center"
                  >
                    {t("clearFilters")}
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
