import type { DocumentView } from "@/lib/models";
export function Timestamp({ value }: { value: string | null | undefined }) {
  if (!value || Number.isNaN(Date.parse(value))) return <span>Unknown</span>;
  const utc = new Date(value).toISOString();
  return (
    <time dateTime={utc} title={value}>
      {utc
        .replace("T", " ")
        .replace(/\.000Z$/, "Z")
        .replace("Z", " UTC")}
    </time>
  );
}
export function TimeRail({ view }: { view: DocumentView }) {
  const available = view.analyses.map((a) => a.available_at).sort()[0];
  return (
    <dl className="time-rail" aria-label="Document time semantics">
      {(
        [
          ["Published", view.document.published_at],
          ["First seen", view.document.first_seen_at],
          ["Ingested", view.document.ingested_at],
          ["Intelligence available", available],
        ] as const
      ).map(([label, time]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>
            {time ? (
              <Timestamp value={time} />
            ) : label === "Intelligence available" ? (
              "Not available"
            ) : (
              "Unknown"
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
