import { expect, test } from "@playwright/test";
import type { AxeResults } from "axe-core";
import { createRequire } from "node:module";
import { documents, entities } from "../src/lib/fixtures";
import { fixtureTopics } from "../src/lib/intelligence-fixtures";

const resolveDependency = createRequire(__filename);
const topic = fixtureTopics({ cutoff: "2026-10-03T09:00:00Z" }).data[0];
const routes = [
  "/",
  "/documents",
  `/documents/${documents[0].document.document_id}`,
  "/search",
  "/entities",
  `/entities/${entities[0].entity_id}`,
  "/events",
  "/topics",
  `/topics/${topic.topic_id}`,
  "/analytics",
  "/discovery",
  "/multimedia",
  "/provenance",
  "/operations",
  "/sources",
  "/security",
];

for (const width of [1440, 1024, 768, 390, 320]) {
  test(`Complete product reflow and accessible evidence at ${width}px`, async ({
    page,
  }, info) => {
    test.setTimeout(120000);
    await page.setViewportSize({ width, height: 1000 });
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator("main h1")).toBeVisible();
      await expect(page.getByLabel("Data Mode", { exact: true })).toHaveValue(
        "mock",
      );
      await expect(
        page.locator("main [role=status]").filter({ hasText: /^Loading/ }),
      ).toHaveCount(0);
      const disclosure = page.locator("main details > summary").first();
      if (await disclosure.isVisible()) {
        await disclosure.focus();
        await page.keyboard.press("Enter");
        await expect(disclosure.locator("..")).toHaveAttribute("open", "");
        const focus = await disclosure.evaluate((el) => ({
          style: getComputedStyle(el).outlineStyle,
          width: getComputedStyle(el).outlineWidth,
        }));
        expect(focus.style).not.toBe("none");
        expect(parseFloat(focus.width)).toBeGreaterThan(0);
      }
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        route,
      ).toBe(true);
      if (width === 1440 || width === 390) {
        await page.addScriptTag({
          path: resolveDependency.resolve("axe-core/axe.min.js"),
        });
        const result: AxeResults = await page.evaluate(async () => {
          const axe = (window as unknown as { axe: typeof import("axe-core") })
            .axe;
          return axe.run(document, {
            runOnly: {
              type: "tag",
              values: [
                "wcag2a",
                "wcag2aa",
                "wcag21a",
                "wcag21aa",
                "wcag22aa",
                "best-practice",
              ],
            },
          });
        });
        if (result.violations.length)
          await info.attach(`axe-${width}-${route.replaceAll("/", "_")}`, {
            body: JSON.stringify(result.violations, null, 2),
            contentType: "application/json",
          });
        expect(
          result.violations.map((v) => ({
            id: v.id,
            impact: v.impact,
            nodes: v.nodes.map((n) => ({
              target: n.target,
              failure: n.failureSummary,
            })),
          })),
          route,
        ).toEqual([]);
      }
      if (await disclosure.isVisible()) {
        await disclosure.focus();
        await page.keyboard.press("Escape");
        await expect(disclosure.locator("..")).not.toHaveAttribute("open");
        await expect(disclosure).toBeFocused();
      }
    }
  });
}

test("Mobile navigation supports keyboard disclosure and fallback fonts remain readable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 1000 });
  await page.route("**/*.woff2", (route) => route.abort());
  await page.goto("/");
  const navigation = page.getByRole("button", {
    name: "Navigation",
    exact: true,
  });
  await navigation.focus();
  await page.keyboard.press("Enter");
  await expect(navigation).toHaveAttribute("aria-expanded", "true");
  await expect(
    page.getByRole("link", { name: "Topics", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(navigation).toHaveAttribute("aria-expanded", "false");
  await expect(navigation).toBeFocused();
  await expect(page.locator("main h1")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("Complete product supports doubled text sizing and readable mobile chart labels", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 720, height: 1000 });
  for (const route of routes) {
    await page.goto(route);
    await expect(page.locator("main h1")).toBeVisible();
    await expect(
      page.locator("main [role=status]").filter({ hasText: /^Loading/ }),
    ).toHaveCount(0);
    await page.evaluate(() => {
      const sizes = Array.from(
        document.querySelectorAll<HTMLElement>("main *"),
      ).map((el) => ({ el, size: parseFloat(getComputedStyle(el).fontSize) }));
      for (const { el, size } of sizes) el.style.fontSize = `${size * 2}px`;
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      route,
    ).toBe(true);
  }
  await page.setViewportSize({ width: 320, height: 1000 });
  await page.goto("/analytics");
  const label = page.getByText("Recorded Documents", { exact: true });
  await expect(label).toBeVisible();
  expect(
    await label.evaluate((el) => parseFloat(getComputedStyle(el).fontSize)),
  ).toBeGreaterThanOrEqual(12);
});
