"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ReportStatus } from "../types/operator.types";

export type ReviewAction = "inReview" | "resolved" | "dismissed";

export function ReportReviewActions({
  status,
  onReview,
}: {
  status: ReportStatus;
  onReview: (next: ReviewAction, reason: string) => void;
}) {
  const t = useTranslations("operator.reports");
  const [open, setOpen] = useState(false);
  // Separate from `open` so title stays during close animation.
  const [action, setAction] = useState<ReviewAction>("resolved");
  const [reason, setReason] = useState("");
  const [reasonMissing, setReasonMissing] = useState(false);

  if (status === "resolved" || status === "dismissed") return null;

  const actions: ReviewAction[] =
    status === "new" ? ["inReview", "resolved", "dismissed"] : ["resolved", "dismissed"];

  const openDialog = (next: ReviewAction) => {
    setAction(next);
    setReason("");
    setReasonMissing(false);
    setOpen(true);
  };

  const handleConfirm = () => {
    if (!reason.trim()) {
      setReasonMissing(true);
      return;
    }
    onReview(action, reason.trim());
    setOpen(false);
  };

  return (
    <>
      <div className="flex shrink-0 flex-wrap gap-2 sm:justify-end">
        {actions.map((item) => (
          <Button
            key={item}
            variant={item === "resolved" ? "default" : "outline"}
            onClick={() => openDialog(item)}
          >
            {t(`actions.${item}`)}
          </Button>
        ))}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              {t(`actions.${action}`)}
            </DialogTitle>
            <DialogDescription>{t("review.description")}</DialogDescription>
          </DialogHeader>

          <div className="space-y-1.5">
            <label htmlFor="review-reason" className="text-sm font-medium">
              {t("review.reason")}
            </label>
            <textarea
              id="review-reason"
              rows={4}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (reasonMissing) setReasonMissing(false);
              }}
              placeholder={t("review.reasonPlaceholder")}
              aria-invalid={reasonMissing}
              className="w-full border border-input bg-card p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
            />
            {reasonMissing && (
              <p className="text-xs text-destructive">{t("review.reasonRequired")}</p>
            )}
            <p className="text-xs text-muted-foreground">{t("review.flow")}</p>
          </div>

          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>
              {t("review.cancel")}
            </DialogClose>
            <Button onClick={handleConfirm}>{t(`actions.${action}`)}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
