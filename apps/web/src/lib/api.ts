import createClient from "openapi-fetch";
import type { paths, components } from "./generated/api";
import type {
  AnalystAdapter,
  DocumentFilters,
  DocumentView,
  IdentityPort,
  IntegrityState,
} from "./models";
import { documents, entities, sources, audit } from "./fixtures";

export class ApiClientError extends Error {
  constructor(
    public code:
      | components["schemas"]["ErrorCode"]
      | "CAPABILITY_UNAVAILABLE"
      | "NETWORK_ERROR",
    message: string,
    public requestId?: string,
    public status?: number,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}
const missing = (subject: string): never => {
  throw new ApiClientError("NOT_FOUND", `${subject} was not found.`);
};
async function pause(ms: number, signal?: AbortSignal) {
  signal?.throwIfAborted();
  await new Promise<void>((resolve, reject) => {
    const cancel = () => {
      clearTimeout(timer);
      reject(new DOMException("Request cancelled", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", cancel);
      resolve();
    }, ms);
    signal?.addEventListener("abort", cancel, { once: true });
  });
}
function filterDocuments(filters: DocumentFilters): DocumentView[] {
  const cutoff = filters.cutoff ? Date.parse(filters.cutoff) : Infinity;
  if (Number.isNaN(cutoff))
    throw new ApiClientError(
      "INVALID_ARGUMENT",
      "Enter a valid knowledge cutoff.",
    );
  const query = filters.query?.trim().toLowerCase() ?? "";
  return documents
    .filter((v) => Date.parse(v.document.first_seen_at) <= cutoff)
    .map((v) => ({
      ...v,
      analyses: v.analyses.filter((a) => Date.parse(a.available_at) <= cutoff),
      events: v.events.filter((e) => Date.parse(e.available_at) <= cutoff),
      entities: v.entities.filter(
        (e) =>
          Date.parse(e.created_at) <= cutoff &&
          v.analyses.some((a) => Date.parse(a.available_at) <= cutoff),
      ),
      provenance: v.provenance.filter(
        (p) => Date.parse(p.recorded_at) <= cutoff,
      ),
    }))
    .filter(
      (v) =>
        (!query ||
          `${v.document.title} ${v.document.text} ${v.source.name} ${v.entities.map((e) => e.canonical_name).join(" ")}`
            .toLowerCase()
            .includes(query)) &&
        (!filters.sourceId || v.source.source_id === filters.sourceId) &&
        (!filters.integrity || v.integrity === filters.integrity),
    );
}
export function createMockAdapter(latency = 180): AnalystAdapter {
  const wait = (signal?: AbortSignal) => pause(latency, signal);
  return {
    async system(signal) {
      await wait(signal);
      return {
        data: {
          name: "AegisNews",
          version: "0.1.0-fixture",
          stage: "foundation",
          architecture: "modular monolith + background workers",
        },
        meta: { api_version: "v1", request_id: "fixture-system" },
      };
    },
    async documents(filters, signal) {
      const result = filterDocuments(filters);
      await wait(signal);
      return structuredClone(result);
    },
    async document(id, signal) {
      await wait(signal);
      return structuredClone(
        documents.find((v) => v.document.document_id === id) ??
          missing("Document"),
      );
    },
    async entities(signal) {
      await wait(signal);
      return structuredClone(entities);
    },
    async entity(id, signal) {
      await wait(signal);
      return structuredClone(
        entities.find((e) => e.entity_id === id) ?? missing("Entity"),
      );
    },
    async events(signal) {
      await wait(signal);
      return structuredClone(
        documents
          .flatMap((v) => v.events)
          .sort((a, b) => b.available_at.localeCompare(a.available_at)),
      );
    },
    async sources(signal) {
      await wait(signal);
      return structuredClone(sources);
    },
    async audit(signal) {
      await wait(signal);
      return structuredClone(audit);
    },
    async verify(id, signal) {
      await wait(signal);
      const view =
        documents.find((v) => v.document.document_id === id) ??
        missing("Document");
      const result: IntegrityState = view.integrity;
      return {
        result,
        signature:
          result === "verified"
            ? "valid"
            : result === "failed"
              ? "invalid"
              : "unsigned",
        checkedAt: new Date().toISOString(),
        simulated: true,
        reason:
          result === "verified"
            ? "Fixture content and signature match."
            : result === "failed"
              ? "Fixture signature does not match. Hold for review."
              : "Fixture has no signature. Integrity is unverified.",
      };
    },
  };
}
function unwrap<T>(result: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (result.error) {
    const envelope = result.error as components["schemas"]["ApiErrorEnvelope"];
    throw new ApiClientError(
      envelope.error?.code ?? "PROCESSING_FAILED",
      envelope.error?.message ?? "Unexpected API response",
      envelope.error?.request_id,
      result.response.status,
    );
  }
  if (!result.data)
    throw new ApiClientError(
      "PROCESSING_FAILED",
      "The API returned an empty response.",
    );
  return result.data;
}
function realClient(baseUrl: string, transport: typeof fetch, token: string) {
  const client = createClient<paths>({
    baseUrl,
    credentials: "omit",
    fetch: async (input) => {
      const request = new Request(input);
      const deadline = AbortSignal.timeout(10000);
      try {
        return await transport(
          new Request(request, {
            signal: AbortSignal.any([request.signal, deadline]),
          }),
        );
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError")
          throw error;
        if (error instanceof DOMException && error.name === "TimeoutError")
          throw new ApiClientError(
            "NETWORK_ERROR",
            "The API request timed out. Retry or check the connection.",
          );
        throw new ApiClientError(
          "NETWORK_ERROR",
          "Unable to reach the API. Check the API address and connection.",
        );
      }
    },
  });
  client.use({
    onRequest({ request }) {
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      return request;
    },
  });
  return client;
}
export function createRealAdapter(
  baseUrl: string,
  transport: typeof fetch = fetch,
  token = "",
): AnalystAdapter {
  const client = realClient(baseUrl, transport, token);
  async function detail(
    id: string,
    signal?: AbortSignal,
    cutoff?: string,
  ): Promise<DocumentView> {
    const result = unwrap(
      await client.GET("/api/v1/documents/{document_id}/intelligence", {
        params: { path: { document_id: id }, query: { as_of: cutoff } },
        signal,
      }),
    );
    return { ...result.data, integrity: "unverified" };
  }
  return {
    async system(signal) {
      return unwrap(await client.GET("/api/v1/system/info", { signal }));
    },
    async documents(filters, signal) {
      if (filters.integrity && filters.integrity !== "unverified") {
        throw new ApiClientError(
          "CAPABILITY_UNAVAILABLE",
          "Verify a document to inspect its current integrity. Feed-wide integrity filtering is unavailable.",
        );
      }
      const values: DocumentView[] = [];
      let cursor: string | undefined;
      do {
        const result = unwrap(
          await client.GET(
            filters.query ? "/api/v1/search" : "/api/v1/documents",
            {
              params: {
                query: {
                  q: filters.query,
                  source_id: filters.sourceId,
                  as_of: filters.cutoff,
                  limit: 100,
                  cursor,
                },
              },
              signal,
            },
          ),
        );
        // Bound concurrent requests while assembling canonical intelligence.
        for (const document of result.data)
          values.push(
            await detail(document.document_id, signal, filters.cutoff),
          );
        cursor = result.pagination.next_cursor ?? undefined;
      } while (cursor);
      return values;
    },
    document: detail,
    async entities(signal) {
      const values: components["schemas"]["Entity"][] = [];
      let cursor: string | undefined;
      do {
        const r = unwrap(
          await client.GET("/api/v1/entities", {
            params: { query: { limit: 100, cursor } },
            signal,
          }),
        );
        values.push(...r.data);
        cursor = r.pagination.next_cursor ?? undefined;
      } while (cursor);
      return values;
    },
    async entity(id, signal) {
      return unwrap(
        await client.GET("/api/v1/entities/{entity_id}", {
          params: { path: { entity_id: id } },
          signal,
        }),
      ).data;
    },
    async events(signal) {
      const values: components["schemas"]["NewsEvent"][] = [];
      let cursor: string | undefined;
      do {
        const r = unwrap(
          await client.GET("/api/v1/events", {
            params: { query: { limit: 100, cursor } },
            signal,
          }),
        );
        values.push(...r.data);
        cursor = r.pagination.next_cursor ?? undefined;
      } while (cursor);
      return values;
    },
    async sources(signal) {
      const values: components["schemas"]["Source"][] = [];
      let cursor: string | undefined;
      do {
        const r = unwrap(
          await client.GET("/api/v1/sources", {
            params: { query: { limit: 100, cursor } },
            signal,
          }),
        );
        values.push(...r.data);
        cursor = r.pagination.next_cursor ?? undefined;
      } while (cursor);
      return values;
    },
    async audit(signal) {
      const result = unwrap(
        await client.GET("/api/v1/security/audit", { signal }),
      );
      return result.data.map((v) => ({
        id: v.event_id,
        at: v.occurred_at,
        action: v.action,
        actor: v.actor_hash ?? "anonymous",
        subject: v.subject_hash ?? "?",
        outcome:
          v.outcome === "success"
            ? "allowed"
            : v.outcome === "failure"
              ? "denied"
              : "warning",
      }));
    },
    async verify(id, signal) {
      const value = unwrap(
        await client.POST("/api/v1/documents/{document_id}/verify", {
          params: { path: { document_id: id } },
          signal,
        }),
      ).data;
      return {
        result: value.valid ? "verified" : "failed",
        signature: value.signature_valid ? "valid" : "invalid",
        checkedAt: new Date().toISOString(),
        simulated: false,
        reason: value.reason,
      };
    },
    async createSource(body) {
      return unwrap(await client.POST("/api/v1/sources", { body })).data;
    },
    async ingest(body) {
      return unwrap(await client.POST("/api/v1/ingestions", { body })).data;
    },
    async ingestionRun(id) {
      return unwrap(
        await client.GET("/api/v1/ingestion-runs/{workflow_id}", {
          params: { path: { workflow_id: id } },
        }),
      ).data;
    },
  };
}
export function createRealIdentity(
  baseUrl: string,
  token: string,
): IdentityPort {
  return {
    async session(signal) {
      if (!token)
        return { state: "anonymous", roles: [], scopes: [], simulated: false };
      const value = unwrap(
        await realClient(baseUrl, fetch, token).GET("/api/v1/security/me", {
          signal,
        }),
      ).data;
      return {
        state: "authenticated",
        displayName: value.subject,
        roles: value.roles,
        scopes: value.scopes,
        simulated: false,
      };
    },
  };
}
export const mockIdentity: IdentityPort = {
  async session() {
    return {
      state: "authenticated",
      displayName: "Demo analyst",
      roles: ["analyst"],
      simulated: true,
    };
  },
};
// Replace this port with Agent 3's OIDC adapter. No fabricated production login.
export const anonymousIdentity: IdentityPort = {
  async session() {
    return { state: "anonymous", roles: [], simulated: false };
  },
};
