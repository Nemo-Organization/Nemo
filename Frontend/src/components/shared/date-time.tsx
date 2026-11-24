"use client";

import { useDateTimeFormatter } from "@/hooks/use-date-formatter";

export function DateTime({
  iso,
  className,
}: {
  iso: string;
  className?: string;
}) {
  const format = useDateTimeFormatter();
  return (
    <time dateTime={iso} className={className}>
      {format(iso)}
    </time>
  );
}
