import Link from "next/link";
import type { DocumentView } from "@/lib/models";
import styles from "./stories.module.css";

function StoryTime({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  if (!value || Number.isNaN(Date.parse(value)))
    return <span>{label} time unknown</span>;
  const date = new Date(value);
  return (
    <span>
      {label}{" "}
      <time dateTime={date.toISOString()} title={date.toISOString()}>
        {new Intl.DateTimeFormat("en-GB", {
          day: "numeric",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "UTC",
        }).format(date)}{" "}
        UTC
      </time>
    </span>
  );
}
export function StoryMetadata({ view }: { view: DocumentView }) {
  return (
    <div className={styles.metadata}>
      <span className={styles.source}>{view.source.name}</span>
      <StoryTime label="Published" value={view.document.published_at} />
      <StoryTime label="First seen" value={view.document.first_seen_at} />
    </div>
  );
}
function SourceExcerpt({
  view,
  length,
}: {
  view: DocumentView;
  length: number;
}) {
  const text = view.document.text.replace(/\s+/g, " ").trim();
  if (!text)
    return (
      <p className={styles.extent}>
        No source text is available in this record.
      </p>
    );
  if (text === view.document.title.trim())
    return (
      <p className={styles.extent}>
        Only headline text is available in this record.
      </p>
    );
  // A visibly labelled, verbatim text preview. No model summary or added claims.
  const characters = Array.from(text);
  const preview = characters.slice(0, length).join("");
  const excerpt =
    characters.length > length
      ? `${preview.slice(0, preview.lastIndexOf(" ") > 0 ? preview.lastIndexOf(" ") : preview.length)}…`
      : text;
  return (
    <div className={styles.excerpt}>
      <span className={styles.extent}>Source excerpt</span>
      <p>{excerpt}</p>
    </div>
  );
}
export function StoryLead({ view }: { view: DocumentView }) {
  return (
    <article className={`story-lead ${styles.lead}`}>
      <StoryMetadata view={view} />
      <h3>
        <Link href={`/documents/${view.document.document_id}`}>
          {view.document.title}
        </Link>
      </h3>
      <SourceExcerpt view={view} length={340} />
      <Link
        className={styles.readLink}
        href={`/documents/${view.document.document_id}`}
      >
        Read source & inspect evidence <span aria-hidden="true">→</span>
      </Link>
    </article>
  );
}
export function StoryRow({
  view,
  compact = false,
}: {
  view: DocumentView;
  compact?: boolean;
}) {
  return (
    <article
      className={`story-row ${styles.row} ${compact ? styles.compact : ""}`}
    >
      <StoryMetadata view={view} />
      <h3>
        <Link href={`/documents/${view.document.document_id}`}>
          {view.document.title}
        </Link>
      </h3>
      {!compact && <SourceExcerpt view={view} length={180} />}
    </article>
  );
}
