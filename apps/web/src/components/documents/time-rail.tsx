import type { DocumentView } from "@/lib/models";
export function Timestamp({ value }: { value: string | null | undefined }) {
  if (!value || Number.isNaN(Date.parse(value))) return <span>Unknown</span>;
  const date = new Date(value);
  const utc = date.toISOString();
  const clock = new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
    ...(date.getUTCSeconds() || date.getUTCMilliseconds()
      ? { second: "2-digit" }
      : {}),
    ...(date.getUTCMilliseconds() ? { fractionalSecondDigits: 3 } : {}),
  } as Intl.DateTimeFormatOptions).format(date);
  return (
    <time className="timestamp" dateTime={utc} title={utc}>
      <span className="timestamp-date">
        {new Intl.DateTimeFormat("en-GB", {
          timeZone: "UTC",
          day: "numeric",
          month: "short",
          year: "numeric",
        }).format(date)}
      </span>{" "}
      <span className="timestamp-clock">{clock} UTC</span>
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
          ["First Seen", view.document.first_seen_at],
          ["Ingested", view.document.ingested_at],
          ["Intelligence Available", available],
        ] as const
      ).map(([label, time]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>
            {time ? (
              <Timestamp value={time} />
            ) : label === "Intelligence Available" ? (
              "Not Available"
            ) : (
              "Unknown"
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
