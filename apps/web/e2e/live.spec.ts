import { expect, test } from "@playwright/test";

test.use({ trace: "off" }); // Access tokens must not enter trace artifacts.
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
  await page.getByLabel("Access token").fill(process.env.AEGIS_E2E_TOKEN!);
  await page.getByRole("button", { name: "Use token" }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await page
    .getByRole("link", {
      name: "Atlas Labs reports growth and merger",
      exact: true,
    })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Model-generated intelligence" }),
  ).toBeVisible();
  await expect(page.getByText("keyword-topics / 1")).toBeVisible();
  await page.getByRole("button", { name: "Verify integrity" }).click();
  await expect(page.locator(".verification-result")).toContainText("verified");
  await page.getByRole("link", { name: "Entities", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Atlas Labs", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Inspect entity" }).first().click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await page
    .getByRole("link", { name: "Events / timeline", exact: true })
    .click();
  await expect(page.locator(".timeline > li").first()).toBeVisible();
  await page.getByRole("link", { name: "Search", exact: true }).click();
  await page.getByLabel("Search terms").fill("Atlas");
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await page
    .getByRole("link", { name: "Operations & Security", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Audit / security", exact: true })
    .click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await page
    .getByRole("link", { name: "Sources / admin", exact: true })
    .click();
  const sourceName = `Browser synthetic ${Date.now()}`;
  await page.getByLabel("Source name", { exact: true }).fill(sourceName);
  await page.getByRole("button", { name: "Create source" }).click();
  await expect(page.getByRole("heading", { name: sourceName })).toBeVisible();
  await page
    .getByRole("combobox", { name: "Source", exact: true })
    .selectOption({ label: sourceName });
  await page.getByLabel("Article title").fill("Browser synthetic article");
  await page
    .getByLabel("Article text")
    .fill("Atlas Labs launched new software with strong profit growth.");
  await page.getByLabel("Submission key").fill(`browser-${Date.now()}`);
  await page.getByRole("button", { name: "Submit article" }).click();
  await expect(
    page.getByRole("button", { name: "Check processing status" }),
  ).toBeVisible();
  await expect
    .poll(
      async () => {
        await page
          .getByRole("button", { name: "Check processing status" })
          .click();
        return page.locator("main").textContent();
      },
      { timeout: 60000 },
    )
    .toContain('"status":"COMPLETED"');
  await page
    .getByLabel("Access token")
    .fill(process.env.AEGIS_E2E_VIEWER_TOKEN!);
  await page.getByRole("button", { name: "Use token" }).click();
  await expect(
    page.getByRole("button", { name: "Create source" }),
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
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.locator(".identity")).toContainText("Anonymous");
  expect(errors).toEqual([]);
});
