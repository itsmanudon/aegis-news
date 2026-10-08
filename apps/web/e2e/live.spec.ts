import { expect, test } from "@playwright/test";
import { expectReaderModel } from "./reader-actions";

test.use({ trace: "off" }); // Access Tokens must not enter trace artifacts.
test("live MVP: authenticated feed, intelligence, verification, entities, events, search and ingestion", async ({
  page,
  request,
}) => {
  test.skip(
    process.env.AEGIS_LIVE_E2E !== "1",
    "Requires the full local MVP and development tokens",
  );
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/documents");
  await page.getByLabel("Access Token").fill(process.env.AEGIS_E2E_TOKEN!);
  await page.getByRole("button", { name: "Use Token" }).click();
  await expect(
    page.locator("tbody tr, .editorial-result").first(),
  ).toBeVisible();
  await page
    .getByRole("link", {
      name: "Atlas Labs reports growth and merger",
      exact: true,
    })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Model-Generated Intelligence" }),
  ).toBeVisible();
  await expectReaderModel(page, "keyword-topics / 1");
  await page.getByRole("button", { name: "Verify Integrity" }).click();
  await expect(page.locator(".verification-result")).toContainText("Verified");
  await page.getByRole("link", { name: "Entities", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Atlas Labs", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Inspect Entity" }).first().click();
  await expect(
    page.locator("tbody tr, .editorial-result").first(),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Events / Timeline", exact: true })
    .click();
  await expect(page.locator(".timeline > li").first()).toBeVisible();
  await page.getByRole("link", { name: "Search", exact: true }).click();
  await page.getByLabel("Search Terms").fill("Atlas");
  await expect(
    page.locator("tbody tr, .editorial-result").first(),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Operations & Security", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Audit / Security", exact: true })
    .click();
  await expect(
    page.locator("tbody tr, .editorial-result").first(),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Sources / Admin", exact: true })
    .click();
  const sourceName = `Browser synthetic ${Date.now()}`;
  await page.getByLabel("Source Name", { exact: true }).fill(sourceName);
  await page.getByRole("button", { name: "Create Source" }).click();
  await expect(page.getByRole("heading", { name: sourceName })).toBeVisible();
  await page
    .getByRole("combobox", { name: "Source", exact: true })
    .selectOption({ label: sourceName });
  await page.getByLabel("Article Title").fill("Browser synthetic article");
  await page
    .getByLabel("Article Text")
    .fill("Atlas Labs launched new software with strong profit growth.");
  await page.getByLabel("Submission Key").fill(`browser-${Date.now()}`);
  await page.getByRole("button", { name: "Submit Article" }).click();
  await expect(
    page.getByRole("button", { name: "Check Processing Status" }),
  ).toBeVisible();
  await expect
    .poll(
      async () => {
        await page
          .getByRole("button", { name: "Check Processing Status" })
          .click();
        return page.locator("main").textContent();
      },
      { timeout: 60000 },
    )
    .toContain('"status":"COMPLETED"');
  await page
    .getByLabel("Access Token")
    .fill(process.env.AEGIS_E2E_VIEWER_TOKEN!);
  await page.getByRole("button", { name: "Use Token" }).click();
  await expect(
    page.getByRole("button", { name: "Create Source" }),
  ).toBeDisabled();
  const denial = await request.post(
    `${process.env.AEGIS_E2E_API_URL}/api/v1/ingestions`,
    {
      headers: {
        Authorization: `Bearer ${process.env.AEGIS_E2E_VIEWER_TOKEN}`,
      },
      data: {},
    },
  );
  expect(denial.status()).toBe(403);
  await page.getByRole("button", { name: "Sign Out" }).click();
  await expect(page.locator(".identity")).toContainText("Anonymous");
  expect(errors).toEqual([]);
});
