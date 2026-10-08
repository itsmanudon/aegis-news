import { expect, test } from "@playwright/test";

test("navigation has one active indicator and a rounded native mode control", async ({
  page,
}) => {
  await page.goto("/");
  const active = page.getByRole("link", { name: "Discover", exact: true });
  await active.hover();
  const indicator = await active.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      decoration: style.textDecorationLine,
      border: style.borderBottomWidth,
      transform: style.textTransform,
    };
  });
  expect(indicator).toEqual({
    decoration: "none",
    border: "2px",
    transform: "none",
  });
  const mode = page.getByLabel("Data Mode", { exact: true });
  await expect(mode).toHaveJSProperty("tagName", "SELECT");
  expect(
    await mode.evaluate((element) => getComputedStyle(element).borderRadius),
  ).toBe("10px");
  await mode.focus();
  await expect(mode).toBeFocused();
  expect(
    await mode.evaluate((element) => getComputedStyle(element).outlineStyle),
  ).toBe("solid");
  await page.keyboard.press("ArrowDown");
  await expect(page.getByLabel("Data Mode", { exact: true })).toHaveValue(
    "real",
  );
});

test("mobile advanced filters are keyboard accessible and retain filtering and reset behavior", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 1000 });
  await page.goto("/documents");
  await expect(page.locator("tbody tr")).toHaveCount(6);
  await expect(
    page.getByLabel("Filter Documents", { exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Integrity", { exact: true })).not.toBeVisible();
  const advanced = page.getByRole("button", {
    name: "Advanced Filters",
    exact: true,
  });
  await advanced.focus();
  await page.keyboard.press("Enter");
  await expect(advanced).toHaveAttribute("aria-expanded", "true");
  await page.getByLabel("Integrity", { exact: true }).selectOption("failed");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Advanced Filters (1)", exact: true })
    .click();
  await expect(page.getByLabel("Integrity", { exact: true })).not.toBeVisible();
  await page
    .getByRole("button", { name: "Reset Filters", exact: true })
    .click();
  await expect(page.locator("tbody tr")).toHaveCount(6);
  await advanced.click();
  await page.getByLabel("Knowledge Cutoff (UTC)").fill("2026-10-03T08:04");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.getByText("Pending", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Reset Filters", exact: true })
    .click();
  await page.goto("/search");
  await page.getByLabel("Search Terms", { exact: true }).fill("credentials");
  await expect(page.locator("tbody tr")).toHaveCount(1);
});

test("timestamp groups and operational numbers use readable interface typography", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".story-lead time").first()).toHaveAttribute(
    "datetime",
    "2026-10-03T08:00:00.000Z",
  );
  await expect(page.locator(".story-lead .timestamp-date").first()).toHaveText(
    "3 Oct 2026",
  );
  await expect(page.locator(".story-lead .timestamp-clock").first()).toHaveText(
    "08:00 UTC",
  );
  await page.goto("/operations");
  await expect(page.locator(".overview-strip strong").first()).toHaveText("6");
  const font = await page
    .locator(".overview-strip strong")
    .first()
    .evaluate((element) => {
      const style = getComputedStyle(element);
      return { family: style.fontFamily, variants: style.fontVariantNumeric };
    });
  expect(font.family).not.toMatch(/Consolas|monospace/);
  expect(font.variants).toContain("tabular-nums");
});

test("polished reading and filter surfaces reflow across the requested widths", async ({
  page,
}) => {
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const route of ["/", "/documents", "/search", "/operations"]) {
      await page.goto(route);
      await expect(page.locator(".story-lead, tbody tr").first()).toBeVisible();
      if (width <= 600 && ["/documents", "/search"].includes(route)) {
        await page
          .getByRole("button", { name: "Advanced Filters", exact: true })
          .click();
        await expect(page.getByLabel("Knowledge Cutoff (UTC)")).toBeVisible();
      }
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBeTruthy();
    }
  }
});

test("operational status labels remain distinct with readable contrast", async ({
  page,
}) => {
  await page.goto("/operations");
  for (const status of ["failed", "unverified", "verified"]) {
    const badge = page.locator(`.badge.${status}`).first();
    await expect(badge).toHaveText(status[0].toUpperCase() + status.slice(1));
    const contrast = await badge.evaluate((element) => {
      const style = getComputedStyle(element);
      const luminance = (rgb: string) => {
        const values = rgb
          .match(/[\d.]+/g)!
          .slice(0, 3)
          .map(Number)
          .map((n) => n / 255)
          .map((n) =>
            n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4,
          );
        return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
      };
      const values = [
        luminance(style.color),
        luminance(style.backgroundColor),
      ].sort((a, b) => a - b);
      return (values[1] + 0.05) / (values[0] + 0.05);
    });
    expect(contrast).toBeGreaterThanOrEqual(4.5);
  }
});
