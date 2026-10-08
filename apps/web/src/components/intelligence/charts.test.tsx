import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { CoverageChart, Distribution } from "./charts";
it("preserves observed days and supplies accessible exact values without filling gaps", () => {
  const html = renderToStaticMarkup(
    <CoverageChart
      buckets={[
        { day: "2026-10-01", document_count: 2, classified_count: 1 },
        { day: "2026-10-03", document_count: 7, classified_count: 0 },
      ]}
    />,
  );
  expect(html).toContain("2026-10-01");
  expect(html).toContain("2026-10-03");
  expect(html).not.toContain("2026-10-02");
  expect(html).toContain("Recorded Documents");
  expect(html).toContain("<svg");
});
it("empty coverage is unavailable observations rather than an invented zero series", () => {
  const html = renderToStaticMarkup(<CoverageChart buckets={[]} />);
  expect(html).toContain("No observations");
  expect(html).not.toContain("<polyline");
});
it("bars show exact populations and preserve arbitrary labels as escaped text", () => {
  const html = renderToStaticMarkup(
    <Distribution
      label="Sentiment Classification"
      denominator={10}
      values={[
        { name: "mixed", count: 2 },
        { name: "<script>", count: 3 },
      ]}
    />,
  );
  expect(html).toContain("2 of 10");
  expect(html).toContain("&lt;script&gt;");
  expect(html).not.toContain("<script>");
});
