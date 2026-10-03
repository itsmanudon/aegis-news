import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { documents } from "../../lib/fixtures";
import { TimeRail, Timestamp } from "./time-rail";
import { AnalysisPanel } from "./analysis-panel";

describe("evidence presentation", () => {
  it("keeps all four time meanings and preserves unknown publication time", () => {
    const markup = renderToStaticMarkup(<TimeRail view={documents[2]} />);
    for (const label of [
      "Published",
      "First seen",
      "Ingested",
      "Intelligence available",
    ])
      expect(markup).toContain(label);
    expect(markup).toContain("Unknown");
    expect(markup).toContain("2026-10-03T08:16:00Z");
    expect(markup).toContain("2026-10-03T08:21:00Z");
  });
  it("labels model outputs and shows confidence, version and availability", () => {
    const markup = renderToStaticMarkup(
      <AnalysisPanel analyses={documents[0].analyses} />,
    );
    expect(markup).toContain("Model-generated intelligence");
    expect(markup).toContain("Assessments may be incorrect");
    expect(markup).toContain("Confidence 89%");
    expect(markup).toContain("aegis-topic-demo / 0.3.1");
    expect(markup).toContain("Configuration hash");
    expect(markup).toContain("Available");
  });
  it("normalizes offset timestamps to UTC and handles malformed dates", () => {
    expect(
      renderToStaticMarkup(<Timestamp value="2026-10-03T13:30:00+05:30" />),
    ).toContain("2026-10-03 08:00:00 UTC");
    expect(renderToStaticMarkup(<Timestamp value="invalid" />)).toContain(
      "Unknown",
    );
  });
});
