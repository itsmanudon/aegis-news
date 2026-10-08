import { expect, test } from "@playwright/test";
test.use({ trace: "off" });
test("real provider articles, image references, video metadata and provenance", async ({
  page,
}) => {
  test.skip(
    process.env.AEGIS_PROVIDERS_E2E !== "1",
    "Opt-in local provider population; never contacts providers in CI",
  );
  const statuses: number[] = [];
  page.on("response", (r) => {
    if (r.url().includes("/api/v1/")) statuses.push(r.status());
  });
  await page.goto("/");
  await page.getByLabel("Access Token").fill(process.env.AEGIS_E2E_TOKEN!);
  await page.getByRole("button", { name: "Use Token" }).click();
  await expect(
    page.getByRole("heading", { name: "Provider Articles", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".external-card").first()).toBeVisible();
  await page.getByRole("link", { name: "Media Lab", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Media Lab", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open on YouTube ↗" }).first(),
  ).toBeVisible();
  await expect(page.locator(".external-image").first()).toBeVisible();
  await expect
    .poll(() =>
      page
        .locator(".external-card img")
        .evaluateAll(
          (images) =>
            images.filter(
              (image) =>
                (image as HTMLImageElement).complete &&
                (image as HTMLImageElement).naturalWidth > 0,
            ).length,
        ),
    )
    .toBeGreaterThan(0);
  await page.locator(".external-card h3 a").first().click();
  await expect(
    page.getByRole("heading", {
      name: "Provider Acquisition / Remote Media",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Model-Generated Intelligence",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Verify Integrity" }).click();
  await expect(
    page.getByText("Verified", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Operations & Security", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Sources / Admin", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Manual Provider Acquisition",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Fetch Bounded Batch" }),
  ).toBeEnabled();
  expect(statuses).not.toContain(429);
  expect(statuses.filter((s) => s >= 500)).toEqual([]);
});
