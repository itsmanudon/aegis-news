import Link from "next/link";
import { record, workflowState } from "@/lib/operations";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import styles from "./operations.module.css";
export function WorkflowStatus({ run }: { run: Record<string, unknown> }) {
  const result = record(run.result);
  return (
    <section aria-label="Reported Workflow" className={styles.result}>
      <div className={styles.resultHeading}>
        <h3>{workflowState(run.status)}</h3>
        <span>Server-Reported State</span>
      </div>
      <dl className={styles.metadata}>
        <dt>Workflow ID</dt>
        <dd className={styles.technical}>
          {typeof run.workflow_id === "string"
            ? run.workflow_id
            : "Not Supplied"}
        </dd>
        <dt>Reported Status</dt>
        <dd>{typeof run.status === "string" ? run.status : "Not Supplied"}</dd>
        {result &&
          Object.entries(result)
            .filter(([, v]) => typeof v === "string" || typeof v === "number")
            .map(([key, value]) => (
              <div className={styles.metadataGroup} key={key}>
                <dt className={styles.technical}>{key}</dt>
                <dd className={styles.technical}>{String(value)}</dd>
              </div>
            ))}
      </dl>
      {typeof result?.document_id === "string" && (
        <Link href={`/documents/${encodeURIComponent(result.document_id)}`}>
          Open Result Document
        </Link>
      )}
      {run.error != null && (
        <div role="status" className={styles.error}>
          <strong>Reported Error</strong>
          <pre>
            {typeof run.error === "string"
              ? run.error
              : JSON.stringify(run.error, null, 2)}
          </pre>
        </div>
      )}
      <p className={styles.hint}>
        No workflow timestamps are supplied by the current status API. Refresh
        is an explicit lookup; no polling runs in the background.
      </p>
      <EvidenceDisclosure title="Workflow Technical Details">
        <pre className={styles.raw}>{JSON.stringify(run, null, 2)}</pre>
      </EvidenceDisclosure>
    </section>
  );
}
