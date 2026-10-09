import { expect, test } from "@playwright/test";
import {
  fixtureTopics,
  fixtureTopicDocuments,
} from "../src/lib/intelligence-fixtures";
import { operationalApi, operator } from "./operations-support";
const cutoff = "2026-10-03T09:00:00Z";
const directory = fixtureTopics({ cutoff });
const topic = directory.data[0];
const members = fixtureTopicDocuments(topic.topic_id, { cutoff });
test("Topic Directory opens model-attributed dossiers and available evidence", async ({
  page,
}) => {
  await page.goto("/topics");
  await expect(
    page.getByRole("heading", { name: "Topic Directory", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Inspect Topic", exact: false })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: topic.label, exact: true }),
  ).toBeVisible();
  await expect(page.locator(".topic-evidence")).toHaveCount(
    members.data.length,
  );
  await expect(
    page.getByRole("link", { name: "View Topic Analytics", exact: false }),
  ).toBeVisible();
});
test("real topic pages preserve cursor snapshot and expand loaded assessments without eager intelligence", async ({
  page,
}) => {
  const requests = await operationalApi(page);
  await page.route("**/api/v1/topics**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/documents")) {
      const next = !!url.searchParams.get("cursor");
      return route.fulfill({
        json: {
          ...members,
          data: [members.data[next ? 1 : 0]],
          pagination: {
            has_more: !next,
            next_cursor: next ? null : "topic-next+/==",
          },
        },
      });
    }
    if (url.pathname === "/api/v1/topics")
      return route.fulfill({ json: directory });
    return route.fulfill({
      json: { data: { ...topic, document_count: 2 }, meta: directory.meta },
    });
  });
  await operator(
    page,
    `/topics/${topic.topic_id}?as_of=${encodeURIComponent(cutoff)}`,
  );
  await expect(page.locator(".topic-evidence")).toHaveCount(1);
  const disclosure = page.locator(".topic-evidence summary");
  await disclosure.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText(members.data[0].analysis_id, { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(disclosure).toBeFocused();
  await page
    .getByRole("navigation", { name: "Topic Evidence Pages" })
    .getByRole("button", { name: "Next Page", exact: true })
    .click();
  await expect(page.locator(".topic-evidence h3")).toContainText(
    members.data[1].document.title,
  );
  const destinations = requests.filter((call) =>
    call.path.includes("/intelligence"),
  );
  expect(destinations).toHaveLength(0);
  expect(
    await page
      .locator(".topic-evidence")
      .getByRole("link", { name: "Full Story", exact: false })
      .getAttribute("href"),
  ).toContain(members.data[1].document.document_id);
});
test("Topic Directory filters explicit labels and shows honest no-record states", async ({
  page,
}) => {
  await page.goto("/topics");
  await page
    .getByLabel("Topic Search", { exact: true })
    .fill("No matching label");
  await page
    .getByRole("button", { name: "Search Topics", exact: true })
    .click();
  await expect(
    page.getByText("No topic assessments match this page and cutoff.", {
      exact: true,
    }),
  ).toBeVisible();
});
test("real topic access failure never reveals simulated memberships", async ({
  page,
}) => {
  await operationalApi(page);
  await page.route("**/api/v1/topics**", (route) =>
    route.fulfill({
      status: 403,
      json: {
        error: {
          code: "FORBIDDEN",
          message: "Topic read scope required",
          request_id: "topic-denied",
        },
      },
    }),
  );
  await operator(page, "/topics");
  await expect(
    page.getByText("Topic read scope required", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".topic-directory-entry")).toHaveCount(0);
  await page.getByLabel("Data Mode", { exact: false }).selectOption("mock");
  await expect(page.locator(".topic-directory-entry")).toHaveCount(2);
});
for (const width of [1440, 1024, 768, 390, 320])
  test(`Topic research reflows and keeps disclosures usable at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/topics");
    await expect(page.locator(".topic-directory-entry")).toHaveCount(2);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page
      .getByRole("link", { name: "Inspect Topic", exact: false })
      .first()
      .click();
    await expect(page.locator(".topic-evidence")).toHaveCount(
      members.data.length,
    );
    await page.locator(".topic-evidence summary").first().click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
