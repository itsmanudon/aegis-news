import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

test.use({ trace: "off", viewport: { width: 1440, height: 1000 } });

test("capture public-safe live demo evidence", async ({ page, request }) => {
  test.skip(
    process.env.AEGIS_CAPTURE_EVIDENCE !== "1",
    "Optional live evidence capture",
  );
  test.setTimeout(120000);
  const output = path.resolve(process.cwd(), "../../docs/evidence/screenshots");
  mkdirSync(output, { recursive: true });
  const capture = async (name: string) => {
    await page.screenshot({
      path: path.join(output, `${name}.jpg`),
      type: "jpeg",
      quality: 70,
    });
  };
  await page.goto("/documents");
  await page.getByLabel("Access token").fill(process.env.AEGIS_E2E_TOKEN!);
  await page.getByRole("button", { name: "Use token" }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await capture("dashboard");
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
  await capture("document-intelligence");
  await page.getByRole("button", { name: "Verify integrity" }).click();
  await expect(page.locator(".verification-result")).toContainText("verified");
  await page.locator(".verification-result").scrollIntoViewIfNeeded();
  await capture("provenance-verification");
  await page
    .getByText("Media / attachments", { exact: true })
    .scrollIntoViewIfNeeded();
  await expect(page.locator(".media-record").first()).toContainText(
    "image/png",
  );
  await page
    .locator(".media-record")
    .first()
    .evaluate((element) => element.scrollIntoView({ block: "center" }));
  await capture("media-links");
  await page.getByRole("link", { name: "Entities", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Atlas Labs", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Inspect entity" }).first().click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await capture("entity-evidence");
  await page
    .getByRole("link", { name: "Events / timeline", exact: true })
    .click();
  await expect(page.locator(".timeline > li").first()).toBeVisible();
  await capture("events");
  await page
    .getByRole("link", { name: "Operations & Security", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Audit / security", exact: true })
    .click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await capture("audit-log");
  await page
    .getByLabel("Access token")
    .fill(process.env.AEGIS_E2E_VIEWER_TOKEN!);
  await page.getByRole("button", { name: "Use token" }).click();
  const denied = await request.post(
    `${process.env.AEGIS_E2E_API_URL}/api/v1/ingestions`,
    {
      headers: {
        Authorization: `Bearer ${process.env.AEGIS_E2E_VIEWER_TOKEN}`,
      },
      data: {},
    },
  );
  expect(denied.status()).toBe(403);
  await page
    .getByRole("link", { name: "Sources / admin", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Create source" }),
  ).toBeDisabled();
  await capture("scope-denial");
  await page.goto("http://127.0.0.1:38233/namespaces/default/workflows");
  await expect(
    page.getByText("ingestion-", { exact: false }).first(),
  ).toBeVisible();
  await capture("temporal-workflows");
  await page.goto("http://127.0.0.1:33001/login");
  await page.locator("input[name='user']").fill("aegis_dev");
  await page.locator("input[name='password']").fill("aegis_dev_only");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/login"));
  await page.goto("http://127.0.0.1:33001/d/aegis-demo");
  await expect(
    page.getByText("Demo worker correlation and trace IDs", { exact: true }),
  ).toBeVisible();
  await page.waitForTimeout(1500); // Allow local panels to finish rendering before export.
  await capture("grafana-loki");
});
