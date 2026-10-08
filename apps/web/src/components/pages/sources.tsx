"use client";
import { useState } from "react";
import { useSourcePage } from "@/lib/queries";
import { SourceAdministration } from "../operations/source-administration";
import { ProviderAdmin } from "../provider-admin";
import { OperationsNav } from "../operations/operations-nav";
import { Timestamp } from "../documents/time-rail";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { CursorPager } from "../ui/cursor-pager";
import { Badge, Empty, PageHeading, QueryState } from "../ui/console";
import styles from "../operations/operations.module.css";
import { sourceAddress as externalUrl } from "@/lib/operations";
export function Sources() {
  const [cursor, setCursor] = useState<string>();
  const records = useSourcePage(cursor);
  return (
    <div className={styles.page}>
      <PageHeading
        title="Sources & Ingestion"
        eyebrow="Operations & Security"
        description="Browse registered sources, submit captured articles and inspect known processing runs."
      />
      <OperationsNav active="sources" />
      <section
        id="registry"
        className={styles.section}
        aria-labelledby="source-registry-heading"
      >
        <div className={styles.sectionHeading}>
          <h2 id="source-registry-heading">Source Registry</h2>
          <p role="status">
            {records.data
              ? `${records.data.length} ${records.data.length === 1 ? "source" : "sources"} on this page`
              : "Bounded Source Browsing"}
          </p>
        </div>
        <QueryState
          pending={records.isPending}
          error={records.error}
          retry={records.refetch}
        >
          {!records.data?.length ? (
            <Empty message="No sources are supplied on this page. An authorized operator can create a source below." />
          ) : (
            <table className={styles.table} role="table">
              <caption className="sr-only">Registered Sources</caption>
              <thead>
                <tr role="row">
                  <th scope="col">Source</th>
                  <th scope="col">Type</th>
                  <th scope="col">Address</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {records.data.map((source) => (
                  <tr
                    className="source-record"
                    role="row"
                    key={source.source_id}
                  >
                    <td role="cell">
                      <h3>{source.name}</h3>
                      <EvidenceDisclosure title="Source Details">
                        <dl className={styles.metadata}>
                          <dt>Source ID</dt>
                          <dd className={styles.technical}>
                            {source.source_id}
                          </dd>
                          <dt>Schema Version</dt>
                          <dd>{source.schema_version}</dd>
                        </dl>
                        <p className={styles.hint}>
                          The registry does not supply health, ownership or
                          ingestion history.
                        </p>
                      </EvidenceDisclosure>
                    </td>
                    <td role="cell" data-label="Source Type">
                      <Badge>
                        {(
                          {
                            feed: "Feed",
                            api: "API",
                            upload: "Upload",
                            web: "Web",
                          } as Record<string, string>
                        )[source.kind] ?? source.kind}
                      </Badge>
                    </td>
                    <td role="cell" data-label="Address">
                      {externalUrl(source.url) ? (
                        <a
                          href={externalUrl(source.url)!}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {source.url}
                        </a>
                      ) : source.url ? (
                        "Address Unavailable"
                      ) : (
                        "No Address Supplied"
                      )}
                    </td>
                    <td role="cell" data-label="Created">
                      <Timestamp value={source.created_at} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </QueryState>
        <CursorPager
          label="Source Pages"
          cursor={cursor}
          nextCursor={records.data?.nextCursor}
          busy={records.isFetching}
          unavailable={!!records.error}
          onPage={setCursor}
        />
      </section>
      <section className={styles.section} aria-label="Administration">
        <div className={styles.sectionHeading}>
          <h2>Administration</h2>
        </div>
        <SourceAdministration sources={records.data ?? []} />
      </section>
      <ProviderAdmin />
    </div>
  );
}
