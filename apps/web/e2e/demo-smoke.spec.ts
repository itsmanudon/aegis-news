import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

test.use({ trace: "off", video: "off", screenshot: "off" });
test.describe.configure({ mode: "serial" });
test.skip(process.env.AEGIS_DEMO_SMOKE !== "1", "Opt-in local demo smoke");

const shots = path.resolve(process.cwd(), "../../.integration-results/local-demo");

async function authenticate(page: Page) {
  const token = process.env.AEGIS_E2E_TOKEN;
  if (!token) throw new Error("Demo smoke requires a memory-only development token");
  await expect(page.getByLabel("Data Mode")).toHaveValue("real");
  await expect(page.getByRole("status").getByText("Real API")).toBeVisible();
  const field = page.getByLabel("Access Token");
  await field.evaluate((element, value) => {
    const input = element as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }, token);
  await page.getByRole("button", { name: "Use Token", exact: true }).click();
  await expect(page.locator(".identity")).toContainText("demo-smoke");
  await expect(field).toHaveValue("");
}

async function shot(page: Page, name: string) {
  mkdirSync(shots, { recursive: true });
  await page.screenshot({ path: path.join(shots, name), animations: "disabled" });
}

test("real API demonstration journey", async ({ page }) => {
  test.setTimeout(180000);
  page.setDefaultTimeout(15000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await authenticate(page);
  const story = page.locator('a[href^="/documents/"]').first();
  await expect(story).toBeVisible({ timeout: 20000 });
  await shot(page, "01-discover-desktop.png");
  await page.setViewportSize({ width: 390, height: 844 });
  await shot(page, "02-discover-mobile.png");
  await page.setViewportSize({ width: 1440, height: 900 });

  await story.click();
  await expect(page.getByRole("heading", { name: "Model-Generated Intelligence" })).toBeVisible();
  await page.getByRole("button", { name: "Verify Integrity" }).click();
  await expect(page.locator(".verification-result")).toContainText("Verified");
  await expect(page.locator(".verification-result")).not.toContainText("Simulated");
  await shot(page, "03-story-verification.png");

  await page.getByRole("link", { name: "Topics", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Topic Directory" })).toBeVisible();
  const topic = page.locator('a[href*="/topics/topic_v1_"]').first();
  await expect(topic).toBeVisible();
  await topic.click();
  const supporting = page.getByRole("heading", { name: "Supporting Reporting" });
  await expect(supporting).toBeVisible();
  await supporting.scrollIntoViewIfNeeded();
  await expect(page.getByText("Simulated Model Assessments")).toHaveCount(0);
  await shot(page, "04-topic-detail.png");

  await page.getByRole("link", { name: "Analytics", exact: true }).click();
  await page.getByLabel("Window Start (Inclusive, UTC)").fill("2020-01-01T00:00");
  await page.getByLabel("Window End (Exclusive, UTC)").fill("2021-01-01T00:00");
  await page.getByLabel("Time Basis").selectOption("published_at");
  await page.getByRole("button", { name: "Apply Window" }).click();
  await expect(page.getByRole("heading", { name: "The Reporting Population" })).toBeVisible();
  const population = page
    .locator("div")
    .filter({ has: page.getByText("Documents in Population", { exact: true }) })
    .locator("dd")
    .first();
  await expect(population).not.toHaveText("0");
  await population.scrollIntoViewIfNeeded();
  await shot(page, "05-analytics.png");

  await page.getByRole("link", { name: "Media Lab", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Media Lab" })).toBeVisible();
  await expect(page.getByText(/video references in this bounded response/)).toBeVisible();
  await shot(page, "06-media-lab.png");

  await page.getByRole("link", { name: "Verification", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Verification Workspace" })).toBeVisible();
  await page.getByLabel("Select Document").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Verify Integrity" }).click();
  const verification = page.locator(".verification-result");
  await expect(verification).toContainText("Passed");
  await expect(verification).toContainText("Content Integrity");
  await expect(verification).toContainText("Provenance Chain");
  await expect(verification).toContainText("Digital Signature");
  await verification.scrollIntoViewIfNeeded();
  await shot(page, "07-verification.png");

  await page.getByRole("link", { name: "Discover", exact: true }).click();
  await page.getByRole("link", { name: /Explore Chronological Discovery/ }).click();
  await expect(page.getByRole("heading", { name: "Chronological Discovery" })).toBeVisible();
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Document Archive" })).toBeVisible();
  await page.getByRole("link", { name: "Search", exact: true }).click();
  await page.getByLabel("Search Terms").fill("Atlas");
  await expect(
    page.getByRole("link", { name: "Atlas Labs reports growth and merger" }).first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "Entities", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Entity Directory" })).toBeVisible();
  await page.getByRole("link", { name: "Events / Timeline", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Events / Timeline" })).toBeVisible();

  await page.getByRole("link", { name: "Operations & Security" }).click();
  await expect(page.getByRole("heading", { name: "Operational Overview" })).toBeVisible();
  await shot(page, "08-operations.png");
  await page.getByRole("link", { name: "Sources / Admin", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sources & Ingestion" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Source Registry" })).toBeVisible();
  await expect(page.locator(".source-record").first()).toBeVisible();
  await page.getByRole("link", { name: "Audit / Security", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Security & Audit" })).toBeVisible();
  await shot(page, "09-security.png");
  expect(errors).toEqual([]);
});
