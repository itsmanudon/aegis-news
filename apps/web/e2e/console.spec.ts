import { expect, test } from "@playwright/test";
const doc = "doc_00000000-0000-4000-8000-000000000001";
test("operations to document, model metadata, verification and entity evidence", async ({
  page,
}) => {
  await page.goto("/operations");
  await expect(
    page.getByRole("heading", { name: "Operational Overview" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open Evidence Register" }).click();
  await page
    .getByRole("link", {
      name: "Port Meridian reports disruption to cargo scheduling",
      exact: true,
    })
    .click();
  await page
    .locator("summary")
    .filter({ hasText: "Record Timestamps" })
    .click();
  for (const label of [
    "Published",
    "First Seen",
    "Ingested",
    "Intelligence Available",
  ])
    await expect(
      page
        .locator(".time-rail dt")
        .filter({ hasText: new RegExp("^" + label + "$") }),
    ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Source Reporting" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Model-Generated Intelligence" }),
  ).toBeVisible();
  await expect(
    page.getByText("aegis-topic-demo / 0.3.1").first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run Mock Verification" }).click();
  await expect(
    page.getByText("Simulated result · Fixture content and signature match."),
  ).toBeVisible();
  await page
    .locator("summary")
    .filter({ hasText: "Resolved Entities" })
    .click();
  await page.getByRole("link", { name: "Port Meridian location" }).click();
  await expect(
    page.getByRole("heading", { name: "Port Meridian", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", {
      name: "Port Meridian reports disruption to cargo scheduling",
    }),
  ).toBeVisible();
});
test("feed filters, empty state and historical availability", async ({
  page,
}) => {
  await page.goto("/documents");
  await expect(
    page.getByRole("status").filter({ hasText: "6 records on this page" }),
  ).toBeVisible();
  await page.getByLabel("Integrity", { exact: true }).selectOption("failed");
  await expect(
    page.getByRole("link", {
      name: "Northstar Logistics issues advisory on credential exposure",
    }),
  ).toBeVisible();
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(1);
  await page.getByRole("button", { name: "Reset Filters" }).click();
  await page.getByLabel("Filter Documents").fill("no-match-value");
  await expect(page.getByText("No records match these filters.")).toBeVisible();
  await page.getByRole("button", { name: "Reset Filters" }).click();
  await page.getByLabel("Knowledge Cutoff (UTC)").fill("2026-10-03T08:04");
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(1);
  await expect(
    page.getByText("No Assessments Available", { exact: true }),
  ).toBeVisible();
});
test("search source text and reset results", async ({ page }) => {
  await page.goto("/search");
  await page.getByLabel("Search Terms").fill("credentials");
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(1);
  await expect(
    page.getByRole("link", {
      name: "Northstar Logistics issues advisory on credential exposure",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Reset Filters" }).click();
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(6);
});
test("timeline evidence filtering and security source shells", async ({
  page,
}) => {
  await page.goto("/events");
  await page.getByLabel("Evidence Kind").selectOption("model_output");
  await expect(page.locator(".timeline > li")).toHaveCount(1);
  await expect(page.getByText("Model Output", { exact: true })).toBeVisible();
  await page
    .getByRole("link", { name: "Operations & Security", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Audit / Security", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Session Context" }),
  ).toBeVisible();
  await page.getByLabel("Outcome", { exact: true }).selectOption("denied");
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(1);
  await page
    .getByRole("link", { name: "Sources / Admin", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Maritime Operations Bulletin" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Administration", exact: true }),
  ).toBeVisible();
});
test("failed and unsigned verification remain distinct", async ({ page }) => {
  await page.goto("/documents/doc_00000000-0000-4000-8000-000000000002");
  await page.getByRole("button", { name: "Run Mock Verification" }).click();
  await expect(
    page.getByText(
      "Simulated result · Fixture signature does not match. Hold for review.",
    ),
  ).toBeVisible();
  await page.goto("/documents/doc_00000000-0000-4000-8000-000000000003");
  await page
    .locator("summary")
    .filter({ hasText: "Media / Attachments" })
    .click();
  await expect(
    page.getByText("corridor-report.txt", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run Mock Verification" }).click();
  await expect(
    page.getByText(
      "Simulated result · Fixture has no signature. Integrity is unverified.",
    ),
  ).toBeVisible();
});
test("real mode clears fixture records and identity, makes only contracted requests", async ({
  page,
}) => {
  const requested: string[] = [];
  await page.route("http://localhost:8000/**", async (route) => {
    requested.push(new URL(route.request().url()).pathname);
    if (!route.request().url().includes("/system/info")) {
      await route.fulfill({
        status: 401,
        json: {
          error: {
            code: "UNAUTHORIZED",
            message: "Token Required",
            request_id: "real-1",
          },
        },
      });
      return;
    }
    await route.fulfill({
      json: {
        data: {
          name: "AegisNews",
          version: "0.1.0",
          stage: "foundation",
          architecture: "modular monolith + background workers",
        },
        meta: { request_id: "real-1", api_version: "v1" },
      },
    });
  });
  await page.goto("/documents");
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(6);
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(
    page.getByText("Token Required", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(0);
  await expect(
    page.locator(".identity").getByText("Token Required"),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Operations & Security", exact: true })
    .click();
  await expect(page.getByText("Connected", { exact: true })).toBeVisible();
  expect(requested.length).toBeGreaterThan(0);
  expect(new Set(requested)).toEqual(
    new Set([
      "/api/v1/documents",
      "/api/v1/sources",
      "/api/v1/events",
      "/api/v1/system/info",
      "/api/v1/provider-articles",
      "/api/v1/youtube-references",
    ]),
  );
  await page.getByLabel("Data Mode").selectOption("mock");
  await expect(page.getByText("Simulated Identity")).toBeVisible();
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(6);
});
test("network failure and missing document have recoverable states", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", (route) => route.abort());
  await page.goto("/");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(
    page
      .getByText(
        "Unable to reach the API. Check the API address and connection.",
      )
      .first(),
  ).toBeVisible();
  await page.getByLabel("Data Mode").selectOption("mock");
  await page.goto("/documents/unknown");
  await expect(page.getByText("Document was not found.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
});
test("provenance view shows operation evidence", async ({ page }) => {
  await page.goto("/provenance");
  await page
    .locator("summary")
    .filter({ hasText: "Provenance Operations" })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Provenance / Integrity", exact: true }),
  ).toHaveCount(7);
  await page
    .locator("summary")
    .filter({ hasText: "Operation Evidence" })
    .first()
    .click();
  await expect(
    page.locator("details[open] details[open]").getByText(doc, { exact: true }),
  ).toBeVisible();
});
test("mobile navigation and keyboard skip link", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  const menu = page.getByRole("button", { name: "Navigation", exact: true });
  await menu.click();
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Document Archive" }),
  ).toBeVisible();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
test("capture desktop operations", async ({ page }) => {
  await page.goto("/operations");
  await expect(page.locator("tbody tr, .editorial-result")).toHaveCount(6);
  await page.screenshot({
    path: "test-results/operations-desktop.png",
    fullPage: true,
  });
});
