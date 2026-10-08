import type { components } from "./generated/domain";
import type { components as ApiComponents } from "./generated/api";
export type Domain = {
  [K in keyof components["schemas"]]: K extends keyof ApiComponents["schemas"]
    ? ApiComponents["schemas"][K]
    : components["schemas"][K];
};
export type SystemResponse =
  ApiComponents["schemas"]["SingleResponse_SystemInfo_"];
export type Mode = "mock" | "real";
export type IntegrityState = "verified" | "failed" | "unverified";
// Frontend composition only. These are not backend response contracts.
export type Verification = {
  result: IntegrityState;
  signature: "valid" | "invalid" | "unsigned";
  responseReceivedAt: string;
  contentVerified?: boolean;
  chainValid?: boolean;
  signatureValid?: boolean;
  simulated: boolean;
  reason: string;
};
export type DocumentView = {
  acquisition?: ApiComponents["schemas"]["ArticleEvidence"][];
  intelligenceLoaded?: boolean;
  document: Domain["NewsDocument"];
  source: Domain["Source"];
  analyses: Domain["AnalysisResult"][];
  entities: Domain["Entity"][];
  events: Domain["NewsEvent"][];
  media: Domain["MediaAsset"][];
  provenance: Domain["ProvenanceRecord"][];
  integrity: IntegrityState;
};
export type DocumentFilters = {
  cursor?: string;
  entityId?: string;
  query?: string;
  sourceId?: string;
  integrity?: string;
  cutoff?: string;
};
export type BoundedList<T> = T[] & { nextCursor?: string };
export type DocumentList = BoundedList<DocumentView>;
export type EntityList = BoundedList<Domain["Entity"]>;
export type EventList = BoundedList<Domain["NewsEvent"]>;
export type SourceList = BoundedList<Domain["Source"]>;
export type AuditList = BoundedList<AuditEntry>;
export type DiscoveryList = DocumentList & { asOf: string };
export type TopicFilters = { cursor?: string; cutoff?: string; query?: string };
export type AnalyticsFilters = {
  start: string;
  end: string;
  cutoff?: string;
  timeBasis?: "published_at" | "first_seen_at";
  topicId?: string;
  sourceId?: string;
};
export type DiscoveryFilters = TopicFilters &
  Partial<AnalyticsFilters> & { order?: "published_at" | "first_seen_at" };
export type AuditEntry = {
  id: string;
  at: string;
  action: string;
  actor: string;
  outcome: string;
  subject: string;
  requestId?: string;
  raw?: ApiComponents["schemas"]["AuditEvent"];
};
export type Session = {
  state: "anonymous" | "authenticated";
  displayName?: string;
  roles: string[];
  simulated: boolean;
  scopes?: string[];
};
export interface IdentityPort {
  session(signal?: AbortSignal): Promise<Session>;
}
export interface AnalystAdapter {
  topics?(
    filters: TopicFilters,
    signal?: AbortSignal,
  ): Promise<
    ApiComponents["schemas"]["SnapshotCollectionResponse_TopicSummary_"]
  >;
  topic?(
    id: string,
    cutoff?: string,
    signal?: AbortSignal,
  ): Promise<ApiComponents["schemas"]["TopicSummary"]>;
  topicDocuments?(
    id: string,
    filters: TopicFilters,
    signal?: AbortSignal,
  ): Promise<
    ApiComponents["schemas"]["SnapshotCollectionResponse_TopicMembership_"]
  >;
  discovery?(
    filters: DiscoveryFilters,
    signal?: AbortSignal,
  ): Promise<DiscoveryList>;
  analytics?(
    filters: AnalyticsFilters,
    signal?: AbortSignal,
  ): Promise<ApiComponents["schemas"]["AnalyticsReport"]>;
  acquisition?(
    id: string,
    signal?: AbortSignal,
  ): Promise<ApiComponents["schemas"]["ArticleEvidence"][]>;
  providerArticles?(
    cursor?: string,
    signal?: AbortSignal,
  ): Promise<
    ApiComponents["schemas"]["CollectionResponse_ProviderArticleView_"]
  >;
  videos?(
    signal?: AbortSignal,
    cursor?: string,
  ): Promise<ApiComponents["schemas"]["CollectionResponse_YouTubeReference_"]>;
  providers?(
    signal?: AbortSignal,
  ): Promise<ApiComponents["schemas"]["ProviderStatus"][]>;
  fetchProvider?(
    provider: ApiComponents["schemas"]["ProviderStatus"]["provider"] | "all",
    body: ApiComponents["schemas"]["FetchOptions"],
    signal?: AbortSignal,
  ): Promise<ApiComponents["schemas"]["ProviderRun"]>;
  providerRun?(
    id: string,
    signal?: AbortSignal,
  ): Promise<ApiComponents["schemas"]["ProviderRun"]>;
  createSource?(
    body: ApiComponents["schemas"]["SourceCreate"],
    signal?: AbortSignal,
  ): Promise<Domain["Source"]>;
  ingest?(
    body: ApiComponents["schemas"]["IngestionRequest"],
    signal?: AbortSignal,
  ): Promise<Record<string, string>>;
  ingestBatch?(
    body: ApiComponents["schemas"]["BatchRequest"],
    signal?: AbortSignal,
  ): Promise<Record<string, unknown>>;
  ingestionRun?(
    id: string,
    signal?: AbortSignal,
  ): Promise<Record<string, unknown>>;
  system(signal?: AbortSignal): Promise<SystemResponse>;
  documents(
    filters: DocumentFilters,
    signal?: AbortSignal,
  ): Promise<DocumentList>;
  document(id: string, signal?: AbortSignal): Promise<DocumentView>;
  entities(signal?: AbortSignal, cursor?: string): Promise<EntityList>;
  entity(id: string, signal?: AbortSignal): Promise<Domain["Entity"]>;
  events(signal?: AbortSignal, cursor?: string): Promise<EventList>;
  sources(signal?: AbortSignal): Promise<Domain["Source"][]>;
  sourcePage(signal?: AbortSignal, cursor?: string): Promise<SourceList>;
  audit(signal?: AbortSignal, cursor?: string): Promise<AuditList>;
  verify(id: string, signal?: AbortSignal): Promise<Verification>;
}
