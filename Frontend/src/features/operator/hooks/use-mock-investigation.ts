"use client";

import { useEffect, useRef, useState } from "react";

import { MOCK_INVESTIGATION_DELAY_MS } from "../constants/operator.constants";
import type { InvestigationResult, InvestigationRun } from "../types/operator.types";

// TODO: replace with investigation API (simulates latency only).
export function useMockInvestigation(result: InvestigationResult) {
  const [run, setRun] = useState<InvestigationRun | null>(null);
  const [running, setRunning] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => () => clearTimeout(timer.current), []);

  const start = () => {
    if (running) return;
    setRunning(true);
    timer.current = setTimeout(() => {
      setRun({
        ...result,
        runId: `RUN-${Date.now().toString().slice(-6)}`,
        ranAt: new Date().toISOString(),
      });
      setRunning(false);
    }, MOCK_INVESTIGATION_DELAY_MS);
  };

  return { run, running, start };
}
