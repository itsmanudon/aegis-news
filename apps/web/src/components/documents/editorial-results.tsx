"use client";
import Link from "next/link";
import type { DocumentView } from "@/lib/models";
import { literalExcerpt } from "@/lib/source-presentation";
import { StoryMetadata } from "../editorial/stories";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { Badge, Empty } from "../ui/console";
import { EvidenceDetails } from "./evidence-details";
import styles from "./editorial-results.module.css";
import { useConsole } from "../providers";
export function EditorialResults({ documents }: { documents: DocumentView[] }) {
  const { mode } = useConsole();
  if (!documents.length) return <Empty />;
  return (
    <div className={styles.results}>
      {documents.map((view) => (
        <article
          className={`editorial-result ${styles.row}`}
          key={view.document.document_id}
        >
          <div className={styles.metadata}>
            <StoryMetadata view={view} />
          </div>
          <div className={styles.copy}>
            <h3>
              <Link href={`/documents/${view.document.document_id}`}>
                {view.document.title}
              </Link>
            </h3>
            {view.document.text &&
              view.document.text.trim() !== view.document.title.trim() && (
                <p className={styles.preview}>
                  <span>Source Excerpt</span>{" "}
                  {literalExcerpt(view.document.text, 160)}
                </p>
              )}
            <div className={styles.status}>
              <Badge tone="model">
                {view.intelligenceLoaded === false
                  ? "Open Detail for Assessments"
                  : view.analyses.length
                    ? `${view.analyses.length} Model Assessment${view.analyses.length === 1 ? "" : "s"}`
                    : "No Assessments Available"}
              </Badge>
              <span>
                {mode === "mock"
                  ? "Simulated Integrity"
                  : "Integrity Not Checked"}
              </span>
              <Badge tone={mode === "mock" ? view.integrity : "unverified"}>
                {mode === "mock" ? view.integrity : "unverified"}
              </Badge>
            </div>
          </div>
          <div className={styles.expansion}>
            <EvidenceDisclosure title="Evidence Details">
              <EvidenceDetails view={view} simulated={mode === "mock"} />
            </EvidenceDisclosure>
          </div>
        </article>
      ))}
    </div>
  );
}
