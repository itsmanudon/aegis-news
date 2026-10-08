import type { Domain } from "@/lib/models";
import { Badge, Empty, Panel } from "../ui/console";
import { Timestamp } from "./time-rail";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { extractionSpan, assessmentLabel } from "@/lib/source-presentation";
import styles from "./analysis-panel.module.css";
export function AnalysisPanel({
  analyses,
  sourceText = "",
}: {
  analyses: Domain["AnalysisResult"][];
  sourceText?: string;
}) {
  return (
    <div className={styles.assessments}>
      <Panel title="Model-Generated Intelligence">
        <p className="panel-intro">
          Assessments may be incorrect. Confidence is model-reported and is not
          a guarantee of accuracy.
        </p>
        {!analyses.length && (
          <Empty message="No model intelligence is available for this document." />
        )}
        {analyses.map((a) => (
          <article className="analysis-record" key={a.analysis_id}>
            <h3>
              {assessmentLabel(a.analysis_type)}{" "}
              <Badge tone="model">Model Output</Badge>
            </h3>
            {a.outputs.map((o, i) => (
              <div className={`analysis-output ${styles.output}`} key={i}>
                <strong>
                  {"label" in o
                    ? o.label
                    : "surface" in o
                      ? o.surface
                      : "proposed_event_type" in o
                        ? o.proposed_event_type
                        : assessmentLabel(o.result_type)}
                </strong>
                {"confidence" in o && (
                  <span>Confidence {Math.round(o.confidence * 100)}%</span>
                )}
                {"score" in o && <span>Score {o.score}</span>}
                {"values" in o && (
                  <span>
                    {o.values.length} vector values. No topic meaning is
                    inferred.
                  </span>
                )}
                {"entity_id" in o && (
                  <span>
                    Entity Association:{" "}
                    {o.entity_id ? "Reported" : "Unresolved"}
                  </span>
                )}
                {"evidence_text" in o && (
                  <blockquote className={styles.extraction}>
                    <span>Model-Reported Extraction Evidence</span>
                    {o.evidence_text}
                  </blockquote>
                )}
                {"start_offset" in o && (
                  <div className={styles.extraction}>
                    <span>
                      Source Span · Characters {o.start_offset}–{o.end_offset}
                    </span>
                    {extractionSpan(
                      sourceText,
                      o.start_offset,
                      o.end_offset,
                      o.surface,
                    ) ?? "Matching source span is unavailable in this view."}
                  </div>
                )}
              </div>
            ))}
            <p className={styles.model}>
              {a.model_name} / {a.model_version}
            </p>
            <div className={styles.available}>
              <span>Available</span>
              <Timestamp value={a.available_at} />
            </div>
            <EvidenceDisclosure title="Technical Metadata">
              <dl className="metadata">
                <dt>Model / Version</dt>
                <dd>
                  {a.model_name} / {a.model_version}
                </dd>
                <dt>Provider</dt>
                <dd>{a.provider}</dd>
                <dt>Generated</dt>
                <dd>
                  <Timestamp value={a.created_at} />
                </dd>
                <dt>Available</dt>
                <dd>
                  <Timestamp value={a.available_at} />
                </dd>
                <dt>Configuration Hash</dt>
                <dd className="hash">{a.configuration_hash}</dd>
                <dt>Analysis ID</dt>
                <dd className="hash">{a.analysis_id}</dd>
                <dt>Output References</dt>
                <dd>
                  {a.outputs.map((output, index) => (
                    <div key={index}>
                      {Object.entries(output)
                        .filter(([field]) =>
                          [
                            "entity_id",
                            "mention_id",
                            "document_id",
                            "event_id",
                            "event_revision",
                          ].includes(field),
                        )
                        .map(([field, value]) => (
                          <p key={field}>
                            <code>{field}</code>:{" "}
                            <span className="hash">{String(value)}</span>
                          </p>
                        ))}
                    </div>
                  ))}
                </dd>
              </dl>
            </EvidenceDisclosure>
          </article>
        ))}
      </Panel>
    </div>
  );
}
