import Link from "next/link";
import type { DocumentView } from "@/lib/models";
import {
  literalExcerpt,
  contentExtent,
  assessmentLabel,
} from "@/lib/source-presentation";
import { Timestamp } from "./time-rail";
import { Badge } from "../ui/console";
export function EvidenceDetails({
  view,
  simulated = false,
}: {
  view: DocumentView;
  simulated?: boolean;
}) {
  return (
    <div className="loaded-evidence">
      <p>
        <strong>{contentExtent(view)}</strong> · Captured source content;
        completeness is not established.
      </p>
      {view.document.text && (
        <div className="expanded-source">
          <span>Literal Source Excerpt</span>
          <p>{literalExcerpt(view.document.text, 600)}</p>
        </div>
      )}
      <dl className="evidence-times">
        <div>
          <dt>Ingested</dt>
          <dd>
            <Timestamp value={view.document.ingested_at} />
          </dd>
        </div>
        <div>
          <dt>Assessment Available</dt>
          <dd>
            {view.analyses.length ? (
              <Timestamp
                value={view.analyses.map((a) => a.available_at).sort()[0]}
              />
            ) : view.intelligenceLoaded === false ? (
              "Not Loaded"
            ) : (
              "Not Available"
            )}
          </dd>
        </div>
      </dl>
      <p>
        <Badge tone="model">Model Assessment</Badge>{" "}
        {view.intelligenceLoaded === false
          ? "Details are not loaded on this archive page. Open Story Detail to read available assessments."
          : view.analyses.length
            ? `${view.analyses.length} loaded assessments. Confidence is model-reported, not factual certainty.`
            : "No assessments available in this record."}
      </p>
      {view.intelligenceLoaded !== false &&
        view.analyses.map((analysis) => (
          <div key={analysis.analysis_id} className="loaded-assessment">
            <strong>{assessmentLabel(analysis.analysis_type)}</strong>:{" "}
            {analysis.outputs.map((output, index) => (
              <span key={index}>
                {"label" in output
                  ? output.label
                  : "surface" in output
                    ? output.surface
                    : "proposed_event_type" in output
                      ? output.proposed_event_type
                      : output.result_type}
                {"confidence" in output
                  ? ` · Confidence ${Math.round(output.confidence * 100)}%`
                  : ""}
                {index < analysis.outputs.length - 1 ? "; " : ""}
              </span>
            ))}
          </div>
        ))}
      <p>
        <strong>Integrity Check:</strong>{" "}
        {simulated
          ? "Loaded fixture state is simulated; no live cryptographic check is claimed."
          : "Not checked in this session."}{" "}
        <Badge tone={simulated ? view.integrity : "unverified"}>
          {simulated ? view.integrity : "unverified"}
        </Badge>
      </p>
      <p>
        Content, chain and signature results are available only after an
        explicit check on Story Detail.
      </p>
      <Link href={`/documents/${view.document.document_id}`}>
        Open Story Detail →
      </Link>
    </div>
  );
}
