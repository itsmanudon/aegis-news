import { expect, test, type Page } from "@playwright/test";

const topicId = "topic_" + "a".repeat(64);
const report = {
  start: "2026-10-01T00:00:07.125Z",
  end: "2026-10-08T00:00:07.125Z",
  as_of: "2026-10-08T09:11:07.125Z",
  time_basis: "published_at",
  topic_id: topicId,
  source_id: "source-example",
  population_count: 8,
  classified_count: 5,
  no_assessment_count: 3,
  unknown_time_count: 2,
  coverage: [
    { day: "2026-10-01", document_count: 3, classified_count: 2 },
    { day: "2026-10-03", document_count: 5, classified_count: 3 },
  ],
  sources: [
    {
      source_id: "source-example",
      name: "Example Publisher",
      document_count: 6,
    },
  ],
  sources_other_count: 2,
  sentiment: [
    { label: "neutral", document_count: 3 },
    { label: "mixed", document_count: 2 },
  ],
  models: [
    {
      provider: "example",
      model_name: "document-demo",
      model_version: "1.2",
      document_count: 4,
    },
  ],
  models_other_count: 1,
  selection_policy:
    "Latest eligible document-level sentiment per source document; analysis availability before snapshot cutoff.",
  limitations: ["Mutable source metadata is not a historical snapshot."],
};
const initial = () => {
  const params = new URLSearchParams({
    start: report.start,
    end: report.end,
    time_basis: "published_at",
    topic: topicId,
    source: "source-example",
    as_of: report.as_of,
  });
  return `/analytics?${params}`;
};
async function setup(page: Page, fail = false) {
  const requests: URL[] = [];
  await page.route("http://localhost:8000/**", async (route) => {
    const url = new URL(route.request().url());
    requests.push(url);
    if (url.pathname.endsWith("/analytics"))
      return route.fulfill(
        fail
          ? {
              status: 403,
              json: {
                error: {
                  code: "FORBIDDEN",
                  message: "Document read permission required",
                  request_id: "demo-analytics",
                },
              },
            }
          : {
              json: {
                data: {
                  ...report,
                  start: url.searchParams.get("start"),
                  end: url.searchParams.get("end"),
                  time_basis: url.searchParams.get("time_basis"),
                  topic_id: url.searchParams.get("topic_id"),
                  source_id: url.searchParams.get("source_id"),
                },
                meta: { request_id: "demo-analytics", api_version: "v1" },
              },
            },
      );
    if (url.pathname.endsWith("/topics"))
      return route.fulfill({
        json: {
          data: [
            {
              topic_id: topicId,
              label: "Synthetic Harbour Coverage",
              document_count: 8,
              first_available_at: report.start,
              latest_available_at: report.as_of,
              as_of: report.as_of,
              selection_policy: "Latest available assessment",
              model: {
                provider: "example",
                model_name: "topic-demo",
                model_version: "1",
                configuration_hash: "b".repeat(64),
              },
            },
          ],
          as_of: report.as_of,
          pagination: { next_cursor: "topic-next", has_more: true },
          meta: { request_id: "demo-topics", api_version: "v1" },
        },
      });
    return route.fulfill({
      status: 401,
      json: {
        error: {
          code: "UNAUTHORIZED",
          message: "Synthetic token required",
          request_id: "demo-session",
        },
      },
    });
  });
  await page.goto(initial());
  await page.getByLabel("Data Mode").selectOption("real");
  return requests;
}

test("analytics keeps denominators, missing evidence and supporting records tied to the returned snapshot", async ({
  page,
}) => {
  const requests = await setup(page);
  await expect(
    page.getByRole("heading", { name: "Intelligence Analytics", exact: true }),
  ).toBeVisible();
  const sentiment = page.getByRole("region", { name: "Document Sentiment" });
  await expect(sentiment.getByText("3 of 5", { exact: true })).toBeVisible();
  await expect(sentiment.getByText("2 of 5", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Outside the dated population", { exact: false }),
  ).toBeVisible();
  const link = page.getByRole("link", {
    name: "Explore Supporting Records",
    exact: true,
  });
  await expect(link).toBeVisible();
  const href = new URL((await link.getAttribute("href"))!, "http://local.test");
  expect(href.pathname).toBe("/discovery");
  for (const [key, value] of Object.entries({
    start: report.start,
    end: report.end,
    time_basis: "published_at",
    topic: topicId,
    source: "source-example",
    as_of: report.as_of,
    order: "published_at",
  }))
    expect(href.searchParams.get(key)).toBe(value);
  expect(
    requests.every((url) => /\/(analytics|topics|me)$/.test(url.pathname)),
  ).toBe(true);
});

test("analytics rejects an invalid interval without fetching another report and applies UTC filters to the URL", async ({
  page,
}) => {
  const requests = await setup(page);
  await expect(
    page.getByRole("heading", { name: "Document Sentiment" }),
  ).toBeVisible();
  const reads = requests.filter((url) =>
    url.pathname.endsWith("/analytics"),
  ).length;
  await page
    .getByLabel("Window End (Exclusive, UTC)", { exact: true })
    .fill("2026-09-01T00:00");
  await page.getByRole("button", { name: "Apply Window", exact: true }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "after the start" }),
  ).toBeVisible();
  expect(
    requests.filter((url) => url.pathname.endsWith("/analytics")),
  ).toHaveLength(reads);
  await page
    .getByLabel("Window End (Exclusive, UTC)", { exact: true })
    .fill("2026-10-09T00:00");
  await page
    .getByLabel("Time Basis", { exact: true })
    .selectOption("first_seen_at");
  await page.getByRole("button", { name: "Apply Window", exact: true }).click();
  await expect(page).toHaveURL(/time_basis=first_seen_at/);
  await expect
    .poll(() =>
      requests
        .filter((url) => url.pathname.endsWith("/analytics"))
        .at(-1)
        ?.searchParams.get("time_basis"),
    )
    .toBe("first_seen_at");
});

test("analytics authorization failures remain recoverable without fixture results", async ({
  page,
}) => {
  await setup(page, true);
  await expect(
    page.getByText("Document read permission required", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Explore Supporting Records" }),
  ).toHaveCount(0);
});

for (const width of [1440, 390, 320])
  test(`analytics chart data and metadata remain accessible at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await setup(page);
    const summary = page
      .locator("summary")
      .filter({ hasText: "Coverage Data" });
    await summary.focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("rowheader", { name: "2026-10-03", exact: true }),
    ).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(summary).toBeFocused();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
