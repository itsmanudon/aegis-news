"use client";
import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useDiscovery } from "@/lib/queries";
import { useConsole } from "../providers";
import { EditorialResults } from "../documents/editorial-results";
import { Timestamp } from "../documents/time-rail";
import { PageHeading, QueryState, Button, Empty } from "../ui/console";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import { CursorPager } from "../ui/cursor-pager";
import styles from "../intelligence/intelligence.module.css";
const utcInput = (value: string | null) =>
  value && Number.isFinite(Date.parse(value))
    ? new Date(value).toISOString().slice(0, -1)
    : "";
export function ChronologicalDiscovery() {
  return (
    <Suspense fallback={<p role="status">Loading Chronological Discovery…</p>}>
      <DiscoveryStream />
    </Suspense>
  );
}
function DiscoveryStream() {
  const params = useSearchParams(),
    cursor = params.get("cursor") || undefined,
    order =
      params.get("order") === "first_seen_at"
        ? "first_seen_at"
        : "published_at";
  const timeBasis =
    params.get("time_basis") === "published_at"
      ? "published_at"
      : "first_seen_at";
  const records = useDiscovery({
    cursor,
    order,
    query: params.get("q") || undefined,
    cutoff: params.get("as_of") || undefined,
    sourceId: params.get("source") || undefined,
    topicId: params.get("topic") || undefined,
    start: params.get("start") || undefined,
    end: params.get("end") || undefined,
    timeBasis,
  });
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
  if (!adapter.discovery)
    return (
      <Empty message="Chronological discovery is unavailable for this adapter." />
    );
  return (
    <div className={styles.page}>
      <PageHeading
        eyebrow="News & Intelligence / Discovery"
        title="Chronological Discovery"
        description="Follow the reporting in a declared time order. Inspect its source evidence."
      />
      <p className={styles.caption}>
        {order === "published_at"
          ? "Global Publication order across eligible documents, with unknown publication times last."
          : "Global First Seen order across eligible documents; this is acquisition evidence, not publisher publication."}{" "}
        Ordering comes from the bounded server query across pages, not sorting
        the loaded page. Source and model timestamps remain distinct.
      </p>
      {mode === "mock" && (
        <p className="notice">
          Fictional records ordered within Mock Development Data.
        </p>
      )}
      <form
        className={styles.filters}
        aria-label="Chronological Discovery Filters"
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          const values: Record<string, string> = {
            q: String(data.get("q")),
            order: String(data.get("order")),
            source: String(data.get("source") ?? ""),
            time_basis: String(data.get("time_basis") ?? "first_seen_at"),
            cursor: "",
          };
          for (const key of ["as_of", "start", "end"]) {
            const value = String(data.get(key) ?? "");
            values[key] = value ? `${value}Z` : "";
          }
          update(values);
        }}
      >
        <label>
          Search Reporting
          <input
            type="search"
            name="q"
            defaultValue={params.get("q") ?? ""}
            maxLength={200}
          />
        </label>
        <label>
          Order By
          <select name="order" aria-label="Order By" defaultValue={order}>
            <option value="published_at">Publication</option>
            <option value="first_seen_at">First Seen</option>
          </select>
        </label>
        <label>
          As Of UTC
          <input
            type="datetime-local"
            step="0.001"
            name="as_of"
            defaultValue={utcInput(params.get("as_of"))}
          />
        </label>
        <EvidenceDisclosure title="Population Filters">
          <label>
            Source ID
            <input name="source" defaultValue={params.get("source") ?? ""} />
          </label>
          <label>
            Window Start (Inclusive, UTC)
            <input
              type="datetime-local"
              step="0.001"
              name="start"
              defaultValue={utcInput(params.get("start"))}
            />
          </label>
          <label>
            Window End (Exclusive, UTC)
            <input
              type="datetime-local"
              step="0.001"
              name="end"
              defaultValue={utcInput(params.get("end"))}
            />
          </label>
          <label>
            Window Time Basis
            <select name="time_basis" defaultValue={timeBasis}>
              <option value="published_at">Publication</option>
              <option value="first_seen_at">First Seen</option>
            </select>
          </label>
          <p className={styles.caption}>
            Date windows use the selected time basis and exclude unknown dates.
            A topic selection in the URL is preserved; its exact model cohort is
            not expanded into related topics.
          </p>
        </EvidenceDisclosure>
        <Button disabled={records.isFetching}>Apply Discovery Filters</Button>
      </form>
      {params.get("topic") && (
        <p className={styles.caption}>
          Filtered by one recorded topic/model cohort.{" "}
          <Link
            href={`/topics/${encodeURIComponent(params.get("topic")!)}${params.get("as_of") ? `?as_of=${encodeURIComponent(params.get("as_of")!)}` : ""}`}
          >
            Inspect Topic Identity →
          </Link>
        </p>
      )}
      {records.data && (
        <p className={styles.caption}>
          {records.data.length} source records on this page · Query Cutoff{" "}
          <Timestamp value={records.data.asOf} />
        </p>
      )}
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        {records.data && (
          <section
            className={styles.section}
            aria-labelledby="discovery-records"
          >
            <h2 id="discovery-records">Supporting Records</h2>
            <EditorialResults documents={records.data} />
          </section>
        )}
      </QueryState>
      <CursorPager
        label="Chronological Discovery Pages"
        cursor={cursor}
        nextCursor={records.data?.nextCursor}
        busy={records.isFetching}
        unavailable={!!records.error}
        onPage={(value) => update({ cursor: value ?? "" })}
      />
      <div className={styles.actions}>
        <Link href="/analytics">Inspect Coverage Analytics →</Link>
        <Link href="/documents">Browse the Document Archive →</Link>
      </div>
    </div>
  );
}
