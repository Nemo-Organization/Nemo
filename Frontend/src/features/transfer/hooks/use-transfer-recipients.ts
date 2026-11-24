"use client";

import { useEffect, useState } from "react";

import { getTransferRecipients } from "../services/transfer.service";
import type { Recipient } from "../types/transfer.types";

export function useTransferRecipients() {
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getTransferRecipients()
      .then(setRecipients)
      .finally(() => setIsLoading(false));
  }, []);

  return { recipients, isLoading };
}
