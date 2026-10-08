"use client";
import Link from "next/link";
import { AcquisitionEvidence, safeExternalUrl } from "../multimedia";
import { useAcquisition, useDocument } from "@/lib/queries";
import { useConsole } from "../providers";
import type { DocumentView } from "@/lib/models";
import { contentExtent } from "@/lib/source-presentation";
import { StoryMetadata } from "../editorial/stories";
import { AnalysisPanel } from "../documents/analysis-panel";
import { ProvenanceCard } from "../documents/provenance-card";
import { useVerification } from "../documents/use-verification";
import { TimeRail, Timestamp } from "../documents/time-rail";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { Badge, Empty, QueryState } from "../ui/console";
import styles from "./document-detail.module.css";

export function DocumentDetail({ id }: { id: string }) {
  const record = useDocument(id);
  return (
    <div className={styles.reader}>
      <Link className="back-link" href="/documents">
        ← Document Archive
      </Link>
      <QueryState
        pending={record.isPending}
        error={record.error}
        retry={record.refetch}
      >
        {record.data && (
          <StoryReader
            key={record.data.document.document_id}
            view={record.data}
          />
        )}
      </QueryState>
    </div>
  );
}
function StoryReader({ view }: { view: DocumentView }) {
  const id = view.document.document_id;
  const { adapter, mode } = useConsole();
  const acquisition = useAcquisition(id);
  const evidence = acquisition.data ?? view.acquisition ?? [];
  const verification = useVerification(id);
  const article = evidence.find((item) => safeExternalUrl(item.article_url));
  const original = safeExternalUrl(article?.article_url);
  const source = safeExternalUrl(view.source.url);
  const extent = contentExtent(view, evidence);
  const available = view.analyses
    .map((analysis) => analysis.available_at)
    .sort()[0];
  const state =
    verification.data?.result ??
    (mode === "mock" ? view.integrity : "unverified");
  return (
    <>
      <header className={`reader-header ${styles.header}`}>
        <p className={styles.eyebrow}>Source Reporting / Document Archive</p>
        <h1 className={styles.headline}>{view.document.title}</h1>
        <div className={styles.headerDetails}>
          <StoryMetadata view={view} />
          <div className={styles.original}>
            {article?.publisher_name && (
              <p>Publisher: {article.publisher_name}</p>
            )}
            {original ? (
              <a href={original} target="_blank" rel="noreferrer">
                Open Publisher Article ↗
              </a>
            ) : source ? (
              <a href={source} target="_blank" rel="noreferrer">
                Open Source Address ↗
              </a>
            ) : (
              <span>No public source URL is available.</span>
            )}
            <p>{extent}</p>
          </div>
        </div>
        <div className={styles.summary} aria-label="Evidence Summary">
          <span>
            {view.analyses.length} Model Assessment
            {view.analyses.length === 1 ? "" : "s"} Loaded
          </span>
          <span>
            {verification.data
              ? "Explicit Check Result"
              : mode === "mock"
                ? "Simulated Fixture State"
                : "Not Checked in This Session"}
            : <Badge tone={state}>{state}</Badge>
          </span>
          <a href="#story-provenance">Inspect Provenance →</a>
        </div>
      </header>
      <div className={styles.readingGrid}>
        <div className={styles.readingColumn}>
          <section
            className={`story-report ${styles.report}`}
            aria-labelledby="source-report-heading"
          >
            <div className={styles.reportHeading}>
              <h2 id="source-report-heading">Source Reporting</h2>
              <Badge tone="fact">Attributed Statement</Badge>
            </div>
            <p className={styles.caption}>
              Reported by {view.source.name}. Attribution does not establish
              independent truth. This is captured text; completeness of the
              publisher article is not established.
            </p>
            {extent === "Headline Only" && (
              <p className="notice">
                Only the headline was captured. The publisher article body is
                not available in this record.
              </p>
            )}
            <article
              className={styles.sourceBody}
              aria-label="Captured Source Text"
            >
              {view.document.text.trim() ? (
                view.document.text
                  .split(/\n\s*\n/)
                  .map((paragraph, index) => <p key={index}>{paragraph}</p>)
              ) : (
                <Empty message="No source text is available in this record." />
              )}
            </article>
          </section>
          <AnalysisPanel
            analyses={view.analyses}
            sourceText={view.document.text}
          />
          <section className={styles.context}>
            <h2>Linked Evidence</h2>
            <EvidenceDisclosure
              title={`Resolved Entities (${view.entities.length})`}
            >
              <p className="muted">
                These links reflect resolution output; review them against
                source evidence.
              </p>
              {view.entities.length ? (
                view.entities.map((entity) => (
                  <Link
                    className="entity-link"
                    key={entity.entity_id}
                    href={`/entities/${entity.entity_id}`}
                  >
                    {entity.canonical_name} <Badge>{entity.kind}</Badge>
                  </Link>
                ))
              ) : (
                <p>No resolved entities are available.</p>
              )}
            </EvidenceDisclosure>
            <EvidenceDisclosure title={`Linked Events (${view.events.length})`}>
              {view.events.length ? (
                view.events.map((event) => (
                  <div className={styles.event} key={event.event_id}>
                    <Badge
                      tone={event.evidence_kind === "fact" ? "fact" : "model"}
                    >
                      {event.evidence_kind === "fact"
                        ? "Source Statement"
                        : "Model Output"}
                    </Badge>
                    <h3>{event.summary}</h3>
                    <dl className="evidence-times">
                      <div>
                        <dt>Occurred</dt>
                        <dd>
                          <Timestamp value={event.occurred_at} />
                        </dd>
                      </div>
                      <div>
                        <dt>Available</dt>
                        <dd>
                          <Timestamp value={event.available_at} />
                        </dd>
                      </div>
                    </dl>
                  </div>
                ))
              ) : (
                <p>No linked events are available.</p>
              )}
            </EvidenceDisclosure>
            <EvidenceDisclosure
              title={`Media / Attachments (${view.media.length})`}
            >
              {view.media.length ? (
                view.media.map((media) => (
                  <div key={media.media_id} className="media-record">
                    <Badge>{media.kind}</Badge>
                    <p className="hash">{media.object.key}</p>
                    <p>
                      {media.object.content_type} ·{" "}
                      {media.object.size_bytes.toLocaleString()} bytes
                    </p>
                    <p className="hash">{media.object.sha256}</p>
                    <p className="muted">
                      Preview awaits an authorized media URL.
                    </p>
                  </div>
                ))
              ) : (
                <p>No stored media assets are attached.</p>
              )}
            </EvidenceDisclosure>
          </section>
        </div>
        <aside
          className={`evidence-rail ${styles.rail}`}
          aria-labelledby="evidence-rail-heading"
        >
          <h2 id="evidence-rail-heading">Evidence at a Glance</h2>
          <p className={styles.caption}>
            Captured bytes, analysis availability and cryptographic checks have
            separate meanings.
          </p>
          <dl className={styles.railFacts}>
            <div>
              <dt>Source</dt>
              <dd>{view.source.name}</dd>
            </div>
            <div>
              <dt>Assessment Availability</dt>
              <dd>
                {available ? (
                  <Timestamp value={available} />
                ) : (
                  "No Assessments Available"
                )}
              </dd>
            </div>
          </dl>
          <EvidenceDisclosure title="Record Timestamps">
            <TimeRail view={view} />
          </EvidenceDisclosure>
          <ProvenanceCard
            view={view}
            verification={verification}
            anchorId="story-provenance"
          />
          <EvidenceDisclosure title="Acquisition / Remote Media">
            {!!adapter.acquisition && (
              <QueryState
                pending={acquisition.isPending}
                error={acquisition.error}
                retry={acquisition.refetch}
              >
                {evidence.length ? (
                  <AcquisitionEvidence values={evidence} />
                ) : (
                  <p>No provider acquisition records are available.</p>
                )}
              </QueryState>
            )}
            {!adapter.acquisition &&
              (evidence.length ? (
                <AcquisitionEvidence values={evidence} />
              ) : (
                <p>
                  Provider acquisition is not simulated in this mock record.
                </p>
              ))}
            <p className={styles.caption}>
              Remote publisher image/video bytes are references, not stored
              cryptographically verified assets.
            </p>
          </EvidenceDisclosure>
          <EvidenceDisclosure title="Document Metadata">
            <dl className="metadata">
              <dt>Document ID</dt>
              <dd className="hash">{id}</dd>
              <dt>Revision / Language</dt>
              <dd>
                {view.document.revision} / {view.document.language ?? "Unknown"}
              </dd>
              <dt>Source ID</dt>
              <dd className="hash">{view.source.source_id}</dd>
              <dt>Content Extent</dt>
              <dd>{extent}</dd>
            </dl>
          </EvidenceDisclosure>
        </aside>
      </div>
    </>
  );
}
