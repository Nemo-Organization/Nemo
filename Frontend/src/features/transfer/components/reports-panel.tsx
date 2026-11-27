"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
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
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { listItemMotion } from "@/lib/motion";
import type {
  AnalysisResult,
  CustomerReport,
  CustomerReportCategory,
  Recipient,
} from "../types/transfer.types";

const selectClass =
  "h-9 w-full border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50";

const CATEGORIES: CustomerReportCategory[] = [
  "phishingMessage",
  "scamRecipient",
  "fraudOrder",
];

export function ReportsPanel({
  recipients,
  reports,
  evidences,
  evidenceId,
  onEvidenceChange,
  onSubmitReport,
}: {
  recipients: Recipient[];
  reports: CustomerReport[];
  evidences: AnalysisResult[];
  evidenceId: string;
  onEvidenceChange: (evidenceId: string) => void;
  onSubmitReport: (payload: {
    recipientId: string;
    category: CustomerReportCategory;
    description: string;
    evidenceId?: string;
  }) => void;
}) {
  const t = useTranslations("transfer.reports");
  const formatDateTime = useDateTimeFormatter();
  const [recipientId, setRecipientId] = useState("");
  const [category, setCategory] = useState<CustomerReportCategory>("phishingMessage");
  const [description, setDescription] = useState("");
  const [errors, setErrors] = useState<{
    recipient?: boolean;
    description?: boolean;
  }>({});

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const nextErrors = {
      recipient: !recipientId,
      description: !description.trim(),
    };
    setErrors(nextErrors);
    if (nextErrors.recipient || nextErrors.description) return;

    onSubmitReport({
      recipientId,
      category,
      description: description.trim(),
      evidenceId: evidenceId || undefined,
    });
    setRecipientId("");
    setDescription("");
    toast.success(t("submittedToast"));
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">{t("createTitle")}</CardTitle>
          <CardDescription>{t("createDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div className="space-y-1.5">
              <label htmlFor="report-recipient" className="text-sm font-medium">
                {t("recipient")}
              </label>
              <select
                id="report-recipient"
                className={selectClass}
                value={recipientId}
                onChange={(e) => {
                  setRecipientId(e.target.value);
                  if (errors.recipient)
                    setErrors((prev) => ({ ...prev, recipient: false }));
                }}
                aria-invalid={errors.recipient}
              >
                <option value="">{t("recipientPlaceholder")}</option>
                {recipients.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} · {r.bankCode} {r.accountNumber}
                  </option>
                ))}
              </select>
              {errors.recipient && (
                <p className="text-xs text-destructive">{t("errors.recipient")}</p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label htmlFor="report-category" className="text-sm font-medium">
                  {t("category")}
                </label>
                <select
                  id="report-category"
                  className={selectClass}
                  value={category}
                  onChange={(e) =>
                    setCategory(e.target.value as CustomerReportCategory)
                  }
                >
                  {CATEGORIES.map((item) => (
                    <option key={item} value={item}>
                      {t(`categories.${item}`)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="report-evidence" className="text-sm font-medium">
                  {t("evidence")}
                </label>
                <select
                  id="report-evidence"
                  className={selectClass}
                  value={evidenceId}
                  onChange={(e) => onEvidenceChange(e.target.value)}
                >
                  <option value="">{t("noEvidence")}</option>
                  {evidences.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      {ev.id} · {ev.verdict}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="report-description" className="text-sm font-medium">
                {t("descriptionLabel")}
              </label>
              <textarea
                id="report-description"
                rows={4}
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  if (errors.description)
                    setErrors((prev) => ({ ...prev, description: false }));
                }}
                placeholder={t("descriptionPlaceholder")}
                aria-invalid={errors.description}
                className="w-full border border-input bg-card p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
              />
              {errors.description && (
                <p className="text-xs text-destructive">{t("errors.description")}</p>
              )}
            </div>

            <Button type="submit">{t("submit")}</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">{t("listTitle")}</CardTitle>
          <CardDescription>{t("listDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {reports.length === 0 && (
            <p className="text-sm text-muted-foreground">{t("empty")}</p>
          )}
          {/* Animate new rows only */}
          <AnimatePresence initial={false}>
            {reports.map((item) => (
              <m.div
                key={item.id}
                layout
                {...listItemMotion}
                className="space-y-2 border p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold">{item.id}</span>
                    <span className="text-xs text-muted-foreground">
                      · {t(`categories.${item.category}`)}
                    </span>
                  </div>
                  <Badge variant="secondary">{t(`status.${item.status}`)}</Badge>
                </div>
                <p className="text-sm font-medium">{item.recipientName}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {item.description}
                </p>
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                  <span>{formatDateTime(item.createdAt)}</span>
                  {item.evidenceId && (
                    <Badge variant="outline" className="font-mono text-[11px]">
                      {item.evidenceId}
                    </Badge>
                  )}
                </div>
              </m.div>
            ))}
          </AnimatePresence>
        </CardContent>
      </Card>
    </div>
  );
}
