import { expect, test, type Page } from "@playwright/test";
import { documents, entities } from "../src/lib/fixtures";

async function controlledPages(page: Page) {
  const requests: string[] = [];
  await page.route("http://localhost:8000/**", async (route) => {
    const url = new URL(route.request().url());
    requests.push(url.pathname + url.search);
    const meta = { request_id: "phase1c-controlled", api_version: "v1" };
    let data: unknown = [];
    let next: string | null = null;
    if (url.pathname.endsWith("/security/me"))
      data = {
        subject: "Controlled reader",
        roles: ["analyst"],
        scopes: ["documents:read", "security:verify"],
      };
    else if (url.pathname.endsWith("/sources")) data = [documents[0].source];
    else if (url.pathname.endsWith("/intelligence")) data = documents[0];
    else if (url.pathname.endsWith("/entities")) {
      data = [entities[url.searchParams.has("cursor") ? 1 : 0]];
      next = url.searchParams.has("cursor") ? null : "directory+/==";
    } else if (url.pathname.includes("/entities/")) data = entities[0];
    else if (url.pathname.endsWith("/documents")) {
      data = [documents[url.searchParams.has("cursor") ? 4 : 0].document];
      next = url.searchParams.has("cursor") ? null : "evidence+/==";
    }
    await route.fulfill({
      json: { data, meta, pagination: { has_more: !!next, next_cursor: next } },
    });
  });
  return requests;
}

test("event revisions retain identity, separate timestamps and bounded page order", async ({
  page,
}) => {
  const calls: string[] = [];
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  const first = {
    ...documents[0].events[0],
    summary: "Initial source statement",
    revision: 1,
    occurred_at: "2026-10-03T07:00:00Z",
  };
  const second = {
    ...first,
    summary: "Revised model assessment",
    revision: 2,
    evidence_kind: "model_output",
    occurred_at: null,
    available_at: "2026-10-03T10:00:00Z",
  };
  await page.route("http://localhost:8000/**", async (route) => {
    const url = new URL(route.request().url());
    calls.push(url.pathname + url.search);
    await route.fulfill({
      json: {
        data: url.searchParams.has("cursor")
          ? [{ ...second, event_id: "next-event", revision: 3 }]
          : [first, second],
        pagination: {
          has_more: !url.searchParams.has("cursor"),
          next_cursor: url.searchParams.has("cursor")
            ? null
            : "event:revision+/==",
        },
        meta: { request_id: "revisions", api_version: "v1" },
      },
    });
  });
  await page.goto("/events");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".event-record")).toHaveCount(2);
  await expect(page.locator(".event-record").first()).toContainText(
    "Revised model assessment",
  );
  await expect(page.locator(".event-record").first()).toContainText("Unknown");
  await expect(page.locator(".event-record").first()).toContainText(
    "Intelligence Available",
  );
  await page.getByLabel("Order on This Page").selectOption("occurred_at");
  await expect(page.locator(".event-record").first()).toContainText(
    "Initial source statement",
  );
  await expect(page.locator(".event-record").first()).toContainText(
    "Source Statement",
  );
  expect(errors.some((text) => text.includes("same key"))).toBe(false);
  expect(calls).toHaveLength(1);
  await page.getByRole("button", { name: "Next Page", exact: true }).click();
  await expect(page.locator(".event-record")).toHaveCount(1);
  expect(calls[1]).toContain("cursor=event%3Arevision%2B%2F%3D%3D");
  expect(calls.every((url) => url.includes("limit=20"))).toBe(true);
});

test("entity directory exposes technical identity on demand without invented totals", async ({
  page,
}) => {
  await page.goto("/entities");
  await expect(
    page.getByRole("heading", { name: "Entity Directory", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".entity-entry")).toHaveCount(3);
  const entry = page.locator(".entity-entry").first();
  await expect(entry).toContainText("Location");
  await expect(
    entry.getByText(entities[0].entity_id, { exact: true }),
  ).not.toBeVisible();
  const disclosure = entry.locator("summary");
  await disclosure.focus();
  await page.keyboard.press("Enter");
  await expect(
    entry.getByText(entities[0].entity_id, { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(disclosure).toBeFocused();
  await entry.getByRole("link", { name: "Inspect Entity" }).click();
  await expect(
    page.getByRole("heading", { name: "Port Meridian", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".editorial-result").first()).toBeVisible();
});

test("real entity and associated evidence browsing stays bounded and expands without intelligence traffic", async ({
  page,
}) => {
  const requests = await controlledPages(page);
  await page.goto("/entities");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".entity-entry")).toHaveCount(1);
  await page.getByRole("button", { name: "Next Page", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Northstar Logistics", exact: true }),
  ).toBeVisible();
  expect(
    requests.filter((path) => path.startsWith("/api/v1/entities?")),
  ).toHaveLength(2);
  expect(
    requests.some((path) => path.includes("cursor=directory%2B%2F%3D%3D")),
  ).toBe(true);
  await page.getByRole("button", { name: "First Page", exact: true }).click();
  await page.getByRole("link", { name: "Inspect Entity" }).click();
  await expect(page.locator(".editorial-result")).toHaveCount(1);
  await page.locator(".editorial-result summary").click();
  await expect(page.locator(".editorial-result")).toContainText(
    "Literal Source Excerpt",
  );
  expect(requests.some((path) => path.includes("/intelligence"))).toBe(false);
  await page.getByRole("button", { name: "Next Page", exact: true }).click();
  await expect(page.locator(".editorial-result")).toContainText(
    documents[4].document.title,
  );
  expect(
    requests.some(
      (path) =>
        path.includes("entity_id=") &&
        path.includes("cursor=evidence%2B%2F%3D%3D"),
    ),
  ).toBe(true);
  await page.getByLabel("Data Mode").selectOption("mock");
  await expect(page.locator(".editorial-result")).toHaveCount(
    documents.filter((view) =>
      view.entities.some(
        (entity) => entity.entity_id === entities[0].entity_id,
      ),
    ).length,
  );
});

test("verification workspace selects one document before loading evidence or checking", async ({
  page,
}) => {
  await page.goto("/provenance");
  await expect(
    page.getByRole("heading", { name: "Verification Workspace", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run Mock Verification" }),
  ).toHaveCount(0);
  await page
    .getByLabel("Select Document", { exact: true })
    .selectOption(documents[0].document.document_id);
  await expect(
    page.getByRole("heading", { name: "Verification Inspector", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".verification-current")).toContainText(
    "Not Checked",
  );
  await page.getByRole("button", { name: "Run Mock Verification" }).click();
  await expect(page.locator(".verification-result")).toContainText(
    "Simulated Mock Result",
  );
  await expect(page.locator(".verification-result")).toContainText(
    "Provenance Chain",
  );
  await page
    .getByLabel("Select Document", { exact: true })
    .selectOption(documents[1].document.document_id);
  await expect(page.locator(".verification-current")).toContainText(
    "Not Checked",
  );
  await expect(page.locator(".verification-result")).toHaveCount(0);
});

test("an indeterminate unsigned mock check is unavailable rather than failed", async ({
  page,
}) => {
  await page.goto("/provenance");
  await page
    .getByLabel("Select Document", { exact: true })
    .selectOption(documents[2].document.document_id);
  await page
    .getByRole("button", { name: "Run Mock Verification", exact: true })
    .click();
  await expect(page.locator(".verification-result")).toContainText(
    "Simulated Mock Result",
  );
  await expect(page.locator(".verification-current")).toContainText(
    "Unavailable",
  );
  await expect(page.locator(".verification-current")).not.toContainText(
    "Failed",
  );
  await expect(page.locator(".verification-result > .badge")).toHaveText(
    "Unavailable",
  );
  await expect(page.locator(".verification-result")).toContainText(
    "Simulated Unsigned",
  );
});

test("events distinguish every supplied supporting document link", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", async (route) =>
    route.fulfill({
      json: {
        data: [
          {
            ...documents[0].events[0],
            document_ids: documents
              .slice(0, 2)
              .map((view) => view.document.document_id),
          },
        ],
        pagination: { has_more: false, next_cursor: null },
        meta: { request_id: "multiple-links", api_version: "v1" },
      },
    }),
  );
  await page.goto("/events");
  await page.getByLabel("Data Mode").selectOption("real");
  const entry = page.locator(".event-record");
  await expect(
    entry.getByRole("link", {
      name: `Open Supporting Document 1, Reference ${documents[0].document.document_id}`,
      exact: true,
    }),
  ).toHaveAttribute("href", `/documents/${documents[0].document.document_id}`);
  await expect(
    entry.getByRole("link", {
      name: `Open Supporting Document 2, Reference ${documents[1].document.document_id}`,
      exact: true,
    }),
  ).toHaveAttribute("href", `/documents/${documents[1].document.document_id}`);
});

test("empty directory has an explicit unavailable evidence state", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", async (route) =>
    route.fulfill({
      json: {
        data: [],
        pagination: { has_more: false, next_cursor: null },
        meta: { request_id: "empty-directory", api_version: "v1" },
      },
    }),
  );
  await page.goto("/entities");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(
    page.getByText("No entities are available on this page.", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".entity-entry")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Next Page", exact: true }),
  ).toBeDisabled();
});

test("authorized verification keeps loading, mixed outcomes and failures distinct", async ({
  page,
}) => {
  const requests = await controlledPages(page);
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let checks = 0;
  await page.route("**/api/v1/documents/*/verify", async (route) => {
    expect(route.request().headers().authorization).toBe(
      "Bearer synthetic-verification",
    );
    checks++;
    if (checks === 1) await held;
    if (checks === 2)
      return route.fulfill({
        status: 403,
        json: {
          error: {
            code: "FORBIDDEN",
            message: "Verification scope denied",
            request_id: "denied-check",
          },
        },
      });
    await route.fulfill({
      json: {
        data: {
          valid: checks > 2,
          content_verified: checks > 2,
          chain_valid: true,
          signature_valid: checks > 2,
          reason: "Controlled integrity response",
        },
        meta: { request_id: "controlled-check", api_version: "v1" },
      },
    });
  });
  await page.goto("/provenance");
  await page.getByLabel("Data Mode").selectOption("real");
  await page.getByLabel("Access Token").fill("synthetic-verification");
  await page.getByRole("button", { name: "Use Token", exact: true }).click();
  await page
    .getByLabel("Select Document", { exact: true })
    .selectOption(documents[0].document.document_id);
  await expect(page.locator(".verification-current")).toContainText(
    "Not Checked",
  );
  expect(checks).toBe(0);
  expect(requests.filter((url) => url.includes("/intelligence"))).toHaveLength(
    1,
  );
  const action = page.getByRole("button", {
    name: "Verify Integrity",
    exact: true,
  });
  await action.click();
  await expect(page.locator(".verification-current")).toContainText("Checking");
  await expect(
    page.getByRole("button", { name: "Checking…", exact: true }),
  ).toBeDisabled();
  release();
  await expect(page.locator(".verification-current")).toContainText("Failed");
  const result = page.locator(".verification-result");
  await expect(result.locator("dl > div").nth(0)).toContainText(
    "Content IntegrityFailed",
  );
  await expect(result.locator("dl > div").nth(1)).toContainText(
    "Provenance ChainPassed",
  );
  await expect(result.locator("dl > div").nth(2)).toContainText(
    "Digital SignatureFailed",
  );
  await expect(result).toContainText("Response Received At");
  await action.click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "Verification scope denied",
  );
  await expect(page.locator(".verification-current")).toContainText(
    "Unavailable",
  );
  await expect(result).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText("unsigned");
  await action.click();
  await expect(page.locator(".verification-current")).toContainText("Passed");
  expect(checks).toBe(3);
  await page.getByLabel("Data Mode").selectOption("mock");
  await expect(page.getByLabel("Select Document", { exact: true })).toHaveValue(
    "",
  );
  await expect(result).toHaveCount(0);
});

test("entity failures and empty linked evidence preserve the identity boundary", async ({
  page,
}) => {
  await controlledPages(page);
  await page.route("**/api/v1/documents?**", async (route) =>
    route.fulfill({
      json: {
        data: [],
        pagination: { has_more: false, next_cursor: null },
        meta: { request_id: "no-links", api_version: "v1" },
      },
    }),
  );
  await page.goto(`/entities/${entities[0].entity_id}`);
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(
    page.getByRole("heading", { name: "Port Meridian", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("No associated source records are available on this page.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.route("**/api/v1/entities?**", async (route) =>
    route.fulfill({
      status: 401,
      json: {
        error: {
          code: "UNAUTHORIZED",
          message: "Token required for entity records",
          request_id: "entity-auth",
        },
      },
    }),
  );
  await page.goto("/entities");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "UNAUTHORIZED",
  );
  await expect(page.locator(".entity-entry")).toHaveCount(0);
  await expect(
    page.getByRole("navigation", { name: "Entity Directory Pages" }),
  ).toContainText("Page availability is unknown.");
});

test("changing the selected document cancels a pending check and clears its result", async ({
  page,
}) => {
  let oldRequestFinished = false;
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/verify")) return route.abort("failed");
    const data = path.endsWith("/sources")
      ? documents.slice(0, 2).map((view) => view.source)
      : path.endsWith("/intelligence")
        ? documents.find((view) => path.includes(view.document.document_id))
        : documents.slice(0, 2).map((view) => view.document);
    await route.fulfill({
      json: {
        data,
        pagination: { has_more: false, next_cursor: null },
        meta: { request_id: "selection-cancel", api_version: "v1" },
      },
    });
  });
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/documents/*/verify", async (route) => {
    await held;
    await route
      .fulfill({
        json: {
          data: {
            valid: true,
            content_verified: true,
            chain_valid: true,
            signature_valid: true,
            reason: "Late old selection",
          },
          meta: { request_id: "old-check", api_version: "v1" },
        },
      })
      .catch(() => {});
    oldRequestFinished = true;
  });
  await page.goto("/provenance");
  await page.getByLabel("Data Mode").selectOption("real");
  await page
    .getByLabel("Select Document", { exact: true })
    .selectOption(documents[0].document.document_id);
  await page
    .getByRole("button", { name: "Verify Integrity", exact: true })
    .click();
  await expect(page.locator(".verification-current")).toContainText("Checking");
  await page
    .getByLabel("Select Document", { exact: true })
    .selectOption(documents[1].document.document_id);
  await expect(page.locator(".verification-current")).toContainText(
    "Not Checked",
  );
  release();
  await expect.poll(() => oldRequestFinished).toBe(true);
  await expect(page.locator(".verification-result")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText("Late old selection");
});

test("native browser zoom when Chromium handles its keyboard shortcut", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/entities");
  await expect(page.locator(".entity-entry")).toHaveCount(3);
  const before = await page.evaluate(() => ({
    ratio: devicePixelRatio,
    width: innerWidth,
  }));
  for (let index = 0; index < 5; index++)
    await page.keyboard.press("Control+Equal");
  const after = await page.evaluate(() => ({
    ratio: devicePixelRatio,
    width: innerWidth,
  }));
  await page.keyboard.press("Control+Digit0");
  test.skip(
    after.ratio === before.ratio && after.width === before.width,
    "Headless Chromium did not apply native browser zoom; doubled text-size and five-width reflow checks still run.",
  );
  expect(after.ratio / before.ratio).toBeGreaterThanOrEqual(1.9);
});

test("long identity values and missing metadata remain readable at narrow width", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", async (route) =>
    route.fulfill({
      json: {
        data: [
          {
            ...entities[0],
            entity_id: "long-" + "x".repeat(120),
            canonical_name: "Long canonical name ".repeat(16),
            created_at: "invalid-time",
          },
        ],
        pagination: { has_more: false, next_cursor: null },
        meta: { request_id: "long-identity", api_version: "v1" },
      },
    }),
  );
  await page.setViewportSize({ width: 320, height: 1000 });
  await page.goto("/entities");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".entity-entry")).toHaveCount(1);
  await page.locator(".entity-entry summary").click();
  await expect(page.locator(".entity-entry")).toContainText("Unknown");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
});

test("research and expanded evidence reflow across the approved widths and text scaling", async ({
  page,
}) => {
  for (const url of [
    "/entities",
    `/entities/${entities[0].entity_id}`,
    "/events",
    "/provenance",
  ]) {
    await page.goto(url);
    if (url === "/provenance") {
      await page
        .getByLabel("Select Document", { exact: true })
        .selectOption(documents[0].document.document_id);
      await expect(
        page.getByRole("button", { name: "Run Mock Verification" }),
      ).toBeVisible();
    } else await expect(page.locator("main h1")).toBeVisible();
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      const disclosure = page.locator("main summary").first();
      await disclosure.focus();
      await page.keyboard.press("Enter");
      await expect(page.locator("main details").first()).toHaveAttribute(
        "open",
        "",
      );
      await expect(disclosure).toBeFocused();
      await expect(disclosure).toHaveCSS("outline-style", "solid");
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      ).toBe(true);
      await page.keyboard.press("Escape");
    }
    await page.setViewportSize({ width: 720, height: 1000 });
    await page.evaluate(() => {
      const sizes = Array.from(
        document.querySelectorAll<HTMLElement>("main *"),
      ).map((element) => ({
        element,
        size: parseFloat(getComputedStyle(element).fontSize),
      }));
      sizes.forEach(
        ({ element, size }) => (element.style.fontSize = `${size * 2}px`),
      );
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await page.evaluate(() =>
      document
        .querySelectorAll<HTMLElement>("main *")
        .forEach((element) => element.style.removeProperty("font-size")),
    );
  }
});
