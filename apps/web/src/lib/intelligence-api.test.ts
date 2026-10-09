import { expect, it, vi } from "vitest";
import { createRealAdapter, createMockAdapter } from "./api";
import { documents } from "./fixtures";
import { fixtureDiscovery, fixtureMemberships } from "./intelligence-fixtures";

it("mock revision selection compares timestamp instants across timezone offsets", () => {
  const view = structuredClone(documents[0]);
  const original = view.analyses.find((a) => a.analysis_type === "topic")!;
  view.analyses = [
    {
      ...original,
      analysis_id: "older",
      available_at: "2026-10-03T14:00:00+05:30",
    },
    { ...original, analysis_id: "newer", available_at: "2026-10-03T09:00:00Z" },
  ];
  const memberships = fixtureMemberships("2026-10-03T10:00:00Z", [view]);
  expect([...memberships.values()].flat().map((m) => m.analysis_id)).toEqual([
    "newer",
  ]);
});

it("mock discovery rejects partial, reversed, oversized and timezone-free windows like the real contract", () => {
  for (const interval of [
    { start: "2026-10-03T00:00:00Z" },
    { end: "2026-10-03T00:00:00Z" },
    { start: "2026-10-04T00:00:00Z", end: "2026-10-03T00:00:00Z" },
    { start: "2024-01-01T00:00:00Z", end: "2026-01-01T00:00:00Z" },
    { start: "2026-10-03T00:00:00", end: "2026-10-04T00:00:00" },
  ])
    expect(() =>
      fixtureDiscovery({ order: "published_at", ...interval }),
    ).toThrow();
});

it("mock chronological cursors apply their frozen cutoff before selecting records", () => {
  const asOf = "2026-10-03T08:20:00Z";
  const cursor = btoa(
    JSON.stringify({
      offset: 0,
      asOf,
      filter: JSON.stringify({ order: "published_at" }),
    }),
  );
  const page = fixtureDiscovery({ order: "published_at", cursor });
  expect(page.as_of).toBe(asOf);
  expect(
    page.data.every(
      (view) => Date.parse(view.document.created_at) <= Date.parse(asOf),
    ),
  ).toBe(true);
});

it("reads chronological source-attributed pages in one bounded authorized request", async () => {
  const transport = vi.fn(async (input: RequestInfo | URL) => {
    const request = input as Request;
    expect(request.headers.get("Authorization")).toBe("Bearer reader");
    expect(new URL(request.url).pathname).toBe("/api/v1/discovery");
    expect(new URL(request.url).searchParams.get("limit")).toBe("20");
    return new Response(
      JSON.stringify({
        data: [
          { document: documents[0].document, source: documents[0].source },
        ],
        as_of: "2026-10-08T00:00:00Z",
        pagination: { has_more: true, next_cursor: "frozen+/==" },
        meta: { request_id: "bounded", api_version: "v1" },
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  });
  const adapter = createRealAdapter(
    "https://api.example.test",
    transport,
    "reader",
  );
  const result = await adapter.discovery!({ order: "published_at" });
  expect(result[0].source.name).toBe(documents[0].source.name);
  expect(result[0].intelligenceLoaded).toBe(false);
  expect(result[0].integrity).toBe("unverified");
  expect(result.asOf).toBe("2026-10-08T00:00:00Z");
  expect(result.nextCursor).toBe("frozen+/==");
  expect(transport).toHaveBeenCalledOnce();
});
it("new intelligence real failures stay separate from mock topic memberships", async () => {
  const transport = vi.fn(
    async () =>
      new Response(
        JSON.stringify({
          error: {
            code: "FORBIDDEN",
            message: "Read scope required",
            request_id: "denied",
          },
        }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      ),
  );
  await expect(
    createRealAdapter("https://api.example.test", transport).topics!({}),
  ).rejects.toMatchObject({ code: "FORBIDDEN", requestId: "denied" });
  const mock = createMockAdapter(0);
  const page = await mock.topics!({ cutoff: "2026-10-03T09:00:00Z" });
  expect(page.data.length).toBe(2);
  expect(
    page.data.every((topic) => topic.model.model_version === "0.3.1"),
  ).toBe(true);
});
