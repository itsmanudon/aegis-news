import { expect, test } from "@playwright/test";
import { documents } from "../src/lib/fixtures";
import { expectReaderModel, openStoredMedia } from "./reader-actions";
const doc = documents[0].document.document_id;

test("live reader model locator addresses visible metadata", async ({
  page,
}) => {
  await page.goto(`/documents/${doc}`);
  await expectReaderModel(page, "aegis-topic-demo / 0.3.1");
});

test("live evidence capture opens stored attachments before inspecting them", async ({
  page,
}) => {
  const media = documents.find((view) => view.media.length)!;
  await page.goto(`/documents/${media.document.document_id}`);
  await openStoredMedia(page);
  await expect(page.locator(".media-record").first()).toBeVisible();
  await expect(page.locator(".media-record").first()).toContainText(
    media.media[0].object.content_type,
  );
});

test("changing data mode clears adapter-specific cursors while retaining filters", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", async (route) => {
    const url = new URL(route.request().url());
    const source = url.pathname.endsWith("/sources");
    await route.fulfill({
      json: {
        data: source ? [documents[0].source] : [documents[0].document],
        pagination: {
          has_more: !source && !url.searchParams.has("cursor"),
          next_cursor:
            source || url.searchParams.has("cursor") ? null : "opaque+/==",
        },
        meta: { request_id: "mode-cursor", api_version: "v1" },
      },
    });
  });
  await page.goto("/documents?q=Port");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".editorial-result")).toHaveCount(1);
  await page.getByRole("button", { name: "Next Page", exact: true }).click();
  await expect(page).toHaveURL(/cursor=/);
  await page.getByLabel("Data Mode").selectOption("mock");
  // Literal substring matching also includes the fixture headline "Field report".
  await expect(page.locator(".editorial-result")).toHaveCount(3);
  await expect(page).not.toHaveURL(/cursor=/);
  await expect(page.getByLabel("Filter Documents")).toHaveValue("Port");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".editorial-result")).toHaveCount(1);
  await expect(page).not.toHaveURL(/cursor=/);
});

test("dense register reports absent assessments without claiming queued processing", async ({
  page,
}) => {
  await page.goto("/documents?cutoff=2026-10-03T08%3A04&view=table");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("tbody tr").first()).toContainText(
    "No Assessments Available",
  );
  await expect(page.locator("tbody tr").first()).not.toContainText("Pending");
});

test("optional acquisition denial preserves reporting and real verification subchecks", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const meta = { api_version: "v1", request_id: "synthetic-reader" };
    if (path.endsWith("/acquisition"))
      return route.fulfill({
        status: 403,
        json: {
          error: {
            code: "FORBIDDEN",
            message: "Acquisition denied",
            request_id: "optional-denial",
          },
        },
      });
    if (path.endsWith("/verify"))
      return route.fulfill({
        json: {
          data: {
            valid: false,
            content_verified: false,
            chain_valid: true,
            signature_valid: true,
            reason: "Synthetic content mismatch",
          },
          meta,
        },
      });
    if (path.endsWith("/intelligence"))
      return route.fulfill({
        json: { data: { ...documents[0], mentions: [] }, meta },
      });
    return route.fulfill({
      json: {
        data: [],
        pagination: { has_more: false, next_cursor: null },
        meta,
      },
    });
  });
  await page.goto(`/documents/${doc}`);
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".story-report")).toBeVisible();
  await expect(page.locator(".reader-header")).toContainText(
    "Not Checked in This Session",
  );
  await page
    .locator("summary")
    .filter({ hasText: "Acquisition / Remote Media" })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: "optional-denial" }),
  ).toBeVisible();
  await expect(page.locator(".story-report")).toContainText(
    "manual procedures remain available",
  );
  await page
    .getByRole("button", { name: "Verify Integrity", exact: true })
    .click();
  const results = page.locator(".verification-result");
  await expect(results).toContainText("Failed");
  await expect(
    results.locator(".verification-checks > div").nth(0),
  ).toContainText("Not Valid");
  await expect(
    results.locator(".verification-checks > div").nth(1),
  ).toContainText("Passed");
  await expect(
    results.locator(".verification-checks > div").nth(2),
  ).toContainText("Passed");
  await expect(results).toContainText("Response Received At");
  await page.getByLabel("Data Mode").selectOption("mock");
  await expect(page.locator(".verification-result")).toHaveCount(0);
  await expect(page.locator(".reader-header")).toContainText(
    "Simulated Fixture State",
  );
});

test("real results preserve bounded opaque cursors without per-row intelligence requests", async ({
  page,
}) => {
  const calls: string[] = [];
  const opaque = "opaque+/==";
  await page.route("http://localhost:8000/**", async (route) => {
    const url = new URL(route.request().url());
    calls.push(url.pathname);
    const data = url.pathname.endsWith("/sources")
      ? documents.slice(0, 3).map((view) => view.source)
      : url.searchParams.get("cursor")
        ? [documents[2].document]
        : documents.slice(0, 2).map((view) => view.document);
    if (!url.pathname.endsWith("/sources"))
      expect(url.searchParams.get("limit")).toBe("20");
    await route.fulfill({
      json: {
        data,
        pagination: {
          has_more:
            !url.pathname.endsWith("/sources") &&
            !url.searchParams.get("cursor"),
          next_cursor:
            !url.pathname.endsWith("/sources") &&
            !url.searchParams.get("cursor")
              ? opaque
              : null,
        },
        meta: { request_id: "controlled-page", api_version: "v1" },
      },
    });
  });
  await page.goto("/documents");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".editorial-result")).toHaveCount(2);
  await page
    .locator(".editorial-result")
    .first()
    .locator("summary")
    .filter({ hasText: "Evidence Details" })
    .click();
  await expect(page.locator(".editorial-result").first()).toContainText(
    "Details are not loaded on this archive page",
  );
  expect(
    calls.some(
      (path) =>
        path.endsWith("/intelligence") ||
        path.endsWith("/acquisition") ||
        path.endsWith("/verify"),
    ),
  ).toBe(false);
  await page.getByRole("button", { name: "Next Page", exact: true }).click();
  await expect(page.locator(".editorial-result")).toHaveCount(1);
  expect(new URL(page.url()).searchParams.get("cursor")).toBe(opaque);
  await page.getByLabel("Filter Documents").fill("receipts");
  await expect(page).not.toHaveURL(/cursor=/);
  await expect(page.locator(".editorial-result")).toHaveCount(2);
});

test("real unsupported integrity filters and permission failures never reveal fixtures", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", (route) =>
    route.fulfill({
      status: 401,
      json: {
        error: {
          code: "UNAUTHORIZED",
          message: "Synthetic token required",
          request_id: "reader-auth",
        },
      },
    }),
  );
  await page.goto("/documents?integrity=failed");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(
    page.getByRole("alert").filter({ hasText: "CAPABILITY_UNAVAILABLE" }),
  ).toBeVisible();
  await expect(page.locator(".editorial-result")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Reset Filters", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: "UNAUTHORIZED" }),
  ).toBeVisible();
  await page.goto(`/documents/${doc}`);
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(
    page.getByRole("alert").filter({ hasText: "UNAUTHORIZED" }),
  ).toBeVisible();
  await expect(page.locator(".story-report")).toHaveCount(0);
});

test("slow acquisition and headline-only captures remain independently readable", async ({
  page,
}) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/acquisition")) {
      await gate;
      return route.fulfill({ json: { data: [], meta: {} } });
    }
    await route.fulfill({
      json: {
        data: {
          ...documents[0],
          document: {
            ...documents[0].document,
            text: documents[0].document.title,
            published_at: null,
          },
          analyses: [],
          entities: [],
          events: [],
          mentions: [],
        },
        meta: {},
      },
    });
  });
  await page.goto(`/documents/${doc}`);
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".story-report")).toContainText(
    "Only the headline was captured",
  );
  await expect(page.locator(".reader-header")).toContainText("Unknown");
  await page
    .locator("summary")
    .filter({ hasText: "Acquisition / Remote Media" })
    .click();
  await expect(page.getByText("Loading intelligence records…")).toBeVisible();
  await expect(
    page.getByText("No model intelligence is available for this document."),
  ).toBeVisible();
  release();
  await expect(
    page.getByText("No provider acquisition records are available."),
  ).toBeVisible();
});

test("reader separates reporting, assessments and expandable technical evidence", async ({
  page,
}) => {
  await page.goto(`/documents/${doc}`);
  await expect(page.locator(".story-report")).toContainText(
    "manual procedures remain available",
  );
  await expect(page.locator(".story-report")).not.toContainText("Confidence");
  await expect(
    page.getByRole("heading", {
      name: "Model-Generated Intelligence",
      exact: true,
    }),
  ).toBeVisible();
  const technical = page
    .locator("summary")
    .filter({ hasText: "Technical Metadata" })
    .first();
  await technical.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Configuration Hash", { exact: true }).first(),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(technical).toBeFocused();
  await expect(
    page.getByText("Configuration Hash", { exact: true }).first(),
  ).not.toBeVisible();
  await page
    .getByRole("button", { name: "Run Mock Verification", exact: true })
    .click();
  await expect(page.locator(".verification-result")).toContainText(
    "Response Received At",
  );
  await expect(page.locator(".verification-result")).toContainText(
    "Not Reported",
  );
});

test("editorial results expand without fetching intelligence and keep explicit dense-table access", async ({
  page,
}) => {
  await page.goto("/documents");
  await expect(page.locator(".editorial-result")).toHaveCount(6);
  await expect(page.locator("tbody tr")).toHaveCount(0);
  const disclosure = page
    .locator(".editorial-result")
    .first()
    .locator("summary")
    .filter({ hasText: "Evidence Details" });
  await disclosure.click();
  await expect(page.locator(".editorial-result").first()).toContainText(
    "Model Assessment",
  );
  await page
    .getByRole("button", { name: "Evidence Table", exact: true })
    .click();
  await expect(page.locator("tbody tr")).toHaveCount(6);
  await page
    .getByRole("button", { name: "Expand Evidence", exact: true })
    .first()
    .click();
  await expect(page.locator("tbody tr")).toHaveCount(7);
  await expect(page.locator("tbody tr").nth(1).locator("td")).toHaveAttribute(
    "colspan",
    "6",
  );
  await page
    .getByRole("button", { name: "Collapse Evidence", exact: true })
    .first()
    .press("Escape");
  await expect(
    page.getByRole("button", { name: "Expand Evidence", exact: true }).first(),
  ).toBeFocused();
  await expect(page.locator("tbody tr")).toHaveCount(6);
  await page.setViewportSize({ width: 320, height: 1000 });
  await expect(page.locator(".editorial-result").first()).toBeVisible();
  await expect(page.locator("table")).not.toBeVisible();
});

test("filter URLs restore literal search and cutoff and reset cursors", async ({
  page,
}) => {
  await page.goto("/search?q=credentials&cutoff=2026-10-03T08%3A20&cursor=0");
  await expect(page.getByLabel("Search Terms")).toHaveValue("credentials");
  await expect(page.locator(".editorial-result")).toHaveCount(1);
  await page.getByLabel("Search Terms").fill("receipts");
  await expect(page).not.toHaveURL(/cursor=/);
  await expect(page.locator(".editorial-result")).toHaveCount(1);
  await page.reload();
  await expect(page.getByLabel("Search Terms")).toHaveValue("receipts");
  await page
    .getByRole("button", { name: "Reset Filters", exact: true })
    .click();
  await expect(page).not.toHaveURL(/q=|cutoff=|cursor=/);
  await expect(page.locator(".editorial-result")).toHaveCount(6);
  await expect(
    page.getByRole("status").filter({ hasText: "6 records on this page" }),
  ).toBeVisible();
});

test("reader and expanded results reflow at five widths and a 200-percent layout equivalent", async ({
  page,
}) => {
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto(`/documents/${documents[2].document.document_id}`);
    await expect(page.locator(".story-report")).toBeVisible();
    await expect(page.locator(".reader-header")).toContainText("Unknown");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await page.goto("/documents");
    await page
      .locator(".editorial-result")
      .first()
      .locator("summary")
      .filter({ hasText: "Evidence Details" })
      .click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  // A 1440px desktop at 200% zoom has a 720px CSS layout viewport.
  await page.setViewportSize({ width: 720, height: 500 });
  await page.goto(`/documents/${doc}`);
  await expect(page.locator(".story-report")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => {
    document.body.style.zoom = "2";
  });
  expect(await page.evaluate(() => getComputedStyle(document.body).zoom)).toBe(
    "2",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.evaluate(() => {
    document.body.style.zoom = "1";
  });
});

test("long source headlines and technical metadata reflow while denied checks retain unchecked state", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 1000 });
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/verify"))
      return route.fulfill({
        status: 403,
        json: {
          error: {
            code: "FORBIDDEN",
            message: "Synthetic check denied",
            request_id: "verify-denial",
          },
        },
      });
    if (path.endsWith("/acquisition"))
      return route.fulfill({
        json: {
          data: [
            {
              acquired_at: "2026-10-03T09:00:00Z",
              provider: "gnews",
              content_kind: "provider excerpt",
              publisher_name: "Synthetic Publisher",
              article_url: "https://publisher.example.org/source",
              image_url: null,
              video_url: null,
              author: null,
              provider_item_id: "synthetic-reference",
            },
          ],
          meta: {},
        },
      });
    return route.fulfill({
      json: {
        data: {
          ...documents[0],
          document: { ...documents[0].document, title: "A".repeat(256) },
          analyses: documents[0].analyses.map((analysis) => ({
            ...analysis,
            model_name: "model".repeat(24),
          })),
          mentions: [],
        },
        meta: {},
      },
    });
  });
  await page.goto(`/documents/${doc}`);
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".reader-header")).toContainText(
    "Provider Excerpt",
  );
  await expect(
    page.getByRole("link", { name: "Open Publisher Article", exact: false }),
  ).toHaveAttribute("href", "https://publisher.example.org/source");
  await page
    .locator("summary")
    .filter({ hasText: "Technical Metadata" })
    .first()
    .click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page
    .getByRole("button", { name: "Verify Integrity", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Synthetic check denied" }),
  ).toBeVisible();
  await expect(page.locator(".verification-result")).toHaveCount(0);
  await expect(page.locator(".reader-header")).toContainText(
    "Not Checked in This Session",
  );
});
