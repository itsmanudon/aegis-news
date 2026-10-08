"use client";
import Link from "next/link";
import { useState } from "react";
import { useDocument, useDocuments } from "@/lib/queries";
import { ProvenanceCard } from "../documents/provenance-card";
import { StoryMetadata } from "../editorial/stories";
import { CursorPager } from "../ui/cursor-pager";
import { Empty, PageHeading, QueryState } from "../ui/console";
import shared from "./intelligence.module.css";
import styles from "./verification.module.css";

export function Provenance() {
  const [cursor, setCursor] = useState<string>();
  const [selected, setSelected] = useState("");
  const records = useDocuments({ cursor });
  function page(cursor?: string) {
    setSelected("");
    setCursor(cursor);
  }
  return (
    <div className={shared.page}>
      <PageHeading
        eyebrow="News & Intelligence / Verification"
        title="Verification Workspace"
        description="Inspect captured evidence, run an explicit integrity check and review each supported outcome."
      />
      <p className={shared.caption}>
        Cryptographic integrity addresses captured bytes and lineage. It does
        not establish factual accuracy.
      </p>
      <div className={styles.workspace}>
        <section
          className={styles.selection}
          aria-labelledby="document-selection-heading"
        >
          <h2 id="document-selection-heading">Select a Document</h2>
          <p>
            Browse the archive, inspect its evidence, then request verification.
          </p>
          <QueryState
            pending={records.isPending}
            error={records.error}
            retry={records.refetch}
          >
            {records.data?.length ? (
              <div className={styles.selector}>
                <label htmlFor="verification-document">Select Document</label>
                <select
                  id="verification-document"
                  value={selected}
                  onChange={(event) => setSelected(event.target.value)}
                >
                  <option value="">Choose a Document</option>
                  {records.data.map((view) => (
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
              <Empty message="No documents are available on this page. Browse another page or use Document Archive." />
            )}
            <p className={styles.caption}>
              {records.data?.length ?? 0} records on this page. Archive order
              does not rank importance or recency.
            </p>
          </QueryState>
          <CursorPager
            cursor={cursor}
            nextCursor={records.error ? undefined : records.data?.nextCursor}
            busy={records.isFetching}
            onPage={page}
            label="Verification Document Pages"
            unavailable={!!records.error}
          />
          <Link href="/documents">Open Document Archive →</Link>
          <ol className={styles.workflow} aria-label="Verification Workflow">
            <li>Select Document</li>
            <li>Inspect Evidence</li>
            <li>Run Authorized Verification</li>
            <li>Review Outcomes</li>
          </ol>
        </section>
        <section
          className={styles.inspector}
          aria-label="Selected Document Evidence"
        >
          {selected ? (
            <SelectedEvidence key={selected} id={selected} />
          ) : (
            <div className={styles.prompt}>
              <h2>Inspect Evidence</h2>
              <p>
                Select a document to inspect available operation history. No
                verification runs until you request it.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
function SelectedEvidence({ id }: { id: string }) {
  const record = useDocument(id);
  return (
    <QueryState
      pending={record.isPending}
      error={record.error}
      retry={record.refetch}
    >
      {record.data && (
        <>
          <div className={styles.story}>
            <h2>{record.data.document.title}</h2>
            <StoryMetadata view={record.data} />
            <Link href={`/documents/${id}`}>Open Story Detail →</Link>
          </div>
          <ProvenanceCard view={record.data} workspace />
        </>
      )}
    </QueryState>
  );
}
