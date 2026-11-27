"use client";

import { useTranslations } from "next-intl";

import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { cn } from "@/lib/utils";
import type {
  BehaviorSignalLevel,
  HoldSignals,
  RecipientSignalLevel,
} from "../types/operator.types";

type Tone = { box: string; code: string };

const TONE = {
  danger: { box: "border-destructive/30 bg-destructive/5", code: "text-destructive" },
  warn: { box: "border-amber-500/40 bg-amber-500/5", code: "text-amber-700 dark:text-amber-400" },
  muted: { box: "border-border bg-muted/60", code: "text-muted-foreground" },
} satisfies Record<string, Tone>;

const RECIPIENT_TONE: Record<RecipientSignalLevel, Tone> = {
  HOLD: TONE.danger,
  WARN: TONE.warn,
  NONE: TONE.muted,
};

const BEHAVIOR_TONE: Record<BehaviorSignalLevel, Tone> = {
  WARN: TONE.warn,
  NONE: TONE.muted,
  INSUFFICIENT_HISTORY: TONE.muted,
};

function SignalBox({
  title,
  code,
  tone,
  summary,
  note,
}: {
  title: string;
  code: string;
  tone: Tone;
  summary: string;
  note?: string;
}) {
  return (
    <div className={cn("space-y-1.5 border p-4 text-sm", tone.box)}>
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium">{title}</p>
        <span className={cn("font-mono text-xs font-semibold", tone.code)}>{code}</span>
      </div>
      <p>{summary}</p>
      {note && <p className="text-xs text-muted-foreground">{note}</p>}
    </div>
  );
}

// Recipient and behavior signals are assessed independently at hold time.
export function HoldSignalBoxes({ signals }: { signals: HoldSignals }) {
  const t = useTranslations("operator.holds.signals");
  const formatDateTime = useDateTimeFormatter();
  const { recipient, behavior } = signals;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <SignalBox
        title={t("recipient")}
        code={recipient.level}
        tone={RECIPIENT_TONE[recipient.level]}
        summary={recipient.summary}
        note={
          recipient.source &&
          t("recipientSource", {
            reports: recipient.source.reportIds.join(", "),
            date: formatDateTime(recipient.source.restrictedAt, { dateStyle: "medium" }),
          })
        }
      />
      <SignalBox
        title={t("behavior")}
        code={behavior.level}
        tone={BEHAVIOR_TONE[behavior.level]}
        summary={behavior.summary}
        note={behavior.note}
      />
    </div>
  );
}
