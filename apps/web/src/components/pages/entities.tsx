"use client";
import Link from "next/link";
import { useState } from "react";
import { useDocuments, useEntities, useEntity } from "@/lib/queries";
import { entityTypeLabel } from "@/lib/source-presentation";
import { EditorialResults } from "../documents/editorial-results";
import { Timestamp } from "../documents/time-rail";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { CursorPager } from "../ui/cursor-pager";
import { Badge, Empty, PageHeading, QueryState } from "../ui/console";
import styles from "./intelligence.module.css";

export function Entities() {
  const [cursor, setCursor] = useState<string>();
  const records = useEntities(cursor);
  return (
    <div className={styles.page}>
      <PageHeading
        eyebrow="News & Intelligence / Entities"
        title="Entity Directory"
        description="Canonical identities and their linked source evidence. Explore the record before drawing conclusions."
      />
      <p className={styles.caption}>
        Associations reflect recorded resolution output. Open an entity to
        explore its available source evidence.
      </p>
      <p className={styles.count} role="status">
        {records.isPending
          ? "Loading this page…"
          : records.error
            ? "Page Count Unavailable"
            : `${records.data?.length ?? 0} entities on this page`}
      </p>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        {!records.data?.length && (
          <Empty message="No entities are available on this page." />
        )}
        <div className={styles.directory}>
          {records.data?.map((entity) => (
            <article
              key={entity.entity_id}
              className={`entity-entry ${styles.entity}`}
            >
              <div className={styles.entityMain}>
                <Badge>{entityTypeLabel(entity.kind)}</Badge>
                <h2>
                  <Link href={`/entities/${entity.entity_id}`}>
                    {entity.canonical_name}
                  </Link>
                </h2>
                <Link href={`/entities/${entity.entity_id}`}>
                  Inspect Entity →
                </Link>
              </div>
              <div className={styles.entityMeta}>
                <dl className="evidence-times">
                  <div>
                    <dt>Record Created</dt>
                    <dd>
                      <Timestamp value={entity.created_at} />
                    </dd>
                  </div>
                </dl>
                <EvidenceDisclosure title="Technical Identity">
                  <dl className="metadata">
                    <dt>Entity ID</dt>
                    <dd className="hash">{entity.entity_id}</dd>
                    <dt>Schema Version</dt>
                    <dd>{entity.schema_version}</dd>
                  </dl>
                </EvidenceDisclosure>
              </div>
            </article>
          ))}
        </div>
      </QueryState>
      <CursorPager
        cursor={cursor}
        nextCursor={records.error ? undefined : records.data?.nextCursor}
        busy={records.isFetching}
        onPage={setCursor}
        label="Entity Directory Pages"
        unavailable={!!records.error}
      />
    </div>
  );
}

export function EntityDetail({ id }: { id: string }) {
  const entity = useEntity(id);
  return (
    <div className={styles.page}>
      <Link className="back-link" href="/entities">
        ← Entity Directory
      </Link>
      <QueryState
        pending={entity.isPending}
        error={entity.error}
        retry={entity.refetch}
      >
        {entity.data && (
          <>
            <PageHeading
              eyebrow="News & Intelligence / Entity Research"
              title={entity.data.canonical_name}
              description="Canonical identity and associated reporting. Resolution links require review against source evidence."
            />
            <div className={styles.identitySummary}>
              <Badge>{entityTypeLabel(entity.data.kind)}</Badge>
              <span>
                Record Created <Timestamp value={entity.data.created_at} />
              </span>
            </div>
            <div className={styles.identityDisclosure}>
              <EvidenceDisclosure title="Technical Identity">
                <dl className="metadata">
                  <dt>Entity ID</dt>
                  <dd className="hash">{entity.data.entity_id}</dd>
                  <dt>Schema Version</dt>
                  <dd>{entity.data.schema_version}</dd>
                </dl>
              </EvidenceDisclosure>
            </div>
            <LinkedEvidence key={id} id={id} />
          </>
        )}
      </QueryState>
    </div>
  );
}
function LinkedEvidence({ id }: { id: string }) {
  const [cursor, setCursor] = useState<string>();
  const records = useDocuments({ entityId: id, cursor });
  return (
    <section
      className={styles.linked}
      aria-labelledby="linked-evidence-heading"
    >
      <div className={styles.sectionHeading}>
        <h2 id="linked-evidence-heading">Linked Evidence</h2>
        <span role="status">
          {records.isPending
            ? "Loading this page…"
            : records.error
              ? "Page Count Unavailable"
              : `${records.data?.length ?? 0} records on this page`}
        </span>
      </div>
      <p className={styles.caption}>
        Associated source records, one page at a time. Archive order is not a
        global recency ranking. Expand for loaded evidence or open the full
        story.
      </p>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        {records.data?.length ? (
          <EditorialResults documents={records.data} />
        ) : (
          <Empty message="No associated source records are available on this page." />
        )}
      </QueryState>
      <CursorPager
        cursor={cursor}
        nextCursor={records.error ? undefined : records.data?.nextCursor}
        busy={records.isFetching}
        onPage={setCursor}
        label="Associated Evidence Pages"
        unavailable={!!records.error}
      />
    </section>
  );
}
