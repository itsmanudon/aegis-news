import { expect, test } from "@playwright/test";
import { sources } from "../src/lib/fixtures";
import { operationalApi, operator } from "./operations-support";
test("bounded source registry separates browsing from authorized actions", async ({
  page,
}) => {
  const calls = await operationalApi(page);
  await operator(page);
  await expect(
    page.getByRole("heading", { name: "Source Registry", exact: true }),
  ).toBeVisible();
  const row = page.locator(".source-record").first();
  await expect(row).toContainText(sources[0].name);
  await expect(
    row.getByText(sources[0].source_id, { exact: true }),
  ).not.toBeVisible();
  await row.locator("summary").focus();
  await page.keyboard.press("Enter");
  await expect(
    row.getByText(sources[0].source_id, { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(row.locator("summary")).toBeFocused();
  await page
    .getByRole("navigation", { name: "Source Pages" })
    .getByRole("button", { name: "Next Page", exact: true })
    .click();
  await expect(page.locator(".source-record").first()).toContainText(
    sources[1].name,
  );
  expect(
    calls.filter((c) => c.path.includes("cursor=registry%2B%2F%3D%3D")),
  ).toHaveLength(1);
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
});
test("source creation and ingestion distinguish accepted requests from reported completion", async ({
  page,
}) => {
  const calls = await operationalApi(page, { delay: 500 });
  await operator(page);
  await page.getByLabel("Source Name", { exact: true }).fill("Created Source");
  await page
    .getByRole("button", { name: "Create Source", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Creating Source…", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("status").filter({ hasText: "Created Source" }),
  ).toContainText("src-created");
  await page.getByLabel("Source", { exact: true }).selectOption("src-created");
  await page
    .getByLabel("Article Title", { exact: true })
    .fill("Submitted Article");
  await page
    .getByLabel("Article Text", { exact: true })
    .fill("Source evidence");
  await page.getByLabel("Submission Key", { exact: true }).fill("stable-key");
  await page
    .locator("form[aria-label='Article Submission']")
    .evaluate((form) => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
    });
  await expect(
    page.getByRole("button", { name: "Submitting Articles…", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Request Accepted", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Workflow Completed", { exact: true }),
  ).not.toBeVisible();
  expect(
    calls.filter((c) => c.path.endsWith("/ingestions") && c.method === "POST"),
  ).toHaveLength(1);
  await page
    .getByRole("button", { name: "Check Processing Status", exact: true })
    .click();
  await expect(
    page.getByText("Workflow Completed", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open Result Document", exact: true }),
  ).toHaveAttribute("href", "/documents/doc-known");
});
test("batch submission preserves per-article keys and never reports submission as completion", async ({
  page,
}) => {
  const calls = await operationalApi(page);
  await operator(page);
  await page
    .getByLabel("Source", { exact: true })
    .selectOption(sources[0].source_id);
  await page.getByLabel("Article Title", { exact: true }).fill("First Article");
  await page
    .getByLabel("Article Text", { exact: true })
    .fill("First source text");
  await page.getByLabel("Submission Key", { exact: true }).fill("first-key");
  await page
    .getByRole("button", { name: "Add Another Article", exact: true })
    .click();
  await page.getByLabel("Article Title").nth(1).fill("Second Article");
  await page.getByLabel("Article Text").nth(1).fill("Second source text");
  await page.getByLabel("Submission Key").nth(1).fill("second-key");
  await page.getByRole("button", { name: "Submit Batch", exact: true }).click();
  await expect(
    page.getByText("accepted-workflow-2", { exact: true }),
  ).toBeVisible();
  const request = calls.find((c) => c.path.endsWith("/ingestions/batch"))!
    .body as { items: { idempotency_key: string }[] };
  expect(request.items.map((i) => i.idempotency_key)).toEqual([
    "first-key",
    "second-key",
  ]);
  await expect(
    page.getByText("Workflow Completed", { exact: true }),
  ).not.toBeVisible();
});
test("audit preserves success failure and attempt, technical references and bounded pagination", async ({
  page,
}) => {
  const calls = await operationalApi(page);
  await operator(page, "/security");
  await expect(page.locator(".audit-record")).toHaveCount(3);
  await expect(page.locator(".audit-record").nth(1)).toContainText("failure");
  await expect(page.locator("main")).not.toContainText("Access Denied");
  await page.locator(".audit-record summary").first().click();
  await expect(
    page.getByText("request-0", { exact: true }).first(),
  ).toBeVisible();
  await page.getByLabel("Outcome", { exact: true }).selectOption("failure");
  await expect(page.locator(".audit-record")).toHaveCount(1);
  await page
    .getByRole("navigation", { name: "Audit Pages" })
    .getByRole("button", { name: "Next Page", exact: true })
    .click();
  await expect
    .poll(
      () =>
        calls.filter((c) => c.path.includes("cursor=audit%7C%2B%2F%3D%3D"))
          .length,
    )
    .toBe(1);
});
test("provider controls show configuration without health claims and require explicit acquisition", async ({
  page,
}) => {
  const calls = await operationalApi(page, { delay: 500 });
  await operator(page);
  const provider = page.locator("#provider-operations");
  await expect(
    provider.getByText("Configuration Present", { exact: true }),
  ).toBeVisible();
  await expect(
    provider.getByText("Configuration Missing", { exact: true }),
  ).toBeVisible();
  await expect(
    provider.getByText("Keyless Capability Available", { exact: true }),
  ).toBeVisible();
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
  await provider
    .getByRole("button", { name: "Fetch Bounded Batch", exact: true })
    .click();
  await expect(
    provider.getByRole("button", {
      name: "Submitting Acquisition…",
      exact: true,
    }),
  ).toBeDisabled();
  await expect(
    provider.getByText("Acquisition Running", { exact: true }),
  ).toBeVisible();
  await expect(
    provider.getByText("Acquisition Completed", { exact: true }),
  ).not.toBeVisible();
  await provider
    .getByRole("button", { name: "Check Provider Run", exact: true })
    .click();
  await expect(
    provider.getByText("Request Submitted", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    provider.getByText("Workflow Running", { exact: true }),
  ).toBeVisible();
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(1);
});
test("provider forbidden responses and mode changes preserve authorization and result isolation", async ({
  page,
}) => {
  const calls = await operationalApi(page, { forbidden: true });
  await operator(page);
  await page
    .getByRole("button", { name: "Fetch Bounded Batch", exact: true })
    .click();
  await expect(page.locator("#provider-operations [role=alert]")).toContainText(
    "denied-write",
  );
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(1);
  await page.getByLabel("Data Mode").selectOption("mock");
  await expect(page.locator("#provider-operations")).toContainText(
    "Real API mode",
  );
  await expect(
    page.getByText("denied-write", { exact: false }),
  ).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create Source", exact: true }),
  ).toBeDisabled();
});
test("uncertain submission errors retain drafts and keys with no hidden retry", async ({
  page,
}) => {
  const calls = await operationalApi(page, { forbidden: true });
  await operator(page);
  await page
    .getByLabel("Source", { exact: true })
    .selectOption(sources[0].source_id);
  await page.getByLabel("Article Title", { exact: true }).fill("Retry Article");
  await page.getByLabel("Article Text", { exact: true }).fill("Same content");
  await page
    .getByLabel("Submission Key", { exact: true })
    .fill("same-retry-key");
  await page
    .getByRole("button", { name: "Submit Article", exact: true })
    .click();
  await expect(page.locator("main [role=alert]")).toContainText(
    "Scope revoked",
  );
  await expect(page.getByLabel("Submission Key", { exact: true })).toHaveValue(
    "same-retry-key",
  );
  await expect(
    page.getByText("Request Accepted", { exact: true }),
  ).not.toBeVisible();
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(1);
  await page
    .getByRole("button", { name: "Submit Article", exact: true })
    .click();
  await expect
    .poll(() => calls.filter((c) => c.method === "POST").length)
    .toBe(2);
  const submitted = calls
    .filter((c) => c.method === "POST")
    .map((c) => c.body as { idempotency_key: string; content_base64: string });
  expect(submitted[1].idempotency_key).toBe(submitted[0].idempotency_key);
  expect(submitted[1].content_base64).toBe(submitted[0].content_base64);
});
test("field validation errors are associated with invalid article controls", async ({
  page,
}) => {
  const calls = await operationalApi(page);
  await operator(page);
  await page
    .getByLabel("Source", { exact: true })
    .selectOption(sources[0].source_id);
  const title = page.getByLabel("Article Title", { exact: true });
  await title.fill("   ");
  await page
    .getByLabel("Article Text", { exact: true })
    .fill("Captured evidence");
  await page
    .getByLabel("Submission Key", { exact: true })
    .fill("validation-key");
  await page
    .getByRole("button", { name: "Submit Article", exact: true })
    .click();
  await expect(title).toHaveAttribute("aria-invalid", "true");
  const error = page.getByText("Article Title must contain text.", {
    exact: true,
  });
  await expect(error).toBeVisible();
  await expect(title).toHaveAttribute(
    "aria-describedby",
    (await error.getAttribute("id")) ?? "missing-error-id",
  );
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
});
test("missing workflow state stays unavailable and reported failure remains structured", async ({
  page,
}) => {
  const calls = await operationalApi(page);
  await operator(page);
  await page.route("**/api/v1/ingestion-runs/**", (route) =>
    route.fulfill({
      json: {
        data: { workflow_id: "unknown-workflow", result: null },
        meta: { request_id: "unavailable", api_version: "v1" },
      },
    }),
  );
  await page
    .getByLabel("Workflow ID", { exact: true })
    .fill("unknown-workflow");
  await page
    .getByRole("button", { name: "Check Processing Status", exact: true })
    .click();
  await expect(
    page.getByText("Workflow State Unavailable", { exact: true }),
  ).toBeVisible();
  await page.route("**/api/v1/ingestion-runs/**", (route) =>
    route.fulfill({
      json: {
        data: {
          workflow_id: "failed-workflow",
          status: "FAILED",
          result: null,
          error: { code: "WORKFLOW_FAILED", message: "Source unavailable" },
        },
        meta: { request_id: "failed", api_version: "v1" },
      },
    }),
  );
  await page.getByLabel("Workflow ID", { exact: true }).fill("failed-workflow");
  await page
    .getByRole("button", { name: "Check Processing Status", exact: true })
    .click();
  await expect(
    page.getByText("Workflow Failed", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Reported Error", { exact: true })).toBeVisible();
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
});
test("empty registry audit pages and authentication expiry have honest states", async ({
  page,
}) => {
  await operationalApi(page, { empty: true });
  await operator(page);
  await expect(
    page.getByText("No sources are supplied on this page.", { exact: false }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "Source Pages" })
      .getByRole("button", { name: "Next Page", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("navigation", { name: "Operational Workspaces" })
    .getByRole("link", { name: "Security & Audit", exact: true })
    .click();
  await expect(
    page.getByText("No audit events are supplied on this page.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.route("http://localhost:8000/**", (route) =>
    route.fulfill({
      status: 401,
      json: {
        error: {
          code: "UNAUTHORIZED",
          message: "Session expired",
          request_id: "expired-request",
        },
      },
    }),
  );
  await page.getByRole("button", { name: "Sign Out", exact: true }).click();
  await expect(page.locator("main [role=alert]")).toContainText(
    "Session expired",
  );
  await expect(page.locator(".audit-record")).toHaveCount(0);
  await page.goto("/sources");
  await expect(
    page.getByRole("button", { name: "Create Source", exact: true }),
  ).toBeDisabled();
});
test("leaving an identity cancels pending submission results", async ({
  page,
}) => {
  const calls = await operationalApi(page, { delay: 750 });
  await operator(page);
  await page
    .getByLabel("Source Name", { exact: true })
    .fill("Old identity source");
  await page
    .getByRole("button", { name: "Create Source", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Creating Source…", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Sign Out", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Create Source", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Source Created", { exact: true }),
  ).not.toBeVisible();
  expect(calls.filter((c) => c.method === "POST")).toHaveLength(1);
});
test("operational screens reflow with long records five widths and doubled text", async ({
  page,
}) => {
  await operationalApi(page);
  await page.route("**/api/v1/sources?*", (route) =>
    route.fulfill({
      json: {
        data: [
          {
            ...sources[0],
            name: "Long Registered Source ".repeat(12),
            source_id: `src-${"abc".repeat(90)}`,
            url: `https://example.test/${"long-path".repeat(70)}`,
          },
        ],
        meta: { request_id: "long", api_version: "v1" },
        pagination: { has_more: false, next_cursor: null },
      },
    }),
  );
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/sources", "/security", "/operations"]) {
      await operator(page, path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
    }
  }
  await page.setViewportSize({ width: 720, height: 900 });
  await operator(page, "/sources");
  await page.evaluate(() => {
    const sizes = Array.from(
      document.querySelectorAll<HTMLElement>("main, main *"),
    ).map((element) => ({
      element,
      size: parseFloat(getComputedStyle(element).fontSize),
    }));
    for (const { element, size } of sizes)
      element.style.fontSize = `${size * 2}px`;
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.locator(".source-record summary").first().focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".source-record details").first()).toHaveAttribute(
    "open",
    "",
  );
  expect(
    await page
      .locator(".source-record summary")
      .first()
      .evaluate((element) => getComputedStyle(element).outlineStyle),
  ).not.toBe("none");
});
