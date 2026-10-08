"use client";
import Link from "next/link";
import { useState } from "react";
import { useAudit } from "@/lib/queries";
import { useConsole } from "../providers";
import { Timestamp } from "../documents/time-rail";
import { Badge, Empty, PageHeading, QueryState } from "../ui/console";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { CursorPager } from "../ui/cursor-pager";
import { OperationsNav } from "../operations/operations-nav";
import styles from "../operations/operations.module.css";
export function Security() {
  const [cursor, setCursor] = useState<string>(),
    [outcome, setOutcome] = useState("");
  const records = useAudit(cursor),
    { session, mode } = useConsole();
  const entries =
    records.data?.filter((e) => !outcome || e.outcome === outcome) ?? [];
  const outcomes = Array.from(
    new Set([
      ...(mode === "mock"
        ? ["allowed", "denied", "warning"]
        : ["success", "failure", "attempt"]),
      ...(records.data ?? []).map((e) => e.outcome),
      ...(outcome ? [outcome] : []),
    ]),
  );
  return (
    <div className={styles.page}>
      <PageHeading
        title="Security & Audit"
        eyebrow="Operations & Security"
        description="Inspect the current authorization context, explicit security operations and recorded audit outcomes."
      />
      <OperationsNav active="security" />
      <div className={styles.context}>
        <section>
          <h2>Session Context</h2>
          <dl className={styles.metadata}>
            <dt>Identity</dt>
            <dd>{session?.displayName ?? "Anonymous"}</dd>
            <dt>State</dt>
            <dd>
              {!session
                ? "Identity Unavailable"
                : session.state === "authenticated"
                  ? "Authenticated"
                  : "Anonymous"}
            </dd>
            <dt>Roles</dt>
            <dd>{session?.roles.join(", ") || "None Reported"}</dd>
            <dt>Identity Context</dt>
            <dd>
              {mode === "mock"
                ? "Simulated Identity"
                : session?.state === "authenticated"
                  ? "Bearer identity verified by the API"
                  : "No verified identity is available"}
            </dd>
          </dl>
          <EvidenceDisclosure title="Authorization Scopes">
            <p className={styles.hint}>
              The server enforces authorization on every request. Scopes shown
              here reflect the current identity response.
            </p>
            <ul>
              {session?.scopes?.map((scope) => (
                <li className={styles.technical} key={scope}>
                  {scope}
                </li>
              ))}
            </ul>
            {!session?.scopes?.length && <p>No scopes are reported.</p>}
          </EvidenceDisclosure>
        </section>
        <section>
          <h2>Security Operations</h2>
          <p>
            Verification is an explicit, scope-authorized action in the document
            evidence workspace. Cryptographic integrity does not establish
            factual accuracy.
          </p>
          <Link className="button secondary" href="/provenance">
            Open Verification Workspace
          </Link>
          <p>
            Audit reads require <code>audit:read</code>. Actor and subject
            hashes are references, not display names.
          </p>
          <Badge>
            {mode === "mock" ? "Simulated Audit" : "Server-Reported Audit"}
          </Badge>
        </section>
      </div>
      <section aria-labelledby="audit-heading">
        <div className={styles.sectionHeading}>
          <h2 id="audit-heading">Audit History</h2>
          <p role="status">
            {records.data
              ? `${records.data.length} events on this page`
              : "Bounded Audit Browsing"}
          </p>
        </div>
        <div className={styles.filter}>
          <label>
            Outcome
            <select
              aria-label="Outcome"
              value={outcome}
              onChange={(event) => setOutcome(event.target.value)}
            >
              <option value="">All Outcomes</option>
              {outcomes.map((value) => (
                <option key={value} value={value}>
                  {mode === "mock"
                    ? ((
                        {
                          allowed: "Allowed",
                          denied: "Denied",
                          warning: "Warning",
                        } as Record<string, string>
                      )[value] ?? value)
                    : value}
                </option>
              ))}
            </select>
          </label>
          <p>
            Filter applies to the loaded page. Outcomes retain their supplied
            meanings.
          </p>
        </div>
        <QueryState
          pending={records.isPending}
          error={records.error}
          retry={records.refetch}
        >
          {!entries.length ? (
            <Empty
              message={
                records.data?.length
                  ? "No events on this page match the selected outcome."
                  : "No audit events are supplied on this page."
              }
            />
          ) : (
            <table
              role="table"
              className={`${styles.table} ${styles.auditTable}`}
            >
              <caption className="sr-only">Audit Events</caption>
              <thead>
                <tr role="row">
                  <th scope="col">Occurred</th>
                  <th scope="col">Action</th>
                  <th scope="col">Outcome</th>
                  <th scope="col">References</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr role="row" className="audit-record" key={entry.id}>
                    <td role="cell" data-label="Occurred">
                      <Timestamp value={entry.at} />
                    </td>
                    <td role="cell" data-label="Action">
                      <span
                        className={
                          mode === "real" ? styles.technical : undefined
                        }
                      >
                        {entry.action}
                      </span>
                    </td>
                    <td role="cell" data-label="Outcome">
                      <Badge
                        tone={
                          entry.outcome === "failure" ||
                          entry.outcome === "denied"
                            ? "failed"
                            : "neutral"
                        }
                      >
                        {entry.outcome}
                      </Badge>
                    </td>
                    <td role="cell">
                      <p className={styles.hint}>
                        {mode === "real"
                          ? "Hashed references and request context"
                          : "Fixture actor and subject references"}
                      </p>
                      <EvidenceDisclosure title="Audit Details">
                        <dl className={styles.metadata}>
                          <dt>Event ID</dt>
                          <dd className={styles.technical}>{entry.id}</dd>
                          <dt>{mode === "real" ? "Actor Hash" : "Actor"}</dt>
                          <dd className={styles.technical}>{entry.actor}</dd>
                          <dt>
                            {mode === "real" ? "Subject Hash" : "Subject"}
                          </dt>
                          <dd className={styles.technical}>{entry.subject}</dd>
                          <dt>Request ID</dt>
                          <dd className={styles.technical}>
                            {entry.requestId || "Not Supplied"}
                          </dd>
                        </dl>
                        <pre className={styles.raw}>
                          {JSON.stringify(entry.raw ?? entry, null, 2)}
                        </pre>
                      </EvidenceDisclosure>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </QueryState>
        <CursorPager
          label="Audit Pages"
          cursor={cursor}
          nextCursor={records.data?.nextCursor}
          busy={records.isFetching}
          unavailable={!!records.error}
          onPage={setCursor}
        />
      </section>
    </div>
  );
}
