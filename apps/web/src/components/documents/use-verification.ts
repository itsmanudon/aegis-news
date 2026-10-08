"use client";
import { useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { useConsole } from "../providers";
export function useVerification(id: string) {
  const { adapter } = useConsole();
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), [id]);
  return useMutation({
    mutationFn: () => {
      controller.current?.abort();
      controller.current = new AbortController();
      return adapter.verify(id, controller.current.signal);
    },
  });
}
