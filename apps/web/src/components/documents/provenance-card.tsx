"use client";
import { useMutation } from "@tanstack/react-query";
import { useConsole } from "../providers";
import { Badge, Button, Panel } from "../ui/console";
import { Timestamp } from "./time-rail";
import type { DocumentView } from "@/lib/models";
export function ProvenanceCard({ view }: { view: DocumentView }) {
  const { adapter, mode } = useConsole();
  const verification = useMutation({
    mutationFn: () => adapter.verify(view.document.document_id),
  });
  return (
    <Panel
      title="Provenance / Integrity"
      action={
        <Badge tone={verification.data?.result ?? view.integrity}>
          {verification.data?.result ?? view.integrity}
        </Badge>
      }
    >
      <p className="panel-intro">
        {mode === "mock"
          ? "Fixture states illustrate verification outcomes. No cryptographic check is performed."
          : "Verification results are supplied by the integrity service."}
      </p>
      {view.intelligenceLoaded === false && (
        <p>Open document detail for the complete provenance chain.</p>
      )}
      <dl className="metadata">
        <dt>Content Hash (SHA-256)</dt>
        <dd className="hash">
          {view.provenance.find(
            (p) => p.subject_id === view.document.document_id,
          )?.content_hash ?? "Unavailable"}
        </dd>
        <dt>Signature State</dt>
        <dd>{verification.data?.signature ?? "Not checked in this session"}</dd>
      </dl>
      <ol className="operation-list">
        {view.provenance.map((p) => (
          <li key={p.provenance_id}>
            <span className="operation-dot" />
            <div>
              <strong>{p.operation}</strong>
              <span className="row-meta">
                <Timestamp value={p.recorded_at} />
              </span>
              <details>
                <summary>Operation Evidence</summary>
                <dl className="metadata">
                  <dt>Record</dt>
                  <dd className="hash">{p.provenance_id}</dd>
                  <dt>Inputs</dt>
                  <dd className="hash">{p.input_ids.join(", ")}</dd>
                  <dt>Subject</dt>
                  <dd className="hash">{p.subject_id}</dd>
                  <dt>Hash</dt>
                  <dd className="hash">{p.content_hash}</dd>
                </dl>
              </details>
            </div>
          </li>
        ))}
      </ol>
      <Button
        disabled={verification.isPending}
        onClick={() => verification.mutate()}
      >
        {verification.isPending
          ? "Checking…"
          : mode === "mock"
            ? "Run Mock Verification"
            : "Verify Integrity"}
      </Button>
      {verification.isPending && <p role="status">Verification in progress…</p>}
      {verification.error && (
        <p className="error-text" role="alert">
          {verification.error.message}
        </p>
      )}
      {verification.data && (
        <div className="verification-result" role="status">
          <Badge tone={verification.data.result}>
            {verification.data.result}
          </Badge>
          <p>
            {verification.data.simulated && "Simulated result · "}
            {verification.data.reason}
          </p>
          <small>
            Response Received At{" "}
            <Timestamp value={verification.data.responseReceivedAt} />
          </small>
        </div>
      )}
    </Panel>
  );
}
