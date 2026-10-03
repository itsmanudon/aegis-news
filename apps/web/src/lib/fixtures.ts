import type { AuditEntry, DocumentView, Domain } from "./models";
const id = (prefix: string, n: number) =>
  `${prefix}_00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const at = (minute: number) =>
  `2026-10-03T08:${String(minute).padStart(2, "0")}:00Z`;
export const sources: Domain["Source"][] = [
  {
    source_id: id("src", 1),
    name: "Maritime Operations Bulletin",
    kind: "feed",
    url: "https://example.test/maritime",
    created_at: at(0),
    schema_version: "1",
  },
  {
    source_id: id("src", 2),
    name: "National Cyber Response Centre",
    kind: "web",
    url: "https://example.test/cyber",
    created_at: at(0),
    schema_version: "1",
  },
  {
    source_id: id("src", 3),
    name: "Field Evidence Desk",
    kind: "upload",
    url: null,
    created_at: at(0),
    schema_version: "1",
  },
];
export const entities: Domain["Entity"][] = [
  {
    entity_id: id("ent", 1),
    canonical_name: "Port Meridian",
    kind: "location",
    created_at: at(7),
    schema_version: "1",
  },
  {
    entity_id: id("ent", 2),
    canonical_name: "Northstar Logistics",
    kind: "organization",
    created_at: at(15),
    schema_version: "1",
  },
  {
    entity_id: id("ent", 3),
    canonical_name: "National Cyber Response Centre",
    kind: "organization",
    created_at: at(20),
    schema_version: "1",
  },
];
const headlines = [
  "Port Meridian reports disruption to cargo scheduling",
  "Northstar Logistics issues advisory on credential exposure",
  "Field report describes communications outage near eastern corridor",
  "Cyber response centre publishes revised incident guidance",
  "Port authority confirms restoration of scheduling services",
  "Northstar Logistics begins independent incident review",
];
const bodies = [
  "Port Meridian reported disruption to its cargo scheduling service at 08:00 UTC. The authority said manual procedures remain available. No cause has been confirmed.\n\nThe bulletin asks operators to retain scheduling receipts and consult official updates before changing arrival plans.",
  "Northstar Logistics issued an advisory after discovering exposed service credentials. The company said it revoked the credentials and is reviewing access logs. The scope of access remains under investigation.\n\nThis fixture represents a source statement, not an independently confirmed incident.",
  "An uploaded field report describes an intermittent communications outage near the eastern corridor. Its author and original publication time have not been independently established.\n\nTreat this account as unverified evidence pending source validation.",
  "The National Cyber Response Centre published revised guidance on preserving incident evidence. The update recommends recording acquisition time separately from publication time.",
  "Port Meridian confirmed that cargo scheduling services were restored. The authority is continuing to assess the original interruption and has not attributed a cause.",
  "Northstar Logistics announced an independent review of its recent credential exposure. The company has not published final findings.",
];
export const documents: DocumentView[] = headlines.map((title, i) => {
  const documentId = id("doc", i + 1),
    source = sources[[0, 1, 2, 1, 0, 1][i]],
    minute = i * 7;
  const available = at(minute + 7),
    entity = entities[[0, 1, 0, 2, 0, 1][i]];
  const base = {
    document_id: documentId,
    provider: "fixture-provider",
    model_name: "aegis-topic-demo",
    model_version: "0.3.1",
    configuration_hash: "b".repeat(64),
    created_at: at(minute + 5),
    available_at: available,
    schema_version: "1" as const,
  };
  const analyses: Domain["AnalysisResult"][] = [
    {
      ...base,
      analysis_id: id("ana", i * 2 + 1),
      analysis_type: "topic",
      outputs: [
        {
          result_type: "topic",
          label: i % 2 === 0 ? "Infrastructure disruption" : "Cybersecurity",
          confidence: 0.89 - i * 0.03,
          schema_version: "1",
        },
      ],
    },
    {
      ...base,
      analysis_id: id("ana", i * 2 + 2),
      model_name: "aegis-sentiment-demo",
      analysis_type: "sentiment",
      outputs: [
        {
          result_type: "sentiment",
          label: i === 4 ? "positive" : "negative",
          score: i === 4 ? 0.42 : -0.61,
          confidence: 0.78,
          entity_id: entity.entity_id,
          schema_version: "1",
        },
      ],
    },
  ];
  if (i === 2)
    analyses[0] = {
      ...analyses[0],
      analysis_type: "event_extraction",
      model_name: "aegis-event-demo",
      outputs: [
        {
          result_type: "event_extraction",
          proposed_event_type: "Communications outage",
          confidence: 0.64,
          document_id: documentId,
          evidence_text:
            "An uploaded field report describes an intermittent communications outage near the eastern corridor.",
          occurred_at: null,
          schema_version: "1",
        },
      ],
    };
  return {
    document: {
      document_id: documentId,
      ingestion_id: id("ing", i + 1),
      source_id: source.source_id,
      title,
      text: bodies[i],
      language: "en",
      revision: 1,
      schema_version: "1",
      published_at: i === 2 ? null : at(minute),
      first_seen_at: at(minute + 2),
      ingested_at: at(minute + 3),
      created_at: at(minute + 3),
    },
    source,
    analyses,
    entities: [entity],
    events: [
      {
        event_id: id("evt", i + 1),
        summary:
          i === 0 ? "Scheduling disruption reported at Port Meridian" : title,
        document_ids: [documentId],
        entity_ids: [entity.entity_id],
        evidence_kind: i === 2 ? "model_output" : "fact",
        analysis_id: i === 2 ? analyses[0].analysis_id : null,
        occurred_at: i === 2 ? null : at(minute),
        created_at: at(minute + 6),
        available_at: available,
        schema_version: "1",
        revision: 1,
      },
    ],
    media:
      i === 2
        ? [
            {
              media_id: id("media", 1),
              ingestion_id: id("ing", i + 1),
              kind: "attachment",
              created_at: at(minute + 3),
              schema_version: "1",
              object: {
                bucket: "fixture-evidence",
                key: "corridor-report.txt",
                sha256: "c".repeat(64),
                size_bytes: 2048,
                content_type: "text/plain",
                schema_version: "1",
              },
            },
          ]
        : [],
    integrity: i === 1 ? "failed" : i === 2 ? "unverified" : "verified",
    provenance: ["acquire", "normalize", "analyze"].map((operation, j) => ({
      provenance_id: id("prov", i * 3 + j + 1),
      subject_id: documentId,
      input_ids: [j === 0 ? id("ing", i + 1) : documentId],
      operation,
      recorded_at: at(minute + 3 + j * 2),
      content_hash: "a".repeat(64),
      analysis_id: j === 2 ? analyses[0].analysis_id : null,
      schema_version: "1",
    })),
  };
});
export const audit: AuditEntry[] = [
  {
    id: "audit-1",
    at: at(49),
    action: "Document viewed",
    actor: "Demo analyst",
    outcome: "allowed",
    subject: documents[0].document.document_id,
  },
  {
    id: "audit-2",
    at: at(48),
    action: "Signature check failed",
    actor: "Fixture verifier",
    outcome: "warning",
    subject: documents[1].document.document_id,
  },
  {
    id: "audit-3",
    at: at(46),
    action: "Source configuration requested",
    actor: "Demo analyst",
    outcome: "denied",
    subject: sources[0].source_id,
  },
];
