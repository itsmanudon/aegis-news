"use client";
import Link from "next/link";
import { useState } from "react";
import { useEvents } from "@/lib/queries";
import { Timestamp } from "../documents/time-rail";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { CursorPager } from "../ui/cursor-pager";
import { Badge, Empty, PageHeading, QueryState } from "../ui/console";
import styles from "./intelligence.module.css";

export function Events() {
  const [cursor, setCursor] = useState<string>();
  const records = useEvents(cursor);
  const [evidence, setEvidence] = useState("");
  const [order, setOrder] = useState<"available_at" | "occurred_at">(
    "available_at",
  );
  const instant = (value?: string | null) =>
    value && !Number.isNaN(Date.parse(value)) ? Date.parse(value) : -Infinity;
  const events = (records.data ?? [])
    .filter((event) => !evidence || event.evidence_kind === evidence)
    .toSorted((a, b) => {
      const left = instant(a[order]),
        right = instant(b[order]);
      return left === right
        ? a.event_id.localeCompare(b.event_id) || b.revision - a.revision
        : left < right
          ? 1
          : -1;
    });
  return (
    <div className={styles.page}>
      <PageHeading
        eyebrow="News & Intelligence / Events"
        title="Events / Timeline"
        description="Compare reported occurrence with the time intelligence became available. Every revision retains its own evidence."
      />
      <p className={styles.caption}>
        Sorting and evidence filters apply to this page. The archive is paged by
        event identity and revision; this view does not imply a globally
        newest-first timeline. Source statements remain attributed reports.
      </p>
      <div className={`filter-bar ${styles.filters}`}>
        <label>
          Evidence Kind
          <select
            value={evidence}
            onChange={(event) => setEvidence(event.target.value)}
          >
            <option value="">All Evidence</option>
            <option value="fact">Source Statements</option>
            <option value="model_output">Model Outputs</option>
          </select>
        </label>
        <label>
          Order on This Page
          <select
            value={order}
            onChange={(event) =>
              setOrder(
                event.target.value === "occurred_at"
                  ? "occurred_at"
                  : "available_at",
              )
            }
          >
            <option value="available_at">Intelligence Available</option>
            <option value="occurred_at">Occurred</option>
          </select>
        </label>
      </div>
      <p className={styles.count} role="status">
        {records.isPending
          ? "Loading this page…"
          : records.error
            ? "Page Count Unavailable"
            : `${events.length} shown · ${records.data?.length ?? 0} event revisions on this page`}
      </p>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        {!events.length && (
          <Empty
            message={
              evidence
                ? "No matching events on this page. Change the filter or browse the next available page."
                : "No event revisions are available on this page."
            }
          />
        )}
        <ol className={styles.timeline} aria-label="Event Evidence Timeline">
          {events.map((event) => (
            <li
              key={`${event.event_id}:${event.revision}`}
              data-event-id={event.event_id}
              data-revision={event.revision}
              className={`event-record ${styles.event}`}
            >
              <div className={styles.eventTop}>
                <Badge tone={event.evidence_kind === "fact" ? "fact" : "model"}>
                  {event.evidence_kind === "fact"
                    ? "Source Statement"
                    : "Model Output"}
                </Badge>
                <span>Revision {event.revision}</span>
              </div>
              <h2>{event.summary}</h2>
              <dl className={styles.eventTimes}>
                <div>
                  <dt>Occurred</dt>
                  <dd>
                    <Timestamp value={event.occurred_at} />
                  </dd>
                </div>
                <div>
                  <dt>Intelligence Available</dt>
                  <dd>
                    <Timestamp value={event.available_at} />
                  </dd>
                </div>
              </dl>
              <div className={styles.eventLinks}>
                {event.document_ids.length ? (
                  event.document_ids.map((id, index) => (
                    <Link
                      key={id}
                      href={`/documents/${id}`}
                      aria-label={
                        event.document_ids.length > 1
                          ? `Open Supporting Document ${index + 1}, Reference ${id}`
                          : undefined
                      }
                    >
                      Open Supporting Document
                      {event.document_ids.length > 1 ? ` ${index + 1}` : ""} →
                    </Link>
                  ))
                ) : (
                  <span>No supporting document references are supplied.</span>
                )}
              </div>
              <EvidenceDisclosure title="Event References">
                <dl className="metadata">
                  <dt>Event ID</dt>
                  <dd className="hash">{event.event_id}</dd>
                  <dt>Revision / Schema Version</dt>
                  <dd>
                    {event.revision} / {event.schema_version}
                  </dd>
                  <dt>Record Created</dt>
                  <dd>
                    <Timestamp value={event.created_at} />
                  </dd>
                  <dt>Analysis Reference</dt>
                  <dd className="hash">
                    {event.analysis_id ?? "Not Available"}
                  </dd>
                  <dt>Supporting Document IDs</dt>
                  <dd className="hash">
                    {event.document_ids.join(", ") || "Not Available"}
                  </dd>
                  <dt>Associated Entity References</dt>
                  <dd>
                    {event.entity_ids.length
                      ? event.entity_ids.map((id) => (
                          <p key={id}>
                            <Link className="hash" href={`/entities/${id}`}>
                              {id}
                            </Link>
                          </p>
                        ))
                      : "Not Available"}
                  </dd>
                </dl>
              </EvidenceDisclosure>
            </li>
          ))}
        </ol>
      </QueryState>
      <CursorPager
        cursor={cursor}
        nextCursor={records.error ? undefined : records.data?.nextCursor}
        busy={records.isFetching}
        onPage={setCursor}
        label="Event Revision Pages"
        unavailable={!!records.error}
      />
    </div>
  );
}
