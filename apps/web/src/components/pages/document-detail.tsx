"use client";
import Link from "next/link";
import { AcquisitionEvidence } from "../multimedia";
import { useDocument } from "@/lib/queries";
import { AnalysisPanel } from "../documents/analysis-panel";
import { ProvenanceCard } from "../documents/provenance-card";
import { TimeRail, Timestamp } from "../documents/time-rail";
import { Badge, Empty, PageHeading, Panel, QueryState } from "../ui/console";
export function DocumentDetail({ id }: { id: string }) {
  const record = useDocument(id),
    view = record.data;
  return (
    <>
      <Link className="back-link" href="/documents">
        ← Evidence register
      </Link>
      <PageHeading
        title={view?.document.title ?? "Document detail"}
        description="Source material, analytical assessments and evidence lineage."
      />
      <QueryState
        pending={record.isPending}
        error={record.error}
        retry={record.refetch}
      >
        {view && (
          <>
            <TimeRail view={view} />
            <div className="detail-grid">
              <div className="detail-primary">
                <Panel
                  title="Source facts"
                  action={<Badge tone="fact">Source statement</Badge>}
                >
                  <p className="panel-intro">
                    Reported by {view.source.name}. Attribution does not
                    establish independent truth.
                  </p>
                  <article className="source-body">
                    {view.document.text.split("\n\n").map((p, i) => (
                      <p key={i}>{p}</p>
                    ))}
                  </article>
                  <dl className="metadata">
                    <dt>Source</dt>
                    <dd>
                      {view.source.name} · {view.source.kind}
                    </dd>
                    <dt>Source address</dt>
                    <dd>
                      {view.source.url ? (
                        <a
                          href={view.source.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open source address ↗
                        </a>
                      ) : (
                        "Uploaded evidence; no source URL"
                      )}
                    </dd>
                    <dt>Document ID</dt>
                    <dd className="hash">{view.document.document_id}</dd>
                    <dt>Revision / language</dt>
                    <dd>
                      {view.document.revision} /{" "}
                      {view.document.language ?? "Unknown"}
                    </dd>
                  </dl>
                </Panel>
                <AnalysisPanel analyses={view.analyses} />
                <Panel title="Linked events">
                  {view.events.length ? (
                    view.events.map((e) => (
                      <div className="event-record" key={e.event_id}>
                        <Badge
                          tone={e.evidence_kind === "fact" ? "fact" : "model"}
                        >
                          {e.evidence_kind === "fact"
                            ? "Source fact"
                            : "Model output"}
                        </Badge>
                        <h3>{e.summary}</h3>
                        <p>
                          Occurred <Timestamp value={e.occurred_at} /> ·
                          Available <Timestamp value={e.available_at} />
                        </p>
                      </div>
                    ))
                  ) : (
                    <Empty message="No linked events." />
                  )}
                </Panel>
              </div>
              <div className="detail-secondary">
                <AcquisitionEvidence values={view.acquisition ?? []} />
                <ProvenanceCard key={id} view={view} />
                <Panel title="Resolved entities">
                  <p className="panel-intro">
                    Entity links reflect resolution output; review them against
                    source evidence.
                  </p>
                  {view.entities.map((e) => (
                    <Link
                      className="entity-link"
                      key={e.entity_id}
                      href={`/entities/${e.entity_id}`}
                    >
                      {e.canonical_name}
                      <Badge>{e.kind}</Badge>
                    </Link>
                  ))}
                </Panel>
                <Panel title="Media / attachments">
                  {view.media.length ? (
                    view.media.map((m) => (
                      <div className="media-record" key={m.media_id}>
                        <Badge>{m.kind}</Badge>
                        <h3>{m.object.key}</h3>
                        <p>
                          {m.object.content_type} ·{" "}
                          {m.object.size_bytes.toLocaleString()} bytes
                        </p>
                        <p className="hash">{m.object.sha256}</p>
                        <p className="muted">
                          Preview awaits an authorized media URL.
                        </p>
                      </div>
                    ))
                  ) : (
                    <Empty message="No media attached to this document." />
                  )}
                </Panel>
              </div>
            </div>
          </>
        )}
      </QueryState>
    </>
  );
}
