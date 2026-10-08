import { expect, test, type Page } from "@playwright/test";
import { documents } from "../src/lib/fixtures";

const article = {
  article_id: "article-demo",
  source_id: documents[0].source.source_id,
  title: "Synthetic harbour image reference",
  acquired_at: "2026-10-08T08:10:07.125Z",
  published_at: null,
  document_id: documents[0].document.document_id,
  evidence: [
    {
      provider: "gnews",
      publisher_name: "Example Publisher",
      author: "Demo correspondent",
      content_kind: "provider excerpt",
      acquired_at: "2026-10-08T08:05:00Z",
      article_url: "https://publisher.example.org/story",
      image_url: "https://images.example.org/harbour.jpg",
    },
  ],
};
const video = {
  video_id: "abcdefghijk",
  title: "Synthetic video reference",
  channel_id: "demo-channel",
  channel_title: "Example Channel",
  youtube_url: "https://evil.example.org/watch",
  thumbnail_url: "https://images.example.org/video.jpg",
  published_at: "2026-10-07T12:01:00Z",
  last_refreshed_at: "2026-10-08T08:11:07.125Z",
  expires_at: "2026-11-07T08:11:07.125Z",
};
const collection = (data: unknown[], next_cursor: string | null = null) => ({
  data,
  pagination: { next_cursor, limit: 12, has_more: !!next_cursor },
  meta: { request_id: "demo-media", api_version: "v1" },
});
async function realMedia(
  page: Page,
  options: {
    failArticles?: boolean;
    emptyVideos?: boolean;
    refreshImage?: boolean;
  } = {},
) {
  const requests: string[] = [];
  let articleReads = 0;
  await page.route("https://images.example.org/**", (route) =>
    route.request().url().endsWith("/refreshed.svg")
      ? route.fulfill({
          contentType: "image/svg+xml",
          body: '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320"><rect width="480" height="320" fill="#0F766E"/></svg>',
        })
      : route.abort(),
  );
  await page.route("http://localhost:8000/**", async (route) => {
    const url = new URL(route.request().url());
    requests.push(url.pathname + url.search);
    if (url.pathname.endsWith("/provider-articles")) {
      articleReads += 1;
      if (options.failArticles)
        return route.fulfill({
          status: 503,
          json: {
            error: {
              code: "PROVIDER_UNAVAILABLE",
              message: "Provider temporarily unavailable",
              request_id: "media-error",
            },
          },
        });
      return route.fulfill({
        json: url.searchParams.has("cursor")
          ? collection([
              {
                ...article,
                article_id: "article-next",
                title: "Synthetic second article page",
                evidence: [],
              },
            ])
          : collection(
              [
                options.refreshImage && articleReads > 1
                  ? {
                      ...article,
                      evidence: [
                        {
                          ...article.evidence[0],
                          image_url: "https://images.example.org/refreshed.svg",
                        },
                      ],
                    }
                  : article,
              ],
              "article-next",
            ),
      });
    }
    if (url.pathname.endsWith("/youtube-references"))
      return route.fulfill({
        json: options.emptyVideos
          ? collection([])
          : url.searchParams.has("cursor")
            ? collection([
                {
                  ...video,
                  video_id: "lmnopqrstuv",
                  title: "Synthetic second video page",
                },
              ])
            : collection([video], "video-next"),
      });
    if (url.pathname.endsWith("/sources"))
      return route.fulfill({
        json: collection(documents.map((view) => view.source)),
      });
    if (url.pathname.endsWith("/documents"))
      return route.fulfill({
        json: collection(
          documents.slice(0, 3).map((view) => view.document),
          "stories-next",
        ),
      });
    const selected = documents.find(
      (view) =>
        url.pathname ===
        `/api/v1/documents/${view.document.document_id}/intelligence`,
    );
    if (selected)
      return route.fulfill({
        json: {
          data: selected,
          meta: { request_id: "demo-detail", api_version: "v1" },
        },
      });
    return route.fulfill({
      status: 401,
      json: {
        error: {
          code: "UNAUTHORIZED",
          message: "Synthetic token required",
          request_id: "media-session",
        },
      },
    });
  });
  await page.goto("/multimedia");
  await page.getByLabel("Data Mode").selectOption("real");
  return requests;
}

test("Media Lab loads only selected stored attachment evidence and clears it across mode changes", async ({
  page,
}) => {
  const requests = await realMedia(page);
  await expect(
    page.getByRole("heading", { name: "Synthetic harbour image reference" }),
  ).toBeVisible();
  expect(requests.some((url) => url.includes("/intelligence"))).toBe(false);
  await page
    .getByLabel("Select Story", { exact: true })
    .selectOption(documents[2].document.document_id);
  await expect(
    page.getByRole("heading", { name: "corridor-report.txt", exact: true }),
  ).toBeVisible();
  expect(requests.filter((url) => url.includes("/intelligence"))).toEqual([
    `/api/v1/documents/${documents[2].document.document_id}/intelligence`,
  ]);
  expect(
    requests.some((url) => /verify|media\/|refresh|ingestions/.test(url)),
  ).toBe(false);
  await page.getByLabel("Data Mode").selectOption("mock");
  await expect(
    page.getByRole("heading", { name: "corridor-report.txt", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Publisher References Unavailable" }),
  ).toBeVisible();
  await page
    .getByLabel("Select Story", { exact: true })
    .selectOption(documents[2].document.document_id);
  await expect(
    page.getByText("Fictional Demo Record", { exact: true }),
  ).toBeVisible();
});

test("publisher pagination, image failure, video expiry and safe source links remain independent", async ({
  page,
}) => {
  await realMedia(page);
  const publisher = page.getByRole("region", {
    name: "Publisher Articles & Images",
  });
  await expect(
    publisher.getByText("Image Unavailable", { exact: true }),
  ).toBeVisible();
  await expect(
    publisher.getByRole("link", { name: "Open Publisher Article" }),
  ).toHaveAttribute("href", "https://publisher.example.org/story");
  await expect(
    publisher.getByRole("link", { name: "Open Publisher Article" }),
  ).toHaveAttribute("rel", /noreferrer/);
  const videos = page.getByRole("region", { name: "Video References" });
  await videos
    .locator("summary")
    .filter({ hasText: "Reference Metadata" })
    .click();
  await expect(
    videos.locator('time[datetime="2026-11-07T08:11:07.125Z"]'),
  ).toBeVisible();
  await expect(
    videos.getByRole("link", { name: "Open on YouTube" }),
  ).toHaveAttribute("href", "https://www.youtube.com/watch?v=abcdefghijk");
  await page
    .getByRole("navigation", { name: "Publisher Reference Pagination" })
    .getByRole("button", { name: "Next Page" })
    .click();
  await expect(
    publisher.getByRole("heading", { name: "Synthetic second article page" }),
  ).toBeVisible();
  await expect(
    videos.getByRole("heading", { name: "Synthetic video reference" }),
  ).toBeVisible();
  await expect(page.locator("iframe, video, audio")).toHaveCount(0);
});

test("a provider failure does not hide the video empty state or stored story selector", async ({
  page,
}) => {
  await realMedia(page, { failArticles: true, emptyVideos: true });
  await expect(
    page.getByText("Provider temporarily unavailable", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("No current video references are available.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByLabel("Select Story", { exact: true })).toBeEnabled();
});

test("video cursor paging preserves the publisher and selected story independently", async ({
  page,
}) => {
  const requests = await realMedia(page);
  await page
    .getByLabel("Select Story", { exact: true })
    .selectOption(documents[2].document.document_id);
  await expect(
    page.getByRole("heading", { name: "corridor-report.txt", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Video Reference Pagination" })
    .getByRole("button", { name: "Next Page" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Synthetic second video page" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Synthetic harbour image reference" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "corridor-report.txt", exact: true }),
  ).toBeVisible();
  expect(
    requests.filter((url) => url.startsWith("/api/v1/youtube-references")),
  ).toEqual([
    "/api/v1/youtube-references?limit=10",
    "/api/v1/youtube-references?limit=10&cursor=video-next",
  ]);
  expect(
    requests.filter((url) => url.startsWith("/api/v1/provider-articles")),
  ).toHaveLength(1);
});

test("a changed publisher image URL recovers after the previous remote reference failed", async ({
  page,
}) => {
  await realMedia(page, { refreshImage: true });
  const publisher = page.getByRole("region", {
    name: "Publisher Articles & Images",
  });
  await expect(
    publisher.getByText("Image Unavailable", { exact: true }),
  ).toBeVisible();
  await page.clock.install();
  await page.clock.fastForward(31_000);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(publisher.locator("img")).toHaveAttribute(
    "src",
    "https://images.example.org/refreshed.svg",
  );
  await expect(publisher.locator("img")).toHaveAttribute(
    "referrerpolicy",
    "no-referrer",
  );
  await expect(publisher.locator("img")).toHaveAttribute("loading", "lazy");
  expect(
    await publisher
      .locator("img")
      .evaluate((image) => (image as HTMLImageElement).naturalWidth),
  ).toBeGreaterThan(0);
});

for (const width of [1440, 390, 320]) {
  test(`Media Lab keeps media, metadata and keyboard disclosures usable at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await realMedia(page);
    await expect(
      page.getByRole("heading", { name: "Media Lab", exact: true }),
    ).toBeVisible();
    const summary = page
      .getByRole("region", { name: "Publisher Articles & Images" })
      .locator("summary")
      .first();
    await summary.focus();
    await page.keyboard.press("Enter");
    await expect(summary.locator("..")).toHaveAttribute("open", "");
    await page.keyboard.press("Escape");
    await expect(summary).toBeFocused();
    await expect(summary.locator("..")).not.toHaveAttribute("open", "");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: test.info().outputPath(`media-lab-${width}.png`),
      fullPage: true,
    });
  });
}
