"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Draft, Order } from "../types/transfer.types";

const selectClass =
  "h-9 w-full border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50";

export function ScreenshotAnalysis({
  drafts,
  orders,
}: {
  drafts: Draft[];
  orders: Order[];
}) {
  const t = useTranslations("transfer.screenshot");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [draftId, setDraftId] = useState("");
  const [orderId, setOrderId] = useState("");
  const [analyzed, setAnalyzed] = useState(false);

  const canAnalyze = Boolean(file) || text.trim().length > 0;

  // TODO: call analysis API.
  const handleAnalyze = () => setAnalyzed(true);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <label htmlFor="shot-file" className="text-sm font-medium">
            {t("upload")}
          </label>
          <input
            id="shot-file"
            type="file"
            accept="image/*"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setAnalyzed(false);
            }}
            className="block w-full border border-input bg-card p-2 text-sm"
          />
        </div>

        <div className="space-y-1.5">
          <label htmlFor="shot-text" className="text-sm font-medium">
            {t("text")}
          </label>
          <textarea
            id="shot-text"
            rows={3}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setAnalyzed(false);
            }}
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

        <Button variant="outline" disabled={!canAnalyze} onClick={handleAnalyze}>
          {t("analyze")}
        </Button>

        {analyzed && (
          <p className="border bg-secondary/45 p-3 text-sm" role="status">
            {t("result")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
