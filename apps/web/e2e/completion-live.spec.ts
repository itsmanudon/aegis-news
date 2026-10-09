import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import type { components } from "../src/lib/generated/api";

// Credentials remain in memory. Authenticated failures must not produce traces,
// video, or automatic screenshots. Explicit captures assert the token input empty.
test.use({ trace: "off", video: "off", screenshot: "off" });
test.describe.configure({ mode: "serial" });
test.skip(
  process.env.AEGIS_COMPLETION_LIVE !== "1",
  "Opt-in disposable completion runtime",
);

const root = existsSync(
  path.join(process.cwd(), "scripts/completion_integration.py"),
)
  ? process.cwd()
  : path.resolve(process.cwd(), "../..");
const runtime = path.join(root, ".test-tmp/completion-runtime");
const api = process.env.AEGIS_E2E_API_URL ?? "http://127.0.0.1:38000";
const web = process.env.AEGIS_E2E_BASE_URL ?? "http://127.0.0.1:33000";
const project = "aegis-completion-20261008-c1600b0";
type Api = components["schemas"];
type Role = "admin" | "viewer" | "source_manager";
type Fixture = {
  analytics: { first_seen_at: { start: string; end: string } };
  media: {
    source_id: string;
    source_name: string;
    articles: { article_id: string; document_id: string; title: string }[];
  };
  topic_selections: {
    topic_id: string;
    label: string;
    document_ids: string[];
  }[];
};

function isolatedFixture(): Fixture {
  if (api !== "http://127.0.0.1:38000" || web !== "http://127.0.0.1:33000")
    throw new Error(
      "Live completion tests require the owned loopback API and web destinations",
    );
  const ownership = JSON.parse(
    readFileSync(path.join(runtime, "runtime.json"), "utf8"),
  );
  if (
    ownership.project !== project ||
    path.resolve(ownership.runtime) !== path.resolve(runtime)
  )
    throw new Error("Owned completion runtime identity mismatch");
  const fixture: Fixture = JSON.parse(
    readFileSync(path.join(runtime, "product-probe.json"), "utf8"),
  );
  if (
    fixture.media.source_name !==
    "DEMO Completion Newsroom — Original CC0 Synthetic"
  )
    throw new Error("Original synthetic completion fixture required");
  execFileSync(
    path.join(root, ".venv/Scripts/python.exe"),
    [
      "-c",
      "from scripts.completion_integration import assert_owned_runtime; assert_owned_runtime()",
    ],
    { cwd: root, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
  );
  return fixture;
}

function developmentToken(role: Role): string {
  // execFileSync captures stdout internally; neither tokens nor ambient .env values
  // are passed to the reporter, browser console, trace, screenshot, or disk.
  const code = [
    "import json,os,sys",
    "from scripts.completion_integration import environment,PROJECT,RUNTIME",
    "r=json.loads((RUNTIME/'runtime.json').read_text())",
    "assert r['project']==PROJECT and r['runtime']==str(RUNTIME)",
    "os.environ.update(environment())",
    "from aegis.settings import Settings",
    "from aegis.security.keys import FileKeyProvider",
    "from aegis.security.dev_identity import issue_development_token",
    "s=Settings()",
    "assert s.database_url.get_secret_value()==environment()['AEGIS_DATABASE_URL']",
    "print(issue_development_token(s,FileKeyProvider(s.security_key_directory),key_id='local',subject='completion-live-'+sys.argv[1],role=sys.argv[1]))",
  ].join(";");
  return execFileSync(
    path.join(root, ".venv/Scripts/python.exe"),
    ["-c", code, role],
    {
      cwd: root,
      windowsHide: true,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    },
  ).trim();
}

async function authenticate(page: Page, role: Role) {
  await expect(page.getByLabel("Data Mode", { exact: true })).toHaveValue(
    "real",
  );
  const field = page.getByLabel("Access Token", { exact: true });
  await expect(field).toBeVisible();
  // Password values passed to fill() can appear in failure call logs. Set the
  // native input value without a secret-bearing action label, then submit the
  // actual UI form; the server still verifies and authorizes the resulting JWT.
  await field.evaluate((element, token) => {
    const input = element as HTMLInputElement;
    input.value = token;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }, developmentToken(role));
  await page.getByRole("button", { name: "Use Token", exact: true }).click();
  await expect(page.locator(".identity")).toContainText(
    `completion-live-${role}`,
  );
  await expect(field).toHaveValue("");
}

async function visit(page: Page, location: string, role: Role = "admin") {
  await page.goto(web + location);
  await authenticate(page, role);
}

function ownedApiUrl(pathname: string): URL {
  const url = new URL(pathname, api);
  if (
    api !== "http://127.0.0.1:38000" ||
    url.origin !== api ||
    url.username ||
    url.password ||
    !url.pathname.startsWith("/api/v1/")
  )
    throw new Error("An owned loopback API destination is required");
  return url;
}
async function apiResponse(
  pathname: string,
  role?: Role,
  method: "GET" | "POST" = "GET",
) {
  const url = ownedApiUrl(pathname);
  try {
    return await fetch(url, {
      method,
      redirect: "error",
      signal: AbortSignal.timeout(15000),
      headers: {
        ...(role ? { Authorization: `Bearer ${developmentToken(role)}` } : {}),
        ...(method === "POST" ? { "Content-Type": "application/json" } : {}),
      },
      ...(method === "POST" ? { body: "{}" } : {}),
    });
  } catch {
    throw new Error(
      "Owned API request failed; credential-bearing details withheld",
    );
  }
}
async function get<T>(pathname: string, role: Role = "admin") {
  const response = await apiResponse(pathname, role);
  expect(response.status).toBe(200);
  try {
    return (await response.json()).data as T;
  } catch {
    throw new Error("Owned API response could not be read safely");
  }
}

test("real completion journeys and disclosed synthetic image evidence", async ({
  page,
}) => {
  test.setTimeout(420000);
  const fixture = isolatedFixture();
  const story = fixture.media.articles[0];
  const topic = fixture.topic_selections.find(
    (value) =>
      value.label === "technology" &&
      value.document_ids.includes(story.document_id),
  );
  expect(topic).toBeDefined();
  const articles = await get<Api["ProviderArticleView"][]>(
    "/api/v1/provider-articles?limit=100",
  );
  const article = articles.find(
    (value) => value.article_id === story.article_id,
  );
  expect(article?.workflow_id).toBeTruthy();
  const pageErrors: string[] = [];
  const serverErrors: number[] = [];
  const calls: { method: string; pathname: string }[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.origin === api && url.pathname.startsWith("/api/v1/"))
      calls.push({ method: request.method(), pathname: url.pathname });
  });
  page.on("response", (response) => {
    if (response.url().startsWith(api + "/api/v1/") && response.status() >= 500)
      serverErrors.push(response.status());
  });
  // ONLY original synthetic image references are intercepted. Every API request
  // goes to the actual isolated secured API. The failure URL remains a failure.
  let imageInterceptions = 0;
  await page.route(
    "https://completion.example.test/images/*",
    async (route) => {
      imageInterceptions++;
      if (
        new URL(route.request().url()).pathname.endsWith("unavailable-demo.png")
      )
        await route.abort("failed");
      else
        await route.fulfill({
          path: path.join(root, "data/samples/demo-image.png"),
          contentType: "image/png",
        });
    },
  );
  const captures: { file: string; width: number; pathname: string }[] = [];
  const evidence = process.env.AEGIS_SCREENSHOT_DIR
    ? process.env.AEGIS_SCREENSHOT_DIR
    : undefined;
  const capture = async (name: string, width: number, group?: string) => {
    await expect(page.getByLabel("Access Token", { exact: true })).toHaveValue(
      "",
    );
    await page.evaluate(() => document.fonts.ready);
    await page.locator("h1").first().click();
    await page.evaluate(() => {
      (document.activeElement as HTMLElement | null)?.blur();
      window.scrollTo(0, 0);
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    if (!evidence) return;
    const directory = path.join(evidence, group ?? String(width));
    mkdirSync(directory, { recursive: true });
    const file = path.join(directory, name + ".png");
    await page.screenshot({
      path: file,
      fullPage: true,
    });
    captures.push({ file, width, pathname: new URL(page.url()).pathname });
  };

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await visit(page, "/");
    await expect(page.locator(".story-lead")).toContainText("DEMO");
    await capture("01-discover", width);
    if (width === 390) {
      await page.getByRole("button", { name: /^Navigation/ }).click();
      await expect(
        page.getByRole("navigation", { name: "Primary navigation" }),
      ).toBeVisible();
      await capture("18-mobile-navigation", width);
      await page.getByRole("button", { name: /^Navigation/ }).click();
    }
    await page
      .getByRole("link", { name: story.title, exact: true })
      .first()
      .click();
    await expect(page).toHaveURL(web + `/documents/${story.document_id}`);
    await expect(
      page.getByRole("heading", { level: 1, name: story.title, exact: true }),
    ).toBeVisible();
    await expect(page.locator(".story-report")).toContainText(
      "Original CC0 synthetic demo",
    );
    await capture("02-story-detail", width);
    const verified = page.waitForResponse(
      (response) =>
        response.url() ===
          `${api}/api/v1/documents/${story.document_id}/verify` &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Verify Integrity", exact: true })
      .click();
    expect((await (await verified).json()).data.valid).toBe(true);
    await expect(page.locator(".verification-result")).toContainText("Passed");

    await visit(page, "/search");
    await page.getByLabel("Search Terms", { exact: true }).fill("DEMO Atlas");
    const result = page
      .locator(".editorial-result")
      .filter({ hasText: story.title });
    await expect(result).toHaveCount(1);
    await capture("03-search", width);
    await result
      .locator("summary")
      .filter({ hasText: "Evidence Details" })
      .click();
    await expect(result).toContainText("Literal Source Excerpt");
    await capture("04-expanded-evidence", width);
    await result.getByRole("link", { name: story.title, exact: true }).click();
    await expect(page.locator(".story-report")).toContainText("Atlas Labs");

    await visit(page, "/entities");
    const entity = page
      .locator(".entity-entry")
      .filter({ hasText: "Atlas Labs" });
    await expect(entity).toHaveCount(1);
    await capture("05-entity-directory", width);
    await entity.getByRole("link", { name: "Inspect Entity" }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Atlas Labs", exact: true }),
    ).toBeVisible();
    await expect(page.locator(".editorial-result").first()).toBeVisible();
    await page.locator(".editorial-result").first().locator("summary").click();
    await expect(page.locator(".editorial-result").first()).toContainText(
      "Literal Source Excerpt",
    );
    await capture("06-entity-intelligence", width);

    await visit(page, "/events");
    await expect(page.locator(".event-record").first()).toBeVisible();
    await capture("07-events", width);
    await page
      .locator(".event-record")
      .first()
      .getByRole("link", { name: /Open Supporting Document/ })
      .first()
      .click();
    await expect(page.locator(".story-report")).toBeVisible();

    await visit(page, "/topics");
    await expect(page.locator(".topic-directory-entry")).toHaveCount(5);
    await capture("08-topic-directory", width);
    await page
      .locator(`.topic-directory-entry a[href*="${topic!.topic_id}"]`)
      .first()
      .click();
    await expect(
      page.getByRole("heading", { level: 1, name: "technology", exact: true }),
    ).toBeVisible();
    await page.locator("summary").filter({ hasText: "Topic Identity" }).click();
    await expect(page.locator("main")).toContainText(topic!.topic_id);
    await page.locator(".topic-evidence").first().locator("summary").click();
    await expect(page.locator(".topic-evidence").first()).toContainText(
      "keyword-topics",
    );
    await capture("09-topic-detail", width);
    await page
      .getByRole("link", { name: "View Topic Analytics →", exact: true })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Intelligence Analytics",
        exact: true,
      }),
    ).toBeVisible();
    await page
      .getByLabel("Window Start (Inclusive, UTC)", { exact: true })
      .fill(
        new Date(fixture.analytics.first_seen_at.start)
          .toISOString()
          .slice(0, 16),
      );
    await page
      .getByLabel("Window End (Exclusive, UTC)", { exact: true })
      .fill(
        new Date(fixture.analytics.first_seen_at.end)
          .toISOString()
          .slice(0, 16),
      );
    await page
      .getByLabel("Source ID (Optional)", { exact: true })
      .fill(fixture.media.source_id);
    await page
      .getByLabel("Time Basis", { exact: true })
      .selectOption("first_seen_at");
    await page
      .getByRole("button", { name: "Apply Window", exact: true })
      .click();
    const population = page.getByRole("region", {
      name: "The Reporting Population",
    });
    await expect(
      population
        .locator("dt")
        .filter({ hasText: "Documents in Population" })
        .locator("+ dd"),
    ).toHaveText("1");
    await capture("10-topic-analytics", width);
    await page
      .getByRole("link", { name: "Explore Supporting Records", exact: true })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Chronological Discovery",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".editorial-result")).toHaveCount(1);
    await expect(page.locator(".editorial-result")).toContainText(story.title);
    await visit(page, "/discovery");
    await expect(
      page.getByRole("heading", {
        name: "Chronological Discovery",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.getByLabel("Order By", { exact: true })).toHaveValue(
      "published_at",
    );
    await expect(page.locator(".editorial-result")).toHaveCount(13);
    await page
      .locator("summary")
      .filter({ hasText: "Population Filters" })
      .click();
    await capture("17-chronological-discovery", width);

    await visit(page, "/multimedia");
    await expect(
      page.getByRole("heading", { name: "Media Lab", exact: true }),
    ).toBeVisible();
    const media = page
      .locator(".media-article-reference")
      .filter({ hasText: story.title });
    await expect(media).toBeVisible();
    await media.scrollIntoViewIfNeeded();
    await expect(media.locator("img")).toHaveJSProperty("naturalWidth", 320);
    await expect(
      page
        .locator(".media-article-reference")
        .filter({ hasText: fixture.media.articles[1].title })
        .getByText("Image Unavailable", { exact: true }),
    ).toBeVisible();
    await media.locator("summary").click();
    await expect(media).toContainText(fixture.media.source_name);
    await expect(media).toContainText(
      "not stored or cryptographically verified",
    );
    await expect(page.locator(".media-video-reference")).toHaveCount(2);
    await page
      .locator(".media-video-reference")
      .first()
      .locator("summary")
      .click();
    await expect(page.locator(".media-video-reference").first()).toContainText(
      "Expires",
    );
    await page
      .getByLabel("Select Story", { exact: true })
      .selectOption(story.document_id);
    await expect(page.locator(".media-stored-record")).toContainText(
      "image/png",
    );
    await capture("11-media-lab", width);
    await media
      .getByRole("link", { name: "Open Associated Story →", exact: true })
      .click();
    await expect(page.locator(".story-report")).toBeVisible();

    await visit(page, "/provenance");
    await page
      .getByLabel("Select Document", { exact: true })
      .selectOption(story.document_id);
    await expect(page.locator(".verification-current")).toContainText(
      "Not Checked",
    );
    await page
      .getByRole("button", { name: "Verify Integrity", exact: true })
      .click();
    await expect(page.locator(".verification-current")).toContainText("Passed");
    await capture("12-verification", width);

    await visit(page, "/operations");
    await expect(
      page.getByRole("heading", { name: "Operational Overview", exact: true }),
    ).toBeVisible();
    await capture("13-operations", width);
    await visit(page, "/sources");
    await expect(
      page
        .locator(".source-record")
        .filter({ hasText: fixture.media.source_name }),
    ).toBeVisible();
    await page
      .getByLabel("Workflow ID", { exact: true })
      .fill(article!.workflow_id!);
    await page
      .getByRole("button", { name: "Check Processing Status", exact: true })
      .click();
    await expect(
      page.getByRole("region", { name: "Reported Workflow" }),
    ).toContainText("Workflow Completed");
    await capture("14-sources-ingestion", width);
    await expect(
      page.getByRole("heading", {
        name: "Manual Provider Acquisition",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator("#provider-operations")).toContainText(
      "Configuration",
    );
    await page.locator("#provider-operations").scrollIntoViewIfNeeded();
    await capture("15-provider-controls", width);

    await visit(page, "/security");
    await expect(
      page
        .getByRole("table", { name: "Audit Events" })
        .locator("tbody tr")
        .first(),
    ).toBeVisible();
    await capture("16-security-audit", width);
  }
  const acquisition = fixture.analytics.first_seen_at;
  for (const view of [
    {
      width: 320,
      route: `/analytics?${new URLSearchParams({
        start: acquisition.start,
        end: acquisition.end,
        time_basis: "first_seen_at",
        source: fixture.media.source_id,
      })}`,
      name: "analytics-320",
    },
    { width: 768, route: "/discovery", name: "discovery-768" },
    { width: 1024, route: "/multimedia", name: "media-lab-1024" },
  ]) {
    await page.setViewportSize({ width: view.width, height: 1000 });
    await visit(page, view.route);
    if (view.width === 320) {
      await expect(
        page.getByRole("region", { name: "The Reporting Population" }),
      ).toBeVisible();
    } else if (view.width === 768) {
      await expect(page.locator(".editorial-result")).toHaveCount(13);
      await page
        .locator("summary")
        .filter({ hasText: "Population Filters" })
        .click();
    } else {
      const reference = page
        .locator(".media-article-reference")
        .filter({ hasText: story.title });
      await reference.scrollIntoViewIfNeeded();
      await expect(reference.locator("img")).toHaveJSProperty(
        "naturalWidth",
        320,
      );
      await page
        .getByLabel("Select Story", { exact: true })
        .selectOption(story.document_id);
      await expect(page.locator(".media-stored-record")).toContainText(
        "image/png",
      );
    }
    await capture(view.name, view.width, "reflow");
  }
  expect(pageErrors).toEqual([]);
  expect(serverErrors).toEqual([]);
  expect(
    calls.some(
      (value) =>
        value.method === "POST" &&
        /\/providers\/.*fetch|\/youtube-references\/refresh/.test(
          value.pathname,
        ),
    ),
  ).toBe(false);
  expect(imageInterceptions).toBeGreaterThan(0);
  if (evidence)
    writeFileSync(
      path.join(evidence, "capture-records.json"),
      JSON.stringify(
        {
          result: "passed",
          captures,
          apiIntercepted: false,
          imageInterceptions,
          imageDisclosure:
            "Only completion.example.test synthetic image references are served from original CC0 data/samples/demo-image.png; the unavailable image is aborted. API data, authentication, model outputs and cryptographic verification are real isolated backend results.",
        },
        null,
        2,
      ),
    );
});

test("real scope failures and identity changes preserve authorization", async ({
  page,
}) => {
  test.setTimeout(90000);
  const fixture = isolatedFixture();
  const story = fixture.media.articles[0];
  expect(() => ownedApiUrl("https://example.org/api/v1/discovery")).toThrow(
    /owned/,
  );
  expect(() => ownedApiUrl("//127.0.0.1:8000/api/v1/discovery")).toThrow(
    /owned/,
  );
  expect((await apiResponse("/api/v1/discovery")).status).toBe(401);
  expect(
    (await apiResponse("/api/v1/discovery", "source_manager")).status,
  ).toBe(403);
  expect((await apiResponse("/api/v1/security/audit", "viewer")).status).toBe(
    403,
  );
  expect(
    (
      await apiResponse(
        `/api/v1/documents/${story.document_id}/verify`,
        "viewer",
        "POST",
      )
    ).status,
  ).toBe(403);
  expect(
    (await apiResponse("/api/v1/ingestions", "viewer", "POST")).status,
  ).toBe(403);
  await visit(page, "/sources", "viewer");
  await expect(
    page.getByRole("button", { name: "Create Source", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Submit Article", exact: true }),
  ).toBeDisabled();
  await authenticate(page, "source_manager");
  await expect(
    page.getByRole("button", { name: "Create Source", exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByRole("button", { name: "Submit Article", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Sign Out", exact: true }).click();
  await expect(page.locator(".identity")).toContainText("Anonymous");
  await expect(
    page.getByRole("button", { name: "Create Source", exact: true }),
  ).toBeDisabled();
  await expect(page.getByLabel("Access Token", { exact: true })).toHaveValue(
    "",
  );
});
