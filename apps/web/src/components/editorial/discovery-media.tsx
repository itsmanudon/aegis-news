"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useConsole } from "../providers";
import { RemoteImage, safeExternalUrl } from "../multimedia";
import { Timestamp } from "../documents/time-rail";
import { QueryState } from "../ui/console";
import styles from "./discovery-media.module.css";

export function DiscoveryMedia() {
  const { adapter, mode } = useConsole();
  const articlesAvailable = mode === "real" && !!adapter.providerArticles;
  const videosAvailable = mode === "real" && !!adapter.videos;
  const articles = useQuery({
    queryKey: [mode, "provider-articles", undefined],
    queryFn: ({ signal }) => adapter.providerArticles!(undefined, signal),
    enabled: articlesAvailable,
  });
  const videos = useQuery({
    queryKey: [mode, "video-references"],
    queryFn: ({ signal }) => adapter.videos!(signal),
    enabled: videosAvailable,
  });
  return (
    <section className={styles.media} aria-labelledby="media-heading">
      <div className={styles.heading}>
        <h2 id="media-heading">Beyond the text</h2>
        <Link href="/multimedia">
          Explore multimedia <span aria-hidden="true">→</span>
        </Link>
      </div>
      <p className={styles.intro}>
        Publisher image references and external video, with their source
        context.
      </p>
      {mode === "mock" ? (
        <p className={styles.availability}>
          Provider media is available in Real API mode. This mock workspace does
          not simulate acquired publisher images or video.
        </p>
      ) : (
        <div className={styles.columns}>
          <div>
            <h3 className={styles.label}>Provider acquisitions</h3>
            <p className={styles.note}>
              Ordered by acquisition time. Publication may be earlier or
              unknown.
            </p>
            {articlesAvailable ? (
              <QueryState
                pending={articles.isPending}
                error={articles.error}
                retry={articles.refetch}
              >
                {articles.data?.data.slice(0, 3).map((article) => {
                  const evidence = article.evidence ?? [];
                  const first = evidence[0];
                  const image = evidence.find((value) =>
                    safeExternalUrl(value.image_url),
                  );
                  const publisherUrl = safeExternalUrl(first?.article_url);
                  return (
                    <article
                      className={styles.article}
                      key={article.article_id}
                    >
                      {image && (
                        <figure className={styles.figure}>
                          <RemoteImage url={image.image_url} alt="" />
                          <figcaption>
                            Remote publisher image · bytes not verified
                          </figcaption>
                        </figure>
                      )}
                      <div>
                        <p className={styles.publisher}>
                          {first?.publisher_name ?? "Publisher unavailable"}
                          {evidence.length > 0 &&
                            ` · ${Array.from(new Set(evidence.map((value) => value.provider))).join(", ")}`}
                        </p>
                        <h4>
                          {article.document_id ? (
                            <Link href={`/documents/${article.document_id}`}>
                              {article.title}
                            </Link>
                          ) : publisherUrl ? (
                            <a
                              href={publisherUrl}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {article.title}
                            </a>
                          ) : (
                            article.title
                          )}
                        </h4>
                        <p className={styles.time}>
                          Acquired <Timestamp value={article.acquired_at} />
                        </p>
                        <p className={styles.time}>
                          Published <Timestamp value={article.published_at} />
                        </p>
                        <p className={styles.note}>
                          {article.document_id
                            ? "Captured text available; open the record for analysis."
                            : "Awaiting pipeline completion."}
                        </p>
                        {publisherUrl && (
                          <a
                            className={styles.publisherLink}
                            href={publisherUrl}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open publisher article ↗
                          </a>
                        )}
                      </div>
                    </article>
                  );
                })}
                {articles.data && !articles.data.data.length && (
                  <p className={styles.availability}>
                    No provider articles acquired yet.
                  </p>
                )}
              </QueryState>
            ) : (
              <p className={styles.availability}>
                Provider article references are unavailable in this workspace.
              </p>
            )}
          </div>
          <div>
            <h3 className={styles.label}>External video references</h3>
            <p className={styles.note}>
              Refreshable metadata. No stored video or model assessment.
            </p>
            {videosAvailable ? (
              <QueryState
                pending={videos.isPending}
                error={videos.error}
                retry={videos.refetch}
              >
                {videos.data?.data.slice(0, 2).map((video) => (
                  <article
                    className={styles.video}
                    key={`${video.video_id}:${video.last_refreshed_at}`}
                  >
                    <p className={styles.publisher}>
                      YouTube · {video.channel_title}
                    </p>
                    <h4>{video.title}</h4>
                    <p className={styles.time}>
                      Published <Timestamp value={video.published_at} />
                    </p>
                    {/^[A-Za-z0-9_-]{11}$/.test(video.video_id) && (
                      <a
                        className={styles.publisherLink}
                        href={`https://www.youtube.com/watch?v=${video.video_id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open on YouTube ↗
                      </a>
                    )}
                  </article>
                ))}
                {videos.data && !videos.data.data.length && (
                  <p className={styles.availability}>
                    No current video references.
                  </p>
                )}
              </QueryState>
            ) : (
              <p className={styles.availability}>
                Video references are unavailable in this workspace.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
