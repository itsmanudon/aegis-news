import { expect, test } from "@playwright/test";

test.use({ trace: "off" });
test("real corpus: unfiltered dashboard and paginated register use bounded requests", async ({
  page,
}) => {
  test.skip(
    process.env.AEGIS_HISTORICAL_E2E !== "1",
    "Requires local corpus and identity",
  );
  const statuses: number[] = [];
  const intelligence: string[] = [];
  page.on("response", (r) => {
    if (r.url().includes("/api/v1/")) statuses.push(r.status());
  });
  page.on("request", (r) => {
    if (r.url().includes("/intelligence")) intelligence.push(r.url());
  });
  await page.goto("/operations");
  await expect(page.getByLabel("Data mode")).toHaveValue("real");
  await page.getByLabel("Access token").fill(process.env.AEGIS_E2E_TOKEN!);
  await page.getByRole("button", { name: "Use token" }).click();
  await expect(page.locator(".queue-record")).toHaveCount(20);
  await expect(page.locator("tbody tr")).toHaveCount(20);
  await page
    .getByRole("link", { name: "News & Intelligence", exact: true })
    .click();
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(20);
  const title = await page.locator("tbody tr").first().innerText();
  await page.getByRole("button", { name: "Next page", exact: true }).click();
  await expect(page.locator("tbody tr").first()).not.toHaveText(title);
  await page.getByRole("link", { name: "Entities", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Entity register", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Events / timeline", exact: true })
    .click();
  await expect(page.locator(".timeline > li").first()).toBeVisible();
  expect(intelligence).toHaveLength(0);
  expect(statuses).not.toContain(429);
  expect(statuses.length).toBeLessThan(30);
});
