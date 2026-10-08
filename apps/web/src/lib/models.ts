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
export type AuditEntry = {
  id: string;
  at: string;
  action: string;
  actor: string;
  outcome: "allowed" | "denied" | "warning";
  subject: string;
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
  ): Promise<ApiComponents["schemas"]["CollectionResponse_YouTubeReference_"]>;
  providers?(
    signal?: AbortSignal,
  ): Promise<ApiComponents["schemas"]["ProviderStatus"][]>;
  fetchProvider?(
    provider: ApiComponents["schemas"]["ProviderStatus"]["provider"] | "all",
    body: ApiComponents["schemas"]["FetchOptions"],
  ): Promise<ApiComponents["schemas"]["ProviderRun"]>;
  providerRun?(id: string): Promise<ApiComponents["schemas"]["ProviderRun"]>;
  createSource?(
    body: ApiComponents["schemas"]["SourceCreate"],
  ): Promise<Domain["Source"]>;
  ingest?(
    body: ApiComponents["schemas"]["IngestionRequest"],
  ): Promise<Record<string, string>>;
  ingestionRun?(id: string): Promise<Record<string, unknown>>;
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
  audit(signal?: AbortSignal): Promise<AuditEntry[]>;
  verify(id: string, signal?: AbortSignal): Promise<Verification>;
}
