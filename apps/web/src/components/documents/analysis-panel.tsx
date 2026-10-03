import type { Domain } from "@/lib/models";
import { Badge, Empty, Panel } from "../ui/console";
import { Timestamp } from "./time-rail";
export function AnalysisPanel({
  analyses,
}: {
  analyses: Domain["AnalysisResult"][];
}) {
  return (
    <Panel title="Model-generated intelligence">
      <p className="panel-intro">
        Assessments may be incorrect. Confidence is model-reported and is not a
        guarantee of accuracy.
      </p>
      {!analyses.length && (
        <Empty message="No model intelligence is available for this document." />
      )}
      {analyses.map((a) => (
        <article className="analysis-record" key={a.analysis_id}>
          <h3>
            {a.analysis_type.replaceAll("_", " ")}{" "}
            <Badge tone="model">Model output</Badge>
          </h3>
          {a.outputs.map((o, i) => (
            <div className="analysis-output" key={i}>
              <strong>
                {"label" in o
                  ? o.label
                  : "surface" in o
                    ? o.surface
                    : "proposed_event_type" in o
                      ? o.proposed_event_type
                      : o.result_type.replaceAll("_", " ")}
              </strong>
              {"confidence" in o && (
                <span>Confidence {Math.round(o.confidence * 100)}%</span>
              )}
              {"score" in o && <span>Score {o.score}</span>}
            </div>
          ))}
          <dl className="metadata">
            <dt>Model / version</dt>
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
            <dt>Configuration hash</dt>
            <dd className="hash">{a.configuration_hash}</dd>
            <dt>Analysis ID</dt>
            <dd className="hash">{a.analysis_id}</dd>
          </dl>
        </article>
      ))}
    </Panel>
  );
}
