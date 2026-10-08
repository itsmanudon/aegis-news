"use client";
import { useQuery } from "@tanstack/react-query";
import { useConsole } from "@/components/providers";
import type {
  DocumentFilters,
  TopicFilters,
  DiscoveryFilters,
  AnalyticsFilters,
} from "./models";
export function useTopics(filters: TopicFilters = {}) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "topics", filters],
    queryFn: ({ signal }) => adapter.topics!(filters, signal),
    enabled: !!adapter.topics,
  });
}
export function useTopic(id: string, cutoff?: string) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "topic", id, cutoff],
    queryFn: ({ signal }) => adapter.topic!(id, cutoff, signal),
    enabled: !!adapter.topic,
  });
}
export function useTopicDocuments(id: string, filters: TopicFilters = {}) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "topic-documents", id, filters],
    queryFn: ({ signal }) => adapter.topicDocuments!(id, filters, signal),
    enabled: !!adapter.topicDocuments,
  });
}
export function useDiscovery(filters: DiscoveryFilters = {}) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "discovery", filters],
    queryFn: ({ signal }) => adapter.discovery!(filters, signal),
    enabled: !!adapter.discovery,
  });
}
export function useAnalytics(filters: AnalyticsFilters) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "analytics", filters],
    queryFn: ({ signal }) => adapter.analytics!(filters, signal),
    enabled: !!adapter.analytics,
  });
}
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
export function useSourcePage(cursor?: string) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "source-page", cursor],
    queryFn: ({ signal }) => adapter.sourcePage(signal, cursor),
  });
}
export function useAudit(cursor?: string) {
  const { adapter, mode } = useConsole();
  return useQuery({
    queryKey: [mode, "audit", cursor],
    queryFn: ({ signal }) => adapter.audit(signal, cursor),
  });
}
