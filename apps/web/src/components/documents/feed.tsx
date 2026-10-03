"use client";
import { useState } from "react";
import { useDocuments, useSources } from "@/lib/queries";
import { DocumentTable } from "./document-table";
import { Button, PageHeading, QueryState } from "../ui/console";
export function Feed({ search = false }: { search?: boolean }) {
  const [query, setQuery] = useState(""),
    [sourceId, setSourceId] = useState(""),
    [integrity, setIntegrity] = useState(""),
    [cutoff, setCutoff] = useState("");
  const utcCutoff = cutoff ? `${cutoff}:00Z` : undefined;
  const records = useDocuments({
    query,
    sourceId,
    integrity,
    cutoff: utcCutoff,
  });
  const sources = useSources();
  return (
    <>
      <PageHeading
        title={search ? "Search intelligence" : "News / documents"}
        description={
          search
            ? "Search source text, titles, source names and resolved entities in the fixture corpus."
            : "Review incoming evidence with source and intelligence availability kept separate."
        }
      />
      <form
        className="filter-bar"
        onSubmit={(e) => e.preventDefault()}
        aria-label="Document filters"
      >
        <div className="filter-field search-filter">
          <label htmlFor="document-query">
            {search ? "Search terms" : "Filter documents"}
          </label>
          <input
            id="document-query"
            type="search"
            placeholder="Title, text, source or entity…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="filter-field">
          <label htmlFor="document-source">Source</label>
          <select
            id="document-source"
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
          >
            <option value="">All sources</option>
            {sources.data?.map((s) => (
              <option key={s.source_id} value={s.source_id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="document-integrity">Integrity</label>
          <select
            id="document-integrity"
            value={integrity}
            onChange={(e) => setIntegrity(e.target.value)}
          >
            <option value="">All states</option>
            <option value="verified">Verified</option>
            <option value="failed">Failed</option>
            <option value="unverified">Unverified</option>
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="document-cutoff">Knowledge cutoff (UTC)</label>
          <input
            id="document-cutoff"
            type="datetime-local"
            value={cutoff}
            onChange={(e) => setCutoff(e.target.value)}
          />
        </div>
        <Button
          type="button"
          className="secondary"
          onClick={() => {
            setQuery("");
            setSourceId("");
            setIntegrity("");
            setCutoff("");
          }}
        >
          Reset filters
        </Button>
      </form>
      {cutoff && (
        <p className="notice">
          Includes documents first seen by the cutoff. Model outputs, entities
          and events are shown only after availability. Detail pages show the
          complete current record.
        </p>
      )}
      <div className="results-heading">
        <h2>{search ? "Search results" : "Evidence register"}</h2>
        <span role="status" aria-live="polite">
          {records.data?.length ?? 0} documents
          {records.isFetching && !records.isPending ? " · Updating…" : ""}
        </span>
      </div>
      <QueryState
        pending={records.isPending}
        error={records.error}
        retry={records.refetch}
      >
        <DocumentTable documents={records.data ?? []} />
      </QueryState>
    </>
  );
}
