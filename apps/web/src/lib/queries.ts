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
export function useAcquisition(id: string, enabled = true) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "document-acquisition", id],
    queryFn: ({ signal }) => adapter.acquisition!(id, signal),
    enabled: enabled && !!adapter.acquisition,
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
export function useEntities(cursor?: string) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "entities", cursor],
    queryFn: ({ signal }) => adapter.entities(signal, cursor),
  });
}
export function useEvents(cursor?: string) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "events", cursor],
    queryFn: ({ signal }) => adapter.events(signal, cursor),
  });
}
export function useAudit() {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "audit"],
    queryFn: ({ signal }) => adapter.audit(signal),
  });
}
