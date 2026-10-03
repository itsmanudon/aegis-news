// Generated from checked-in schemas. Run pnpm api:generate; do not edit.
export interface paths {
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
        /** ApiErrorEnvelope */
        ApiErrorEnvelope: {
            error: components["schemas"]["ErrorDetail"];
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
        /** HealthStatus */
        HealthStatus: {
            /**
             * Status
             * @default ok
             * @constant
             */
            status: "ok";
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
        /** SingleResponse[HealthStatus] */
        SingleResponse_HealthStatus_: {
            data: components["schemas"]["HealthStatus"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[ReadinessStatus] */
        SingleResponse_ReadinessStatus_: {
            data: components["schemas"]["ReadinessStatus"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** SingleResponse[SystemInfo] */
        SingleResponse_SystemInfo_: {
            data: components["schemas"]["SystemInfo"];
            meta: components["schemas"]["ResponseMeta"];
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
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
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
