import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { documents } from "./fixtures";
import {
  contentExtent,
  extractionSpan,
  literalExcerpt,
} from "./source-presentation";
import { VerificationDetails } from "../components/documents/verification-details";
import { AnalysisPanel } from "../components/documents/analysis-panel";

describe("source-first presentation", () => {
  it("never upgrades unknown capture extent to a complete publisher article", () => {
    expect(contentExtent(documents[0])).toBe(
      "Captured Text · Extent Unconfirmed",
    );
    expect(
      contentExtent({
        ...documents[0],
        document: {
          ...documents[0].document,
          text: documents[0].document.title,
        },
      }),
    ).toBe("Headline Only");
    expect(
      contentExtent({
        ...documents[0],
        document: { ...documents[0].document, text: "" },
      }),
    ).toBe("No Source Text");
    expect(
      literalExcerpt(
        "A literal source statement, with no added explanation.",
        30,
      ),
    ).toBe("A literal source statement,…");
  });
  it("validates Unicode character spans without inventing matching extraction evidence", () => {
    expect(extractionSpan("😀 Port", 2, 6, "Port")).toBe("Port");
    expect(extractionSpan("😀 Port", 2, 99, "Port")).toBeUndefined();
    expect(extractionSpan("😀 Port", 2, 6, "Other")).toBeUndefined();
  });
  it("renders content, chain and signature independently and identifies browser receipt time", () => {
    const html = renderToStaticMarkup(
      <VerificationDetails
        value={{
          result: "failed",
          signature: "valid",
          contentVerified: false,
          chainValid: true,
          signatureValid: true,
          reason: "Synthetic mismatch",
          responseReceivedAt: "2026-10-03T08:04:00Z",
          simulated: false,
        }}
      />,
    );
    expect(html).toContain("Content Integrity</dt><dd>Not Valid");
    expect(html).toContain("Chain Validity</dt><dd>Passed");
    expect(html).toContain("Digital Signature</dt><dd>Passed");
    expect(html).toContain("Response Received At");
    expect(html).toContain("no server-attested verification timestamp");
    expect(html).toContain("not the factual truth");
  });
  it("preserves model-reported zero confidence and actual extraction evidence", () => {
    const analysis = {
      ...documents[0].analyses[0],
      outputs: [
        {
          result_type: "entity_extraction" as const,
          schema_version: "1" as const,
          surface: "Port",
          start_offset: 2,
          end_offset: 6,
          confidence: 0,
        },
      ],
    };
    const html = renderToStaticMarkup(
      <AnalysisPanel analyses={[analysis]} sourceText="😀 Port" />,
    );
    expect(html).toContain("Confidence 0%");
    expect(html).toContain("Source Span");
    expect(html).toContain("Technical Metadata");
    expect(html).toContain("Assessments may be incorrect");
  });
});
