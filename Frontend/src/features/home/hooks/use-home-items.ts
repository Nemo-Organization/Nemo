"use client";

import { useEffect, useState } from "react";

import { getHomeItems } from "../services/home.service";
import type { HomeItem } from "../types/home.types";

export function useHomeItems() {
  const [items, setItems] = useState<HomeItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getHomeItems()
      .then(setItems)
      .finally(() => setIsLoading(false));
  }, []);

  return { items, isLoading };
}
