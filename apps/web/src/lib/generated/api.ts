// Generated from checked-in schemas. Run pnpm api:generate; do not edit.
export interface paths {
    "/api/v1/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Analytics */
        get: operations["analytics_api_v1_analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/discovery": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Discovery */
        get: operations["discovery_api_v1_discovery_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Documents */
        get: operations["documents_api_v1_documents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{document_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Document */
        get: operations["get_document_api_v1_documents__document_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{document_id}/acquisition": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Acquisition */
        get: operations["acquisition_api_v1_documents__document_id__acquisition_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{document_id}/intelligence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Intelligence */
        get: operations["intelligence_api_v1_documents__document_id__intelligence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{document_id}/similar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Similar */
        get: operations["similar_api_v1_documents__document_id__similar_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{document_id}/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Verify */
        post: operations["verify_api_v1_documents__document_id__verify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/entities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Entities */
        get: operations["entities_api_v1_entities_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/entities/{entity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Entity */
        get: operations["entity_api_v1_entities__entity_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/entities/{entity_id}/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Entity Documents */
        get: operations["entity_documents_api_v1_entities__entity_id__documents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Events */
        get: operations["events_api_v1_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/{event_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Event */
        get: operations["event_api_v1_events__event_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ingestion-runs/{workflow_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Run */
        get: operations["get_run_api_v1_ingestion_runs__workflow_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ingestions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit */
        post: operations["submit_api_v1_ingestions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ingestions/batch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit Batch */
        post: operations["submit_batch_api_v1_ingestions_batch_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ingestions/{ingestion_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Ingestion */
        get: operations["get_ingestion_api_v1_ingestions__ingestion_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/provider-articles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Article List */
        get: operations["article_list_api_v1_provider_articles_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/provider-runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Run */
        get: operations["get_run_api_v1_provider_runs__run_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/providers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Providers */
        get: operations["providers_api_v1_providers_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/providers/fetch-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Fetch All */
        post: operations["fetch_all_api_v1_providers_fetch_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/providers/{provider}/fetch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Fetch */
        post: operations["fetch_api_v1_providers__provider__fetch_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Documents */
        get: operations["documents_api_v1_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/security/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Audit Events */
        get: operations["audit_events_api_v1_security_audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/security/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_v1_security_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/security/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Verify */
        post: operations["verify_api_v1_security_verify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sources */
        get: operations["sources_api_v1_sources_get"];
        put?: never;
        /** Create Source */
        post: operations["create_source_api_v1_sources_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources/{source_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Source */
        get: operations["get_source_api_v1_sources__source_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/info": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** System Info */
        get: operations["system_info_api_v1_system_info_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/topics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topics */
        get: operations["topics_api_v1_topics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/topics/{topic_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topic */
        get: operations["topic_api_v1_topics__topic_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/topics/{topic_id}/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Topic Documents */
        get: operations["topic_documents_api_v1_topics__topic_id__documents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/youtube-references": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Video List */
        get: operations["video_list_api_v1_youtube_references_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/youtube-references/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh */
        post: operations["refresh_api_v1_youtube_references_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/youtube-references/{video_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Video */
        delete: operations["delete_video_api_v1_youtube_references__video_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ready */
        get: operations["ready_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
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
        /** AnalyticsReport */
        AnalyticsReport: {
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            /** Classified Count */
            classified_count: number;
            /** Coverage */
            coverage: components["schemas"]["CoverageBucket"][];
            /**
             * End
             * Format: date-time
             */
            end: string;
            /** Limitations */
            limitations: string[];
            /** Models */
            models: components["schemas"]["ModelDistribution"][];
            /** Models Other Count */
            models_other_count: number;
            /** No Assessment Count */
            no_assessment_count: number;
            /** Population Count */
            population_count: number;
            /** Selection Policy */
            selection_policy: string;
            /** Sentiment */
            sentiment: components["schemas"]["SentimentDistribution"][];
            /** Source Id */
            source_id?: string | null;
            /** Sources */
            sources: components["schemas"]["SourceDistribution"][];
            /** Sources Other Count */
            sources_other_count: number;
            /**
             * Start
             * Format: date-time
             */
            start: string;
            /**
             * Time Basis
             * @enum {string}
             */
            time_basis: "published_at" | "first_seen_at";
            /** Topic Id */
            topic_id?: string | null;
            /** Unknown Time Count */
            unknown_time_count: number;
        };
        /** ApiErrorEnvelope */
        ApiErrorEnvelope: {
            error: components["schemas"]["ErrorDetail"];
        };
        /** ArticleEvidence */
        ArticleEvidence: {
            /**
             * Acquired At
             * Format: date-time
             */
            acquired_at: string;
            /** Article Url */
            article_url?: string | null;
            /** Author */
            author?: string | null;
            /**
             * Content Kind
             * @enum {string}
             */
            content_kind: "provider excerpt" | "headline only";
            /** Image Url */
            image_url?: string | null;
            /**
             * Provider
             * @enum {string}
             */
            provider: "newsdata" | "gnews" | "newsapi" | "gdelt" | "youtube";
            /** Provider Item Id */
            provider_item_id?: string | null;
            /** Publisher Name */
            publisher_name?: string | null;
            /** Video Url */
            video_url?: string | null;
        };
        /** AuditEvent */
        AuditEvent: {
            /** Action */
            action: string;
            /** Actor Hash */
            actor_hash?: string | null;
            /** Event Id */
            event_id: string;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /**
             * Outcome
             * @default attempt
             */
            outcome: string;
            /**
             * Request Id
             * @default
             */
            request_id: string;
            /** Subject Hash */
            subject_hash?: string | null;
        };
        /** BatchRequest */
        BatchRequest: {
            /** Items */
            items: components["schemas"]["IngestionRequest"][];
        };
        /** CollectionResponse[AuditEvent] */
        CollectionResponse_AuditEvent_: {
            /** Data */
            data: components["schemas"]["AuditEvent"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** CollectionResponse[Entity] */
        CollectionResponse_Entity_: {
            /** Data */
            data: components["schemas"]["Entity"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** CollectionResponse[NewsDocument] */
        CollectionResponse_NewsDocument_: {
            /** Data */
            data: components["schemas"]["NewsDocument"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** CollectionResponse[NewsEvent] */
        CollectionResponse_NewsEvent_: {
            /** Data */
            data: components["schemas"]["NewsEvent"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** CollectionResponse[ProviderArticleView] */
        CollectionResponse_ProviderArticleView_: {
            /** Data */
            data: components["schemas"]["ProviderArticleView"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** CollectionResponse[SimilarDocument] */
        CollectionResponse_SimilarDocument_: {
            /** Data */
            data: components["schemas"]["SimilarDocument"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** CollectionResponse[Source] */
        CollectionResponse_Source_: {
            /** Data */
            data: components["schemas"]["Source"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** CollectionResponse[YouTubeReference] */
        CollectionResponse_YouTubeReference_: {
            /** Data */
            data: components["schemas"]["YouTubeReference"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** CoverageBucket */
        CoverageBucket: {
            /** Classified Count */
            classified_count: number;
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Document Count */
            document_count: number;
        };
        /** CursorPagination */
        CursorPagination: {
            /**
             * Has More
             * @default false
             */
            has_more: boolean;
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** DependencyStatus */
        DependencyStatus: {
            /**
             * Name
             * @enum {string}
             */
            name: "postgres" | "redis" | "object_storage" | "temporal";
            /** Ready */
            ready: boolean;
        };
        /** DocumentDiscoveryItem */
        DocumentDiscoveryItem: {
            document: components["schemas"]["NewsDocument"];
            source: components["schemas"]["Source"];
        };
        /** DocumentIntelligence */
        DocumentIntelligence: {
            /** Analyses */
            analyses: components["schemas"]["AnalysisResult"][];
            document: components["schemas"]["NewsDocument"];
            /** Entities */
            entities: components["schemas"]["Entity"][];
            /** Events */
            events: components["schemas"]["NewsEvent"][];
            /** Media */
            media: components["schemas"]["MediaAsset"][];
            /** Mentions */
            mentions: components["schemas"]["EntityMention"][];
            /** Provenance */
            provenance: components["schemas"]["ProvenanceRecord"][];
            source: components["schemas"]["Source"];
        };
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
        /** EntityExtractionResult */
        EntityExtractionResult: {
            /** Confidence */
            confidence: number;
            /** End Offset */
            end_offset: number;
            /** Predicted Kind */
            predicted_kind?: ("organization" | "person" | "location" | "other") | null;
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
        /** EntityMention */
        EntityMention: {
            /** Analysis Id */
            analysis_id?: string | null;
            /** Document Id */
            document_id: string;
            /** End Offset */
            end_offset: number;
            /** Entity Id */
            entity_id?: string | null;
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
        /**
         * ErrorCode
         * @enum {string}
         */
        ErrorCode: "INVALID_ARGUMENT" | "UNAUTHORIZED" | "FORBIDDEN" | "NOT_FOUND" | "CONFLICT" | "RATE_LIMITED" | "SOURCE_UNAVAILABLE" | "PROCESSING_FAILED" | "INTEGRITY_FAILED" | "INTERNAL_ERROR";
        /** ErrorDetail */
        ErrorDetail: {
            code: components["schemas"]["ErrorCode"];
            /** Message */
            message: string;
            /** Request Id */
            request_id: string;
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
            /** Occurred At */
            occurred_at?: string | null;
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
        /** FetchOptions */
        FetchOptions: {
            /** Country */
            country?: ("in" | "us") | null;
            /**
             * Limit
             * @default 3
             */
            limit: number;
            /**
             * Query
             * @default technology
             */
            query: string;
            /**
             * Retry Failed
             * @default false
             */
            retry_failed: boolean;
        };
        /** HealthStatus */
        HealthStatus: {
            /**
             * Status
             * @default ok
             * @constant
             */
            status: "ok";
        };
        /** IdentityResponse */
        IdentityResponse: {
            /** Kind */
            kind: string;
            /** Roles */
            roles: string[];
            /** Scopes */
            scopes: string[];
            /** Subject */
            subject: string;
        };
        /** IngestionRequest */
        IngestionRequest: {
            /** Content Base64 */
            content_base64: string;
            /**
             * Content Type
             * @default text/plain
             * @enum {string}
             */
            content_type: "text/plain" | "text/html" | "application/json";
            /**
             * Correlation Id
             * @default local-ingestion
             */
            correlation_id: string;
            /** First Seen At */
            first_seen_at?: string | null;
            /** Idempotency Key */
            idempotency_key: string;
            /** Language */
            language?: string | null;
            /**
             * Media
             * @default []
             */
            media: components["schemas"]["MediaInput"][];
            /** Published At */
            published_at?: string | null;
            /** Source Id */
            source_id: string;
            /** Source Url */
            source_url?: string | null;
            /** Title */
            title?: string | null;
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
        /** MediaInput */
        MediaInput: {
            /** Content Base64 */
            content_base64: string;
            /**
             * Content Type
             * @enum {string}
             */
            content_type: "image/png" | "image/jpeg" | "application/pdf" | "text/plain";
            /**
             * Kind
             * @enum {string}
             */
            kind: "image" | "attachment";
        };
        /** ModelDistribution */
        ModelDistribution: {
            /** Document Count */
            document_count: number;
            /** Model Name */
            model_name: string;
            /** Model Version */
            model_version: string;
            /** Provider */
            provider: string;
        };
        /** ModelIdentity */
        ModelIdentity: {
            /** Configuration Hash */
            configuration_hash: string;
            /** Model Name */
            model_name: string;
            /** Model Version */
            model_version: string;
            /** Provider */
            provider: string;
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
            /** Language */
            language?: string | null;
            /** Published At */
            published_at?: string | null;
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
            /** Analysis Id */
            analysis_id?: string | null;
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
            /** Occurred At */
            occurred_at?: string | null;
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
        /** ProvenanceRecord */
        ProvenanceRecord: {
            /** Analysis Id */
            analysis_id?: string | null;
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
        /** ProviderArticleView */
        ProviderArticleView: {
            /**
             * Acquired At
             * Format: date-time
             */
            acquired_at: string;
            /** Article Id */
            article_id: string;
            /** Document Id */
            document_id?: string | null;
            /**
             * Evidence
             * @default []
             */
            evidence: components["schemas"]["ArticleEvidence"][];
            /** Published At */
            published_at?: string | null;
            /** Source Id */
            source_id: string;
            /** Title */
            title: string;
            /** Workflow Id */
            workflow_id?: string | null;
        };
        /** ProviderOutcome */
        ProviderOutcome: {
            /**
             * Duplicates
             * @default 0
             */
            duplicates: number;
            /** Error */
            error?: string | null;
            /**
             * Fetched
             * @default 0
             */
            fetched: number;
            /**
             * Images
             * @default 0
             */
            images: number;
            /**
             * Provider
             * @enum {string}
             */
            provider: "newsdata" | "gnews" | "newsapi" | "gdelt" | "youtube";
            /**
             * Requests
             * @default 0
             */
            requests: number;
            /**
             * Skipped
             * @default 0
             */
            skipped: number;
            /**
             * Status
             * @enum {string}
             */
            status: "submitted" | "disabled" | "failed";
            /**
             * Submitted
             * @default 0
             */
            submitted: number;
            /**
             * Videos
             * @default 0
             */
            videos: number;
            /**
             * Workflow Ids
             * @default []
             */
            workflow_ids: string[];
        };
        /** ProviderRun */
        ProviderRun: {
            /** Completed At */
            completed_at?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Outcomes
             * @default []
             */
            outcomes: components["schemas"]["ProviderOutcome"][];
            /** Run Id */
            run_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "submitted" | "interrupted";
            /**
             * Workflow Statuses
             * @default {}
             */
            workflow_statuses: {
                [key: string]: string;
            };
        };
        /** ProviderStatus */
        ProviderStatus: {
            /** Enabled */
            enabled: boolean;
            /**
             * Mode
             * @default manual local development
             */
            mode: string;
            /**
             * Provider
             * @enum {string}
             */
            provider: "newsdata" | "gnews" | "newsapi" | "gdelt" | "youtube";
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
            /** Published At */
            published_at?: string | null;
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
            /** Source Url */
            source_url?: string | null;
        };
        /** ReadinessStatus */
        ReadinessStatus: {
            /** Dependencies */
            dependencies: components["schemas"]["DependencyStatus"][];
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "not_ready";
        };
        /** ResponseMeta */
        ResponseMeta: {
            /**
             * Api Version
             * @default v1
             * @constant
             */
            api_version: "v1";
            /** Request Id */
            request_id: string;
        };
        /** SentimentDistribution */
        SentimentDistribution: {
            /** Document Count */
            document_count: number;
            /**
             * Label
             * @enum {string}
             */
            label: "positive" | "neutral" | "negative" | "mixed";
        };
        /** SentimentResult */
        SentimentResult: {
            /** Confidence */
            confidence: number;
            /** Entity Id */
            entity_id?: string | null;
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
        /** SignedManifest */
        SignedManifest: {
            /** Chain Hashes */
            chain_hashes: string[];
            /** Key Id */
            key_id: string;
            /** Records */
            records: components["schemas"]["ProvenanceRecord"][];
            /** Signature */
            signature: string;
            /**
             * Version
             * @default aegis-provenance-1
             */
            version: string;
        };
        /** SimilarDocument */
        SimilarDocument: {
            /** Distance */
            distance: number;
            document: components["schemas"]["NewsDocument"];
            /** Model Name */
            model_name: string;
        };
        /** SingleResponse[AnalyticsReport] */
        SingleResponse_AnalyticsReport_: {
            data: components["schemas"]["AnalyticsReport"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[DocumentIntelligence] */
        SingleResponse_DocumentIntelligence_: {
            data: components["schemas"]["DocumentIntelligence"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[Entity] */
        SingleResponse_Entity_: {
            data: components["schemas"]["Entity"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[HealthStatus] */
        SingleResponse_HealthStatus_: {
            data: components["schemas"]["HealthStatus"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[IdentityResponse] */
        SingleResponse_IdentityResponse_: {
            data: components["schemas"]["IdentityResponse"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[NewsDocument] */
        SingleResponse_NewsDocument_: {
            data: components["schemas"]["NewsDocument"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[NewsEvent] */
        SingleResponse_NewsEvent_: {
            data: components["schemas"]["NewsEvent"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[ProviderRun] */
        SingleResponse_ProviderRun_: {
            data: components["schemas"]["ProviderRun"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[RawIngestion] */
        SingleResponse_RawIngestion_: {
            data: components["schemas"]["RawIngestion"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[ReadinessStatus] */
        SingleResponse_ReadinessStatus_: {
            data: components["schemas"]["ReadinessStatus"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[Source] */
        SingleResponse_Source_: {
            data: components["schemas"]["Source"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[SystemInfo] */
        SingleResponse_SystemInfo_: {
            data: components["schemas"]["SystemInfo"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[TopicSummary] */
        SingleResponse_TopicSummary_: {
            data: components["schemas"]["TopicSummary"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[VerificationResult] */
        SingleResponse_VerificationResult_: {
            data: components["schemas"]["VerificationResult"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[dict[str, Any]] */
        SingleResponse_dict_str__Any__: {
            /** Data */
            data: {
                [key: string]: unknown;
            };
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[dict[str, int]] */
        SingleResponse_dict_str__int__: {
            /** Data */
            data: {
                [key: string]: number;
            };
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[dict[str, str]] */
        SingleResponse_dict_str__str__: {
            /** Data */
            data: {
                [key: string]: string;
            };
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[tuple[ArticleEvidence, ...]] */
        SingleResponse_tuple_ArticleEvidence__________: {
            /** Data */
            data: components["schemas"]["ArticleEvidence"][];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[tuple[ProviderStatus, ...]] */
        SingleResponse_tuple_ProviderStatus__________: {
            /** Data */
            data: components["schemas"]["ProviderStatus"][];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SnapshotCollectionResponse[DocumentDiscoveryItem] */
        SnapshotCollectionResponse_DocumentDiscoveryItem_: {
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            /** Data */
            data: components["schemas"]["DocumentDiscoveryItem"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** SnapshotCollectionResponse[TopicMembership] */
        SnapshotCollectionResponse_TopicMembership_: {
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            /** Data */
            data: components["schemas"]["TopicMembership"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
        };
        /** SnapshotCollectionResponse[TopicSummary] */
        SnapshotCollectionResponse_TopicSummary_: {
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            /** Data */
            data: components["schemas"]["TopicSummary"][];
            meta: components["schemas"]["ResponseMeta"];
            pagination: components["schemas"]["CursorPagination"];
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
            /** Url */
            url?: string | null;
        };
        /** SourceCreate */
        SourceCreate: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "feed" | "api" | "upload" | "web";
            /** Name */
            name: string;
            /** Url */
            url?: string | null;
        };
        /** SourceDistribution */
        SourceDistribution: {
            /** Document Count */
            document_count: number;
            /** Name */
            name: string;
            /** Source Id */
            source_id: string;
        };
        /** SystemInfo */
        SystemInfo: {
            /**
             * Architecture
             * @default modular monolith + background workers
             * @constant
             */
            architecture: "modular monolith + background workers";
            /**
             * Name
             * @default AegisNews
             * @constant
             */
            name: "AegisNews";
            /**
             * Stage
             * @default foundation
             * @constant
             */
            stage: "foundation";
            /** Version */
            version: string;
        };
        /** TopicMembership */
        TopicMembership: {
            /** Analysis Id */
            analysis_id: string;
            /**
             * Available At
             * Format: date-time
             */
            available_at: string;
            /** Confidence */
            confidence: number;
            document: components["schemas"]["NewsDocument"];
            model: components["schemas"]["ModelIdentity"];
            source: components["schemas"]["Source"];
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
        /** TopicSummary */
        TopicSummary: {
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            /** Document Count */
            document_count: number;
            /**
             * First Available At
             * Format: date-time
             */
            first_available_at: string;
            /** Label */
            label: string;
            /**
             * Latest Available At
             * Format: date-time
             */
            latest_available_at: string;
            model: components["schemas"]["ModelIdentity"];
            /** Selection Policy */
            selection_policy: string;
            /** Topic Id */
            topic_id: string;
        };
        /** VerificationRequest */
        VerificationRequest: {
            /** Contents */
            contents: {
                [key: string]: string;
            };
            manifest: components["schemas"]["SignedManifest"];
        };
        /** VerificationResult */
        VerificationResult: {
            /** Chain Valid */
            chain_valid: boolean;
            /** Content Verified */
            content_verified: boolean;
            /** Reason */
            reason: string;
            /** Signature Valid */
            signature_valid: boolean;
            /** Valid */
            valid: boolean;
        };
        /** YouTubeReference */
        YouTubeReference: {
            /** Channel Id */
            channel_id: string;
            /** Channel Title */
            channel_title: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /**
             * Last Refreshed At
             * Format: date-time
             */
            last_refreshed_at?: string;
            /** Published At */
            published_at?: string | null;
            /** Thumbnail Url */
            thumbnail_url?: string | null;
            /** Title */
            title: string;
            /** Video Id */
            video_id: string;
            /** Youtube Url */
            youtube_url: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    analytics_api_v1_analytics_get: {
        parameters: {
            query: {
                start: string;
                end: string;
                as_of?: string | null;
                time_basis?: "published_at" | "first_seen_at";
                source_id?: string | null;
                topic_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_AnalyticsReport_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    discovery_api_v1_discovery_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                as_of?: string | null;
                order?: "published_at" | "first_seen_at";
                q?: string;
                source_id?: string | null;
                topic_id?: string | null;
                start?: string | null;
                end?: string | null;
                time_basis?: "published_at" | "first_seen_at";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SnapshotCollectionResponse_DocumentDiscoveryItem_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    documents_api_v1_documents_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                as_of?: string | null;
                q?: string;
                source_id?: string | null;
                entity_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_NewsDocument_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    get_document_api_v1_documents__document_id__get: {
        parameters: {
            query?: {
                as_of?: string | null;
            };
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_NewsDocument_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    acquisition_api_v1_documents__document_id__acquisition_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_tuple_ArticleEvidence__________"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    intelligence_api_v1_documents__document_id__intelligence_get: {
        parameters: {
            query?: {
                as_of?: string | null;
            };
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_DocumentIntelligence_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    similar_api_v1_documents__document_id__similar_get: {
        parameters: {
            query?: {
                limit?: number;
                as_of?: string | null;
            };
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_SimilarDocument_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    verify_api_v1_documents__document_id__verify_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_VerificationResult_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    entities_api_v1_entities_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                as_of?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_Entity_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    entity_api_v1_entities__entity_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_Entity_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    entity_documents_api_v1_entities__entity_id__documents_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                as_of?: string | null;
            };
            header?: never;
            path: {
                entity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_NewsDocument_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    events_api_v1_events_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                as_of?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_NewsEvent_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    event_api_v1_events__event_id__get: {
        parameters: {
            query?: {
                as_of?: string | null;
                revision?: number | null;
            };
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_NewsEvent_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    get_run_api_v1_ingestion_runs__workflow_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workflow_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_dict_str__Any__"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    submit_api_v1_ingestions_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IngestionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_dict_str__str__"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    submit_batch_api_v1_ingestions_batch_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_dict_str__Any__"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    get_ingestion_api_v1_ingestions__ingestion_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                ingestion_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_RawIngestion_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    article_list_api_v1_provider_articles_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_ProviderArticleView_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    get_run_api_v1_provider_runs__run_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_ProviderRun_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    providers_api_v1_providers_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_tuple_ProviderStatus__________"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    fetch_all_api_v1_providers_fetch_all_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FetchOptions"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_ProviderRun_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    fetch_api_v1_providers__provider__fetch_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                provider: "newsdata" | "gnews" | "newsapi" | "gdelt" | "youtube";
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FetchOptions"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_ProviderRun_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    documents_api_v1_search_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                as_of?: string | null;
                q?: string;
                source_id?: string | null;
                entity_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_NewsDocument_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    audit_events_api_v1_security_audit_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_AuditEvent_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    me_api_v1_security_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_IdentityResponse_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    verify_api_v1_security_verify_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VerificationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_VerificationResult_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    sources_api_v1_sources_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_Source_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    create_source_api_v1_sources_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SourceCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_Source_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    get_source_api_v1_sources__source_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_Source_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    system_info_api_v1_system_info_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_SystemInfo_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    topics_api_v1_topics_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                as_of?: string | null;
                q?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SnapshotCollectionResponse_TopicSummary_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    topic_api_v1_topics__topic_id__get: {
        parameters: {
            query?: {
                as_of?: string | null;
            };
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_TopicSummary_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    topic_documents_api_v1_topics__topic_id__documents_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
                as_of?: string | null;
            };
            header?: never;
            path: {
                topic_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SnapshotCollectionResponse_TopicMembership_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    video_list_api_v1_youtube_references_get: {
        parameters: {
            query?: {
                limit?: number;
                cursor?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CollectionResponse_YouTubeReference_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    refresh_api_v1_youtube_references_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_dict_str__int__"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    delete_video_api_v1_youtube_references__video_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                video_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_dict_str__str__"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_HealthStatus_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
    ready_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SingleResponse_ReadinessStatus_"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApiErrorEnvelope"];
                };
            };
        };
    };
}
