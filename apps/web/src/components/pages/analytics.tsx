"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { components } from "@/lib/generated/api";
import type { AnalyticsFilters } from "@/lib/models";
import { useAnalytics, useTopics } from "@/lib/queries";
import { useConsole } from "../providers";
import { CoverageChart, Distribution } from "../intelligence/charts";
import { Timestamp } from "../documents/time-rail";
import { Badge, Button, PageHeading, QueryState } from "../ui/console";
import { EvidenceDisclosure } from "../ui/evidence-disclosure";
import styles from "../intelligence/intelligence.module.css";

type Report = components["schemas"]["AnalyticsReport"];
export function AnalyticsTopicSelector({
  topics,
  selected,
  onSelect,
}: {
  topics: components["schemas"]["TopicSummary"][];
  selected?: string;
  onSelect: (id: string) => void;
}) {
  const cohort = topics.find((topic) => topic.topic_id === selected);
  return (
    <>
      <label htmlFor="analytics-topic">Topic</label>
      <select
        id="analytics-topic"
        value={selected ?? ""}
        onChange={(event) => onSelect(event.target.value)}
      >
        <option value="">All Eligible Documents</option>
        {selected && !cohort && (
          <option value={selected}>Selected Topic · {selected}</option>
        )}
        {topics.map((topic) => (
          <option key={topic.topic_id} value={topic.topic_id}>
            {`${topic.label} · ${topic.model.provider} · ${topic.model.model_name} / ${topic.model.model_version} · ${topic.model.configuration_hash.slice(0, 12)}`}
          </option>
        ))}
      </select>
      {selected && (
        <EvidenceDisclosure title="Selected Topic Identity">
          <dl className={styles.analyticsSourceRecords}>
            <div>
              <dt>Topic ID</dt>
              <dd>
                <code>{selected}</code>
              </dd>
            </div>
            {cohort && (
              <>
                <div>
                  <dt>Topic Label</dt>
                  <dd>{cohort.label}</dd>
                </div>
                <div>
                  <dt>Provider</dt>
                  <dd>{cohort.model.provider}</dd>
                </div>
                <div>
                  <dt>Model Name</dt>
                  <dd>{cohort.model.model_name}</dd>
                </div>
                <div>
                  <dt>Model Version</dt>
                  <dd>{cohort.model.model_version}</dd>
                </div>
                <div>
                  <dt>Configuration Hash</dt>
                  <dd>
                    <code>{cohort.model.configuration_hash}</code>
                  </dd>
                </div>
              </>
            )}
          </dl>
          {!cohort && (
            <p className={styles.caption}>
              Model identity is not supplied on this bounded page.
            </p>
          )}
          <p className={styles.caption}>
            The selected ID denotes one exact topic/model/configuration cohort.
            Similar labels do not combine separate cohorts.
          </p>
        </EvidenceDisclosure>
      )}
    </>
  );
}
const day = 86400000;

export function readAnalyticsParameters(
  params: URLSearchParams,
): AnalyticsFilters {
  const end = new Date();
  end.setUTCHours(0, 0, 0, 0);
  end.setUTCDate(end.getUTCDate() + 1);
  const basis = params.get("time_basis") ?? "first_seen_at";
  if (basis !== "published_at" && basis !== "first_seen_at")
    throw new Error("Choose Publication or First Seen as the time basis.");
  return {
    start:
      params.get("start") ?? new Date(end.getTime() - 30 * day).toISOString(),
    end: params.get("end") ?? end.toISOString(),
    timeBasis: basis,
    topicId: params.get("topic") || undefined,
    sourceId: params.get("source") || undefined,
    cutoff: params.get("as_of") || undefined,
  };
}
export function analyticsParameters(
  filters: AnalyticsFilters,
): URLSearchParams {
  const params = new URLSearchParams({
    start: filters.start,
    end: filters.end,
    time_basis: filters.timeBasis ?? "first_seen_at",
  });
  if (filters.topicId) params.set("topic", filters.topicId);
  if (filters.sourceId) params.set("source", filters.sourceId);
  if (filters.cutoff) params.set("as_of", filters.cutoff);
  return params;
}
function awareInstant(value: string) {
  return (
    /T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})$/i.test(
      value,
    ) && Number.isFinite(Date.parse(value))
  );
}
export function validateAnalyticsFilters(
  filters: AnalyticsFilters,
): string | undefined {
  if (!awareInstant(filters.start) || !awareInstant(filters.end))
    return "Choose valid start and end timestamps with an explicit timezone. Controls use UTC.";
  if (Date.parse(filters.end) <= Date.parse(filters.start))
    return "The window end must be after the start.";
  if (Date.parse(filters.end) - Date.parse(filters.start) > 366 * day)
    return "Choose an interval of at most 366 days.";
  if (filters.cutoff && !awareInstant(filters.cutoff))
    return "Choose a valid As Of timestamp with an explicit timezone.";
}
export function supportingRecordsUrl(report: Report): string {
  const params = analyticsParameters({
    start: report.start,
    end: report.end,
    timeBasis: report.time_basis,
    topicId: report.topic_id ?? undefined,
    sourceId: report.source_id ?? undefined,
    cutoff: report.as_of,
  });
  params.set("order", report.time_basis);
  return `/discovery?${params}`;
}

export function AnalyticsResults({
  report,
  simulated,
}: {
  report: Report;
  simulated: boolean;
}) {
  const basis =
    report.time_basis === "published_at"
      ? "Publisher Publication"
      : "First Seen";
  const sentiments = {
    positive: "Positive",
    negative: "Negative",
    neutral: "Neutral",
    mixed: "Mixed",
  };
  return (
    <div className={styles.analyticsResults}>
      {simulated && <Badge tone="warning">Fictional Demo Analytics</Badge>}
      <section
        className={styles.analyticsPopulation}
        aria-labelledby="analytics-population-heading"
      >
        <h2 id="analytics-population-heading">The Reporting Population</h2>
        <p className={styles.caption}>
          Recorded source documents dated by {basis.toLowerCase()}, within this
          start-inclusive, end-exclusive UTC window and available at the
          returned snapshot.
        </p>
        <dl className={styles.analyticsTimes}>
          <div>
            <dt>Window Start · Inclusive</dt>
            <dd>
              <Timestamp value={report.start} />
            </dd>
          </div>
          <div>
            <dt>Window End · Exclusive</dt>
            <dd>
              <Timestamp value={report.end} />
            </dd>
          </div>
          <div>
            <dt>Snapshot · As Of</dt>
            <dd>
              <Timestamp value={report.as_of} />
            </dd>
          </div>
        </dl>
        <dl className={styles.metrics}>
          <div>
            <dt>Documents in Population</dt>
            <dd>{report.population_count}</dd>
          </div>
          <div>
            <dt>Classified Documents</dt>
            <dd>{report.classified_count}</dd>
          </div>
          <div>
            <dt>No Persisted Document Assessment</dt>
            <dd>{report.no_assessment_count}</dd>
          </div>
        </dl>
        <p className={styles.caption}>
          Outside the dated population: {report.unknown_time_count} otherwise
          eligible documents have an unknown{" "}
          {report.time_basis === "published_at" ? "publication" : "first-seen"}{" "}
          time and are excluded. This count is not part of the population or the
          sentiment denominator.
        </p>
        <p className={styles.caption}>
          Missing persisted document-level assessments do not establish
          abstention, failure, neutrality or lack of entity-specific analysis.
        </p>
        <div className={styles.actions}>
          <Link href={supportingRecordsUrl(report)}>
            Explore Supporting Records
          </Link>
        </div>
      </section>
      <div className={styles.analyticsGrid}>
        <section
          className={styles.section}
          aria-labelledby="analytics-coverage-heading"
        >
          <h2 id="analytics-coverage-heading">Coverage Over Time</h2>
          <p className={styles.caption}>
            Documents in the returned population, grouped by observed UTC day
            using {basis.toLowerCase()} time.
          </p>
          <CoverageChart buckets={report.coverage} />
        </section>
        <section
          className={styles.section}
          aria-labelledby="analytics-sentiment-heading"
        >
          <h2 id="analytics-sentiment-heading">Document Sentiment</h2>
          <p className={styles.caption}>
            Each category uses {report.classified_count} classified source
            documents as its denominator, from {report.population_count}{" "}
            documents in the population.
          </p>
          {report.classified_count ? (
            <Distribution
              label="Sentiment Distribution"
              denominator={report.classified_count}
              values={report.sentiment.map((value) => ({
                name: sentiments[value.label],
                count: value.document_count,
              }))}
            />
          ) : (
            <p role="status" className={styles.caption}>
              No document-level sentiment classifications are supplied for this
              population. Available entity-specific assessments are not
              substituted.
            </p>
          )}
          <p className={styles.caption}>
            Model-reported classifications describe stored assessments, not
            measured public opinion or calibrated factual certainty. Neutral and
            mixed outcomes retain their own categories.
          </p>
        </section>
      </div>
      <div className={styles.analyticsGrid}>
        <section
          className={styles.section}
          aria-labelledby="analytics-source-heading"
        >
          <h2 id="analytics-source-heading">Source Distribution</h2>
          <p className={styles.caption}>
            Coverage counts use all {report.population_count} documents in the
            same population.
          </p>
          <Distribution
            label="Source Coverage Distribution"
            denominator={report.population_count}
            values={[
              ...report.sources.map((source) => ({
                name: source.name,
                count: source.document_count,
              })),
              ...(report.sources_other_count
                ? [{ name: "Other Sources", count: report.sources_other_count }]
                : []),
            ]}
          />
          <p className={styles.caption}>
            Other Sources: {report.sources_other_count} documents from source
            rows outside the returned distribution limit.
          </p>
          <EvidenceDisclosure title="Source IDs & Counts">
            <dl className={styles.analyticsSourceRecords}>
              {report.sources.map((source) => (
                <div key={source.source_id}>
                  <dt>
                    {source.name} · {source.document_count} documents
                  </dt>
                  <dd>
                    <code>{source.source_id}</code>
                  </dd>
                </div>
              ))}
            </dl>
          </EvidenceDisclosure>
        </section>
        <section
          className={styles.section}
          aria-labelledby="analytics-model-heading"
        >
          <h2 id="analytics-model-heading">Model Attribution</h2>
          <p className={styles.caption}>
            Selected document-level sentiment models among{" "}
            {report.classified_count} classified documents.
          </p>
          <Distribution
            label="Selected Model Distribution"
            denominator={report.classified_count}
            values={[
              ...report.models.map((model) => ({
                name: `${model.provider} · ${model.model_name} / ${model.model_version}`,
                count: model.document_count,
              })),
              ...(report.models_other_count
                ? [{ name: "Other Models", count: report.models_other_count }]
                : []),
            ]}
          />
          <p className={styles.caption}>
            Other Models: {report.models_other_count} classified documents from
            model rows outside the returned distribution limit.
          </p>
        </section>
      </div>
      <section
        className={styles.section}
        aria-labelledby="analytics-method-heading"
      >
        <h2 id="analytics-method-heading">Method & Available Evidence</h2>
        <p className={styles.caption}>{report.selection_policy}</p>
        <EvidenceDisclosure title="Population Filters & Limitations">
          <dl className={styles.analyticsSourceRecords}>
            <div>
              <dt>Time Basis</dt>
              <dd>{basis}</dd>
            </div>
            <div>
              <dt>Topic ID</dt>
              <dd>
                {report.topic_id ? (
                  <code>{report.topic_id}</code>
                ) : (
                  "All eligible documents"
                )}
              </dd>
            </div>
            <div>
              <dt>Source ID</dt>
              <dd>
                {report.source_id ? (
                  <code>{report.source_id}</code>
                ) : (
                  "All eligible sources"
                )}
              </dd>
            </div>
          </dl>
          {report.limitations.length ? (
            <ul className={styles.analyticsLimitations}>
              {report.limitations.map((limitation, index) => (
                <li key={index}>{limitation}</li>
              ))}
            </ul>
          ) : (
            <p>No additional limitations are supplied by this response.</p>
          )}
        </EvidenceDisclosure>
      </section>
    </div>
  );
}

function ReportQuery({ filters }: { filters: AnalyticsFilters }) {
  const query = useAnalytics(filters);
  const { mode, adapter } = useConsole();
  if (!adapter.analytics)
    return (
      <p className={styles.caption}>
        Analytics are unavailable through this connection.
      </p>
    );
  return (
    <QueryState
      pending={query.isPending}
      error={query.error}
      retry={query.refetch}
    >
      {query.data && (
        <AnalyticsResults report={query.data} simulated={mode === "mock"} />
      )}
    </QueryState>
  );
}
function utcInput(value?: string) {
  return value && Number.isFinite(Date.parse(value))
    ? new Date(value).toISOString().slice(0, -1)
    : "";
}
function initialParameters(params: URLSearchParams) {
  try {
    const filters = readAnalyticsParameters(params);
    return { filters, error: validateAnalyticsFilters(filters) };
  } catch (error) {
    const corrected = new URLSearchParams(params);
    corrected.delete("time_basis");
    return {
      filters: readAnalyticsParameters(corrected),
      error:
        error instanceof Error ? error.message : "Invalid analytics filters.",
    };
  }
}

function AnalyticsWorkspace({ params }: { params: URLSearchParams }) {
  const [initial] = useState(() => initialParameters(params));
  const [draft, setDraft] = useState(initial.filters);
  const [error, setError] = useState(initial.error);
  const topics = useTopics({ cutoff: initial.filters.cutoff });
  const { adapter } = useConsole();
  const router = useRouter();
  const change = <K extends keyof AnalyticsFilters>(
    key: K,
    value: AnalyticsFilters[K],
  ) => setDraft((current) => ({ ...current, [key]: value }));
  return (
    <div className={`${styles.page} ${styles.analyticsPage}`}>
      <PageHeading
        eyebrow="News & Intelligence"
        title="Intelligence Analytics"
        description="Read the coverage. Inspect the population behind every count."
      />
      <p className={styles.caption}>
        Recorded coverage and stored model assessments, with the date window,
        selection policy and supporting records kept together.
      </p>
      <form
        className={`${styles.filters} ${styles.analyticsFilters}`}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          const message = validateAnalyticsFilters(draft);
          setError(message);
          if (!message) router.push(`/analytics?${analyticsParameters(draft)}`);
        }}
      >
        <label htmlFor="analytics-start">
          Window Start (Inclusive, UTC)
          <input
            id="analytics-start"
            type="datetime-local"
            step="0.001"
            value={utcInput(draft.start)}
            onChange={(event) =>
              change(
                "start",
                event.target.value ? `${event.target.value}Z` : "",
              )
            }
          />
        </label>
        <label htmlFor="analytics-end">
          Window End (Exclusive, UTC)
          <input
            id="analytics-end"
            type="datetime-local"
            step="0.001"
            value={utcInput(draft.end)}
            onChange={(event) =>
              change("end", event.target.value ? `${event.target.value}Z` : "")
            }
          />
        </label>
        <div className={styles.analyticsControl}>
          <label htmlFor="analytics-basis">Time Basis</label>
          <select
            id="analytics-basis"
            value={draft.timeBasis}
            onChange={(event) =>
              change(
                "timeBasis",
                event.target.value as AnalyticsFilters["timeBasis"],
              )
            }
          >
            <option value="published_at">Publication</option>
            <option value="first_seen_at">First Seen</option>
          </select>
        </div>
        <label htmlFor="analytics-source">
          Source ID (Optional)
          <input
            id="analytics-source"
            value={draft.sourceId ?? ""}
            placeholder="All eligible sources"
            onChange={(event) =>
              change("sourceId", event.target.value || undefined)
            }
          />
        </label>
        <label htmlFor="analytics-cutoff">
          As Of (UTC, Optional)
          <input
            id="analytics-cutoff"
            type="datetime-local"
            step="0.001"
            value={utcInput(draft.cutoff)}
            onChange={(event) =>
              change(
                "cutoff",
                event.target.value ? `${event.target.value}Z` : undefined,
              )
            }
          />
        </label>
        <div className={styles.analyticsTopicControl}>
          <AnalyticsTopicSelector
            topics={topics.data?.data ?? []}
            selected={draft.topicId}
            onSelect={(id) => change("topicId", id || undefined)}
          />
          <p className={styles.caption}>
            Choices come from one bounded topic page at the requested cutoff,
            not a global taxonomy. A topic absent from this page retains its
            exact selected ID.
          </p>
          {adapter.topics ? (
            <QueryState
              pending={topics.isPending}
              error={topics.error}
              retry={topics.refetch}
            >
              <span className={styles.caption}>
                {topics.data?.data.length ?? 0} topic choices supplied
                {topics.data?.pagination.next_cursor
                  ? "; more topics exist in the Topic Directory."
                  : "."}
              </span>
            </QueryState>
          ) : (
            <p className={styles.caption}>
              Topic choices are unavailable through this connection.
            </p>
          )}
        </div>
        <div className={styles.analyticsApply}>
          <Button type="submit">Apply Window</Button>
          <p className={styles.caption}>
            UTC only · Maximum interval: 366 days. Changes apply after
            submission.
          </p>
        </div>
        {error && (
          <p role="alert" className={styles.analyticsValidation}>
            {error}
          </p>
        )}
      </form>
      {!initial.error && <ReportQuery filters={initial.filters} />}
    </div>
  );
}

export function AnalyticsPage() {
  const params = useSearchParams();
  return (
    <AnalyticsWorkspace
      key={params.toString()}
      params={new URLSearchParams(params.toString())}
    />
  );
}
