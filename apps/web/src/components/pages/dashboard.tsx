"use client";
import Link from "next/link";
import { useDocuments, useEvents, useSystem } from "@/lib/queries";
import { DocumentTable } from "../documents/document-table";
import { Timestamp } from "../documents/time-rail";
import { Badge, PageHeading, Panel, QueryState } from "../ui/console";
export function Dashboard() {
  const records = useDocuments(),
    events = useEvents(),
    system = useSystem();
  const documents = records.data ?? [];
  const flagged = documents.filter((v) => v.integrity !== "verified");
  return (
    <>
      <PageHeading
        title="Operational overview"
        description="A source-first view of evidence, machine assessments and integrity exceptions."
        action={
          <Link className="button" href="/documents">
            Open evidence register
          </Link>
        }
      />
      <div className="overview-strip" aria-label="Workspace counts">
        <div>
          <span>Documents in workspace</span>
          <strong>{records.data ? documents.length : "—"}</strong>
        </div>
        <div>
          <span>Model assessments</span>
          <strong>
            {records.data
              ? documents.reduce((n, v) => n + v.analyses.length, 0)
              : "—"}
          </strong>
        </div>
        <div>
          <span>Integrity exceptions</span>
          <strong className="caution">
            {records.data ? flagged.length : "—"}
          </strong>
        </div>
        <div>
          <span>API connection</span>
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
          title="Review queue"
          action={<Link href="/provenance">Inspect provenance</Link>}
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
                    : "Unsigned source material. Independent verification required."}
                </p>
              </div>
            ))}
            {records.data && !flagged.length && (
              <p className="empty">
                No integrity exceptions in the loaded records.
              </p>
            )}
          </QueryState>
        </Panel>
        <Panel
          title="Intelligence timeline"
          action={<Link href="/events">All events</Link>}
        >
          <QueryState
            pending={events.isPending}
            error={events.error}
            retry={events.refetch}
          >
            <ol className="timeline compact">
              {events.data?.slice(0, 3).map((e) => (
                <li key={e.event_id}>
                  <small>
                    Available <Timestamp value={e.available_at} />
                  </small>
                  <Link href={`/documents/${e.document_ids[0]}`}>
                    {e.summary}
                  </Link>
                  <Badge tone={e.evidence_kind === "fact" ? "fact" : "model"}>
                    {e.evidence_kind === "fact"
                      ? "Source fact"
                      : "Model output"}
                  </Badge>
                </li>
              ))}
            </ol>
          </QueryState>
        </Panel>
      </div>
      <Panel
        title="Latest evidence"
        action={<Link href="/documents">Browse documents</Link>}
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
    </>
  );
}
