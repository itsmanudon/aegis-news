"use client";
import Link from "next/link";
import { MultimediaFeed } from "../multimedia";
import { useDocuments, useEvents, useSystem } from "@/lib/queries";
import { DocumentTable } from "../documents/document-table";
import { Timestamp } from "../documents/time-rail";
import { Badge, PageHeading, Panel, QueryState } from "../ui/console";
import { OperationsNav } from "../operations/operations-nav";
import styles from "../operations/operations.module.css";
export function Dashboard() {
  const records = useDocuments(),
    events = useEvents(),
    system = useSystem();
  const documents = records.data ?? [];
  const flagged = documents.filter((v) => v.integrity !== "verified");
  return (
    <div className={styles.page}>
      <PageHeading
        title="Operational Overview"
        description="A source-first view of evidence, machine assessments and integrity exceptions."
        action={
          <Link className="button" href="/documents">
            Open Evidence Register
          </Link>
        }
      />
      <OperationsNav active="overview" />
      <div className="overview-strip" aria-label="Workspace Counts">
        <div>
          <span>Documents on Loaded Page</span>
          <strong>{records.data ? documents.length : "—"}</strong>
        </div>
        <div>
          <span>Model Assessments</span>
          <strong>
            {records.data
              ? documents.some((v) => v.intelligenceLoaded === false)
                ? "On Detail"
                : documents.reduce((n, v) => n + v.analyses.length, 0)
              : "—"}
          </strong>
        </div>
        <div>
          <span>Records Awaiting Review</span>
          <strong className="caution">
            {records.data ? flagged.length : "—"}
          </strong>
        </div>
        <div>
          <span>API Connection</span>
          <strong className="connection">
            {system.isPending
              ? "Connecting…"
              : system.error
                ? "Unavailable"
                : "Connected"}
          </strong>
          <small>{system.data?.data.version}</small>
        </div>
      </div>
      {system.error && (
        <div className="notice" role="status">
          {system.error.message}
        </div>
      )}
      <div className="two-column">
        <Panel
          title="Review Queue"
          action={<Link href="/provenance">Inspect Provenance</Link>}
        >
          <QueryState
            pending={records.isPending}
            error={records.error}
            retry={records.refetch}
          >
            {flagged.map((v) => (
              <div className="queue-record" key={v.document.document_id}>
                <Badge tone={v.integrity}>{v.integrity}</Badge>
                <Link href={`/documents/${v.document.document_id}`}>
                  {v.document.title}
                </Link>
                <p>
                  {v.integrity === "failed"
                    ? "Signature mismatch in fixture. Hold for review."
                    : "Integrity not checked in this session. Open detail to verify."}
                </p>
              </div>
            ))}
            {records.data && !flagged.length && (
              <p className="empty">
                No records awaiting integrity review on the loaded page.
              </p>
            )}
          </QueryState>
        </Panel>
        <Panel
          title="Intelligence Timeline"
          action={<Link href="/events">Browse Events</Link>}
        >
          <QueryState
            pending={events.isPending}
            error={events.error}
            retry={events.refetch}
          >
            <p className="muted">
              A sample from the loaded event page; not a global recency ranking.
            </p>
            <ol className="timeline compact">
              {events.data?.slice(0, 3).map((e) => (
                <li key={`${e.event_id}:${e.revision}`}>
                  <small>
                    Available <Timestamp value={e.available_at} />
                  </small>
                  {e.document_ids[0] ? (
                    <Link href={`/documents/${e.document_ids[0]}`}>
                      {e.summary}
                    </Link>
                  ) : (
                    <p>{e.summary}</p>
                  )}
                  <Badge tone={e.evidence_kind === "fact" ? "fact" : "model"}>
                    {e.evidence_kind === "fact"
                      ? "Source Fact"
                      : "Model Output"}
                  </Badge>
                </li>
              ))}
            </ol>
          </QueryState>
        </Panel>
      </div>
      <Panel
        title="Evidence on Loaded Page"
        action={<Link href="/documents">Browse Documents</Link>}
      >
        <QueryState
          pending={records.isPending}
          error={records.error}
          retry={records.refetch}
        >
          <DocumentTable
            documents={[...documents].sort((a, b) =>
              b.document.first_seen_at.localeCompare(a.document.first_seen_at),
            )}
          />
        </QueryState>
      </Panel>
      <MultimediaFeed compact />
    </div>
  );
}
