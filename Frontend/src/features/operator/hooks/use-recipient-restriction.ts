"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { RESTRICTION_TTL_DAYS } from "../constants/operator.constants";
import type {
  Restriction,
  RestrictionHistoryEntry,
  RestrictionLevel,
} from "../types/operator.types";

const DAY_MS = 24 * 60 * 60 * 1000;

// TODO: call restriction API. Every create/revoke appends an audit entry.
export function useRecipientRestriction({
  restriction: initialRestriction,
  history: initialHistory,
  evidenceReportIds,
}: {
  restriction: Restriction | null;
  history: RestrictionHistoryEntry[];
  evidenceReportIds: string[];
}) {
  const t = useTranslations("operator.decision");
  const [restriction, setRestriction] = useState(initialRestriction);
  const [history, setHistory] = useState(initialHistory);

  const create = (level: RestrictionLevel, reason: string) => {
    const now = new Date();
    const created: Restriction = {
      id: `rs-${now.getTime()}`,
      level,
      reason,
      createdAt: now.toISOString(),
      createdBy: "OPS",
      expiresAt: new Date(now.getTime() + RESTRICTION_TTL_DAYS * DAY_MS).toISOString(),
      evidenceReportIds,
    };
    setRestriction(created);
    setHistory((prev) => [
      { id: `rh-${now.getTime()}`, action: "created", level, at: created.createdAt, by: "OPS", reason },
      ...prev,
    ]);
    toast.success(t("created"));
  };

  const revoke = () => {
    if (!restriction) return;
    const now = new Date();
    setHistory((prev) => [
      { id: `rh-${now.getTime()}`, action: "revoked", level: restriction.level, at: now.toISOString(), by: "OPS" },
      ...prev,
    ]);
    setRestriction(null);
    toast.success(t("revoked"));
  };

  return { restriction, history, create, revoke };
}
