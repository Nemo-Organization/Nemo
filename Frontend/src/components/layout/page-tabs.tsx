"use client";

import type { Icon as PhosphorIcon } from "@phosphor-icons/react";

import { TabsIndicator, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type PageTabItem<T extends string> = {
  value: T;
  label: string;
  icon: PhosphorIcon;
};

// Full-width sliding tab bar (horizontal scroll on narrow screens).
export function PageTabsList<T extends string>({
  items,
  active,
  label,
}: {
  items: PageTabItem<T>[];
  active: T;
  label: string;
}) {
  return (
    <TabsList
      aria-label={label}
      className="flex h-auto w-full justify-start gap-1 overflow-x-auto border border-border bg-muted/60 p-1 group-data-horizontal/tabs:h-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      <TabsIndicator renderBeforeHydration className="bg-primary shadow-sm" />
      {items.map(({ value, label: itemLabel, icon: TabIcon }) => (
        <TabsTrigger
          key={value}
          value={value}
          className="h-9 gap-2 px-3 text-xs font-medium text-muted-foreground transition-colors duration-300 not-data-active:hover:bg-background/70 data-active:bg-transparent data-active:text-primary-foreground data-active:hover:text-primary-foreground dark:data-active:border-transparent dark:data-active:bg-transparent dark:data-active:text-primary-foreground dark:data-active:hover:text-primary-foreground"
        >
          <TabIcon
            className="size-4"
            weight={active === value ? "fill" : "regular"}
            aria-hidden
          />
          <span>{itemLabel}</span>
        </TabsTrigger>
      ))}
    </TabsList>
  );
}
