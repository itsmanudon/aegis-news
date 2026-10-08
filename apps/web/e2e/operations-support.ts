import { expect, type Page } from "@playwright/test";
import { sources } from "../src/lib/fixtures";

export async function operationalApi(
  page: Page,
  options: {
    delay?: number;
    forbidden?: boolean;
    empty?: boolean;
    outcomes?: string[];
  } = {},
) {
  const calls: { path: string; method: string; body: unknown }[] = [];
  await page.route("http://localhost:8000/**", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    calls.push({
      path: url.pathname + url.search,
      method: request.method(),
      body: request.method() === "POST" ? request.postDataJSON() : null,
    });
    const meta = { request_id: "phase1d-controlled", api_version: "v1" };
    let data: unknown = [],
      next: string | null = null;
    if (url.pathname.endsWith("/security/me"))
      data = {
        subject: "Controlled operator",
        roles: ["operator"],
        scopes: [
          "sources:read",
          "sources:write",
          "ingestions:write",
          "documents:read",
          "audit:read",
          "security:verify",
        ],
      };
    else if (request.method() === "POST") {
      if (options.delay) await new Promise((r) => setTimeout(r, options.delay));
      if (options.forbidden) {
        await route.fulfill({
          status: 403,
          json: {
            error: {
              code: "FORBIDDEN",
              message: "Scope revoked",
              request_id: "denied-write",
            },
          },
        });
        return;
      }
      if (url.pathname.endsWith("/sources"))
        data = {
          ...sources[0],
          source_id: "src-created",
          name: request.postDataJSON().name,
        };
      else if (url.pathname.endsWith("/batch"))
        data = {
          submissions: request
            .postDataJSON()
            .items.map((_: unknown, i: number) => ({
              workflow_id: `accepted-workflow-${i + 1}`,
            })),
        };
      else if (url.pathname.includes("/providers/"))
        data = {
          run_id: "provider-known",
          created_at: "2026-10-08T10:00:00Z",
          status: "running",
          outcomes: [],
          workflow_statuses: {},
        };
      else data = { workflow_id: "accepted-workflow" };
    } else if (url.pathname.includes("/ingestion-runs/"))
      data = {
        workflow_id: url.pathname.split("/").pop(),
        status: "COMPLETED",
        result: { document_id: "doc-known", ingestion_id: "ing-known" },
      };
    else if (url.pathname.endsWith("/sources")) {
      data = options.empty
        ? []
        : [sources[url.searchParams.has("cursor") ? 1 : 0]];
      next =
        options.empty || url.searchParams.has("cursor") ? null : "registry+/==";
    } else if (url.pathname.endsWith("/providers"))
      data = [
        { provider: "gnews", enabled: true, mode: "manual local development" },
        {
          provider: "newsapi",
          enabled: false,
          mode: "manual local development",
        },
        { provider: "gdelt", enabled: true, mode: "manual local development" },
      ];
    else if (url.pathname.includes("/provider-runs/"))
      data = {
        run_id: "provider-known",
        created_at: "2026-10-08T10:00:00Z",
        completed_at: "2026-10-08T10:02:00Z",
        status: "submitted",
        outcomes: [
          {
            provider: "gnews",
            status: "submitted",
            fetched: 2,
            submitted: 1,
            duplicates: 1,
            skipped: 0,
            images: 0,
            videos: 0,
            requests: 1,
            workflow_ids: ["ingestion-known"],
          },
        ],
        workflow_statuses: { "ingestion-known": "RUNNING" },
      };
    else if (url.pathname.endsWith("/security/audit")) {
      data = options.empty
        ? []
        : (options.outcomes ?? ["success", "failure", "attempt"]).map(
            (outcome, i) => ({
              event_id: `audit-${i}-${url.searchParams.has("cursor")}`,
              occurred_at: "2026-10-08T10:00:00Z",
              action:
                i === 1 ? "signature_verification" : "source_modification",
              outcome,
              actor_hash: i ? "actor-hash" : null,
              subject_hash: "subject-hash",
              request_id: `request-${i}`,
            }),
          );
      next =
        options.empty || url.searchParams.has("cursor") ? null : "audit|+/==";
    }
    await route.fulfill({
      json: { data, meta, pagination: { has_more: !!next, next_cursor: next } },
    });
  });
  return calls;
}
export async function operator(page: Page, path = "/sources") {
  await page.goto(path);
  await page.getByLabel("Data Mode").selectOption("real");
  await page.getByLabel("Access Token").fill("synthetic-operator");
  await page.getByRole("button", { name: "Use Token", exact: true }).click();
  await expect(page.locator(".identity")).toContainText("Controlled operator");
}
