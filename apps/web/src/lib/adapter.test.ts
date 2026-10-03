import { describe, expect, it, vi } from "vitest";
import { createMockAdapter, createRealAdapter, ApiClientError } from "./api";

describe("analyst data boundary", () => {
  it("filters source, search and integrity together", async () => {
    const client = createMockAdapter(0);
    const all = await client.documents({});
    const selected = await client.documents({
      query: "receipts",
      sourceId: all[0].source.source_id,
      integrity: "verified",
    });
    expect(selected).toHaveLength(1);
    expect(selected[0].document.title).toContain("Port");
    expect(await client.documents({ query: "not-in-the-corpus" })).toEqual([]);
  });
  it("uses first seen for document cutoffs and availability for intelligence", async () => {
    const client = createMockAdapter(0);
    const all = await client.documents({ cutoff: "2026-10-03T08:04:00Z" });
    expect(all).toHaveLength(1);
    expect(all[0].analyses).toEqual([]);
    expect(all[0].events).toEqual([]);
    expect(all[0].entities).toEqual([]);
  });
  it("returns not-found and never verifies unknown records", async () => {
    const client = createMockAdapter(0);
    await expect(client.document("unknown")).rejects.toMatchObject({
      code: "NOT_FOUND",
    });
    await expect(client.verify("unknown")).rejects.toMatchObject({
      code: "NOT_FOUND",
    });
  });
  it("simulates verified, failed and unsigned results independently", async () => {
    const client = createMockAdapter(0);
    const all = await client.documents({});
    expect(await client.verify(all[0].document.document_id)).toMatchObject({
      result: "verified",
      simulated: true,
    });
    expect(await client.verify(all[1].document.document_id)).toMatchObject({
      result: "failed",
    });
    expect(await client.verify(all[2].document.document_id)).toMatchObject({
      result: "unverified",
    });
  });
  it("does not request unregistered endpoints or fall back to mocks", async () => {
    const transport = vi.fn();
    const client = createRealAdapter("https://api.example.test", transport);
    await expect(client.documents({})).rejects.toMatchObject({
      code: "CAPABILITY_UNAVAILABLE",
    });
    await expect(client.verify("doc")).rejects.toBeInstanceOf(ApiClientError);
    expect(transport).not.toHaveBeenCalled();
  });
  it("calls the generated system path and preserves server request IDs on errors", async () => {
    const transport = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            error: {
              code: "FORBIDDEN",
              message: "Restricted",
              request_id: "req-42",
            },
          }),
          { status: 403, headers: { "Content-Type": "application/json" } },
        ),
    );
    const client = createRealAdapter("https://api.example.test", transport);
    await expect(client.system()).rejects.toMatchObject({
      code: "FORBIDDEN",
      requestId: "req-42",
      status: 403,
    });
    expect(transport.mock.calls).toHaveLength(1);
  });
  it("supports cancellation and rejects invalid cutoffs", async () => {
    const client = createMockAdapter(20);
    await expect(client.documents({ cutoff: "invalid" })).rejects.toMatchObject(
      { code: "INVALID_ARGUMENT" },
    );
    const controller = new AbortController();
    controller.abort();
    await expect(client.documents({}, controller.signal)).rejects.toMatchObject(
      { name: "AbortError" },
    );
  });
  it("does not reveal an existing entity association before document analysis availability", async () => {
    const records = await createMockAdapter(0).documents({
      cutoff: "2026-10-03T08:17:00Z",
    });
    const field = records.find((v) =>
      v.document.title.startsWith("Field report"),
    );
    expect(field?.entities).toEqual([]);
  });
  it("applies the request deadline even when the query supplies a cancellation signal", async () => {
    const deadline = new AbortController();
    const timeout = vi
      .spyOn(AbortSignal, "timeout")
      .mockReturnValue(deadline.signal);
    const transport = vi.fn(
      (input: RequestInfo | URL) =>
        new Promise<Response>((resolve, reject) => {
          const request = input instanceof Request ? input : new Request(input);
          if (request.signal.aborted) {
            reject(request.signal.reason);
            return;
          }
          request.signal.addEventListener(
            "abort",
            () => reject(request.signal.reason),
            { once: true },
          );
        }),
    );
    try {
      const promise = createRealAdapter(
        "https://api.example.test",
        transport,
      ).system(new AbortController().signal);
      const rejection = expect(promise).rejects.toMatchObject({
        code: "NETWORK_ERROR",
        message: "The API request timed out. Retry or check the connection.",
      });
      deadline.abort(new DOMException("Deadline exceeded", "TimeoutError"));
      await rejection;
      expect(timeout).toHaveBeenCalledWith(10000);
    } finally {
      timeout.mockRestore();
    }
  });
});
