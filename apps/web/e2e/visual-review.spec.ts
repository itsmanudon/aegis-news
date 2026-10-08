import { expect, test } from "@playwright/test";
import { join } from "node:path";

test("capture the editorial reading and discovery review gate", async ({
  page,
}, info) => {
  const file = (name: string) =>
    process.env.AEGIS_SCREENSHOT_DIR
      ? join(process.env.AEGIS_SCREENSHOT_DIR, name)
      : info.outputPath(name);
  const capture = async (name: string, fullPage = true) => {
    await page.evaluate(() => document.fonts.ready);
    // Full-page captures must begin at the top after locators scroll to evidence.
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.mouse.move(0, 0);
    await page.screenshot({ path: file(name), fullPage });
  };
  const story = "/documents/doc_00000000-0000-4000-8000-000000000001";
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(story);
  await expect(page.locator(".story-report")).toBeVisible();
  await capture("phase1b-story-desktop.png");
  await page
    .locator("summary")
    .filter({ hasText: "Technical Metadata" })
    .first()
    .click();
  await page
    .locator("summary")
    .filter({ hasText: "Provenance Operations" })
    .click();
  await page
    .locator("summary")
    .filter({ hasText: "Operation Evidence" })
    .first()
    .click();
  await capture("phase1b-story-evidence-expanded.png");
  await page.goto(story);
  await expect(page.locator(".story-report")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await capture("phase1b-story-mobile.png");
  await page.setViewportSize({ width: 320, height: 844 });
  await capture("phase1b-story-narrow.png");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/documents");
  await expect(page.locator(".editorial-result")).toHaveCount(6);
  await capture("phase1b-documents-desktop-collapsed.png");
  await page.locator(".editorial-result").first().locator("summary").click();
  await capture("phase1b-documents-desktop-expanded.png");
  await page.setViewportSize({ width: 390, height: 844 });
  await capture("phase1b-documents-mobile-expanded.png");
  await page.locator(".editorial-result").first().locator("summary").click();
  await capture("phase1b-documents-mobile-collapsed.png");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("button", { name: "Evidence Table", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Expand Evidence", exact: true })
    .first()
    .click();
  await capture("phase1b-evidence-table-expanded.png");
  await page.goto("/search?q=credentials");
  await expect(page.locator(".editorial-result")).toHaveCount(1);
  await capture("phase1b-search-desktop.png");
  await page.setViewportSize({ width: 390, height: 1000 });
  await page
    .getByRole("button", { name: "Advanced Filters", exact: true })
    .click();
  await capture("phase1b-search-mobile-filters.png");
});
