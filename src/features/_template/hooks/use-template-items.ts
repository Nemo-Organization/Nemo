"use client";

import { useEffect, useState } from "react";

import { getTemplateItems } from "../services/template.service";
import type { TemplateItem } from "../types/template.types";

// TODO: swap for a data-fetching library (e.g. TanStack Query) if the project adopts one.
export function useTemplateItems() {
  const [items, setItems] = useState<TemplateItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getTemplateItems()
      .then(setItems)
      .finally(() => setIsLoading(false));
  }, []);

  return { items, isLoading };
}
