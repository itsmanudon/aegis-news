"use client";
import { useEffect, useRef, useState } from "react";
export function useOperation() {
  const active = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  useEffect(
    () => () => {
      active.current?.abort();
    },
    [],
  );
  async function run<T>(
    work: (signal: AbortSignal) => Promise<T>,
  ): Promise<T | undefined> {
    if (active.current) return undefined;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError(null);
    try {
      const value = await work(controller.signal);
      return controller.signal.aborted ? undefined : value;
    } catch (cause) {
      if (!controller.signal.aborted)
        setError(cause instanceof Error ? cause : new Error("Request failed."));
    } finally {
      if (!controller.signal.aborted) {
        active.current = null;
        setBusy(false);
      }
    }
  }
  return { run, busy, error };
}
