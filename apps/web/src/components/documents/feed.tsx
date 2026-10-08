"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useDocuments, useSources } from "@/lib/queries";
import { useConsole } from "../providers";
import { DocumentTable } from "./document-table";
import { EditorialResults } from "./editorial-results";
import { Button, PageHeading, QueryState } from "../ui/console";
import styles from "./feed.module.css";

export function Feed({ search = false }: { search?: boolean }) {
  return (
    <Suspense
      fallback={
        <PageHeading
          eyebrow="News & Intelligence / Archive"
          title={search ? "Search the Archive" : "Document Archive"}
          description="Loading the archive controls…"
        />
      }
    >
      <DiscoveryFeed search={search} />
    </Suspense>
  );
}
function DiscoveryFeed({ search }: { search: boolean }) {
  const params = useSearchParams();
  const { mode } = useConsole();
  const query = params.get("q") ?? "",
    sourceId = params.get("source") ?? "",
    integrity = params.get("integrity") ?? "",
    cutoff = params.get("cutoff") ?? "";
  const cursor = params.get("cursor") || undefined;
  const view = params.get("view") === "table" ? "table" : "stories";
  const records = useDocuments({
    query,
    sourceId,
    integrity,
    cutoff: cutoff ? `${cutoff}:00Z` : undefined,
    cursor,
  });
  const sources = useSources();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const advancedCount = [sourceId, integrity, cutoff].filter(Boolean).length;
  function update(
    values: Record<string, string>,
    resetCursor = true,
    push = false,
  ) {
    const next = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(values)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (resetCursor) next.delete("cursor");
    const url = `${window.location.pathname}${next.size ? `?${next}` : ""}${window.location.hash}`;
    if (push) window.history.pushState(null, "", url);
    else window.history.replaceState(null, "", url);
  }
  const reset = () => update({ q: "", source: "", integrity: "", cutoff: "" });
  return (
    <div className={styles.feed}>
      <PageHeading
        eyebrow="News & Intelligence / Archive"
        title={search ? "Search the Archive" : "Document Archive"}
        description={
          search
            ? "Find literal matches in source titles and captured text."
            : "Source reporting and its evidence, one bounded archive page at a time."
        }
      />
      <p className={styles.semantics}>
        {mode === "mock"
          ? "Mock search also matches fictional source names and resolved entity names."
          : "Real search matches literal title/text. Assessment details load only on Story Detail."}{" "}
        Archive order is not a global recency or importance ranking.
      </p>
      <form
        className="filter-bar document-filters"
        onSubmit={(event) => event.preventDefault()}
        aria-label="Document Filters"
      >
        <div className="filter-primary">
          <div className="filter-field search-filter">
            <label htmlFor="document-query">
              {search ? "Search Terms" : "Filter Documents"}
            </label>
            <input
              id="document-query"
              type="search"
              placeholder="Title or captured source text…"
              value={query}
              onChange={(event) => update({ q: event.target.value })}
            />
          </div>
          <Button
            type="button"
            className="secondary filter-toggle"
            aria-expanded={advancedOpen}
            aria-controls="document-advanced-filters"
            onClick={() => setAdvancedOpen(!advancedOpen)}
          >
            Advanced Filters{advancedCount ? ` (${advancedCount})` : ""}
          </Button>
          <Button
            type="button"
            className="secondary filter-reset"
            onClick={reset}
          >
            Reset Filters
          </Button>
        </div>
        <div
          id="document-advanced-filters"
          className="advanced-filters"
          data-open={advancedOpen}
        >
          <div className="filter-field">
            <label htmlFor="document-source">Source</label>
            <select
              id="document-source"
              value={sourceId}
              onChange={(event) => update({ source: event.target.value })}
            >
              <option value="">All Sources</option>
              {sourceId &&
                !sources.data?.some(
                  (source) => source.source_id === sourceId,
                ) && <option value={sourceId}>Selected Source</option>}
              {sources.data?.map((source) => (
                <option key={source.source_id} value={source.source_id}>
                  {source.name}
                </option>
              ))}
            </select>
          </div>
          <div className="filter-field">
            <label htmlFor="document-integrity">Integrity</label>
            <select
              id="document-integrity"
              value={integrity}
              onChange={(event) => update({ integrity: event.target.value })}
            >
              <option value="">All States</option>
              <option value="verified" disabled={mode === "real"}>
                Verified{mode === "real" ? " (Mock Only)" : ""}
              </option>
              <option value="failed" disabled={mode === "real"}>
                Failed{mode === "real" ? " (Mock Only)" : ""}
              </option>
              <option value="unverified">Unverified</option>
            </select>
          </div>
          <div className="filter-field">
            <label htmlFor="document-cutoff">Knowledge Cutoff (UTC)</label>
            <input
              id="document-cutoff"
              type="datetime-local"
              value={cutoff}
              onChange={(event) => update({ cutoff: event.target.value })}
            />
          </div>
        </div>
      </form>
      {sources.error && (
        <p className="notice" role="status">
          Source filters are unavailable: {sources.error.message}{" "}
          <Button className="secondary" onClick={() => sources.refetch()}>
            Retry Sources
          </Button>
        </p>
      )}
      {(query || advancedCount > 0) && (
        <div className={styles.active} aria-label="Active Filters">
          {query && <span>Text: {query}</span>}
          {sourceId && (
            <span>
              Source:{" "}
              {sources.data?.find((source) => source.source_id === sourceId)
                ?.name ?? sourceId}
            </span>
          )}
          {integrity && (
            <span>
              Integrity: {integrity}
              {mode === "real" && integrity !== "unverified"
                ? " · Unsupported in Real API"
                : ""}
            </span>
          )}
          {cutoff && <span>Cutoff: {cutoff.replace("T", " ")} UTC</span>}
        </div>
      )}
      {mode === "real" && (
        <p className={styles.semantics}>
          Feed-wide verified/failed filtering is unavailable. Open a story for
          an explicit integrity check.
        </p>
      )}
      {cutoff && (
        <p className="notice">
          Real API includes documents persisted by the cutoff; mock mode uses
          fixture first-seen times. Model outputs, entities and events are shown
          only after availability. Detail pages show the complete current
          record.
        </p>
      )}
      <div className={styles.resultsHeading}>
        <h2>{search ? "Search Results" : "Source Records"}</h2>
        <span role="status" aria-live="polite">
          {records.error
            ? "Page Count Unavailable"
            : records.isPending
              ? "Loading this page…"
              : `${records.data?.length ?? 0} ${(records.data?.length ?? 0) === 1 ? "record" : "records"} on this page`}
          {records.isFetching && !records.isPending ? " · Updating…" : ""}
        </span>
      </div>
      <div
        className={styles.viewControls}
        role="group"
        aria-label="Results View"
      >
        <Button
          className="secondary"
          aria-pressed={view === "stories"}
          onClick={() => update({ view: "" }, false)}
        >
          Editorial Rows
        </Button>
        <Button
          className="secondary"
          aria-pressed={view === "table"}
          onClick={() => update({ view: "table" }, false)}
        >
          Evidence Table
        </Button>
        <span>No total corpus count is supplied.</span>
      </div>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        <div className={styles.editorial} data-view={view}>
          <EditorialResults documents={records.data ?? []} />
        </div>
        {view === "table" && (
          <div className={styles.register}>
            <DocumentTable documents={records.data ?? []} expandable />
          </div>
        )}
        <div className="pagination" aria-label="Document Pagination">
          <Button
            disabled={!cursor || records.isFetching}
            onClick={() => update({ cursor: "" }, false, true)}
          >
            First Page
          </Button>
          <Button
            disabled={!records.data?.nextCursor || records.isFetching}
            onClick={() =>
              update({ cursor: records.data?.nextCursor ?? "" }, false, true)
            }
          >
            Next Page
          </Button>
          <p className={styles.semantics}>
            Cursor pages are bounded; a previous-page cursor and page total are
            not available.
          </p>
        </div>
      </QueryState>
    </div>
  );
}
