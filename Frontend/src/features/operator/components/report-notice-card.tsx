"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  CheckCircleIcon,
  InfoIcon,
  LockSimpleIcon,
  MagnifyingGlassIcon,
} from "@phosphor-icons/react/ssr";
import { AnimatePresence, m } from "motion/react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { fadeMotion } from "@/lib/motion";
import type { NoticeDraft, ReportStatus } from "../types/operator.types";
import { StateBox } from "./state-box";

// Audience from AI trace batch; publishing requires resolved status.
export function ReportNoticeCard({
  notice,
  investigated,
  status,
  published,
  onPublish,
}: {
  notice: NoticeDraft | null;
  investigated: boolean;
  status: ReportStatus;
  published: boolean;
  onPublish: () => void;
}) {
  const t = useTranslations("operator.notice");

  const stateKey = !investigated ? "notInvestigated" : !notice ? "noScope" : "preview";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <AnimatePresence mode="wait" initial={false}>
          {stateKey === "notInvestigated" && (
            <m.div key="notInvestigated" {...fadeMotion}>
              <StateBox
                icon={MagnifyingGlassIcon}
                title={t("notInvestigated.title")}
                hint={t("notInvestigated.hint")}
              />
            </m.div>
          )}
          {stateKey === "noScope" && (
            <m.div key="noScope" {...fadeMotion}>
              <StateBox icon={InfoIcon} title={t("noScope.title")} hint={t("noScope.hint")} />
            </m.div>
          )}
          {stateKey === "preview" && notice && (
            <m.div key="preview" {...fadeMotion} className="space-y-4">
              <NoticePreview
                notice={notice}
                status={status}
                published={published}
                onPublish={onPublish}
              />
            </m.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}

function NoticePreview({
  notice,
  status,
  published,
  onPublish,
}: {
  notice: NoticeDraft;
  status: ReportStatus;
  published: boolean;
  onPublish: () => void;
}) {
  const t = useTranslations("operator.notice");
  const [confirming, setConfirming] = useState(false);
  const count = notice.recipients.length;

  const footerKey = published
    ? "published"
    : status === "dismissed"
      ? "dismissed"
      : status !== "resolved"
        ? "locked"
        : confirming
          ? "confirming"
          : "ready";

  return (
    <>
      <div className="space-y-1 border bg-secondary/45 p-3">
        <p className="text-xs text-muted-foreground">{t("template")}</p>
        <p className="text-sm font-medium">{notice.title}</p>
        <p className="text-sm">{notice.body}</p>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">{t("audience", { count, batch: notice.batch })}</p>
        <ul className="max-h-64 divide-y overflow-y-auto border">
          {notice.recipients.map((entry) => (
            <li
              key={entry.customerId}
              className="flex items-center justify-between gap-3 px-4 py-2 text-sm"
            >
              <span>
                {entry.customerName}
                <span className="ml-2 text-xs text-muted-foreground">{entry.customerId}</span>
              </span>
              <Badge variant="secondary" className="font-mono">
                {entry.orderLabel}
              </Badge>
            </li>
          ))}
        </ul>
        <p className="text-xs text-muted-foreground">
          {t("derivedFrom", { batch: notice.batch })}
        </p>
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <m.div key={footerKey} {...fadeMotion}>
          {footerKey === "published" && (
            <p className="flex items-center gap-2 border border-primary/25 bg-primary/5 p-3 text-sm font-medium">
              <CheckCircleIcon className="size-4 shrink-0 text-primary" aria-hidden />
              {t("published", { count })}
            </p>
          )}
          {footerKey === "locked" && (
            <StateBox icon={LockSimpleIcon} title={t("locked.title")} hint={t("locked.hint")} />
          )}
          {footerKey === "dismissed" && (
            <StateBox
              icon={LockSimpleIcon}
              title={t("dismissed.title")}
              hint={t("dismissed.hint")}
            />
          )}
          {footerKey === "confirming" && (
            <div className="space-y-3 border border-primary/25 bg-primary/5 p-4">
              <p className="text-sm">{t("confirm", { count })}</p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setConfirming(false)}>
                  {t("back")}
                </Button>
                <Button onClick={onPublish}>{t("confirmPublish")}</Button>
              </div>
            </div>
          )}
          {footerKey === "ready" && (
            <Button onClick={() => setConfirming(true)}>{t("publish")}</Button>
          )}
        </m.div>
      </AnimatePresence>
    </>
  );
}
