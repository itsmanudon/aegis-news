"use client";
import { useConsole } from "../providers";
import { Badge, Button, Panel } from "../ui/console";
import { Timestamp } from "./time-rail";
import type { DocumentView } from "@/lib/models";
import { useVerification } from "./use-verification";
import { VerificationDetails } from "./verification-details";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
export function ProvenanceCard({
  view,
  verification: shared,
  anchorId,
  workspace = false,
}: {
  view: DocumentView;
  verification?: ReturnType<typeof useVerification>;
  anchorId?: string;
  workspace?: boolean;
}) {
  const { mode } = useConsole();
  const own = useVerification(view.document.document_id);
  const verification = shared ?? own;
  const outcomeLabels = {
    verified: "Passed",
    failed: "Failed",
    unverified: "Unavailable",
  } as const;
  const checkState = verification.isPending
    ? "Checking"
    : verification.error
      ? "Unavailable"
      : verification.data
        ? outcomeLabels[verification.data.result]
        : "Not Checked";
  return (
    <div id={anchorId}>
      <Panel
        title={workspace ? "Verification Inspector" : "Provenance / Integrity"}
        action={
          !workspace && (
            <Badge tone={verification.data?.result ?? view.integrity}>
              {verification.data?.result ?? view.integrity}
            </Badge>
          )
        }
      >
        <p className="panel-intro">
          {mode === "mock"
            ? "Fixture states illustrate verification outcomes. No cryptographic check is performed."
            : "Verification results are supplied by the integrity service."}
        </p>
        {workspace && (
          <p className="verification-current" role="status">
            Current Check{" "}
            <Badge
              tone={
                verification.error
                  ? "unavailable"
                  : (verification.data?.result ?? "unverified")
              }
            >
              {checkState}
            </Badge>
            {verification.data?.simulated && "Simulated Mock Result"}
          </p>
        )}
        {view.intelligenceLoaded === false && (
          <p>Open document detail for the complete provenance chain.</p>
        )}
        <p className="muted">
          {verification.isPending
            ? "Waiting for the requested verification result."
            : verification.data
              ? "An explicit check returned the result below."
              : mode === "mock"
                ? workspace
                  ? "No check has been requested. Mock verification returns a simulated result."
                  : "The badge is a simulated fixture state; no live check has run."
                : "Not checked in this session. No content, chain or signature outcome is claimed."}
        </p>
        <EvidenceDisclosure title="Provenance Operations">
          <dl className="metadata">
            <dt>Content Hash (SHA-256)</dt>
            <dd className="hash">
              {view.provenance.find(
                (p) => p.subject_id === view.document.document_id,
              )?.content_hash ?? "Unavailable"}
            </dd>
            <dt>Signature State</dt>
            <dd>
              {verification.data?.signatureValid === undefined
                ? workspace && verification.data && !verification.data.simulated
                  ? "Unavailable (Not Reported)"
                  : (verification.data?.signature ??
                    "Not Checked in This Session")
                : verification.data.signatureValid
                  ? "Valid"
                  : "Not Valid"}
            </dd>
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
          {!view.provenance.length && (
            <p>No provenance operations are loaded in this view.</p>
          )}
        </EvidenceDisclosure>
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
        {verification.isPending && (
          <p role="status">Verification in progress…</p>
        )}
        {verification.error && (
          <p className="error-text" role="alert">
            {verification.error.message}
          </p>
        )}
        {verification.data && (
          <div className="verification-result" role="status">
            <Badge tone={verification.data.result}>
              {workspace ? checkState : verification.data.result}
            </Badge>
            <p>
              {verification.data.simulated &&
                (workspace
                  ? "Simulated Mock Result · "
                  : "Simulated result · ")}
              {verification.data.reason}
            </p>
            <VerificationDetails
              value={verification.data}
              workspace={workspace}
            />
          </div>
        )}
      </Panel>
    </div>
  );
}
