// Generated from checked-in schemas. Run pnpm api:generate; do not edit.
export type paths = Record<string, never>;
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** EmbeddingResult */
        EmbeddingResult: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            result_type: "embedding";
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Values */
            values: number[];
        };
        /** EntityExtractionResult */
        EntityExtractionResult: {
            /** Confidence */
            confidence: number;
            /** End Offset */
            end_offset: number;
            /**
             * Predicted Kind
             * @default null
             */
            predicted_kind: ("organization" | "person" | "location" | "other") | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            result_type: "entity_extraction";
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Start Offset */
            start_offset: number;
            /** Surface */
            surface: string;
        };
        /** EntityResolutionResult */
        EntityResolutionResult: {
            /** Confidence */
            confidence: number;
            /** Entity Id */
            entity_id: string | null;
            /** Mention Id */
            mention_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            result_type: "entity_resolution";
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
        };
        /** EventClassificationResult */
        EventClassificationResult: {
            /** Confidence */
            confidence: number;
            /** Event Id */
            event_id: string;
            /** Event Revision */
            event_revision: number;
            /** Label */
            label: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            result_type: "event_classification";
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
        };
        /** EventExtractionResult */
        EventExtractionResult: {
            /** Confidence */
            confidence: number;
            /** Document Id */
            document_id: string;
            /** Evidence Text */
            evidence_text: string;
            /**
             * Occurred At
             * @default null
             */
            occurred_at: string | null;
            /** Proposed Event Type */
            proposed_event_type: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            result_type: "event_extraction";
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
        };
        /** SentimentResult */
        SentimentResult: {
            /** Confidence */
            confidence: number;
            /**
             * Entity Id
             * @default null
             */
            entity_id: string | null;
            /**
             * Label
             * @enum {string}
             */
            label: "positive" | "neutral" | "negative" | "mixed";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            result_type: "sentiment";
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Score */
            score: number;
        };
        /** TopicResult */
        TopicResult: {
            /** Confidence */
            confidence: number;
            /** Label */
            label: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            result_type: "topic";
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
        };
        /** AnalysisResult */
        AnalysisResult: {
            /** Analysis Id */
            analysis_id: string;
            /**
             * Analysis Type
             * @enum {string}
             */
            analysis_type: "topic" | "sentiment" | "entity_extraction" | "entity_resolution" | "embedding" | "event_extraction" | "event_classification";
            /**
             * Available At
             * Format: date-time
             */
            available_at: string;
            /** Configuration Hash */
            configuration_hash: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Document Id */
            document_id: string;
            /** Model Name */
            model_name: string;
            /** Model Version */
            model_version: string;
            /** Outputs */
            outputs: (components["schemas"]["TopicResult"] | components["schemas"]["SentimentResult"] | components["schemas"]["EntityExtractionResult"] | components["schemas"]["EntityResolutionResult"] | components["schemas"]["EmbeddingResult"] | components["schemas"]["EventExtractionResult"] | components["schemas"]["EventClassificationResult"])[];
            /** Provider */
            provider: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
        };
        /** AssetMapping */
        AssetMapping: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Entity Id */
            entity_id: string;
            /** Identifier */
            identifier: string;
            /** Mapping Id */
            mapping_id: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /**
             * Scheme
             * @enum {string}
             */
            scheme: "exchange_symbol" | "isin" | "provider_id";
            /**
             * Venue
             * @default null
             */
            venue: string | null;
        };
        /** DocumentMediaLink */
        DocumentMediaLink: {
            /** Document Id */
            document_id: string;
            /** Media Id */
            media_id: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
        };
        /** Entity */
        Entity: {
            /** Canonical Name */
            canonical_name: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Entity Id */
            entity_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "organization" | "person" | "location" | "other";
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
        };
        /** EntityMention */
        EntityMention: {
            /**
             * Analysis Id
             * @default null
             */
            analysis_id: string | null;
            /** Document Id */
            document_id: string;
            /** End Offset */
            end_offset: number;
            /**
             * Entity Id
             * @default null
             */
            entity_id: string | null;
            /**
             * Evidence Kind
             * @enum {string}
             */
            evidence_kind: "fact" | "model_output";
            /** Mention Id */
            mention_id: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Start Offset */
            start_offset: number;
            /** Surface */
            surface: string;
        };
        /** ObjectReference */
        ObjectReference: {
            /** Bucket */
            bucket: string;
            /** Content Type */
            content_type: string;
            /** Key */
            key: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Sha256 */
            sha256: string;
            /** Size Bytes */
            size_bytes: number;
        };
        /** MediaAsset */
        MediaAsset: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Ingestion Id */
            ingestion_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "image" | "audio" | "video" | "attachment";
            /** Media Id */
            media_id: string;
            object: components["schemas"]["ObjectReference"];
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
        };
        /** NewsDocument */
        NewsDocument: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Document Id */
            document_id: string;
            /**
             * First Seen At
             * Format: date-time
             */
            first_seen_at: string;
            /**
             * Ingested At
             * Format: date-time
             */
            ingested_at: string;
            /** Ingestion Id */
            ingestion_id: string;
            /**
             * Language
             * @default null
             */
            language: string | null;
            /**
             * Published At
             * @default null
             */
            published_at: string | null;
            /**
             * Revision
             * @default 1
             */
            revision: number;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Source Id */
            source_id: string;
            /** Text */
            text: string;
            /** Title */
            title: string;
        };
        /** NewsEvent */
        NewsEvent: {
            /**
             * Analysis Id
             * @default null
             */
            analysis_id: string | null;
            /**
             * Available At
             * Format: date-time
             */
            available_at: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Document Ids */
            document_ids: string[];
            /**
             * Entity Ids
             * @default []
             */
            entity_ids: string[];
            /** Event Id */
            event_id: string;
            /**
             * Evidence Kind
             * @enum {string}
             */
            evidence_kind: "fact" | "model_output";
            /**
             * Occurred At
             * @default null
             */
            occurred_at: string | null;
            /**
             * Revision
             * @default 1
             */
            revision: number;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Summary */
            summary: string;
        };
        /** ProvenanceRecord */
        ProvenanceRecord: {
            /**
             * Analysis Id
             * @default null
             */
            analysis_id: string | null;
            /** Content Hash */
            content_hash: string;
            /** Input Ids */
            input_ids: string[];
            /** Operation */
            operation: string;
            /** Provenance Id */
            provenance_id: string;
            /**
             * Recorded At
             * Format: date-time
             */
            recorded_at: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Subject Id */
            subject_id: string;
        };
        /** RawIngestion */
        RawIngestion: {
            /**
             * First Seen At
             * Format: date-time
             */
            first_seen_at: string;
            /** Idempotency Key */
            idempotency_key: string;
            /**
             * Ingested At
             * Format: date-time
             */
            ingested_at: string;
            /** Ingestion Id */
            ingestion_id: string;
            object: components["schemas"]["ObjectReference"];
            /**
             * Published At
             * @default null
             */
            published_at: string | null;
            /** Raw Object Id */
            raw_object_id: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Source Id */
            source_id: string;
            /**
             * Source Url
             * @default null
             */
            source_url: string | null;
        };
        /** Source */
        Source: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "feed" | "api" | "upload" | "web";
            /** Name */
            name: string;
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: "1";
            /** Source Id */
            source_id: string;
            /**
             * Url
             * @default null
             */
            url: string | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export type operations = Record<string, never>;
