"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { components } from "@/lib/generated/api";
import type { DocumentView } from "@/lib/models";
import { useDocument, useDocuments } from "@/lib/queries";
import { useConsole } from "../providers";
import { RemoteImage, safeExternalUrl } from "../multimedia";
import { Timestamp } from "../documents/time-rail";
import { Badge, Empty, PageHeading, QueryState } from "../ui/console";
import { CursorPager } from "../ui/cursor-pager";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import styles from "./media-lab.module.css";

type Api = components["schemas"];

function ExternalLink({
  url,
  children,
}: {
  url?: string | null;
  children: React.ReactNode;
}) {
  const href = safeExternalUrl(url);
  return href ? (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      referrerPolicy="no-referrer"
    >
      {children}
      <span aria-hidden="true"> ↗</span>
    </a>
  ) : null;
}

function AcquisitionRecord({ evidence }: { evidence: Api["ArticleEvidence"] }) {
  return (
    <div className={styles.acquisition}>
      <p>
        <strong>{evidence.publisher_name ?? "Publisher unavailable"}</strong> ·{" "}
        {evidence.provider}
      </p>
      <dl className={styles.facts}>
        <div>
          <dt>Captured Content</dt>
          <dd>{evidence.content_kind}</dd>
        </div>
        <div>
          <dt>Acquired</dt>
          <dd>
            <Timestamp value={evidence.acquired_at} />
          </dd>
        </div>
        <div>
          <dt>Author</dt>
          <dd>{evidence.author ?? "Unknown"}</dd>
        </div>
        {evidence.provider_item_id && (
          <div>
            <dt>Provider Item</dt>
            <dd>
              <code>{evidence.provider_item_id}</code>
            </dd>
          </div>
        )}
      </dl>
      <div className={styles.links}>
        <ExternalLink url={evidence.article_url}>
          Open Publisher Article
        </ExternalLink>
        <ExternalLink url={evidence.image_url}>
          Open Publisher Image
        </ExternalLink>
        <ExternalLink url={evidence.video_url}>
          Open Video Reference
        </ExternalLink>
      </div>
    </div>
  );
}

export function ArticleReference({
  article,
}: {
  article: Api["ProviderArticleView"];
}) {
  const evidence = article.evidence ?? [];
  const illustrated = evidence.find((record) =>
    safeExternalUrl(record.image_url),
  );
  const sourceReference = evidence.find((record) =>
    safeExternalUrl(record.article_url),
  );
  return (
    <article className={`media-article-reference ${styles.reference}`}>
      <figure className={styles.figure}>
        <RemoteImage
          url={illustrated?.image_url}
          alt={`Publisher image reference for ${article.title}`}
        />
        <figcaption>
          {illustrated
            ? `${illustrated.publisher_name ?? "Publisher unavailable"} · ${illustrated.provider}`
            : "No usable publisher image reference"}
        </figcaption>
      </figure>
      <div className={styles.referenceBody}>
        <Badge>
          {illustrated ? "Remote Publisher Image" : "Article Reference"}
        </Badge>
        <h3>{article.title}</h3>
        <p className={styles.attribution}>
          {sourceReference?.publisher_name ??
            evidence[0]?.publisher_name ??
            "Publisher unavailable"}
        </p>
        <dl className={styles.times}>
          <div>
            <dt>Published</dt>
            <dd>
              <Timestamp value={article.published_at} />
            </dd>
          </div>
          <div>
            <dt>Article Acquired</dt>
            <dd>
              <Timestamp value={article.acquired_at} />
            </dd>
          </div>
        </dl>
        <div className={styles.links}>
          <ExternalLink url={sourceReference?.article_url}>
            Open Publisher Article
          </ExternalLink>
          {article.document_id ? (
            <Link href={`/documents/${article.document_id}`}>
              Open Associated Story →
            </Link>
          ) : (
            <span>Associated story unavailable</span>
          )}
        </div>
        <EvidenceDisclosure title="Attribution & Acquisition">
          {evidence.length ? (
            evidence.map((record, index) => (
              <AcquisitionRecord
                key={`${record.provider}:${index}`}
                evidence={record}
              />
            ))
          ) : (
            <p>
              No provider acquisition evidence is supplied for this reference.
            </p>
          )}
          <dl className={styles.facts}>
            <div>
              <dt>Article ID</dt>
              <dd>
                <code>{article.article_id}</code>
              </dd>
            </div>
            <div>
              <dt>Source ID</dt>
              <dd>
                <code>{article.source_id}</code>
              </dd>
            </div>
            {article.workflow_id && (
              <div>
                <dt>Acquisition Workflow</dt>
                <dd>
                  <code>{article.workflow_id}</code>
                </dd>
              </div>
            )}
          </dl>
          <p className={styles.note}>
            Remote image and video bytes are not stored or cryptographically
            verified by Aegis. Publisher publication and provider acquisition
            are separate timestamps.
          </p>
        </EvidenceDisclosure>
      </div>
    </article>
  );
}

export function VideoReference({ video }: { video: Api["YouTubeReference"] }) {
  const validId = /^[A-Za-z0-9_-]{11}$/.test(video.video_id);
  return (
    <article className={`media-video-reference ${styles.reference}`}>
      <figure className={`${styles.figure} ${styles.videoFigure}`}>
        <RemoteImage
          url={video.thumbnail_url}
          alt={`Thumbnail reference for ${video.title}`}
        />
        <figcaption>YouTube · {video.channel_title}</figcaption>
      </figure>
      <div className={styles.referenceBody}>
        <Badge>Video Reference</Badge>
        <h3>{video.title}</h3>
        <dl className={styles.times}>
          <div>
            <dt>Published</dt>
            <dd>
              <Timestamp value={video.published_at} />
            </dd>
          </div>
        </dl>
        <div className={styles.links}>
          {validId ? (
            <ExternalLink
              url={`https://www.youtube.com/watch?v=${video.video_id}`}
            >
              Open on YouTube
            </ExternalLink>
          ) : (
            <span>Video navigation unavailable: invalid reference ID.</span>
          )}
        </div>
        <EvidenceDisclosure title="Reference Metadata">
          <dl className={styles.facts}>
            <div>
              <dt>Channel</dt>
              <dd>{video.channel_title}</dd>
            </div>
            <div>
              <dt>Last Refreshed</dt>
              <dd>
                <Timestamp value={video.last_refreshed_at} />
              </dd>
            </div>
            <div>
              <dt>Expires</dt>
              <dd>
                <Timestamp value={video.expires_at} />
              </dd>
            </div>
            <div>
              <dt>Video ID</dt>
              <dd>
                <code>{video.video_id}</code>
              </dd>
            </div>
            <div>
              <dt>Channel ID</dt>
              <dd>
                <code>{video.channel_id}</code>
              </dd>
            </div>
          </dl>
          <p className={styles.note}>
            YouTube metadata only. No video download, playback, transcription or
            AI assessment is supplied. A thumbnail reference is not a
            cryptographic check of the video.
          </p>
          <p className={styles.note}>
            The expiry belongs to the provider metadata record. It does not
            establish when the remote video or thumbnail will stop being
            available. An acquisition timestamp and associated Aegis story are
            not supplied.
          </p>
        </EvidenceDisclosure>
      </div>
    </article>
  );
}

function ProvenanceRecords({
  records,
}: {
  records: DocumentView["provenance"];
}) {
  return records.length ? (
    <ol className={styles.provenance}>
      {records.map((record) => (
        <li key={record.provenance_id}>
          <p>
            <strong>{record.operation}</strong> ·{" "}
            <Timestamp value={record.recorded_at} />
          </p>
          <dl className={styles.facts}>
            <div>
              <dt>Subject</dt>
              <dd>
                <code>{record.subject_id}</code>
              </dd>
            </div>
            <div>
              <dt>Input IDs</dt>
              <dd>
                {record.input_ids.length
                  ? record.input_ids.map((id) => (
                      <code key={id}>
                        {id}
                        <br />
                      </code>
                    ))
                  : "None supplied"}
              </dd>
            </div>
            <div>
              <dt>Content Hash</dt>
              <dd>
                <code>{record.content_hash}</code>
              </dd>
            </div>
            <div>
              <dt>Provenance ID</dt>
              <dd>
                <code>{record.provenance_id}</code>
              </dd>
            </div>
            {record.analysis_id && (
              <div>
                <dt>Analysis ID</dt>
                <dd>
                  <code>{record.analysis_id}</code>
                </dd>
              </div>
            )}
          </dl>
        </li>
      ))}
    </ol>
  ) : (
    <p>No story provenance records are supplied.</p>
  );
}

export function StoredMediaRecords({
  view,
  simulated,
}: {
  view: DocumentView;
  simulated: boolean;
}) {
  return (
    <div className={styles.storedRecords}>
      <div className={styles.storyIdentity}>
        {simulated && <Badge tone="warning">Fictional Demo Record</Badge>}
        <h3>{view.document.title}</h3>
        <p>{view.source.name}</p>
        <div className={styles.links}>
          <Link href={`/documents/${view.document.document_id}`}>
            Open Associated Story →
          </Link>
        </div>
      </div>
      <dl className={styles.times}>
        <div>
          <dt>Story Published</dt>
          <dd>
            <Timestamp value={view.document.published_at} />
          </dd>
        </div>
        <div>
          <dt>First Seen</dt>
          <dd>
            <Timestamp value={view.document.first_seen_at} />
          </dd>
        </div>
        <div>
          <dt>Story Ingested</dt>
          <dd>
            <Timestamp value={view.document.ingested_at} />
          </dd>
        </div>
      </dl>
      {view.acquisition?.length ? (
        <EvidenceDisclosure title="Story Acquisition">
          <>
            {view.acquisition.map((record, index) => (
              <AcquisitionRecord
                key={`${record.provider}:${index}`}
                evidence={record}
              />
            ))}
          </>
        </EvidenceDisclosure>
      ) : null}
      {view.media.length ? (
        <div className={styles.assets}>
          {view.media.map((asset) => {
            const related = view.provenance.filter(
              (record) =>
                record.subject_id === asset.media_id ||
                record.input_ids.includes(asset.media_id),
            );
            return (
              <article
                key={asset.media_id}
                className={`media-stored-record ${styles.asset}`}
              >
                <div className={styles.assetHeading}>
                  <Badge>
                    Stored{" "}
                    {asset.kind.charAt(0).toUpperCase() + asset.kind.slice(1)}
                  </Badge>
                  <span>
                    {asset.object.content_type} ·{" "}
                    {asset.object.size_bytes.toLocaleString("en-GB")} bytes
                  </span>
                </div>
                <h4 className={styles.objectName}>{asset.object.key}</h4>
                <p className={styles.note}>
                  Metadata Available · Preview Unavailable
                </p>
                <p className={styles.note}>
                  The response supplies a storage reference, without an
                  authorized delivery URL. No media integrity check has been run
                  in this workspace.
                </p>
                <EvidenceDisclosure title="Storage & Media Provenance">
                  <dl className={styles.facts}>
                    <div>
                      <dt>Stored Record Created</dt>
                      <dd>
                        <Timestamp value={asset.created_at} />
                      </dd>
                    </div>
                    <div>
                      <dt>Media ID</dt>
                      <dd>
                        <code>{asset.media_id}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>Ingestion ID</dt>
                      <dd>
                        <code>{asset.ingestion_id}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>Object Bucket</dt>
                      <dd>
                        <code>{asset.object.bucket}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>Object Key</dt>
                      <dd>
                        <code>{asset.object.key}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>Recorded SHA-256</dt>
                      <dd>
                        <code>{asset.object.sha256}</code>
                      </dd>
                    </div>
                  </dl>
                  {related.length ? (
                    <ProvenanceRecords records={related} />
                  ) : (
                    <p>
                      No provenance record in this response directly references
                      this media asset.
                    </p>
                  )}
                  <p className={styles.note}>
                    A recorded hash or lineage record is not a successful
                    integrity check, source truth or independently trusted media
                    provenance.
                  </p>
                </EvidenceDisclosure>
              </article>
            );
          })}
        </div>
      ) : (
        <Empty message="No stored media assets are attached to this story." />
      )}
      <EvidenceDisclosure
        title={`Story Provenance (${view.provenance.length})`}
      >
        <p className={styles.note}>
          These records belong to the selected story response. They do not
          establish that its attachments were signed or verified.
        </p>
        <ProvenanceRecords records={view.provenance} />
      </EvidenceDisclosure>
    </div>
  );
}

function SelectedStory({ id }: { id: string }) {
  const query = useDocument(id);
  const { mode } = useConsole();
  return (
    <QueryState
      pending={query.isPending}
      error={query.error}
      retry={query.refetch}
    >
      {query.data && (
        <StoredMediaRecords view={query.data} simulated={mode === "mock"} />
      )}
    </QueryState>
  );
}

function StoredAttachments() {
  const [cursor, setCursor] = useState<string>();
  const [selected, setSelected] = useState("");
  const query = useDocuments({ cursor });
  const { mode } = useConsole();
  return (
    <section className={styles.section} aria-labelledby="stored-media-heading">
      <div className={styles.sectionHeading}>
        <h2 id="stored-media-heading">Stored Attachments</h2>
        <span>Selected Story Evidence</span>
      </div>
      <p className={styles.intro}>
        Inspect the attachment metadata and available provenance returned for
        one story. Story lists do not establish attachment availability.
      </p>
      {mode === "mock" && (
        <p className={styles.note}>
          Mock mode uses fictional stories and stored attachment records. No
          live storage or cryptographic result is claimed.
        </p>
      )}
      <div className={styles.selector}>
        <QueryState
          pending={query.isPending}
          error={query.error}
          retry={query.refetch}
        >
          {query.data?.length ? (
            <div className={styles.storyControl}>
              <label htmlFor="media-story-select">Select Story</label>
              <select
                id="media-story-select"
                value={selected}
                onChange={(event) => setSelected(event.target.value)}
              >
                <option value="">Select a story…</option>
                {query.data.map((view) => (
                  <option
                    key={view.document.document_id}
                    value={view.document.document_id}
                  >
                    {view.document.title}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <Empty message="No stories are available on this page." />
          )}
          <p className={styles.note}>
            {query.data?.length ?? 0} stories on this bounded page. Attachments
            load only after selection.
          </p>
        </QueryState>
        <CursorPager
          label="Stored Story Pagination"
          cursor={cursor}
          nextCursor={query.data?.nextCursor}
          busy={query.isFetching}
          unavailable={!!query.error}
          onPage={(next) => {
            setSelected("");
            setCursor(next);
          }}
        />
      </div>
      {selected ? (
        <SelectedStory key={selected} id={selected} />
      ) : (
        <p className={styles.prompt}>
          Select a story to inspect its stored attachment records.
        </p>
      )}
    </section>
  );
}

function PublisherReferences() {
  const { adapter, mode } = useConsole();
  const [cursor, setCursor] = useState<string>();
  const available = mode === "real" && !!adapter.providerArticles;
  const query = useQuery({
    queryKey: [mode, "provider-articles", cursor],
    queryFn: ({ signal }) => adapter.providerArticles!(cursor, signal),
    enabled: available,
  });
  return (
    <section
      className={styles.section}
      aria-labelledby="publisher-media-heading"
    >
      <div className={styles.sectionHeading}>
        <h2 id="publisher-media-heading">Publisher Articles & Images</h2>
        <span>Remote References</span>
      </div>
      <p className={styles.intro}>
        Captured provider excerpts and publisher-hosted image references. Each
        publisher retains its media; images load directly in your browser.
      </p>
      {!available ? (
        <div className={styles.unavailable}>
          <h3>Publisher References Unavailable</h3>
          <p>
            {mode === "mock"
              ? "Provider acquisition is available in Real API mode. Mock mode does not simulate successful provider fetches."
              : "The connected adapter does not supply publisher article references."}
          </p>
        </div>
      ) : (
        <>
          <QueryState
            pending={query.isPending}
            error={query.error}
            retry={query.refetch}
          >
            <p className={styles.count}>
              {query.data?.data.length ?? 0} article references on this page
            </p>
            {query.data?.data.length ? (
              <div className={styles.articleGrid}>
                {query.data.data.map((article) => (
                  <ArticleReference
                    key={article.article_id}
                    article={article}
                  />
                ))}
              </div>
            ) : (
              <Empty message="No publisher article references have been acquired." />
            )}
          </QueryState>
          <CursorPager
            label="Publisher Reference Pagination"
            cursor={cursor}
            nextCursor={query.data?.pagination.next_cursor ?? undefined}
            busy={query.isFetching}
            unavailable={!!query.error}
            onPage={setCursor}
          />
        </>
      )}
    </section>
  );
}

function VideoReferences() {
  const { adapter, mode } = useConsole();
  const [cursor, setCursor] = useState<string>();
  const available = mode === "real" && !!adapter.videos;
  const query = useQuery({
    queryKey: [mode, "video-references", cursor],
    queryFn: ({ signal }) => adapter.videos!(signal, cursor),
    enabled: available,
  });
  return (
    <section className={styles.section} aria-labelledby="video-media-heading">
      <div className={styles.sectionHeading}>
        <h2 id="video-media-heading">Video References</h2>
        <span>Refreshable Metadata</span>
      </div>
      <p className={styles.intro}>
        Channel attribution, publication time and known metadata expiry, with
        links to the original video.
      </p>
      {!available ? (
        <div className={styles.unavailable}>
          <h3>Video References Unavailable</h3>
          <p>
            {mode === "mock"
              ? "Live YouTube references are available in Real API mode. Mock mode does not simulate acquired video metadata."
              : "The connected adapter does not supply video references."}
          </p>
        </div>
      ) : (
        <>
          <QueryState
            pending={query.isPending}
            error={query.error}
            retry={query.refetch}
          >
            <p className={styles.count}>
              {query.data?.data.length ?? 0} video references in this bounded
              response. Publication, refresh and expiry describe different
              events.
            </p>
            {query.data?.data.length ? (
              <div className={styles.videoGrid}>
                {query.data.data.map((video) => (
                  <VideoReference
                    key={`${video.video_id}:${video.last_refreshed_at}`}
                    video={video}
                  />
                ))}
              </div>
            ) : (
              <Empty message="No current video references are available." />
            )}
          </QueryState>
          <CursorPager
            label="Video Reference Pagination"
            cursor={cursor}
            nextCursor={query.data?.pagination.next_cursor ?? undefined}
            busy={query.isFetching}
            unavailable={!!query.error}
            onPage={setCursor}
          />
        </>
      )}
    </section>
  );
}

export function MediaLabPage() {
  return (
    <div className={styles.page}>
      <PageHeading
        eyebrow="News & Intelligence"
        title="Media Lab"
        description="Explore publisher references. Inspect the records behind stored media."
      />
      <div className={styles.boundary}>
        <strong>Reference, Record, Evidence</strong>
        <p>
          Remote availability and stored metadata have different meanings. Open
          attribution and provenance details to see what each record supports.
        </p>
      </div>
      <PublisherReferences />
      <VideoReferences />
      <StoredAttachments />
    </div>
  );
}
