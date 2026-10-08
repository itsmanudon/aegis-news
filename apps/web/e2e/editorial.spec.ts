import { expect, test } from "@playwright/test";
import { documents } from "../src/lib/fixtures";

const headline = "Port Meridian reports disruption to cargo scheduling";

test("pinned local editorial and interface fonts load in the browser", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".story-lead")).toBeVisible();
  const fonts = await page.evaluate(async () => {
    await document.fonts.ready;
    const loaded = Array.from(document.fonts)
      .filter((font) => font.status === "loaded")
      .map((font) => font.family.replaceAll('"', ""));
    const serif = getComputedStyle(document.querySelector(".story-lead h3")!)
      .fontFamily.split(",")[0]
      .trim()
      .replaceAll('"', "");
    const ui = getComputedStyle(document.body)
      .fontFamily.split(",")[0]
      .trim()
      .replaceAll('"', "");
    return { serif: loaded.includes(serif), ui: loaded.includes(ui) };
  });
  expect(fonts).toEqual({ serif: true, ui: true });
});

test("desktop masthead aligns with the editorial reading grid", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.locator(".story-lead")).toBeVisible();
  const brand = await page
    .getByRole("link", { name: "Aegis News Discover", exact: true })
    .boundingBox();
  const heading = await page
    .getByRole("heading", { name: "A Wider View. A Closer Read." })
    .boundingBox();
  expect(brand).not.toBeNull();
  expect(heading).not.toBeNull();
  expect(Math.abs(brand!.x - heading!.x)).toBeLessThanOrEqual(1);
});

test("Discover presents attributed archive evidence without ranking or integrity claims", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A Wider View. A Closer Read." }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "From the Archive", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: headline, exact: true }),
  ).toBeVisible();
  await expect(page.locator(".story-lead")).toContainText(
    "Maritime Operations Bulletin",
  );
  await expect(page.locator(".story-lead")).toContainText(
    "manual procedures remain available",
  );
  await expect(page.locator(".story-lead")).toContainText("Source Excerpt");
  await expect(page.locator(".story-lead time").first()).toHaveAttribute(
    "datetime",
    "2026-10-03T08:00:00.000Z",
  );
  await expect(page.locator(".story-row")).toHaveCount(5);
  await expect(page.locator("#main-content")).not.toContainText("Latest News");
  await expect(page.locator("#main-content")).not.toContainText("verified");
  await expect(
    page.getByRole("heading", { name: "Operational Overview" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("status").filter({ hasText: "Mock Workspace" }),
  ).toBeVisible();
  await page.getByRole("link", { name: headline, exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Source Facts", exact: true }),
  ).toBeVisible();
});

test("Operations retains the overview and existing administration routes", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("link", { name: "Operations & Security", exact: true })
    .click();
  await expect(page).toHaveURL(/\/operations$/);
  await expect(
    page.getByRole("heading", { name: "Operational Overview", exact: true }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(6);
  await expect(
    page.getByRole("heading", { name: "Review Queue", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Sources / Admin", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Administration", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Audit / Security", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Session Context", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "News & Intelligence", exact: true })
    .click();
  await expect(page).toHaveURL(/\/$/);
});

test("mobile navigation supports Escape, focus restoration and route changes", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const menu = page.getByRole("button", { name: "Navigation", exact: true });
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect(
    page.getByRole("link", { name: "Search", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await expect(menu).toBeFocused();
  await menu.click();
  await page
    .getByRole("link", { name: "Events / Timeline", exact: true })
    .click();
  await expect(page).toHaveURL(/\/events$/);
  await expect(menu).toHaveAttribute("aria-expanded", "false");
});

test("editorial and existing pages reflow with local fonts and with fallback fonts", async ({
  page,
  browser,
}) => {
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/");
    await expect(page.locator(".story-lead")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    await page.goto("/documents");
    await expect(page.locator("tbody tr")).toHaveCount(6);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
  // A fresh context prevents previously loaded web fonts from masking a failed download.
  const fallbackContext = await browser.newContext({
    viewport: { width: 320, height: 1000 },
  });
  await fallbackContext.route("**/*.woff2", (route) => route.abort());
  const fallbackPage = await fallbackContext.newPage();
  await fallbackPage.goto("/");
  await expect(fallbackPage.locator(".story-lead")).toBeVisible();
  await fallbackPage.evaluate(() => document.fonts.ready);
  expect(
    await fallbackPage.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await fallbackContext.close();
});

test("long source strings and media titles wrap at narrow mobile width", async ({
  page,
}) => {
  const token = "a".repeat(300);
  await page.setViewportSize({ width: 320, height: 1000 });
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const data =
      path === "/api/v1/documents"
        ? documents
            .slice(0, 4)
            .map(({ document }) => ({
              ...document,
              title: token,
              text: `https://source.example.org/${token}`,
            }))
        : path === "/api/v1/sources"
          ? documents.map(({ source }) => ({ ...source, name: token }))
          : path === "/api/v1/provider-articles"
            ? [
                {
                  article_id: "synthetic-long-title",
                  acquired_at: "2026-10-04T10:00:00Z",
                  document_id: null,
                  title: token,
                  source_id: documents[0].source.source_id,
                  published_at: null,
                  workflow_id: "synthetic-workflow",
                  evidence: [
                    {
                      provider: "gnews",
                      provider_item_id: "synthetic-item",
                      publisher_name: token,
                      article_url: "https://publisher.example.org/report",
                      author: null,
                      image_url: null,
                      video_url: null,
                      acquired_at: "2026-10-04T10:00:00Z",
                      content_kind: "provider excerpt",
                    },
                  ],
                },
              ]
            : [];
    await route.fulfill({
      json: {
        data,
        pagination: { has_more: false, next_cursor: null },
        meta: { request_id: "controlled-long-text", api_version: "v1" },
      },
    });
  });
  await page.goto("/");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".story-lead")).toContainText(token);
  await expect(page.locator(".story-row")).toHaveCount(3);
  await expect(page.getByText("Awaiting pipeline completion.")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("real permission failures clear the mock homepage while preserving navigation", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", (route) =>
    route.fulfill({
      status: 403,
      json: {
        error: {
          code: "FORBIDDEN",
          message: "This identity cannot read this evidence.",
          request_id: "editorial-denial",
        },
      },
    }),
  );
  await page.goto("/");
  await expect(page.locator(".story-lead")).toBeVisible();
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(page.locator(".story-lead")).toHaveCount(0);
  await expect(page.getByRole("alert").first()).toContainText("FORBIDDEN");
  await expect(page.getByRole("alert").first()).toContainText(
    "editorial-denial",
  );
  await expect(
    page.getByRole("status").filter({ hasText: "Real API" }),
  ).toBeVisible();
  await expect(page.locator(".identity")).toContainText("Token Required");
  await expect(
    page.getByRole("link", { name: "Search", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Data Mode").selectOption("mock");
  await expect(page.locator(".story-lead")).toBeVisible();
  await expect(
    page.getByRole("alert").filter({ hasText: "FORBIDDEN" }),
  ).toHaveCount(0);
});

test("empty real archive and media retain useful entry points without fictional fallback", async ({
  page,
}) => {
  await page.route("http://localhost:8000/**", (route) =>
    route.fulfill({
      json: {
        data: [],
        pagination: { has_more: false, next_cursor: null },
        meta: { request_id: "empty-real", api_version: "v1" },
      },
    }),
  );
  await page.goto("/");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(
    page.getByRole("heading", { name: "No Source Records to Explore Yet." }),
  ).toBeVisible();
  await expect(page.locator(".story-lead")).toHaveCount(0);
  await expect(
    page.getByText("No provider articles acquired yet."),
  ).toBeVisible();
  await expect(page.getByText("No current video references.")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open the Document Register →" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Explore Multimedia", exact: false }),
  ).toBeVisible();
});

test("slow archive and failed remote image leave independent media and source links usable", async ({
  page,
}) => {
  let releaseDocuments!: () => void;
  const documentGate = new Promise<void>((resolve) => {
    releaseDocuments = resolve;
  });
  await page.route("https://images.example.org/missing.jpg", (route) =>
    route.abort(),
  );
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown[] = [];
    if (path === "/api/v1/documents") {
      await documentGate;
      data = [documents[0].document];
    } else if (path === "/api/v1/sources") {
      data = [documents[0].source];
    } else if (path === "/api/v1/provider-articles") {
      data = [
        {
          article_id: "synthetic-acquisition",
          acquired_at: "2026-10-04T10:00:00Z",
          document_id: null,
          title: "Synthetic provider reference",
          source_id: documents[0].source.source_id,
          published_at: null,
          workflow_id: "synthetic-workflow",
          evidence: [
            {
              provider: "gnews",
              provider_item_id: "synthetic-item",
              publisher_name: "Synthetic publisher",
              article_url: "https://publisher.example.org/report",
              author: null,
              image_url: "https://images.example.org/missing.jpg",
              video_url: null,
              acquired_at: "2026-10-04T10:00:00Z",
              content_kind: "provider excerpt",
            },
          ],
        },
      ];
    }
    await route.fulfill({
      json: {
        data,
        pagination: { has_more: false, next_cursor: null },
        meta: { request_id: "controlled-loading", api_version: "v1" },
      },
    });
  });
  await page.goto("/");
  await page.getByLabel("Data Mode").selectOption("real");
  await expect(
    page.getByText("Loading intelligence records…").first(),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Synthetic provider reference",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Image Unavailable", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open Publisher Article ↗", exact: true }),
  ).toHaveAttribute("href", "https://publisher.example.org/report");
  await expect(
    page.getByText("Remote publisher image · bytes not verified"),
  ).toBeVisible();
  await expect(page.locator(".story-lead")).toHaveCount(0);
  releaseDocuments();
  await expect(page.locator(".story-lead")).toBeVisible();
});

test("identity changes and sign-out isolate cached evidence across both experiences", async ({
  page,
}) => {
  test.info().annotations.push({
    type: "identity",
    description: "All tokens and API responses in this test are synthetic.",
  });
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const authorization = route.request().headers().authorization;
    const name =
      authorization === "Bearer synthetic-first"
        ? "First test identity"
        : "Second test identity";
    if (!authorization && path !== "/api/v1/system/info") {
      await route.fulfill({
        status: 401,
        json: {
          error: {
            code: "UNAUTHORIZED",
            message: "Token Required",
            request_id: "synthetic-auth",
          },
        },
      });
      return;
    }
    const meta = { request_id: "synthetic-session", api_version: "v1" };
    if (path === "/api/v1/security/me") {
      await route.fulfill({
        json: {
          data: {
            subject: name,
            kind: "user",
            roles: ["viewer"],
            scopes: ["documents:read", "sources:read", "events:read"],
          },
          meta,
        },
      });
    } else if (path === "/api/v1/system/info") {
      await route.fulfill({
        json: {
          data: {
            name: "AegisNews",
            version: "test",
            stage: "foundation",
            architecture: "modular monolith + background workers",
          },
          meta,
        },
      });
    } else {
      const data =
        path === "/api/v1/documents"
          ? [{ ...documents[0].document, title: `${name} source record` }]
          : path === "/api/v1/sources"
            ? [documents[0].source]
            : [];
      await route.fulfill({
        json: {
          data,
          pagination: { has_more: false, next_cursor: null },
          meta,
        },
      });
    }
  });
  await page.goto("/");
  await page.getByLabel("Data Mode").selectOption("real");
  await page.getByLabel("Access Token").fill("synthetic-first");
  await page.getByRole("button", { name: "Use Token", exact: true }).click();
  await expect(page.locator(".identity")).toContainText("First test identity");
  await expect(page.locator(".story-lead")).toContainText(
    "First test identity source record",
  );
  await page
    .getByRole("link", { name: "Operations & Security", exact: true })
    .click();
  await expect(page.locator(".identity")).toContainText("First test identity");
  await page.getByLabel("Access Token").fill("synthetic-second");
  await page.getByRole("button", { name: "Use Token", exact: true }).click();
  await expect(page.locator(".identity")).toContainText("Second test identity");
  await expect(page.locator("#main-content")).not.toContainText(
    "First test identity source record",
  );
  await page
    .getByRole("link", { name: "News & Intelligence", exact: true })
    .click();
  await expect(page.locator(".story-lead")).toContainText(
    "Second test identity source record",
  );
  await page.getByRole("button", { name: "Sign Out", exact: true }).click();
  await expect(page.locator(".identity")).toContainText("Anonymous");
  await expect(page.locator(".story-lead")).toHaveCount(0);
  await expect(page.getByRole("alert").first()).toContainText("UNAUTHORIZED");
});
