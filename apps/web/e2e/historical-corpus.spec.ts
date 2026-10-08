import { expect, test } from "@playwright/test";

test.use({ trace: "off" }); // Development tokens never enter trace artifacts.
test("historical corpus: real search, document intelligence, provenance and product views", async ({
  page,
}) => {
  test.skip(
    process.env.AEGIS_HISTORICAL_E2E !== "1",
    "Requires the optional local historical corpus",
  );
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/search");
  await expect(page.getByLabel("Data Mode")).toHaveValue("real");
  await page.getByLabel("Access Token").fill(process.env.AEGIS_E2E_TOKEN!);
  await page.getByRole("button", { name: "Use Token" }).click();
  await page
    .getByLabel("Search Terms")
    .fill(process.env.AEGIS_HISTORICAL_TITLE!);
  await page
    .getByLabel("Source", { exact: true })
    .selectOption(process.env.AEGIS_HISTORICAL_SOURCE_ID!);
  await expect(
    page
      .getByRole("link", {
        name: process.env.AEGIS_HISTORICAL_TITLE!,
        exact: true,
      })
      .first(),
  ).toBeVisible();
  await page
    .getByRole("link", {
      name: process.env.AEGIS_HISTORICAL_TITLE!,
      exact: true,
    })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Model-Generated Intelligence" }),
  ).toBeVisible();
  await expect(page.getByText("keyword-topics / 1")).toBeVisible();
  await page.getByRole("button", { name: "Verify Integrity" }).click();
  await expect(page.locator(".verification-result")).toContainText("Verified");
  await page.getByRole("link", { name: "Entities", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Entity Register", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Events / Timeline", exact: true })
    .click();
  await expect(page.locator(".timeline > li").first()).toBeVisible();
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await page
    .getByLabel("Filter Documents")
    .fill(process.env.AEGIS_HISTORICAL_TITLE!);
  await page
    .getByLabel("Source", { exact: true })
    .selectOption(process.env.AEGIS_HISTORICAL_SOURCE_ID!);
  await expect(
    page
      .getByRole("link", {
        name: process.env.AEGIS_HISTORICAL_TITLE!,
        exact: true,
      })
      .first(),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
