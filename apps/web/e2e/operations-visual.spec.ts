import { expect, test } from "@playwright/test";
import { join } from "node:path";
import { operationalApi, operator } from "./operations-support";
import { sources } from "../src/lib/fixtures";

test("capture operations source ingestion provider audit and state visual review", async ({
  page,
}, info) => {
  test.setTimeout(60000);
  await operationalApi(page);
  const output = (name: string) =>
    process.env.AEGIS_SCREENSHOT_DIR
      ? join(process.env.AEGIS_SCREENSHOT_DIR, name)
      : info.outputPath(name);
  const capture = async (name: string, selector?: string) => {
    await page.evaluate(() => document.fonts.ready);
    await page.mouse.move(0, 0);
    if (selector) {
      // Capture a viewport fitted to the section. Tall element crops can
      // incorrectly composite offscreen fixed navigation into the image.
      const viewport=page.viewportSize()!;
      const target=page.locator(selector),box=await target.boundingBox();
      if(!box) throw new Error(`Missing screenshot section: ${selector}`);
      await page.setViewportSize({width:viewport.width,height:Math.ceil(box.height)+48});
      await target.evaluate(element=>window.scrollTo(0,window.scrollY+element.getBoundingClientRect().top-24));
      await page.screenshot({path:output(name),fullPage:false});
      await page.setViewportSize(viewport);
    } else {
      await page.evaluate(() => scrollTo(0, 0));
      await page.screenshot({ path: output(name), fullPage: true });
    }
  };
  for (const [name, width, height] of [
    ["desktop", 1440, 1000],
    ["tablet", 768, 1024],
    ["mobile", 390, 844],
  ] as const) {
    await page.setViewportSize({ width, height });
    await operator(page);
    await expect(page.locator(".source-record")).toHaveCount(1);
    await capture(`phase1d-registry-${name}.png`, "#registry");
    await capture(
      `phase1d-create-source-${name}.png`,
      "section:has(> h2:text-is('Create Source'))",
    );
    await page.locator(".source-record summary").first().click();
    await capture(`phase1d-source-details-${name}.png`, "#registry");
    await page
      .getByLabel("Source", { exact: true })
      .selectOption(sources[0].source_id);
    await page
      .getByLabel("Article Title", { exact: true })
      .fill("Controlled Article Submission");
    await page
      .getByLabel("Article Text", { exact: true })
      .fill(
        "Synthetic captured text used only by the intercepted browser test. No live source is submitted.",
      );
    await page
      .getByLabel("Submission Key", { exact: true })
      .fill("visual-review-stable-key");
    await page
      .getByRole("button", { name: "Submit Article", exact: true })
      .click();
    await expect(
      page.getByText("Request Accepted", { exact: true }),
    ).toBeVisible();
    await capture(
      `phase1d-ingestion-accepted-${name}.png`,
      "section:has(> h2:text-is('Submit Articles'))",
    );
    await page
      .getByRole("button", { name: "Check Processing Status", exact: true })
      .click();
    await expect(
      page.getByText("Workflow Completed", { exact: true }),
    ).toBeVisible();
    await page
      .locator("summary")
      .filter({ hasText: "Workflow Technical Details" })
      .click();
    await capture(`phase1d-workflow-${name}.png`, "#workflow-lookup");
    await page
      .getByRole("button", { name: "Fetch Bounded Batch", exact: true })
      .click();
    await expect(
      page.getByText("Acquisition Running", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Check Provider Run", exact: true })
      .click();
    await expect(
      page.getByText("Acquisition Completed", { exact: true }),
    ).toBeVisible();
    await page
      .locator("summary")
      .filter({ hasText: "Acquisition Details" })
      .first()
      .click();
    await capture(`phase1d-providers-${name}.png`, "#provider-operations");
    await page
      .getByRole("navigation", { name: "Operational Workspaces" })
      .getByRole("link", { name: "Security & Audit", exact: true })
      .click();
    await expect(page.locator(".audit-record")).toHaveCount(3);
    await capture(`phase1d-security-${name}.png`);
    await page.locator(".audit-record summary").first().click();
    await capture(
      `phase1d-audit-details-${name}.png`,
      "section:has(> div > #audit-heading)",
    );
    await page.goto("/operations");
    await expect(
      page.getByRole("heading", { name: "Operational Overview", exact: true }),
    ).toBeVisible();
    if (width === 390)
      await page
        .getByRole("button", { name: "Navigation", exact: true })
        .click();
    await capture(`phase1d-navigation-${name}.png`);
  }
  for (const [name, width, height] of [
    ["desktop", 1440, 1000],
    ["tablet", 768, 1024],
    ["mobile", 390, 844],
  ] as const) {
    await page.setViewportSize({ width, height });
    let release: () => void = () => {};
    const blocked = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route("**/api/v1/sources?*", async (route) => {
      await blocked;
      await route.fulfill({
        json: {
          data: [],
          meta: { request_id: "empty-review", api_version: "v1" },
          pagination: { has_more: false, next_cursor: null },
        },
      });
    });
    await operator(page);
    await expect(
      page
        .locator("#registry [role=status]")
        .filter({ hasText: "Loading intelligence records" }),
    ).toBeVisible();
    await capture(`phase1d-loading-${name}.png`, "#registry");
    release();
    await expect(
      page.getByText("No sources are supplied on this page.", { exact: false }),
    ).toBeVisible();
    await capture(`phase1d-empty-${name}.png`, "#registry");
    await page.unroute("**/api/v1/sources?*");
    await page.route("**/api/v1/sources?*", (route) =>
      route.fulfill({
        status: 403,
        json: {
          error: {
            code: "FORBIDDEN",
            message: "Source registry access is unavailable to this identity.",
            request_id: "forbidden-review",
          },
        },
      }),
    );
    await operator(page);
    await expect(page.locator("#registry [role=alert]")).toBeVisible();
    await capture(`phase1d-error-${name}.png`, "#registry");
    await page.unroute("**/api/v1/sources?*");
  }
});
