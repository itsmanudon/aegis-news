"use client";
import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useTopics, useTopic, useTopicDocuments } from "@/lib/queries";
import { useConsole } from "../providers";
import { Timestamp } from "../documents/time-rail";
import { Badge, Button, Empty, PageHeading, QueryState } from "../ui/console";
import { CursorPager } from "../ui/cursor-pager";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { TopicEvidence, TopicIdentity } from "../intelligence/topic-evidence";
import styles from "../intelligence/intelligence.module.css";

export function Topics() {
  return (
    <Suspense fallback={<p role="status">Loading Topic Directory…</p>}>
      <TopicDirectory />
    </Suspense>
  );
}
function TopicDirectory() {
  const params = useSearchParams(),
    query = params.get("q") ?? "",
    cutoff = params.get("as_of") || undefined,
    cursor = params.get("cursor") || undefined;
  const records = useTopics({ query, cutoff, cursor });
  const { adapter, mode } = useConsole();
  const update = (values: Record<string, string>) => {
    const next = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(values)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}${next.size ? `?${next}` : ""}`,
    );
  };
  if (!adapter.topics)
    return <Empty message="Topic browsing is unavailable for this adapter." />;
  return (
    <div className={styles.page}>
      <PageHeading
        eyebrow="News & Intelligence / Model Evidence"
        title="Topic Directory"
        description="Explore recorded topic assessments and the reporting that supports them."
      />
      <p className={styles.caption}>
        Each topic belongs to an exact model/version/configuration cohort.
        Similar labels are not merged into a global taxonomy.
      </p>
      {mode === "mock" && (
        <p className="notice">
          Fictional topic assessments derived from Mock Development Data.
        </p>
      )}
      <form
        className={styles.filters}
        aria-label="Topic Filters"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const instant = String(data.get("as_of"));
          update({
            q: String(data.get("q")),
            as_of: instant ? new Date(`${instant}Z`).toISOString() : "",
            cursor: "",
          });
        }}
      >
        <label>
          Topic Search
          <input type="search" name="q" defaultValue={query} maxLength={200} />
        </label>
        <label>
          As Of UTC
          <input
            type="datetime-local"
            name="as_of"
            step="1"
            defaultValue={
              cutoff && Number.isFinite(Date.parse(cutoff))
                ? new Date(cutoff).toISOString().slice(0, 19)
                : ""
            }
          />
        </label>
        <Button disabled={records.isFetching}>Search Topics</Button>
      </form>
      <p className={styles.count} role="status">
        {records.data
          ? `${records.data.data.length} topic cohorts on this page`
          : records.error
            ? "Page Count Unavailable"
            : "Loading this page…"}
      </p>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        {!records.data?.data.length && (
          <Empty message="No topic assessments match this page and cutoff." />
        )}
        <div className={styles.directory}>
          {records.data?.data.map((topic) => (
            <article
              className={`topic-directory-entry ${styles.topic}`}
              key={topic.topic_id}
            >
              <div>
                <Badge tone="model">Model-Derived Topic</Badge>
                <h2>
                  <Link
                    href={`/topics/${encodeURIComponent(topic.topic_id)}?as_of=${encodeURIComponent(records.data!.as_of)}`}
                  >
                    {topic.label}
                  </Link>
                </h2>
                <p>
                  {topic.model.provider} · {topic.model.model_name} ·{" "}
                  {topic.model.model_version}
                </p>
                <Link
                  href={`/topics/${encodeURIComponent(topic.topic_id)}?as_of=${encodeURIComponent(records.data!.as_of)}`}
                >
                  Inspect Topic →
                </Link>
              </div>
              <div>
                <p>{topic.document_count} unique documents in this cohort</p>
                <dl className="evidence-times">
                  <div>
                    <dt>Latest Selected Assessment</dt>
                    <dd>
                      <Timestamp value={topic.latest_available_at} />
                    </dd>
                  </div>
                </dl>
                <EvidenceDisclosure title="Model Identity">
                  <p className={styles.technical}>
                    {topic.model.configuration_hash}
                  </p>
                  <p className={styles.caption}>{topic.selection_policy}</p>
                </EvidenceDisclosure>
              </div>
            </article>
          ))}
        </div>
      </QueryState>
      {records.data && (
        <p className={styles.caption}>
          Query Cutoff <Timestamp value={records.data.as_of} />. Counts
          deduplicate documents within each exact topic cohort; different model
          cohorts remain separate.
        </p>
      )}
      <CursorPager
        label="Topic Directory Pages"
        cursor={cursor}
        nextCursor={records.data?.pagination.next_cursor ?? undefined}
        busy={records.isFetching}
        unavailable={!!records.error}
        onPage={(value) => update({ cursor: value ?? "" })}
      />
    </div>
  );
}
export function TopicDetail({ id }: { id: string }) {
  return (
    <Suspense fallback={<p role="status">Loading Topic Research…</p>}>
      <TopicResearch id={id} />
    </Suspense>
  );
}
function TopicResearch({ id }: { id: string }) {
  const params = useSearchParams(),
    cutoff = params.get("as_of") || undefined;
  const topic = useTopic(id, cutoff);
  const { adapter, mode } = useConsole();
  if (!adapter.topic)
    return <Empty message="Topic research is unavailable for this adapter." />;
  return (
    <div className={styles.page}>
      <Link className="back-link" href="/topics">
        ← Topic Directory
      </Link>
      <QueryState
        pending={topic.isPending}
        error={topic.error}
        retry={topic.refetch}
      >
        {topic.data && (
          <>
            <PageHeading
              eyebrow="News & Intelligence / Topic Research"
              title={topic.data.label}
              description="A model-attributed research dossier grounded in available source documents."
            />
            {mode === "mock" && (
              <p className="notice">
                Fictional Topic Research · Simulated Model Assessments
              </p>
            )}
            <TopicIdentity topic={topic.data} />
            <p className={styles.caption}>
              Query Cutoff <Timestamp value={topic.data.as_of} />. These are
              recorded classifications, not summaries or established source
              facts.
            </p>
            <div className={styles.actions}>
              <Link
                className="button secondary"
                href={`/analytics?topic=${encodeURIComponent(id)}&as_of=${encodeURIComponent(topic.data.as_of)}`}
              >
                View Topic Analytics →
              </Link>
              <Link href="/entities">Explore the Entity Directory →</Link>
            </div>
            <SupportingStories
              key={`${id}:${topic.data.as_of}`}
              id={id}
              cutoff={topic.data.as_of}
            />
          </>
        )}
      </QueryState>
    </div>
  );
}
function SupportingStories({ id, cutoff }: { id: string; cutoff: string }) {
  const [cursor, setCursor] = useState<string>();
  const records = useTopicDocuments(id, { cutoff, cursor });
  const { mode, adapter } = useConsole();
  if (!adapter.topicDocuments)
    return (
      <Empty message="Topic membership is unavailable for this adapter." />
    );
  return (
    <section
      className={styles.section}
      aria-labelledby="topic-evidence-heading"
    >
      <h2 id="topic-evidence-heading">Supporting Reporting</h2>
      <p className={styles.caption}>
        Publication order across bounded pages, with unknown publication times
        last. Assessment availability is shown separately. Topic assessments
        expand from these loaded records; full Story Detail provides further
        intelligence, entities and event evidence.
      </p>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        {!records.data?.data.length ? (
          <Empty message="No topic evidence is available on this page at the selected cutoff." />
        ) : (
          records.data.data.map((member) => (
            <TopicEvidence
              member={member}
              simulated={mode === "mock"}
              key={member.document.document_id}
            />
          ))
        )}
      </QueryState>
      <CursorPager
        label="Topic Evidence Pages"
        cursor={cursor}
        nextCursor={records.data?.pagination.next_cursor ?? undefined}
        busy={records.isFetching}
        unavailable={!!records.error}
        onPage={setCursor}
      />
    </section>
  );
}
