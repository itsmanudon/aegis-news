"use client";
import Link from "next/link";
import { useState } from "react";
import { useEvents } from "@/lib/queries";
import { Timestamp } from "../documents/time-rail";
import { Badge, Empty, PageHeading, QueryState } from "../ui/console";
export function Events() {
  const records = useEvents();
  const [evidence, setEvidence] = useState(""),
    [order, setOrder] = useState<"available_at" | "occurred_at">(
      "available_at",
    );
  const events = (records.data ?? [])
    .filter((e) => !evidence || e.evidence_kind === evidence)
    .sort((a, b) => (b[order] ?? "").localeCompare(a[order] ?? ""));
  return (
    <>
      <PageHeading
        title="Events / timeline"
        description="Compare occurrence time with the point at which intelligence became available."
      />
      <div className="filter-bar">
        <label>
          Evidence kind
          <select
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
          >
            <option value="">All evidence</option>
            <option value="fact">Source facts</option>
            <option value="model_output">Model outputs</option>
          </select>
        </label>
        <label>
          Order by
          <select
            value={order}
            onChange={(e) =>
              setOrder(
                e.target.value === "occurred_at"
                  ? "occurred_at"
                  : "available_at",
              )
            }
          >
            <option value="available_at">Intelligence available</option>
            <option value="occurred_at">Occurred</option>
          </select>
        </label>
      </div>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        {!events.length && <Empty />}
        <ol className="timeline">
          {events.map((e) => (
            <li key={e.event_id}>
              <Badge tone={e.evidence_kind === "fact" ? "fact" : "model"}>
                {e.evidence_kind === "fact" ? "Source fact" : "Model output"}
              </Badge>
              <h2>{e.summary}</h2>
              <dl className="metadata">
                <dt>Occurred</dt>
                <dd>
                  <Timestamp value={e.occurred_at} />
                </dd>
                <dt>Available</dt>
                <dd>
                  <Timestamp value={e.available_at} />
                </dd>
                <dt>Revision</dt>
                <dd>{e.revision}</dd>
                {e.analysis_id && (
                  <>
                    <dt>Analysis reference</dt>
                    <dd className="hash">{e.analysis_id}</dd>
                  </>
                )}
              </dl>
              {e.document_ids.map((id) => (
                <Link key={id} href={`/documents/${id}`}>
                  Open supporting document →
                </Link>
              ))}
            </li>
          ))}
        </ol>
      </QueryState>
    </>
  );
}
