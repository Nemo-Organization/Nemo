"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { SparkleIcon, UploadSimpleIcon, XIcon } from "@phosphor-icons/react/ssr";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { mockSampleSuspiciousText } from "../mocks/transfer.mock";
import type { Draft, Order } from "../types/transfer.types";

const selectClass =
  "h-9 w-full border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50";

export function ScreenshotAnalysis({
  drafts,
  orders,
  onAnalyze,
}: {
  drafts: Draft[];
  orders: Order[];
  onAnalyze: (payload: {
    fileName?: string;
    text: string;
    draftId: string;
    orderId: string;
  }) => void;
}) {
  const t = useTranslations("transfer.screenshot");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [draftId, setDraftId] = useState("");
  const [orderId, setOrderId] = useState("");

  const canAnalyze = Boolean(file) || text.trim().length > 0;

  const handleClearFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFillSample = () => {
    setText(mockSampleSuspiciousText);
    if (orders[1]) setOrderId(orders[1].id);
    if (drafts[1]) setDraftId(drafts[1].id);
  };

  const handleAnalyze = () => {
    if (!canAnalyze) return;
    onAnalyze({
      fileName: file?.name,
      text,
      draftId,
      orderId,
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
            <CardDescription>{t("description")}</CardDescription>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={handleFillSample}>
            {t("fillSample")}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <label htmlFor="shot-file" className="text-sm font-medium">
            {t("upload")}
          </label>
          <div className="flex flex-col gap-2 border border-dashed border-input bg-secondary/25 p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <UploadSimpleIcon className="size-4 shrink-0" aria-hidden />
                <span className="truncate">{file ? file.name : t("uploadHint")}</span>
              </div>
              {file && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleClearFile}
                  aria-label={t("removeFile")}
                  className="h-7 px-2"
                >
                  <XIcon className="size-3.5" aria-hidden />
                </Button>
              )}
            </div>
            <input
              ref={fileInputRef}
              id="shot-file"
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-xs text-muted-foreground file:mr-3 file:border file:border-border file:bg-card file:px-2.5 file:py-1 file:text-xs file:font-medium file:text-foreground hover:file:bg-accent/50"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="shot-text" className="text-sm font-medium">
            {t("text")}
          </label>
          <textarea
            id="shot-text"
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t("textPlaceholder")}
            className="w-full border border-input bg-card p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label htmlFor="shot-draft" className="text-sm font-medium">
              {t("linkDraft")}
            </label>
            <select
              id="shot-draft"
              className={selectClass}
              value={draftId}
              onChange={(e) => setDraftId(e.target.value)}
            >
              <option value="">{t("none")}</option>
              {drafts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="shot-order" className="text-sm font-medium">
              {t("linkOrder")}
            </label>
            <select
              id="shot-order"
              className={selectClass}
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
            >
              <option value="">{t("none")}</option>
              {orders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <Button disabled={!canAnalyze} onClick={handleAnalyze}>
          <SparkleIcon data-icon="inline-start" aria-hidden />
          {t("analyze")}
        </Button>
      </CardContent>
    </Card>
  );
}
