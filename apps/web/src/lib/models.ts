import type { components } from "./generated/domain";
import type { components as ApiComponents } from "./generated/api";
export type Domain = components["schemas"];
export type SystemResponse =
  ApiComponents["schemas"]["SingleResponse_SystemInfo_"];
export type Mode = "mock" | "real";
export type IntegrityState = "verified" | "failed" | "unverified";
// Frontend composition only. These are not backend response contracts.
export type Verification = {
  result: IntegrityState;
  signature: "valid" | "invalid" | "unsigned";
  checkedAt: string;
  simulated: boolean;
  reason: string;
};
export type DocumentView = {
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
  query?: string;
  sourceId?: string;
  integrity?: string;
  cutoff?: string;
};
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
};
export interface IdentityPort {
  session(signal?: AbortSignal): Promise<Session>;
}
export interface AnalystAdapter {
  system(signal?: AbortSignal): Promise<SystemResponse>;
  documents(
    filters: DocumentFilters,
    signal?: AbortSignal,
  ): Promise<DocumentView[]>;
  document(id: string, signal?: AbortSignal): Promise<DocumentView>;
  entities(signal?: AbortSignal): Promise<Domain["Entity"][]>;
  entity(id: string, signal?: AbortSignal): Promise<Domain["Entity"]>;
  events(signal?: AbortSignal): Promise<Domain["NewsEvent"][]>;
  sources(signal?: AbortSignal): Promise<Domain["Source"][]>;
  audit(signal?: AbortSignal): Promise<AuditEntry[]>;
  verify(id: string, signal?: AbortSignal): Promise<Verification>;
}
