import { expect, test } from "@playwright/test";
import { join } from "node:path";
import { documents, entities } from "../src/lib/fixtures";

test("capture the entity, event and verification visual review gate", async ({
  page,
}, info) => {
  const capture = async (name: string) => {
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.mouse.move(0, 0);
    await page.screenshot({
      path: process.env.AEGIS_SCREENSHOT_DIR
        ? join(process.env.AEGIS_SCREENSHOT_DIR, name)
        : info.outputPath(name),
      fullPage: true,
    });
  };
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/entities");
  await expect(page.locator(".entity-entry")).toHaveCount(3);
  await capture("phase1c-directory-desktop.png");
  await page.setViewportSize({ width: 390, height: 844 });
  await capture("phase1c-directory-mobile.png");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/entities/${entities[0].entity_id}`);
  await expect(page.locator(".editorial-result").first()).toBeVisible();
  await capture("phase1c-entity-desktop.png");
  await page.locator(".editorial-result summary").first().click();
  await capture("phase1c-entity-evidence-expanded.png");
  await page.setViewportSize({ width: 390, height: 844 });
  await capture("phase1c-entity-evidence-mobile.png");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/events");
  await expect(page.locator(".event-record")).toHaveCount(6);
  await capture("phase1c-events-desktop.png");
  await page.setViewportSize({ width: 390, height: 844 });
  await capture("phase1c-events-mobile.png");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/provenance");
  await page
    .getByLabel("Select Document", { exact: true })
    .selectOption(documents[0].document.document_id);
  await expect(page.locator(".verification-current")).toContainText(
    "Not Checked",
  );
  await capture("phase1c-verification-desktop.png");
  await page.getByRole("button", { name: "Run Mock Verification" }).click();
  await expect(page.locator(".verification-result")).toContainText(
    "Simulated Mock Result",
  );
  await page
    .locator("summary")
    .filter({ hasText: "Provenance Operations" })
    .click();
  await page
    .locator("summary")
    .filter({ hasText: "Operation Evidence" })
    .first()
    .click();
  await capture("phase1c-verification-expanded.png");
  await page.setViewportSize({ width: 390, height: 844 });
  await capture("phase1c-verification-mobile.png");
});
