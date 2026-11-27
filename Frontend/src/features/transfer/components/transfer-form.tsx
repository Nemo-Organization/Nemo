"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatVnd } from "@/lib/format";
import { cn } from "@/lib/utils";
import { QUICK_TRANSFER_AMOUNTS } from "../constants/transfer.constants";
import type { Recipient } from "../types/transfer.types";

const selectClass =
  "h-9 w-full border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50";

export function TransferForm({
  recipients,
  recipientId,
  amount,
  availableBalance,
  disabled,
  onRecipientChange,
  onAmountChange,
  onSubmit,
}: {
  recipients: Recipient[];
  recipientId: string;
  amount: string;
  availableBalance: number;
  disabled?: boolean;
  onRecipientChange: (id: string) => void;
  onAmountChange: (amount: string) => void;
  onSubmit: (value: { recipientId: string; amount: number }) => void;
}) {
  const t = useTranslations("transfer.form");
  const locale = useLocale();
  const [errors, setErrors] = useState<{
    recipient?: boolean;
    amount?: "invalid" | "insufficient";
  }>({});

  const selectRecipient = (id: string) => {
    onRecipientChange(id);
    if (errors.recipient) setErrors((prev) => ({ ...prev, recipient: false }));
  };

  const updateAmount = (raw: string) => {
    onAmountChange(raw);
    if (errors.amount) setErrors((prev) => ({ ...prev, amount: undefined }));
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const value = Number(amount);
    // VND: positive integer only.
    const invalidAmount =
      !/^\d+$/.test(amount) || !Number.isSafeInteger(value) || value <= 0;
    const nextErrors: typeof errors = {
      recipient: !recipientId,
      amount: invalidAmount
        ? "invalid"
        : value > availableBalance
          ? "insufficient"
          : undefined,
    };
    setErrors(nextErrors);
    if (nextErrors.recipient || nextErrors.amount) return;
    onSubmit({ recipientId, amount: value });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">
              {t("quickRecipients")}
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {recipients.map((r) => {
                const selected = recipientId === r.id;
                return (
                  <button
                    key={r.id}
                    type="button"
                    disabled={disabled}
                    onClick={() => selectRecipient(r.id)}
                    className={cn(
                      "flex flex-col items-start gap-1 border p-2.5 text-left transition-colors disabled:opacity-50",
                      selected
                        ? "border-primary bg-primary/5"
                        : "border-border bg-card hover:bg-accent/40",
                    )}
                  >
                    <div className="flex w-full items-center justify-between gap-1">
                      <span className="truncate text-xs font-medium text-foreground">
                        {r.name}
                      </span>
                      {r.restriction && (
                        <Badge
                          variant="secondary"
                          className={cn(
                            "px-1.5 py-0 text-[10px]",
                            r.restriction === "HOLD"
                              ? "text-destructive"
                              : "text-amber-600 dark:text-amber-400",
                          )}
                        >
                          {t(`restrictionTag.${r.restriction}`)}
                        </Badge>
                      )}
                    </div>
                    <span className="text-[11px] tabular-nums text-muted-foreground">
                      {r.bankCode} · {r.accountNumber}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="recipient" className="text-sm font-medium">
              {t("recipient")}
            </label>
            <select
              id="recipient"
              className={selectClass}
              value={recipientId}
              onChange={(e) => selectRecipient(e.target.value)}
              aria-invalid={errors.recipient}
              disabled={disabled}
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

          <div className="space-y-2">
            <label htmlFor="amount" className="text-sm font-medium">
              {t("amount")}
            </label>
            <Input
              id="amount"
              inputMode="numeric"
              placeholder="500000"
              value={amount}
              onChange={(e) => updateAmount(e.target.value.trim())}
              aria-invalid={Boolean(errors.amount)}
              disabled={disabled}
            />
            <div className="flex flex-wrap gap-1.5" aria-label={t("quickAmounts")}>
              {QUICK_TRANSFER_AMOUNTS.map((preset) => (
                <Button
                  key={preset}
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={disabled}
                  onClick={() => updateAmount(String(preset))}
                  className="h-7 px-2 text-xs tabular-nums"
                >
                  {formatVnd(preset, locale)}
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">{t("amountHint")}</p>
            {errors.amount === "invalid" && (
              <p className="text-xs text-destructive">{t("errors.amount")}</p>
            )}
            {errors.amount === "insufficient" && (
              <p className="text-xs text-destructive">{t("errors.insufficient")}</p>
            )}
          </div>

          <Button type="submit" disabled={disabled}>
            {t("submit")}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
