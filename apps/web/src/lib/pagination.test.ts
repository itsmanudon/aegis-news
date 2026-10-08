import { describe, expect, it, vi } from "vitest";
import { createMockAdapter, createRealAdapter } from "./api";
import { documents, entities } from "./fixtures";

describe("bounded intelligence browsing", () => {
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
