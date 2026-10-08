import { describe, expect, it, vi } from "vitest";
import { createMockAdapter, createRealAdapter } from "./api";
import { documents, entities } from "./fixtures";

describe("bounded intelligence browsing", () => {
  it("preserves audit outcomes, hashes, request references and opaque pages", async () => {
    const transport = vi.fn(async (input: RequestInfo | URL) => {
      const request = input as Request;
      expect(request.headers.get("Authorization")).toBe("Bearer audit-reader");
      expect(new URL(request.url).searchParams.get("limit")).toBe("20");
      return new Response(JSON.stringify({
        data: ["success", "failure", "attempt", "custom"].map((outcome) => ({
          event_id: outcome, occurred_at: "2026-10-08T10:00:00Z", action: "signature_verification",
          outcome, actor_hash: null, subject_hash: "hashed-subject", request_id: "request-reference",
        })), pagination: { has_more: true, next_cursor: "audit|+/==" }, meta: { request_id: "page", api_version: "v1" },
      }), { headers: { "Content-Type": "application/json" } });
    });
    const adapter = createRealAdapter("https://api.example.test", transport, "audit-reader");
    const page = await adapter.audit();
    expect(page.map((entry) => entry.outcome)).toEqual(["success", "failure", "attempt", "custom"]);
    expect(page[0].requestId).toBe("request-reference");
    expect(page[0].raw?.actor_hash).toBeNull();
    expect(page.nextCursor).toBe("audit|+/==");
    expect(transport).toHaveBeenCalledOnce();
    await adapter.audit(undefined, page.nextCursor);
    expect(new URL((transport.mock.calls[1][0] as Request).url).searchParams.get("cursor")).toBe("audit|+/==");
  });
  it("reads a bounded registry without changing document source composition", async () => {
    const transport = vi.fn(async (input: RequestInfo | URL) => {
      const cursor = new URL((input as Request).url).searchParams.get("cursor");
      return new Response(JSON.stringify({data: [documents[0].source], pagination: {has_more: !cursor, next_cursor: cursor ? null : "source+/=="}, meta: {request_id: "registry", api_version: "v1"}}), {headers: {"Content-Type": "application/json"}});
    });
    const adapter = createRealAdapter("https://api.example.test", transport);
    const page = await adapter.sourcePage();
    expect(transport).toHaveBeenCalledOnce();
    expect(page.nextCursor).toBe("source+/==");
    await adapter.sourcePage(undefined, page.nextCursor);
    expect(new URL((transport.mock.calls[1][0] as Request).url).searchParams.get("cursor")).toBe("source+/==");
    expect((await adapter.sources()).length).toBe(2);
    expect(transport).toHaveBeenCalledTimes(4);
  });
  it("posts a contracted ingestion batch with authorization and cancellation", async () => {
    const transport = vi.fn(async (input: RequestInfo | URL) => {
      const request = input as Request;
      expect(request.method).toBe("POST");
      expect(new URL(request.url).pathname).toBe("/api/v1/ingestions/batch");
      expect(request.headers.get("Authorization")).toBe("Bearer batch-writer");
      expect(await request.json()).toEqual({items: []});
      return new Response(JSON.stringify({data: {submissions: [{workflow_id: "known-workflow"}]}, meta: {request_id: "batch", api_version: "v1"}}), {headers: {"Content-Type": "application/json"}});
    });
    const adapter = createRealAdapter("https://api.example.test", transport, "batch-writer");
    expect(await adapter.ingestBatch!({items: []})).toEqual({submissions: [{workflow_id: "known-workflow"}]});
    const controller = new AbortController();
    controller.abort();
    await expect(adapter.ingestBatch!({items: []}, controller.signal)).rejects.toMatchObject({name: "AbortError"});
    expect(transport).toHaveBeenCalledOnce();
  });
  it("cancels a bounded event read without losing the authorization boundary", async () => {
    const controller = new AbortController();
    const transport = vi.fn(
      (input: RequestInfo | URL) =>
        new Promise<Response>((_resolve, reject) => {
          const request = input as Request;
          expect(request.headers.get("Authorization")).toBe(
            "Bearer synthetic-cancel-page",
          );
          if (request.signal.aborted) reject(request.signal.reason);
          else
            request.signal.addEventListener(
              "abort",
              () => reject(request.signal.reason),
              { once: true },
            );
        }),
    );
    const pending = createRealAdapter(
      "https://api.example.test",
      transport,
      "synthetic-cancel-page",
    ).events(controller.signal, "opaque+/==");
    const assertion = expect(pending).rejects.toMatchObject({
      name: "AbortError",
    });
    controller.abort();
    await assertion;
    expect(transport).toHaveBeenCalledOnce();
  });
  for (const subject of ["entities", "events"] as const) {
    it(`reads one ${subject} page and preserves opaque cursors and authorization`, async () => {
      const calls: Request[] = [];
      const transport = vi.fn(async (input: RequestInfo | URL) => {
        const request = input as Request;
        calls.push(request);
        const cursor = new URL(request.url).searchParams.get("cursor");
        return new Response(
          JSON.stringify({
            data:
              subject === "entities"
                ? entities.slice(0, 1)
                : documents[0].events,
            pagination: {
              has_more: !cursor,
              next_cursor: cursor ? null : "opaque+/==",
            },
            meta: { request_id: "bounded-page", api_version: "v1" },
          }),
          { headers: { "Content-Type": "application/json" } },
        );
      });
      const adapter = createRealAdapter(
        "https://api.example.test",
        transport,
        "synthetic-page-token",
      );
      const first = await adapter[subject]();
      expect(calls).toHaveLength(1);
      expect(first.nextCursor).toBe("opaque+/==");
      expect(new URL(calls[0].url).searchParams.get("limit")).toBe("20");
      expect(calls[0].headers.get("Authorization")).toBe(
        "Bearer synthetic-page-token",
      );
      await adapter[subject](undefined, first.nextCursor);
      expect(calls).toHaveLength(2);
      expect(new URL(calls[1].url).searchParams.get("cursor")).toBe(
        "opaque+/==",
      );
    });
  }
  it("retains every supplied event revision and mock page isolation", async () => {
    const adapter = createMockAdapter(0);
    const events = await adapter.events();
    expect(events.length).toBe(documents.flatMap((view) => view.events).length);
    expect((await adapter.events(undefined, "20")).length).toBe(0);
    expect((await adapter.entities(undefined, "20")).length).toBe(0);
  });
});
