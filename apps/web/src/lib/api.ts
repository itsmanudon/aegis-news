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
export function createRealAdapter(
  baseUrl: string,
  transport: typeof fetch = fetch,
): AnalystAdapter {
  const client = createClient<paths>({
    baseUrl,
    fetch: transport,
    credentials: "omit",
  });
  const unavailable = async (): Promise<never> => {
    throw new ApiClientError(
      "CAPABILITY_UNAVAILABLE",
      "This capability is not registered in the current API contract. Switch to mock data to explore the console.",
    );
  };
  return {
    async system(signal) {
      try {
        const deadline = AbortSignal.timeout(10000);
        const { data, error, response } = await client.GET(
          "/api/v1/system/info",
          { signal: signal ? AbortSignal.any([signal, deadline]) : deadline },
        );
        if (error)
          throw new ApiClientError(
            error.error.code,
            error.error.message,
            error.error.request_id,
            response.status,
          );
        if (
          !data ||
          !data.data ||
          !data.meta ||
          typeof data.data.version !== "string"
        )
          throw new ApiClientError(
            "PROCESSING_FAILED",
            "The API returned an unexpected system response.",
          );
        return data;
      } catch (error) {
        if (
          error instanceof ApiClientError ||
          (error instanceof DOMException && error.name === "AbortError")
        )
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
    documents: unavailable,
    document: unavailable,
    entities: unavailable,
    entity: unavailable,
    events: unavailable,
    sources: unavailable,
    audit: unavailable,
    verify: unavailable,
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
