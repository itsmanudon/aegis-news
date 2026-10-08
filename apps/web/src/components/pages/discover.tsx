"use client";
import Link from "next/link";
import { useDocuments } from "@/lib/queries";
import { StoryLead, StoryRow } from "../editorial/stories";
import { DiscoveryMedia } from "../editorial/discovery-media";
import { QueryState } from "../ui/console";
import styles from "./discover.module.css";

export function Discover() {
  const records = useDocuments();
  const [lead, ...supporting] = records.data ?? [];
  return (
    <div className={styles.discover}>
      <div className={styles.introduction}>
        <div>
          <p className={styles.eyebrow}>Discover / News & Intelligence</p>
          <h1>
            A Wider View.
            <br />A Closer Read.
          </h1>
        </div>
        <div className={styles.introNote}>
          <p>
            Start with the reporting.
            <br />
            Follow its evidence.
          </p>
          <Link href="/search">
            Search the Archive <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </div>
      <section aria-labelledby="archive-heading" className={styles.archive}>
        <div className={styles.sectionHeading}>
          <h2 id="archive-heading">From the Archive</h2>
          <Link href="/documents">
            Open Evidence Register <span aria-hidden="true">→</span>
          </Link>
        </div>
        <p className={styles.orderNote}>
          Stories from one archive page. Layout emphasis does not indicate
          recency or importance.
        </p>
        <QueryState
          pending={records.isPending}
          error={records.error}
          retry={records.refetch}
        >
          {lead ? (
            <>
              <div className={styles.leadGrid}>
                <StoryLead view={lead} />
                <div className={styles.supporting}>
                  <p className={styles.eyebrow}>Further Reading</p>
                  {supporting.slice(0, 2).map((view) => (
                    <StoryRow
                      key={view.document.document_id}
                      view={view}
                      compact
                    />
                  ))}
                  {!supporting.length && (
                    <p className={styles.orderNote}>
                      More source records can be explored in the evidence
                      register.
                    </p>
                  )}
                </div>
              </div>
              <div className={styles.archiveBottom}>
                <div className={styles.storyList}>
                  {supporting.slice(2).map((view) => (
                    <StoryRow key={view.document.document_id} view={view} />
                  ))}
                  <Link className={styles.archiveLink} href="/documents">
                    Explore the Document Archive{" "}
                    <span aria-hidden="true">→</span>
                  </Link>
                </div>
                <aside
                  className={styles.evidenceGuide}
                  aria-labelledby="evidence-guide-heading"
                >
                  <p className={styles.eyebrow}>Reading the Evidence</p>
                  <h2 id="evidence-guide-heading">
                    A Report Is <br />a Starting Point.
                  </h2>
                  <p>
                    Source statements, model assessments and cryptographic
                    checks answer different questions.
                  </p>
                  <Link href="/entities">
                    Explore Canonical Entities <span aria-hidden="true">→</span>
                  </Link>
                  <Link href="/events">
                    Follow Source and Model Events{" "}
                    <span aria-hidden="true">→</span>
                  </Link>
                  <Link href="/provenance">
                    Inspect Provenance <span aria-hidden="true">→</span>
                  </Link>
                  <p className={styles.verificationNote}>
                    A valid hash or signature does not establish that a report
                    is factually true.
                  </p>
                </aside>
              </div>
            </>
          ) : (
            <div className={styles.empty} role="status">
              <h3>No Source Records to Explore Yet.</h3>
              <p>
                Try the document register or explore available media references
                below.
              </p>
              <Link href="/documents">Open the Document Register →</Link>
            </div>
          )}
        </QueryState>
      </section>
      <DiscoveryMedia />
    </div>
  );
}
