import { expect, test } from "@playwright/test";
import { documents } from "../src/lib/fixtures";
import { operationalApi, operator } from "./operations-support";
test("chronological discovery preserves bounded server order and population filters across pages", async ({
  page,
}) => {
  await operationalApi(page);
  const requests: URL[] = [];
  await page.route("**/api/v1/discovery?*", (route) => {
    const url = new URL(route.request().url());
    requests.push(url);
    const next = !!url.searchParams.get("cursor");
    return route.fulfill({
      json: {
        data: (next ? [documents[2]] : [documents[5], documents[0]]).map(
          ({ document, source }) => ({ document, source }),
        ),
        as_of: "2026-10-03T09:00:00Z",
        pagination: {
          has_more: !next,
          next_cursor: next ? null : "frozen-next+/==",
        },
        meta: { request_id: "snapshot", api_version: "v1" },
      },
    });
  });
  await operator(
    page,
    "/discovery?start=2026-10-01T00%3A00%3A00Z&end=2026-10-04T00%3A00%3A00Z&time_basis=first_seen_at&source=src_00000000-0000-4000-8000-000000000001",
  );
  await expect(
    page.getByRole("heading", { name: "Chronological Discovery", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".editorial-result h3").first()).toContainText(
    documents[5].document.title,
  );
  await page
    .getByRole("navigation", { name: "Chronological Discovery Pages" })
    .getByRole("button", { name: "Next Page", exact: true })
    .click();
  await expect(page.locator(".editorial-result h3")).toContainText(
    documents[2].document.title,
  );
  await expect(page.locator(".editorial-result")).toContainText("Unknown");
  expect(requests.at(-1)!.searchParams.get("cursor")).toBe("frozen-next+/==");
  expect(requests.at(-1)!.searchParams.get("start")).toBe(
    "2026-10-01T00:00:00Z",
  );
  expect(requests.at(-1)!.searchParams.get("time_basis")).toBe("first_seen_at");
});
test("chronological order controls distinguish publication from first seen and clear cursors", async ({
  page,
}) => {
  await page.goto("/discovery");
  await expect(page.locator(".editorial-result")).toHaveCount(6);
  await page
    .getByLabel("Order By", { exact: true })
    .selectOption("first_seen_at");
  await page
    .getByRole("button", { name: "Apply Discovery Filters", exact: true })
    .click();
  await expect(page).toHaveURL(/order=first_seen_at/);
  await expect(
    page.getByText("Global First Seen order", { exact: false }),
  ).toBeVisible();
});
test("chronological discovery forbidden and empty states do not use mock success", async ({
  page,
}) => {
  await operationalApi(page);
  await page.route("**/api/v1/discovery?*", (route) =>
    route.fulfill({
      status: 403,
      json: {
        error: {
          code: "FORBIDDEN",
          message: "Chronological read permission required",
          request_id: "discovery-denied",
        },
      },
    }),
  );
  await operator(page, "/discovery");
  await expect(
    page.getByText("Chronological read permission required", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".editorial-result")).toHaveCount(0);
});
