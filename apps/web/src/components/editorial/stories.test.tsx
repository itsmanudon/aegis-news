import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { documents } from "../../lib/fixtures";
import { StoryLead, StoryRow } from "./stories";

describe("editorial source presentation", () => {
  it("attributes a verbatim excerpt without displaying fixture integrity as a news claim", () => {
    const html = renderToStaticMarkup(<StoryLead view={documents[0]} />);
    expect(html).toContain("Maritime Operations Bulletin");
    expect(html).toContain("manual procedures remain available");
    expect(html).toContain("Source Excerpt");
    expect(html).not.toContain("verified");
    expect(html).not.toContain("Confidence");
  });
  it("preserves unknown publication time and UTC first-seen semantics", () => {
    const html = renderToStaticMarkup(<StoryRow view={documents[2]} />);
    expect(html).toContain("<dt>Published</dt><dd><span>Unknown</span>");
    expect(html).toContain("First Seen");
    expect(html).toContain("2026-10-03T08:16:00.000Z");
  });
  it("does not duplicate a headline-only record as an invented excerpt", () => {
    const view = {
      ...documents[0],
      document: { ...documents[0].document, text: documents[0].document.title },
    };
    const html = renderToStaticMarkup(<StoryLead view={view} />);
    expect(html).toContain("Only headline text is available");
    expect(html).not.toContain("Source Excerpt");
  });
  it("distinguishes unavailable body text from a headline-only acquisition", () => {
    const view = {
      ...documents[0],
      document: { ...documents[0].document, text: "" },
    };
    const html = renderToStaticMarkup(<StoryLead view={view} />);
    expect(html).toContain("No source text is available");
    expect(html).not.toContain("Only headline text");
  });
});
