"use client";

import { useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { cn } from "@/lib/utils";
import type {
  ActivitySeries,
  DailyActivity,
} from "../types/dashboard.types";

const SERIES_KEYS: ActivitySeries[] = ["leads", "errors"];

export function OverviewChart({
  activity,
  className,
}: {
  activity: DailyActivity[];
  className?: string;
}) {
  const t = useTranslations("dashboard.chart");
  const locale = useLocale();
  const [selectedSeries, setSelectedSeries] = useState<ActivitySeries>("leads");

  const chartConfig = {
    leads: { label: t("leads"), color: "var(--chart-1)" },
    errors: { label: t("errors"), color: "var(--chart-2)" },
  } satisfies ChartConfig;

  const totals = useMemo(
    () => ({
      leads: activity.reduce((sum, day) => sum + day.leads, 0),
      errors: activity.reduce((sum, day) => sum + day.errors, 0),
    }),
    [activity],
  );

  const formatDate = (isoDate: string, withYear = false) =>
    new Date(isoDate).toLocaleDateString(locale, {
      month: "short",
      day: "numeric",
      ...(withYear ? { year: "numeric" } : {}),
      timeZone: "UTC",
    });

  const gradientId = `fill-${selectedSeries}`;

  return (
    <Card className={cn("py-0", className)}>
      <CardHeader className="flex flex-col items-stretch space-y-0 border-b p-0 sm:flex-row">
        <div className="flex flex-1 flex-col justify-center gap-1 px-6 py-5">
          <CardTitle className="text-base font-semibold">
            {t("title")}
          </CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </div>
        <div className="flex">
          {SERIES_KEYS.map((seriesKey) => {
            const isActive = selectedSeries === seriesKey;
            const accentColor =
              seriesKey === "leads" ? "var(--chart-1)" : "var(--chart-2)";

            return (
              <button
                key={seriesKey}
                type="button"
                data-active={isActive}
                style={
                  isActive
                    ? {
                        boxShadow: `inset 0 -2px 0 0 ${accentColor}`,
                        backgroundColor: `color-mix(in oklch, ${accentColor} 7%, transparent)`,
                      }
                    : undefined
                }
                className="flex flex-1 cursor-pointer flex-col justify-center gap-1.5 border-t px-6 py-4 text-left transition-colors even:border-l hover:bg-muted/40 sm:min-w-36 sm:border-t-0 sm:border-l sm:px-7 sm:py-5"
                onClick={() => setSelectedSeries(seriesKey)}
              >
                <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <span
                    className="inline-block size-2 shrink-0"
                    style={{ backgroundColor: accentColor }}
                    aria-hidden
                  />
                  {chartConfig[seriesKey].label}
                </span>
                <span className="text-2xl leading-none font-bold tracking-tight tabular-nums sm:text-3xl">
                  {totals[seriesKey].toLocaleString(locale)}
                </span>
              </button>
            );
          })}
        </div>
      </CardHeader>
      <CardContent className="px-3 py-6 sm:px-6">
        <ChartContainer
          config={chartConfig}
          className="aspect-auto h-64 w-full"
        >
          <AreaChart
            accessibilityLayer
            data={activity}
            margin={{ left: 12, right: 12, top: 8 }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={`var(--color-${selectedSeries})`}
                  stopOpacity={0.28}
                />
                <stop
                  offset="95%"
                  stopColor={`var(--color-${selectedSeries})`}
                  stopOpacity={0.02}
                />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={10}
              minTickGap={32}
              tickFormatter={(isoDate) => formatDate(isoDate)}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  className="w-40"
                  labelFormatter={(isoDate) => formatDate(String(isoDate), true)}
                />
              }
            />
            <Area
              dataKey={selectedSeries}
              type="monotone"
              fill={`url(#${gradientId})`}
              stroke={`var(--color-${selectedSeries})`}
              strokeWidth={2.25}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
