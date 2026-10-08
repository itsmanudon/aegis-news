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
  it("does not infer unsigned or simulated real verification from missing subchecks", () => {
    const html = renderToStaticMarkup(
      <VerificationDetails
        workspace
        value={{
          result: "failed",
          signature: "unsigned",
          simulated: false,
          reason: "Missing fields",
          responseReceivedAt: "2026-10-03T08:00:00Z",
        }}
      />,
    );
    expect(html).toContain("Provenance Chain");
    expect(html).not.toContain("Simulated Unsigned");
    expect(html).not.toContain("<dd>unsigned</dd>");
    expect(html.match(/Unavailable \(Not Reported\)/g)).toHaveLength(3);
  });
  it("presents actual predicted kinds and extraction occurrence times without inventing missing values", () => {
    const html = renderToStaticMarkup(
      <AnalysisPanel
        analyses={[
          {
            ...documents[0].analyses[0],
            outputs: [
              {
                result_type: "entity_extraction",
                schema_version: "1",
                surface: "Port",
                start_offset: 0,
                end_offset: 4,
                confidence: 0,
                predicted_kind: "location",
              },
              {
                result_type: "event_extraction",
                schema_version: "1",
                document_id: documents[0].document.document_id,
                proposed_event_type: "disruption",
                evidence_text: "Port disruption reported",
                confidence: 0.5,
                occurred_at: "2026-10-03T08:00:00Z",
              },
              {
                result_type: "event_extraction",
                schema_version: "1",
                document_id: documents[0].document.document_id,
                proposed_event_type: "outage",
                evidence_text: "Unknown time",
                confidence: 0,
                occurred_at: null,
              },
            ],
          },
        ]}
        sourceText="Port"
      />,
    );
    expect(html).toContain("Predicted Entity Type");
    expect(html).toContain("Location");
    expect(html).toContain("Model-Reported Occurrence");
    expect(html).toContain('dateTime="2026-10-03T08:00:00.000Z"');
    expect(html).toContain("Unknown");
  });
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
