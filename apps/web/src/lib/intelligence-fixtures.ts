import type { components } from "./generated/api";
import type {
  AnalyticsFilters,
  DiscoveryFilters,
  TopicFilters,
} from "./models";
import { documents } from "./fixtures";
type Api = components["schemas"];
const policy =
  "Latest available topic analysis per document and exact provider/model/version/configuration; exact labels, unique documents and maximum matching confidence. Simulated fixture records.";
const model = (analysis: Api["AnalysisResult"]): Api["ModelIdentity"] => ({
  provider: analysis.provider,
  model_name: analysis.model_name,
  model_version: analysis.model_version,
  configuration_hash: analysis.configuration_hash,
});
const pack = (value: unknown) =>
  btoa(
    Array.from(new TextEncoder().encode(JSON.stringify(value)), (byte) =>
      String.fromCharCode(byte),
    ).join(""),
  )
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
export const fixtureTopicId = (label: string, identity: Api["ModelIdentity"]) =>
  `topic_v1_${pack([label, identity.provider, identity.model_name, identity.model_version, identity.configuration_hash])}`;
const eligible = (cutoff: string, views = documents) =>
  views.filter(
    (view) => Date.parse(view.document.created_at) <= Date.parse(cutoff),
  );
const aware = (value: string) =>
  /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value));
function validateWindow(start?: string, end?: string) {
  if (!!start !== !!end) throw new Error("Supply both window start and end.");
  if (
    start &&
    end &&
    (!aware(start) ||
      !aware(end) ||
      Date.parse(end) <= Date.parse(start) ||
      Date.parse(end) - Date.parse(start) > 366 * 86400000)
  )
    throw new Error(
      "Choose timezone-aware start and end within an interval of at most 366 days.",
    );
}
const instant = (cutoff?: string, cursor?: string) => {
  let value = cutoff ?? new Date().toISOString();
  if (cursor) {
    try {
      if (cursor.length > 32768) throw new Error();
      const stored = JSON.parse(
        atob(cursor.replaceAll("-", "+").replaceAll("_", "/")),
      );
      if (typeof stored.asOf !== "string") throw new Error();
      value = stored.asOf;
    } catch {
      throw new Error("Invalid mock cursor.");
    }
  }
  if (!aware(value)) throw new Error("Enter a valid cutoff.");
  return value;
};
const meta = {
  api_version: "v1" as const,
  request_id: "simulated-intelligence",
};
function page<T>(
  values: T[],
  filters: TopicFilters,
  asOf: string,
  fingerprint: unknown,
) {
  let offset = 0;
  if (filters.cursor) {
    try {
      const stored = JSON.parse(
        atob(filters.cursor.replaceAll("-", "+").replaceAll("_", "/")),
      );
      if (
        stored.filter !== JSON.stringify(fingerprint) ||
        !Number.isInteger(stored.offset) ||
        stored.offset < 0 ||
        (filters.cutoff &&
          Date.parse(stored.asOf) !== Date.parse(filters.cutoff))
      )
        throw new Error();
      asOf = stored.asOf;
      offset = stored.offset;
    } catch {
      throw new Error("Invalid mock cursor or changed filters.");
    }
  }
  const more = offset + 20 < values.length;
  return {
    data: structuredClone(values.slice(offset, offset + 20)),
    as_of: asOf,
    meta,
    pagination: {
      has_more: more,
      next_cursor: more
        ? pack({
            offset: offset + 20,
            asOf,
            filter: JSON.stringify(fingerprint),
          })
        : null,
    },
  };
}
export function fixtureMemberships(
  cutoff: string,
  views = documents,
): Map<string, Api["TopicMembership"][]> {
  const result = new Map<string, Api["TopicMembership"][]>();
  for (const view of eligible(cutoff, views)) {
    const latest = new Map<string, Api["AnalysisResult"]>();
    for (const analysis of view.analyses) {
      if (
        analysis.analysis_type !== "topic" ||
        Date.parse(analysis.available_at) > Date.parse(cutoff)
      )
        continue;
      const identity = JSON.stringify(model(analysis)),
        before = latest.get(identity);
      if (
        !before ||
        Date.parse(analysis.available_at) > Date.parse(before.available_at) ||
        (Date.parse(analysis.available_at) ===
          Date.parse(before.available_at) &&
          analysis.analysis_id > before.analysis_id)
      )
        latest.set(identity, analysis);
    }
    for (const analysis of latest.values()) {
      const matching = new Map<string, number>();
      for (const output of analysis.outputs)
        if (output.result_type === "topic")
          matching.set(
            output.label,
            Math.max(matching.get(output.label) ?? 0, output.confidence),
          );
      for (const [label, confidence] of matching) {
        const key = fixtureTopicId(label, model(analysis));
        const rows = result.get(key) ?? [];
        rows.push({
          document: view.document,
          source: view.source,
          analysis_id: analysis.analysis_id,
          available_at: analysis.available_at,
          confidence,
          model: model(analysis),
        });
        result.set(key, rows);
      }
    }
  }
  return result;
}
export function fixtureTopics(
  filters: TopicFilters,
  views = documents,
): Api["SnapshotCollectionResponse_TopicSummary_"] {
  const cutoff = instant(filters.cutoff, filters.cursor);
  const values = [...fixtureMemberships(cutoff, views)]
    .map(([topic_id, members]) => {
      const label = JSON.parse(
        new TextDecoder().decode(
          Uint8Array.from(
            atob(topic_id.slice(9).replaceAll("-", "+").replaceAll("_", "/")),
            (c) => c.charCodeAt(0),
          ),
        ),
      )[0] as string;
      const times = members
        .map((member) => member.available_at)
        .sort((a, b) => Date.parse(a) - Date.parse(b));
      return {
        topic_id,
        label,
        model: members[0].model,
        document_count: members.length,
        first_available_at: times[0],
        latest_available_at: times.at(-1)!,
        as_of: cutoff,
        selection_policy: policy,
      };
    })
    .filter(
      (topic) =>
        !filters.query ||
        topic.label.toLowerCase().includes(filters.query.toLowerCase()),
    )
    .sort(
      (a, b) =>
        a.label.localeCompare(b.label) || a.topic_id.localeCompare(b.topic_id),
    );
  return page(values, filters, cutoff, {
    kind: "topics",
    query: filters.query ?? "",
  });
}
function chronological<T extends { document: Api["NewsDocument"] }>(
  values: T[],
  order: "published_at" | "first_seen_at",
) {
  return values.sort((a, b) => {
    const left = a.document[order],
      right = b.document[order];
    return (
      (left && right
        ? Date.parse(right) - Date.parse(left)
        : left
          ? -1
          : right
            ? 1
            : 0) || a.document.document_id.localeCompare(b.document.document_id)
    );
  });
}
export function fixtureTopicDocuments(
  id: string,
  filters: TopicFilters,
): Api["SnapshotCollectionResponse_TopicMembership_"] {
  const cutoff = instant(filters.cutoff, filters.cursor);
  return page(
    chronological(fixtureMemberships(cutoff).get(id) ?? [], "published_at"),
    filters,
    cutoff,
    { kind: "members", id },
  );
}
export function fixtureDiscovery(
  filters: DiscoveryFilters,
): Api["SnapshotCollectionResponse_DocumentDiscoveryItem_"] {
  validateWindow(filters.start, filters.end);
  const cutoff = instant(filters.cutoff, filters.cursor),
    membership = filters.topicId
      ? new Set(
          (fixtureMemberships(cutoff).get(filters.topicId) ?? []).map(
            (member) => member.document.document_id,
          ),
        )
      : undefined;
  const values = eligible(cutoff)
    .filter(
      (view) =>
        (!membership || membership.has(view.document.document_id)) &&
        (!filters.sourceId || view.source.source_id === filters.sourceId) &&
        (!filters.query ||
          `${view.document.title} ${view.document.text}`
            .toLowerCase()
            .includes(filters.query.toLowerCase())) &&
        (!filters.start ||
          !filters.end ||
          (view.document[filters.timeBasis ?? "first_seen_at"] != null &&
            Date.parse(view.document[filters.timeBasis ?? "first_seen_at"]!) >=
              Date.parse(filters.start) &&
            Date.parse(view.document[filters.timeBasis ?? "first_seen_at"]!) <
              Date.parse(filters.end))),
    )
    .map(({ document, source }) => ({ document, source }));
  return page(
    chronological(values, filters.order ?? "published_at"),
    filters,
    cutoff,
    { ...filters, cursor: undefined, cutoff: undefined },
  );
}
export function fixtureAnalytics(
  filters: AnalyticsFilters,
): Api["AnalyticsReport"] {
  validateWindow(filters.start, filters.end);
  const cutoff = instant(filters.cutoff),
    basis = filters.timeBasis ?? "first_seen_at",
    start = Date.parse(filters.start),
    end = Date.parse(filters.end);
  if (
    !Number.isFinite(start) ||
    !Number.isFinite(end) ||
    end <= start ||
    end - start > 366 * 86400000
  )
    throw new Error("Choose an interval of at most 366 days.");
  const topic = filters.topicId
    ? new Set(
        (fixtureMemberships(cutoff).get(filters.topicId) ?? []).map(
          (member) => member.document.document_id,
        ),
      )
    : undefined;
  const candidates = eligible(cutoff).filter(
    (view) =>
      (!topic || topic.has(view.document.document_id)) &&
      (!filters.sourceId || view.source.source_id === filters.sourceId),
  );
  const population = candidates.filter(
    (view) =>
      view.document[basis] &&
      Date.parse(view.document[basis]!) >= start &&
      Date.parse(view.document[basis]!) < end,
  );
  const coverage = new Map<string, Api["CoverageBucket"]>(),
    sources = new Map<string, Api["SourceDistribution"]>(),
    sentiment = new Map<string, Api["SentimentDistribution"]>(),
    models = new Map<string, Api["ModelDistribution"]>();
  let classified = 0;
  for (const view of population) {
    const day = new Date(view.document[basis]!).toISOString().slice(0, 10),
      bucket = coverage.get(day) ?? {
        day,
        document_count: 0,
        classified_count: 0,
      };
    bucket.document_count++;
    coverage.set(day, bucket);
    const source = sources.get(view.source.source_id) ?? {
      source_id: view.source.source_id,
      name: view.source.name,
      document_count: 0,
    };
    source.document_count++;
    sources.set(source.source_id, source);
    const analysis = view.analyses
      .filter(
        (a) =>
          a.analysis_type === "sentiment" &&
          Date.parse(a.available_at) <= Date.parse(cutoff) &&
          a.outputs.some((o) => o.result_type === "sentiment" && !o.entity_id),
      )
      .sort(
        (a, b) =>
          Date.parse(b.available_at) - Date.parse(a.available_at) ||
          b.analysis_id.localeCompare(a.analysis_id),
      )[0];
    const output = analysis?.outputs.find(
      (o) => o.result_type === "sentiment" && !o.entity_id,
    );
    if (output?.result_type === "sentiment" && analysis) {
      classified++;
      bucket.classified_count++;
      const distribution = sentiment.get(output.label) ?? {
        label: output.label,
        document_count: 0,
      };
      distribution.document_count++;
      sentiment.set(output.label, distribution);
      const key = JSON.stringify([
        analysis.provider,
        analysis.model_name,
        analysis.model_version,
      ]);
      const family = models.get(key) ?? {
        provider: analysis.provider,
        model_name: analysis.model_name,
        model_version: analysis.model_version,
        document_count: 0,
      };
      family.document_count++;
      models.set(key, family);
    }
  }
  return {
    start: filters.start,
    end: filters.end,
    as_of: cutoff,
    time_basis: basis,
    topic_id: filters.topicId ?? null,
    source_id: filters.sourceId ?? null,
    population_count: population.length,
    classified_count: classified,
    no_assessment_count: population.length - classified,
    unknown_time_count: candidates.filter((view) => !view.document[basis])
      .length,
    coverage: [...coverage.values()].sort((a, b) => a.day.localeCompare(b.day)),
    sources: [...sources.values()],
    sources_other_count: 0,
    sentiment: [...sentiment.values()],
    models: [...models.values()],
    models_other_count: 0,
    selection_policy:
      "Simulated fixture population; latest available document-level sentiment per document, entity-specific assessments excluded.",
    limitations: [
      "Fictional mock records; no measured public opinion.",
      "Missing persisted assessments do not identify abstention or inference failure.",
      "Mutable source/entity metadata is not a historical snapshot.",
    ],
  };
}
