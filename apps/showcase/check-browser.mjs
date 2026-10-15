// Production-output acceptance checks. No private API or provider is contacted.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(root, "../web/package.json"));
const { chromium } = require("@playwright/test");
const dist = path.join(root, "dist");
const dataset = JSON.parse(
  await readFile(path.join(dist, "data/dataset.json")),
);
const manifest = JSON.parse(
  await readFile(path.join(dist, "data/manifest.json")),
);
const reportDir = path.join(root, "test-results");
await mkdir(reportDir, { recursive: true });
const mime = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "text/javascript",
  ".json": "application/json",
  ".woff2": "font/woff2",
};
const headers = Object.fromEntries(
  (await readFile(path.join(root, "_headers"), "utf8"))
    .trim()
    .split("\n")
    .slice(1)
    .map((line) => {
      const index = line.indexOf(":");
      return [line.slice(0, index).trim(), line.slice(index + 1).trim()];
    }),
);
const server = createServer(async (request, response) => {
  if (!["GET", "HEAD"].includes(request.method)) {
    response.writeHead(405);
    response.end();
    return;
  }
  let name = decodeURIComponent(
    new URL(request.url, "http://preview").pathname,
  );
  if (name.endsWith("/")) name += "index.html";
  const target = path.resolve(dist, "." + name);
  if (!target.startsWith(dist + path.sep)) {
    response.writeHead(403);
    response.end();
    return;
  }
  try {
    const body = await readFile(target);
    response.writeHead(200, {
      ...headers,
      "Content-Type": mime[path.extname(target)] || "text/plain",
    });
    response.end(request.method === "HEAD" ? undefined : body);
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain" });
    response.end("Not Found");
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
    ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
    : {}),
});
const errors = [];
const requests = [];
const context = await browser.newContext();
const page = await context.newPage();
page.on("pageerror", (error) => errors.push(error.message));
page.on("request", (request) =>
  requests.push({ url: request.url(), method: request.method() }),
);
const routes = Object.keys(manifest.files)
  .filter((name) => name.endsWith("index.html"))
  .map((name) => "/" + name.slice(0, -10));
try {
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    for (const route of routes) {
      const response = await page.goto(base + route);
      assert.equal(response.status(), 200, route);
      await page.locator("h1").waitFor();
      assert.equal(await page.locator("h1").count(), 1, route);
      assert.equal(await page.locator("form,iframe").count(), 0, route);
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `Horizontal overflow: ${route} at ${viewport.width}`,
      );
      if (viewport.width === 1440 && route.startsWith("/stories/")) {
        await page.locator("[data-verify]").click();
        await page.waitForFunction(
          () => !document.querySelector("[data-verify]").disabled,
        );
        assert(
          (await page.locator(".verify-status").innerText()).startsWith(
            "Verified:",
          ),
          route,
        );
      }
    }
    await page.goto(base + "/");
    await page.screenshot({
      path: path.join(reportDir, `${viewport.width}-discover.png`),
      fullPage: true,
    });
    await page.goto(base + "/archive/");
    await page.screenshot({
      path: path.join(reportDir, `${viewport.width}-archive.png`),
      fullPage: true,
    });
  }
  await page.locator("#search").fill("zzzz-no-such-headline");
  assert.equal(await page.locator("[data-story]:visible").count(), 0);
  assert(await page.locator("#no-results").isVisible());
  await page.locator("#search").fill("NASA");
  assert.equal(
    await page.locator("[data-story]:visible").count(),
    dataset.records.filter((r) =>
      r.metadata.title.toLowerCase().includes("nasa"),
    ).length,
  );
  await page.locator("#search").fill("");
  const topics = [
    ...new Set(
      dataset.records.map(
        (r) =>
          r.analyses.find((a) => a.analysis_type === "topic").outputs[0].label,
      ),
    ),
  ];
  for (const topic of topics) {
    await page.locator("#topic").selectOption(topic);
    assert.equal(
      await page.locator("[data-story]:visible").count(),
      dataset.records.filter(
        (r) =>
          r.analyses.find((a) => a.analysis_type === "topic").outputs[0]
            .label === topic,
      ).length,
    );
  }
  await page.goto(base + "/analytics/");
  for (const table of await page.locator("table").all()) {
    const counts = await table
      .locator("tbody td:first-of-type")
      .allTextContents();
    assert.equal(
      counts.reduce((sum, value) => sum + Number(value), 0),
      dataset.records.length,
    );
  }
  const first = dataset.records[0].metadata.id;
  for (const file of [
    "metadata.json",
    "analysis.json",
    "manifest.json",
    "signed-body.json",
  ]) {
    const pattern = "**/data/evidence/" + first + "/" + file;
    await page.route(pattern, async (route) => {
      const response = await route.fetch();
      const text = await response.text();
      let body;
      if (file === "metadata.json") body = text.replace("NASA", "NAsA");
      else if (file === "analysis.json")
        body = text.replace("local-baseline", "local-bAseline");
      else if (file === "manifest.json") {
        const value = JSON.parse(text);
        value.signature = "A".repeat(88);
        body = JSON.stringify(value);
      } else body = text.replace("aegis-provenance-1", "aegis-provenance-2");
      await route.fulfill({ response, body });
    });
    await page.goto(base + "/verification/");
    await page.locator("[data-verify]").click();
    await page.waitForFunction(
      () => !document.querySelector("[data-verify]").disabled,
    );
    assert(
      (await page.locator(".verify-status").innerText()).startsWith(
        "Not Verified:",
      ),
      file,
    );
    await page.unroute(pattern);
  }
  await page.goto(base + "/verification/");
  await page.locator("[data-verify]").click();
  await page.waitForFunction(
    () => !document.querySelector("[data-verify]").disabled,
  );
  assert(
    (await page.locator(".verify-status").innerText()).startsWith("Verified:"),
  );
  for (const endpoint of [
    "/api/documents",
    "/admin/",
    "/security/",
    ".env",
    "/functions/",
  ]) {
    assert.equal(
      (
        await context.request.get(base + "/" + endpoint.replace(/^\//, ""))
      ).status(),
      404,
    );
  }
  assert(requests.every((r) => r.url.startsWith(base) && r.method === "GET"));
  assert.deepEqual(errors, []);
  const report = {
    routes: routes.length,
    viewports: [1440, 390],
    signedRecordsVerified: dataset.records.length,
    tamperingCasesRejected: 4,
    search: true,
    topics: true,
    analytics: true,
    externalRequests: 0,
    browserErrors: errors,
    export_sha256: manifest.export_sha256,
  };
  await import("node:fs/promises").then((fs) =>
    fs.writeFile(
      path.join(reportDir, "report.json"),
      JSON.stringify(report, null, 2),
    ),
  );
  console.log(JSON.stringify(report));
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
