"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { components } from "@/lib/generated/api";
import { useConsole } from "./providers";
import { Timestamp } from "./documents/time-rail";
import { Badge, Panel, QueryState } from "./ui/console";

type Api = components["schemas"];
export function safeExternalUrl(value?: string | null): string | undefined {
  if (!value || value.length > 4096 || /[\x00-\x20]/.test(value)) return;
  try {
    const url = new URL(value),
      host = url.hostname.toLowerCase();
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      (url.port && url.port !== "443") ||
      !host.includes(".") ||
      /(?:\.local|\.localhost|\.internal)$/.test(host) ||
      /^[\d.]+$/.test(host)
    )
      return;
    for (const key of url.searchParams.keys())
      if (/^(apikey|api_key|access_token|key|token)$/i.test(key)) return;
    return url.href;
  } catch {
    return;
  }
}

export function RemoteImage({
  url,
  alt,
}: {
  url?: string | null;
  alt: string;
}) {
  const [failed, setFailed] = useState(false);
  const src = safeExternalUrl(url);
  return src && !failed ? (
    // Remote references are loaded by the browser, never copied to MinIO or proxied.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      className="external-image"
      src={src}
      alt={alt}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
    />
  ) : (
    <div className="external-image image-fallback">Image Unavailable</div>
  );
}

export function ArticleCard({
  article,
}: {
  article: Api["ProviderArticleView"];
}) {
  const evidence = article.evidence ?? [],
    first = evidence[0];
  const image = evidence.find((e) => safeExternalUrl(e.image_url))?.image_url;
  const source = safeExternalUrl(first?.article_url);
  return (
    <article className="external-card">
      {image && <RemoteImage url={image} alt="Publisher image reference" />}
      <div className="external-card-body">
        <Badge>{image ? "Image-Backed Article" : "Article"}</Badge>
        <h3>
          {article.document_id ? (
            <Link href={`/documents/${article.document_id}`}>
              {article.title}
            </Link>
          ) : (
            article.title
          )}
        </h3>
        <p>
          {first?.publisher_name ?? "Publisher unavailable"} ·{" "}
          {Array.from(new Set(evidence.map((e) => e.provider))).join(", ")}
        </p>
        <p>
          Published <Timestamp value={article.published_at} />
        </p>
        <p>
          {article.document_id
            ? "Document ready · open detail for analysis"
            : "Awaiting pipeline completion"}
        </p>
        {source && (
          <a href={source} target="_blank" rel="noreferrer">
            Open Publisher Article ↗
          </a>
        )}
      </div>
    </article>
  );
}

export function VideoCard({ video }: { video: Api["YouTubeReference"] }) {
  // Construct the official watch link from a validated ID instead of trusting arbitrary URLs.
  const validId = /^[A-Za-z0-9_-]{11}$/.test(video.video_id);
  return (
    <article className="external-card">
      <RemoteImage url={video.thumbnail_url} alt={`${video.title} thumbnail`} />
      <div className="external-card-body">
        <Badge>Video Reference</Badge>
        <h3>{video.title}</h3>
        <p>YouTube · {video.channel_title}</p>
        <p>
          Published <Timestamp value={video.published_at} />
        </p>
        {validId && (
          <a
            href={`https://www.youtube.com/watch?v=${video.video_id}`}
            target="_blank"
            rel="noreferrer"
          >
            Open on YouTube ↗
          </a>
        )}
        <p className="muted">
          Refreshable metadata; no downloaded video or AI assessment.
        </p>
      </div>
    </article>
  );
}

export function MultimediaFeed({ compact = false }: { compact?: boolean }) {
  const { adapter, mode } = useConsole();
  const [cursor, setCursor] = useState<string>();
  const articles = useQuery({
    queryKey: [mode, "provider-articles", cursor],
    queryFn: ({ signal }) => adapter.providerArticles!(cursor, signal),
    enabled: mode === "real" && !!adapter.providerArticles,
  });
  const videos = useQuery({
    queryKey: [mode, "video-references"],
    queryFn: ({ signal }) => adapter.videos!(signal),
    enabled: mode === "real" && !!adapter.videos,
  });
  if (mode !== "real")
    return (
      <Panel title="Provider Multimedia">
        <p>
          Provider acquisition is available in Real API mode. Mock mode does not
          simulate successful live fetches.
        </p>
      </Panel>
    );
  return (
    <>
      <Panel
        title="Provider Articles"
        action={<Link href="/multimedia">Articles / Images / Video</Link>}
      >
        <p className="panel-intro">
          Current or delayed provider excerpts. Publisher images remain remote
          references.
        </p>
        <QueryState
          pending={articles.isPending}
          error={articles.error}
          retry={articles.refetch}
        >
          <div className="external-grid">
            {articles.data?.data.slice(0, compact ? 3 : 12).map((article) => (
              <ArticleCard key={article.article_id} article={article} />
            ))}
          </div>
          {articles.data && !articles.data.data.length && (
            <p className="empty">No provider articles acquired yet.</p>
          )}
          {!compact && (
            <div className="pagination">
              <button disabled={!cursor} onClick={() => setCursor(undefined)}>
                First Page
              </button>
              <button
                disabled={!articles.data?.pagination.next_cursor}
                onClick={() =>
                  setCursor(articles.data?.pagination.next_cursor ?? undefined)
                }
              >
                Next Page
              </button>
            </div>
          )}
        </QueryState>
      </Panel>
      <Panel title="YouTube Video References">
        <QueryState
          pending={videos.isPending}
          error={videos.error}
          retry={videos.refetch}
        >
          <div className="external-grid">
            {videos.data?.data.slice(0, compact ? 2 : 10).map((video) => (
              <VideoCard
                key={`${video.video_id}:${video.last_refreshed_at}`}
                video={video}
              />
            ))}
          </div>
          {videos.data && !videos.data.data.length && (
            <p className="empty">
              No current video references. Administrators can fetch or refresh
              metadata.
            </p>
          )}
        </QueryState>
      </Panel>
    </>
  );
}

export function AcquisitionEvidence({
  values,
}: {
  values: Api["ArticleEvidence"][];
}) {
  if (!values.length) return null;
  return (
    <Panel title="Provider Acquisition / Remote Media">
      {values.map((e, i) => (
        <div key={`${e.provider}:${i}`} className="media-record">
          <p>
            <Badge>{e.provider}</Badge>{" "}
            {e.publisher_name ?? "Publisher unavailable"} · {e.content_kind}
          </p>
          <p>
            Acquired <Timestamp value={e.acquired_at} />
          </p>
          {e.image_url && (
            <RemoteImage url={e.image_url} alt="Publisher image reference" />
          )}
          {safeExternalUrl(e.article_url) && (
            <p>
              <a
                href={safeExternalUrl(e.article_url)}
                target="_blank"
                rel="noreferrer"
              >
                Open Publisher Article ↗
              </a>
            </p>
          )}
          {safeExternalUrl(e.video_url) && (
            <p>
              <a
                href={safeExternalUrl(e.video_url)}
                target="_blank"
                rel="noreferrer"
              >
                Open external video reference ↗
              </a>
            </p>
          )}
        </div>
      ))}
      <p className="muted">
        Integrity verification covers captured article content. Remote
        image/video bytes are not stored or verified.
      </p>
    </Panel>
  );
}
