"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  CaretRightIcon,
  CircleNotchIcon,
  InfoIcon,
  UsersIcon,
  WarningIcon,
} from "@phosphor-icons/react/ssr";
import { AnimatePresence, m } from "motion/react";

import { Collapse } from "@/components/motion/collapse";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { cardVariants, fadeMotion, itemVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import {
  INVESTIGATION_LIMITS,
  OPS_INVESTIGATION_TOOLS,
} from "../constants/operator.constants";
import type {
  FindingRelation,
  InvestigationActivity,
  InvestigationRun,
  TraceResult,
  TraceStatus,
} from "../types/operator.types";
import { ReportStatusBadge } from "./report-status-badge";

const SECTION_TITLE = "text-xs font-semibold uppercase tracking-wide text-muted-foreground";

const RELATION_TONE: Record<FindingRelation, string> = {
  supportsConcern: "border-destructive/40 bg-destructive/10 text-destructive",
  countersConcern: "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-400",
  unresolved: "border-border bg-muted text-muted-foreground",
};

const TRACE_TONE: Record<TraceStatus, string> = {
  MATCHED_SCOPE: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  NO_MATCH: "border-border bg-muted text-muted-foreground",
  NO_REFERENCE: "border-border bg-muted text-muted-foreground",
};

const ACTIVITY_TONE: Record<InvestigationActivity["status"], string> = {
  SUCCEEDED: "border-primary/40 bg-primary/10 text-primary",
  NOT_FOUND: "border-border bg-muted text-muted-foreground",
  DENIED: "border-destructive/40 bg-destructive/10 text-destructive",
  UNAVAILABLE: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
};

export function InvestigationCard({
  run,
  running,
  onRun,
}: {
  run: InvestigationRun | null;
  running: boolean;
  onRun: () => void;
}) {
  const t = useTranslations("operator.investigation");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Skip animation when restoring result on tab switch */}
        <AnimatePresence mode="wait" initial={false}>
          {running ? (
            <m.div key="running" {...fadeMotion} className="space-y-3" aria-live="polite">
              <div className="flex items-center gap-2 border bg-secondary/40 p-3 text-sm text-muted-foreground">
                <CircleNotchIcon className="size-4 shrink-0 animate-spin" aria-hidden />
                {t("runningHint")}
              </div>
              <Skeleton className="h-16" />
              <Skeleton className="h-24" />
            </m.div>
          ) : run ? (
            <m.div
              key={run.runId}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="space-y-5"
            >
              <InvestigationResultView run={run} />
            </m.div>
          ) : (
            <m.div
              key="idle"
              {...fadeMotion}
              className="space-y-1.5 border bg-secondary/40 p-3 text-xs text-muted-foreground"
            >
              <p>
                {t("allowedTools")}{" "}
                <span className="font-mono">{OPS_INVESTIGATION_TOOLS.join(" · ")}</span>
              </p>
              <p>
                {t("limits", {
                  seconds: INVESTIGATION_LIMITS.seconds,
                  models: INVESTIGATION_LIMITS.modelCalls,
                  tools: INVESTIGATION_LIMITS.toolCalls,
                })}
              </p>
            </m.div>
          )}
        </AnimatePresence>

        <div className="flex flex-wrap items-center gap-3 border-t pt-4">
          <Button variant={run ? "outline" : "default"} disabled={running} onClick={onRun}>
            {running && (
              <CircleNotchIcon data-icon="inline-start" className="animate-spin" aria-hidden />
            )}
            {running ? t("running") : run ? t("rerun") : t("run")}
          </Button>
          {run && !running && (
            <p className="text-xs text-muted-foreground">{t("rerunHint")}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function InvestigationResultView({ run }: { run: InvestigationRun }) {
  const t = useTranslations("operator.investigation");
  const formatDateTime = useDateTimeFormatter();
  const [showActivity, setShowActivity] = useState(false);

  return (
    <>
      <m.div
        variants={itemVariants}
        className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground"
      >
        <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary">
          SUCCEEDED
        </Badge>
        <span className="tabular-nums">
          {t("usage", {
            models: run.modelCalls,
            maxModels: INVESTIGATION_LIMITS.modelCalls,
            tools: run.toolCalls,
            maxTools: INVESTIGATION_LIMITS.toolCalls,
          })}
        </span>
        <span>· {formatDateTime(run.ranAt)}</span>
      </m.div>

      <m.section variants={itemVariants} className="space-y-2">
        <h3 className={SECTION_TITLE}>{t("findings.title")}</h3>
        {run.findings.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("findings.empty")}</p>
        ) : (
          <ul className="space-y-2">
            {run.findings.map((finding) => (
              <li key={finding.id} className="flex items-start gap-3 border p-3">
                <Badge
                  variant="outline"
                  className={cn("shrink-0", RELATION_TONE[finding.relation])}
                >
                  {t(`relation.${finding.relation}`)}
                </Badge>
                <div className="min-w-0 space-y-1">
                  <p className="text-sm">{finding.statement}</p>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                    <span>{t("findings.sources")}</span>
                    {finding.sources.map((source) => (
                      <span key={source.id} className="font-mono">
                        {source.id} · {source.kind.replaceAll("_", " ")}
                      </span>
                    ))}
                    {finding.signal && (
                      <Badge variant="outline" className="text-[11px]">
                        {t(`signal.${finding.signal}`)}
                      </Badge>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </m.section>

      <m.section variants={itemVariants} className="space-y-2">
        <h3 className={SECTION_TITLE}>
          {t("related.title", { count: run.relatedReports.length })}
        </h3>
        {run.relatedReports.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("related.empty")}</p>
        ) : (
          <>
            <ul className="divide-y border">
              {run.relatedReports.map((item) => (
                <li
                  key={item.id}
                  className="flex items-start justify-between gap-3 px-3 py-2.5 text-sm"
                >
                  <p>
                    <span className="font-mono text-xs font-semibold">{item.id}</span>
                    <span className="text-muted-foreground"> · </span>
                    {item.summary}
                  </p>
                  <ReportStatusBadge status={item.status} withLabel={false} />
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground">{t("related.note")}</p>
          </>
        )}
      </m.section>

      <m.section variants={itemVariants} className="space-y-3">
        <h3 className={SECTION_TITLE}>{t("trace.title")}</h3>
        <TraceView trace={run.trace} />
      </m.section>

      {run.recommendedChecks.length > 0 && (
        <m.section variants={itemVariants} className="space-y-2">
          <h3 className={SECTION_TITLE}>{t("checks")}</h3>
          <ol className="list-decimal space-y-1 border bg-secondary/40 py-3 pr-3 pl-8 text-sm">
            {run.recommendedChecks.map((check) => (
              <li key={check}>{check}</li>
            ))}
          </ol>
        </m.section>
      )}

      {run.missingInformation.length > 0 && (
        <m.section variants={itemVariants} className="space-y-2">
          <h3 className={SECTION_TITLE}>{t("missing")}</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {run.missingInformation.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </m.section>
      )}

      {run.limitations.length > 0 && (
        <m.section
          variants={itemVariants}
          className="space-y-1.5 border border-sky-500/30 bg-sky-500/5 p-3"
        >
          <p className="flex items-center gap-1.5 text-xs font-semibold text-sky-700 dark:text-sky-400">
            <InfoIcon className="size-4" aria-hidden />
            {t("limitations")}
          </p>
          <ul className="list-disc space-y-1 pl-5 text-xs">
            {run.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </m.section>
      )}

      {run.activity.length > 0 && (
        <m.section variants={itemVariants}>
          <button
            type="button"
            onClick={() => setShowActivity((value) => !value)}
            aria-expanded={showActivity}
            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <CaretRightIcon
              className={cn(
                "size-3.5 transition-transform duration-200",
                showActivity && "rotate-90",
              )}
              aria-hidden
            />
            {t("activity", { count: run.activity.length })}
          </button>
          <AnimatePresence initial={false}>
            {showActivity && (
              <Collapse key="activity">
                <ol className="space-y-1.5 pt-2.5">
                  {run.activity.map((item) => (
                    <li key={item.step} className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="tabular-nums text-muted-foreground">{item.step}.</span>
                      <span className="font-mono">{item.tool}</span>
                      <Badge variant="outline" className={ACTIVITY_TONE[item.status]}>
                        {item.status}
                      </Badge>
                      <span className="text-muted-foreground">{item.summary}</span>
                    </li>
                  ))}
                </ol>
              </Collapse>
            )}
          </AnimatePresence>
        </m.section>
      )}

      {run.citationWarningCount > 0 && (
        <m.p
          variants={itemVariants}
          className="flex items-center gap-2 border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-400"
        >
          <WarningIcon className="size-4 shrink-0" aria-hidden />
          {t("citationWarnings", { count: run.citationWarningCount })}
        </m.p>
      )}
    </>
  );
}

function TraceView({ trace }: { trace: TraceResult }) {
  const t = useTranslations("operator.investigation.trace");
  const formatDateTime = useDateTimeFormatter();

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline" className={TRACE_TONE[trace.status]}>
          {trace.status}
        </Badge>
        <span>{t(`status.${trace.status}`, { count: trace.references.length })}</span>
      </div>

      {trace.references.map((ref) => (
        <div key={ref.code} className="space-y-3 border p-4">
          <div className="flex items-center justify-between gap-2">
            <p className="font-mono text-sm font-semibold">{ref.code}</p>
            <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary">
              {t("exact")}
            </Badge>
          </div>
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-muted-foreground">{t("batch")}</dt>
              <dd className="font-mono">{ref.batch}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{t("partner")}</dt>
              <dd className="font-mono">{ref.partner}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{t("issuedAt")}</dt>
              <dd>{formatDateTime(ref.issuedAt)}</dd>
            </div>
          </dl>
        </div>
      ))}

      {trace.batch && (
        <>
          <div className="space-y-2 border p-4">
            <p className="text-sm font-medium">{t("access", { batch: trace.batch })}</p>
            {trace.accessEvents.length === 0 ? (
              <p className="text-xs text-muted-foreground">{t("noAccess")}</p>
            ) : (
              <ul className="space-y-1.5">
                {trace.accessEvents.map((event) => (
                  <li key={event.id} className="flex flex-wrap items-center gap-2 text-xs">
                    <Badge variant="secondary" className="font-mono">
                      {event.action}
                    </Badge>
                    <span className="text-muted-foreground">
                      {event.partner} · {formatDateTime(event.occurredAt)}
                      {event.beforeReport && ` · ${t("beforeReport")}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <p className="flex items-center gap-2 text-sm">
            <UsersIcon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            {t("candidates", { count: trace.candidateCustomerCount, batch: trace.batch })}
          </p>
        </>
      )}
    </>
  );
}
