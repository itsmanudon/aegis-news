import { describe, expect, it, vi } from "vitest";
import { createMockAdapter, createRealAdapter, ApiClientError } from "./api";

describe("analyst data boundary", () => {
  it("cancels optional acquisition through the same authenticated request boundary", async () => {
    const controller = new AbortController();
    const transport = vi.fn(
      (input: RequestInfo | URL) =>
        new Promise<Response>((_resolve, reject) => {
          const request = input as Request;
          expect(request.headers.get("Authorization")).toBe(
            "Bearer synthetic-cancel",
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
      "synthetic-cancel",
    ).acquisition!("synthetic-document", controller.signal);
    const rejected = expect(pending).rejects.toMatchObject({
      name: "AbortError",
    });
    controller.abort();
    await rejected;
    expect(transport).toHaveBeenCalledOnce();
  });
  it("keeps primary story reads independent of optional acquisition failures", async () => {
    const view = await createMockAdapter(0).document(
      "doc_00000000-0000-4000-8000-000000000001",
    );
    const transport = vi.fn(async (input: RequestInfo | URL) => {
      const request = input as Request;
      expect(request.headers.get("Authorization")).toBe(
        "Bearer synthetic-token",
      );
      const optional = request.url.endsWith("/acquisition");
      return new Response(
        JSON.stringify(
          optional
            ? {
                error: {
                  code: "FORBIDDEN",
                  message: "Acquisition access denied",
                  request_id: "optional-403",
                },
              }
            : { data: view, meta: {} },
        ),
        {
          status: optional ? 403 : 200,
          headers: { "Content-Type": "application/json" },
        },
      );
    });
    const adapter = createRealAdapter(
      "https://api.example.test",
      transport,
      "synthetic-token",
    );
    await expect(
      adapter.document(view.document.document_id),
    ).resolves.toMatchObject({
      document: view.document,
      integrity: "unverified",
    });
    expect(transport).toHaveBeenCalledTimes(1);
    await expect(
      adapter.acquisition!(view.document.document_id),
    ).rejects.toMatchObject({ code: "FORBIDDEN", requestId: "optional-403" });
  });
  it("preserves distinct verification subchecks and labels the local receipt instant", async () => {
    const transport = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            data: {
              valid: false,
              content_verified: false,
              chain_valid: true,
              signature_valid: true,
              reason: "Synthetic content mismatch",
            },
            meta: {},
          }),
          { headers: { "Content-Type": "application/json" } },
        ),
    );
    const value = await createRealAdapter(
      "https://api.example.test",
      transport,
    ).verify("synthetic-document");
    expect(value).toMatchObject({
      result: "failed",
      contentVerified: false,
      chainValid: true,
      signatureValid: true,
      signature: "valid",
      simulated: false,
    });
    expect(Number.isNaN(Date.parse(value.responseReceivedAt))).toBe(false);
    expect(value).not.toHaveProperty("checkedAt");
  });
  it("loads one cursor page without eagerly requesting document intelligence", async () => {
    const fixtures = await createMockAdapter(0).documents({});
    const transport = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL((input as Request).url);
      if (url.pathname.includes("/intelligence"))
        throw new Error("Unexpected eager intelligence request");
      const data =
        url.pathname === "/api/v1/sources"
          ? fixtures.map((v) => v.source)
          : fixtures.map((v) => v.document);
      return new Response(
        JSON.stringify({
          data,
          pagination: {
            has_more: url.pathname !== "/api/v1/sources",
            next_cursor:
              url.pathname !== "/api/v1/sources" ? "next-page" : null,
          },
          meta: {},
        }),
        { headers: { "Content-Type": "application/json" } },
      );
    });
    const adapter = createRealAdapter("https://api.example.test", transport);
    const page = await adapter.documents({});
    expect(page).toHaveLength(fixtures.length);
    expect(page.nextCursor).toBe("next-page");
    expect(transport.mock.calls).toHaveLength(2);
    expect(
      transport.mock.calls.some(([r]) =>
        (r as Request).url.includes("/intelligence"),
      ),
    ).toBe(false);
    expect(page[0].intelligenceLoaded).toBe(false);
  });
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
  it("requests real product endpoints and never falls back to fixtures", async () => {
    const transport = vi.fn(async (input: RequestInfo | URL) => {
      expect(input).toBeInstanceOf(Request);
      return new Response(
        JSON.stringify({
          error: {
            code: "UNAUTHORIZED",
            message: "Token required",
            request_id: "auth-1",
          },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      );
    });
    const client = createRealAdapter(
      "https://api.example.test",
      transport,
      "test-token",
    );
    await expect(client.documents({})).rejects.toMatchObject({
      code: "UNAUTHORIZED",
    });
    await expect(client.verify("doc")).rejects.toBeInstanceOf(ApiClientError);
    expect(transport).toHaveBeenCalledTimes(2);
    const request = transport.mock.calls[0][0] as Request;
    expect(request.headers.get("Authorization")).toBe("Bearer test-token");
    expect(request.url).toContain("/api/v1/documents");
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
