import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { components } from "@/lib/generated/api";
import {
  AnalyticsResults,
  AnalyticsTopicSelector,
  analyticsParameters,
  readAnalyticsParameters,
  supportingRecordsUrl,
  validateAnalyticsFilters,
} from "./analytics";

const report: components["schemas"]["AnalyticsReport"] = {
  start: "2026-10-01T00:00:07.125Z",
  end: "2026-10-08T00:00:07.125Z",
  as_of: "2026-10-08T09:11:07.125Z",
  time_basis: "published_at",
  topic_id: "topic-a",
  source_id: "source-b",
  population_count: 8,
  classified_count: 5,
  no_assessment_count: 3,
  unknown_time_count: 2,
  coverage: [
    { day: "2026-10-01", document_count: 3, classified_count: 2 },
    { day: "2026-10-03", document_count: 5, classified_count: 3 },
  ],
  sources: [
    { source_id: "source-b", name: "Example Publisher", document_count: 6 },
  ],
  sources_other_count: 2,
  sentiment: [
    { label: "neutral", document_count: 3 },
    { label: "mixed", document_count: 2 },
  ],
  models: [
    {
      provider: "example",
      model_name: "demo-document",
      model_version: "1.2",
      document_count: 4,
    },
  ],
  models_other_count: 1,
  selection_policy: "Latest eligible document-level assessment per document.",
  limitations: ["Mutable source metadata is not historical."],
};

describe("analytics query and evidence", () => {
  it("distinguishes otherwise identical topic cohorts and exposes the exact selected identity", () => {
    const first: components["schemas"]["TopicSummary"] = {
      topic_id: "cohort-a",
      label: "Synthetic Harbour Coverage",
      document_count: 3,
      as_of: report.as_of,
      first_available_at: report.start,
      latest_available_at: report.as_of,
      selection_policy: "Latest eligible topic assessment",
      model: {
        provider: "provider-a",
        model_name: "topic-demo",
        model_version: "1",
        configuration_hash: "a".repeat(64),
      },
    };
    const second = {
      ...first,
      topic_id: "cohort-b",
      model: {
        ...first.model,
        provider: "provider-b",
        configuration_hash: "b".repeat(64),
      },
    };
    const html = renderToStaticMarkup(
      <AnalyticsTopicSelector
        topics={[first, second]}
        selected="cohort-b"
        onSelect={() => {}}
      />,
    );
    expect(html).toContain(
      "Synthetic Harbour Coverage · provider-a · topic-demo / 1 · aaaaaaaaaaaa",
    );
    expect(html).toContain(
      "Synthetic Harbour Coverage · provider-b · topic-demo / 1 · bbbbbbbbbbbb",
    );
    expect(html).toContain('value="cohort-b" selected=""');
    expect(html).toContain("Selected Topic Identity");
    expect(html).toContain("b".repeat(64));
    expect(html).not.toContain("a".repeat(64));
  });
  it("retains a selected topic absent from the bounded choice page without assigning a different model identity", () => {
    const html = renderToStaticMarkup(
      <AnalyticsTopicSelector
        topics={[]}
        selected="cohort-not-on-page"
        onSelect={() => {}}
      />,
    );
    expect(html).toContain('value="cohort-not-on-page" selected=""');
    expect(html).toContain(
      "Model identity is not supplied on this bounded page.",
    );
    expect(html).not.toContain("Configuration Hash");
  });
  it("preserves exact population times, IDs and report snapshot in supporting records", () => {
    const url = new URL(supportingRecordsUrl(report), "https://local.test");
    expect(url.pathname).toBe("/discovery");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      start: "2026-10-01T00:00:07.125Z",
      end: "2026-10-08T00:00:07.125Z",
      time_basis: "published_at",
      topic: "topic-a",
      source: "source-b",
      as_of: "2026-10-08T09:11:07.125Z",
      order: "published_at",
    });
  });
  it("preserves aware offset timestamps and validates a bounded ordered UTC interval", () => {
    const params = new URLSearchParams({
      start: "2026-10-01T13:30:07.125+05:30",
      end: report.end,
      time_basis: "published_at",
      topic: "topic-a",
      source: "source-b",
      as_of: report.as_of,
    });
    const filters = readAnalyticsParameters(params);
    expect(filters.start).toBe("2026-10-01T13:30:07.125+05:30");
    expect(analyticsParameters(filters).get("as_of")).toBe(report.as_of);
    expect(validateAnalyticsFilters(filters)).toBeUndefined();
    expect(
      validateAnalyticsFilters({ ...filters, end: filters.start }),
    ).toContain("after the start");
    expect(
      validateAnalyticsFilters({ ...filters, start: "2024-01-01T00:00:00Z" }),
    ).toContain("366 days");
    expect(
      validateAnalyticsFilters({ ...filters, start: "2026-10-01T00:00" }),
    ).toContain("timezone");
    expect(
      validateAnalyticsFilters({ ...filters, cutoff: "invalid" }),
    ).toContain("As Of");
  });
  it("declares the classified denominator, missing-assessment population and excluded unknown times", () => {
    const html = renderToStaticMarkup(
      <AnalyticsResults report={report} simulated={false} />,
    );
    expect(html).toContain("3 of 5");
    expect(html).toContain("2 of 5");
    expect(html).toContain("Neutral");
    expect(html).toContain("Mixed");
    expect(html).toContain("Outside the dated population");
    expect(html).toContain(
      "Latest eligible document-level assessment per document.",
    );
    expect(html).toContain("Other Sources");
    expect(html).toContain("Other Models");
    expect(html).not.toContain("2026-10-02");
    expect(html).toContain("not measured public opinion");
  });
  it("does not invent sentiment classifications for persisted entity-specific demo assessments", () => {
    const html = renderToStaticMarkup(
      <AnalyticsResults
        report={{
          ...report,
          classified_count: 0,
          no_assessment_count: 8,
          sentiment: [],
          models: [],
          models_other_count: 0,
        }}
        simulated
      />,
    );
    expect(html).toContain(
      "No document-level sentiment classifications are supplied",
    );
    expect(html).toContain("Fictional Demo Analytics");
    expect(html).not.toContain("3 of 5");
  });
});
