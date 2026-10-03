"use client";
import { useQuery } from "@tanstack/react-query";
import { useConsole } from "@/components/providers";
import type { DocumentFilters } from "./models";
export function useDocuments(filters: DocumentFilters = {}) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "documents", filters],
    queryFn: ({ signal }) => adapter.documents(filters, signal),
  });
}
export function useDocument(id: string) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "document", id],
    queryFn: ({ signal }) => adapter.document(id, signal),
  });
}
export function useEntity(id: string) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "entity", id],
    queryFn: ({ signal }) => adapter.entity(id, signal),
  });
}
export function useSystem() {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "system"],
    queryFn: ({ signal }) => adapter.system(signal),
  });
}
export function useSources() {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "sources"],
    queryFn: ({ signal }) => adapter.sources(signal),
  });
}
export function useEntities() {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "entities"],
    queryFn: ({ signal }) => adapter.entities(signal),
  });
}
export function useEvents() {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "events"],
    queryFn: ({ signal }) => adapter.events(signal),
  });
}
export function useAudit() {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "audit"],
    queryFn: ({ signal }) => adapter.audit(signal),
  });
}
