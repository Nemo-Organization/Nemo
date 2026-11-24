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
import { Input } from "@/components/ui/input";
import type { Recipient } from "../types/transfer.types";

const selectClass =
  "h-9 w-full border border-input bg-card px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50";

export function TransferForm({
  recipients,
  disabled,
  onSubmit,
}: {
  recipients: Recipient[];
  disabled?: boolean;
  onSubmit: (value: { recipientId: string; amount: number }) => void;
}) {
  const t = useTranslations("transfer.form");
  const [recipientId, setRecipientId] = useState("");
  const [amount, setAmount] = useState("");
  const [errors, setErrors] = useState<{ recipient?: boolean; amount?: boolean }>({});

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const value = Number(amount);
    const next = {
      recipient: !recipientId,
      // VND: positive integer only.
      amount: !/^\d+$/.test(amount) || !Number.isSafeInteger(value) || value <= 0,
    };
    setErrors(next);
    if (next.recipient || next.amount) return;
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
          <div className="space-y-1.5">
            <label htmlFor="recipient" className="text-sm font-medium">
              {t("recipient")}
            </label>
            <select
              id="recipient"
              className={selectClass}
              value={recipientId}
              onChange={(e) => {
                setRecipientId(e.target.value);
                if (errors.recipient) setErrors((prev) => ({ ...prev, recipient: false }));
              }}
              aria-invalid={errors.recipient}
              disabled={disabled}
            >
              <option value="">{t("recipientPlaceholder")}</option>
              {recipients.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} · {r.accountNumber}
                </option>
              ))}
            </select>
            {errors.recipient && (
              <p className="text-xs text-destructive">{t("errors.recipient")}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="amount" className="text-sm font-medium">
              {t("amount")}
            </label>
            <Input
              id="amount"
              inputMode="numeric"
              placeholder="500000"
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value.trim());
                if (errors.amount) setErrors((prev) => ({ ...prev, amount: false }));
              }}
              aria-invalid={errors.amount}
              disabled={disabled}
            />
            <p className="text-xs text-muted-foreground">{t("amountHint")}</p>
            {errors.amount && (
              <p className="text-xs text-destructive">{t("errors.amount")}</p>
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
