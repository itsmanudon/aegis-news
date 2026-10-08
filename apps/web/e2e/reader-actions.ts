import { expect, type Page } from "@playwright/test";

export async function expectReaderModel(page: Page, name: string) {
  await expect(
    page.locator(".analysis-record > p").filter({ hasText: name }).first(),
  ).toBeVisible();
}

export async function openStoredMedia(page: Page) {
  await page
    .locator("summary")
    .filter({ hasText: /^Media \/ Attachments \(/ })
    .click();
}
