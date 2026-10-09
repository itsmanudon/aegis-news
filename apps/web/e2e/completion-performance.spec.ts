import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

type ProbeState = {
  supported: string[];
  lcpMs: number | null;
  cls: number;
  shiftSession: { first: number; last: number; value: number } | null;
  longTasks: { startMs: number; durationMs: number }[];
  chartMountedAtMs: number | null;
  chartAnimationFrameAtMs: number | null;
};
type ProbeWindow = Window & { __aegisCompletionPerformance?: ProbeState };

const outputDirectory =
  process.env.AEGIS_COMPLETION_PERF_DIR ??
  "C:/Users/manan/.codex/visualizations/2026/10/08/01a11a47-4b4a-7592-a1eb-cef2573b628a";

test.use({ trace: "off", video: "off" });

test("record local production navigation and resource performance without eager intelligence", async ({
  browser,
  baseURL,
}) => {
  test.skip(
    process.env.AEGIS_COMPLETION_PERF !== "1",
    "Opt-in production performance probe; use an existing production server in mock mode.",
  );
  test.setTimeout(120_000);
  const samples = [];
  const routes = [
    { path: "/", ready: ".story-lead" },
    { path: "/analytics", ready: "#analytics-population-heading" },
    { path: "/multimedia", ready: "#media-story-select" },
  ];

  for (const route of routes) {
    for (let sample = 1; sample <= 3; sample++) {
      // Fresh contexts isolate browser HTTP/storage/query caches. The browser
      // process, operating system and already-built local server stay warm.
      const context = await browser.newContext({
        baseURL: baseURL ?? "http://127.0.0.1:3104",
        viewport: { width: 1440, height: 1000 },
        serviceWorkers: "block",
      });
      try {
        await context.addInitScript(() => {
          const state: ProbeState = {
            supported: [...PerformanceObserver.supportedEntryTypes],
            lcpMs: null,
            cls: 0,
            shiftSession: null,
            longTasks: [],
            chartMountedAtMs: null,
            chartAnimationFrameAtMs: null,
          };
          (window as ProbeWindow).__aegisCompletionPerformance = state;
          if (state.supported.includes("largest-contentful-paint")) {
            new PerformanceObserver((list) => {
              const last = list.getEntries().at(-1);
              if (last) state.lcpMs = last.startTime;
            }).observe({ type: "largest-contentful-paint", buffered: true });
          }
          if (state.supported.includes("layout-shift")) {
            new PerformanceObserver((list) => {
              for (const entry of list.getEntries()) {
                const shift = entry as PerformanceEntry & {
                  value: number;
                  hadRecentInput: boolean;
                };
                if (shift.hadRecentInput) continue;
                const session = state.shiftSession;
                if (
                  session &&
                  shift.startTime - session.last < 1000 &&
                  shift.startTime - session.first < 5000
                ) {
                  session.last = shift.startTime;
                  session.value += shift.value;
                } else {
                  state.shiftSession = {
                    first: shift.startTime,
                    last: shift.startTime,
                    value: shift.value,
                  };
                }
                state.cls = Math.max(state.cls, state.shiftSession!.value);
              }
            }).observe({ type: "layout-shift", buffered: true });
          }
          if (state.supported.includes("longtask")) {
            new PerformanceObserver((list) => {
              for (const entry of list.getEntries()) {
                state.longTasks.push({
                  startMs: entry.startTime,
                  durationMs: entry.duration,
                });
              }
            }).observe({ type: "longtask", buffered: true });
          }
          const chartObserver = new MutationObserver(() => {
            if (
              document.querySelector(
                'svg[aria-label="Recorded Documents by Observed UTC Day"]',
              )
            ) {
              state.chartMountedAtMs = performance.now();
              requestAnimationFrame(() => {
                state.chartAnimationFrameAtMs = performance.now();
              });
              chartObserver.disconnect();
            }
          });
          chartObserver.observe(document, { childList: true, subtree: true });
        });
        const page = await context.newPage();
        const apiRequests: string[] = [];
        const eagerIntelligenceRequests: string[] = [];
        page.on("request", (request) => {
          const pathname = new URL(request.url()).pathname;
          if (!pathname.startsWith("/api/v1/")) return;
          // Record route shapes only: no query parameters, headers, request
          // bodies, credentials, document/source IDs or model identifiers.
          const path = pathname
            .replace(/(\/documents\/)[^/]+/, "$1:id")
            .replace(/(\/topics\/)[^/]+/, "$1:id")
            .replace(/(\/entities\/)[^/]+/, "$1:id")
            .replace(/(\/sources\/)[^/]+/, "$1:id");
          apiRequests.push(path);
          if (/\/documents\/[^/]+\/intelligence$/.test(pathname))
            eagerIntelligenceRequests.push(path);
        });

        await page.goto(route.path, { waitUntil: "load" });
        await expect(page.getByLabel("Data Mode")).toHaveValue("mock");
        await expect(page.locator(route.ready)).toBeVisible();
        await page.evaluate(async () => {
          await document.fonts.ready;
          await new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
          );
        });
        // Observe a fixed one-second idle interval after content and fonts are
        // ready. This is a reproducible local sample, not field CWV measurement.
        await page.waitForTimeout(1000);

        const measurements = await page.evaluate(() => {
          const state = (window as ProbeWindow).__aegisCompletionPerformance!;
          const navigation = performance.getEntriesByType(
            "navigation",
          )[0] as PerformanceNavigationTiming;
          const resources = performance.getEntriesByType(
            "resource",
          ) as PerformanceResourceTiming[];
          const categories = {
            javascript: {
              count: 0,
              encodedBytes: 0,
              decodedBytes: 0,
              transferBytes: 0,
              zeroTransferCount: 0,
            },
            css: {
              count: 0,
              encodedBytes: 0,
              decodedBytes: 0,
              transferBytes: 0,
              zeroTransferCount: 0,
            },
            fonts: {
              count: 0,
              encodedBytes: 0,
              decodedBytes: 0,
              transferBytes: 0,
              zeroTransferCount: 0,
            },
          };
          let unclassifiedResourceCount = 0;
          let crossOriginZeroSizeCount = 0;
          let devAssetsObserved = false;
          for (const resource of resources) {
            const url = new URL(resource.name);
            if (
              /webpack-hmr|turbopack-hmr|next-devtools|\/static\/development\//.test(
                url.pathname,
              )
            )
              devAssetsObserved = true;
            if (
              url.origin !== location.origin &&
              resource.transferSize === 0 &&
              resource.encodedBodySize === 0
            )
              crossOriginZeroSizeCount++;
            const category = /\.(?:woff2?|ttf|otf)$/i.test(url.pathname)
              ? categories.fonts
              : /\.css$/i.test(url.pathname)
                ? categories.css
                : /\.(?:m?js)$/i.test(url.pathname)
                  ? categories.javascript
                  : undefined;
            if (!category) {
              unclassifiedResourceCount++;
              continue;
            }
            category.count++;
            category.encodedBytes += resource.encodedBodySize;
            category.decodedBytes += resource.decodedBodySize;
            category.transferBytes += resource.transferSize;
            if (!resource.transferSize) category.zeroTransferCount++;
          }
          const chart = document.querySelector(
            'svg[aria-label="Recorded Documents by Observed UTC Day"]',
          );
          const chartReadStart = performance.now();
          const chartElementCount = chart?.querySelectorAll("*").length ?? 0;
          if (chart) chart.getBoundingClientRect();
          const chartDomReadMs = chart
            ? performance.now() - chartReadStart
            : null;
          const fonts = {
            status: document.fonts.status,
            loadedFaceCount: Array.from(document.fonts).filter(
              (font) => font.status === "loaded",
            ).length,
            registeredFaceCount: document.fonts.size,
          };
          return {
            navigation: {
              ttfbMs: navigation.responseStart - navigation.startTime,
              domContentLoadedMs:
                navigation.domContentLoadedEventEnd - navigation.startTime,
              loadMs: navigation.loadEventEnd - navigation.startTime,
              durationMs: navigation.duration,
              documentEncodedBytes: navigation.encodedBodySize,
              documentTransferBytes: navigation.transferSize,
            },
            observed: {
              supportedEntryTypes: state.supported,
              lcpMs: state.lcpMs,
              firstContentfulPaintMs:
                performance.getEntriesByName("first-contentful-paint")[0]
                  ?.startTime ?? null,
              cls: state.supported.includes("layout-shift") ? state.cls : null,
              longTaskCount: state.longTasks.length,
              longTaskTotalMs: state.longTasks.reduce(
                (total, entry) => total + entry.durationMs,
                0,
              ),
              observationEndMs: performance.now(),
            },
            resources: {
              ...categories,
              totalCount: resources.length,
              unclassifiedResourceCount,
              crossOriginZeroSizeCount,
            },
            fonts,
            chart: {
              present: !!chart,
              mountedAtMs: state.chartMountedAtMs,
              animationFrameAfterMountMs: state.chartAnimationFrameAtMs,
              svgDescendantCount: chartElementCount,
              domReadDurationMs: chartDomReadMs,
            },
            horizontalOverflow:
              document.documentElement.scrollWidth > innerWidth,
            devAssetsObserved,
          };
        });

        const apiPathCounts = Object.fromEntries(
          [...new Set(apiRequests)]
            .sort()
            .map((path) => [
              path,
              apiRequests.filter((request) => request === path).length,
            ]),
        );
        samples.push({
          route: route.path,
          sample,
          ...measurements,
          apiRequestCount: apiRequests.length,
          apiPathCounts,
          eagerIntelligenceRequestCount: eagerIntelligenceRequests.length,
        });
        expect(eagerIntelligenceRequests).toEqual([]);
        expect(measurements.horizontalOverflow).toBe(false);
        if (route.path === "/")
          expect(
            measurements.observed.cls,
            "Initial archive loading should reserve reading space",
          ).toBeLessThan(0.1);
        expect(
          measurements.devAssetsObserved,
          "Use next build/start with AEGIS_E2E_EXTERNAL_SERVER=1 for production measurements.",
        ).toBe(false);
        const checkFinite = (value: unknown) => {
          if (typeof value === "number")
            expect(Number.isFinite(value)).toBe(true);
          else if (value && typeof value === "object")
            for (const child of Object.values(value)) checkFinite(child);
        };
        checkFinite(measurements);
      } finally {
        await context.close();
      }
    }
  }

  mkdirSync(outputDirectory, { recursive: true });
  writeFileSync(
    join(outputDirectory, "completion-performance.json"),
    JSON.stringify(
      {
        capturedAt: new Date().toISOString(),
        browserVersion: browser.version(),
        mode: "mock",
        viewport: { width: 1440, height: 1000 },
        samplesPerRoute: 3,
        environment:
          "Local production build expected, unthrottled browser, fictional mock records. No live API or provider latency is measured.",
        cacheSemantics:
          "Fresh isolated browser context per navigation. Browser process, operating system and local server may remain warm. Fonts are local assets. Zero transfer sizes can indicate cache reuse or unavailable cross-origin timing, not zero asset size.",
        measurementLimits:
          "Observed LCP and CLS cover initial load through one idle second after content/fonts readiness; these are local laboratory observations, not field Core Web Vitals or percentile claims. Unsupported observer values stay null. No INP is measured. Chart mount/frame timing and one DOM read are proxies, not isolated React render CPU. Resource totals include visible-link prefetching; RSC/fetch resources remain unclassified.",
        samples,
      },
      null,
      2,
    ),
  );
});

test("mobile omits the desktop-only italic font download", async ({
  browser,
  baseURL,
}) => {
  test.skip(
    process.env.AEGIS_COMPLETION_PERF !== "1",
    "Opt-in production font probe",
  );
  const samples = [];
  for (let sample = 1; sample <= 3; sample++) {
    const context = await browser.newContext({
      baseURL,
      viewport: { width: 390, height: 1000 },
    });
    try {
      const page = await context.newPage();
      await page.goto("/");
      await expect(page.locator(".story-lead")).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      const fonts = await page.evaluate(() =>
        performance
          .getEntriesByType("resource")
          .filter((entry) => entry.name.includes(".woff2"))
          .map((entry) => {
            const resource = entry as PerformanceResourceTiming;
            return {
              path: new URL(resource.name).pathname,
              encodedBytes: resource.encodedBodySize,
              transferBytes: resource.transferSize,
            };
          }),
      );
      expect(fonts.some((font) => font.path.includes("Italic"))).toBe(false);
      expect(fonts).toHaveLength(2);
      samples.push({
        sample,
        fonts,
        encodedBytes: fonts.reduce((sum, font) => sum + font.encodedBytes, 0),
      });
    } finally {
      await context.close();
    }
  }
  mkdirSync(outputDirectory, { recursive: true });
  writeFileSync(
    join(outputDirectory, "completion-mobile-performance.json"),
    JSON.stringify(
      {
        viewport: { width: 390, height: 1000 },
        mode: "mock",
        samples,
        baselineEncodedBytes: 1128028,
        retainedOriginalLicensedAssets: true,
      },
      null,
      2,
    ),
  );
});
