import { bucket, defineRailway, github, preserve, project, service } from "railway/iac";

/**
 * Aegis News on Railway: its slice of the shared `stockviz` project.
 *
 * The project also holds StockViz (Postgres, api, web, cron), declared in
 * `itsmanudon/stock-viz-simulator` under `.railway/railway.ts` as the
 * `stockviz` partial. Each file names a partial, and the CLI records which
 * partial owns each resource, so a plan or apply from one repository never
 * deletes the other's services. Without the partial export a plan from either
 * file would delete everything it does not declare.
 *
 * Three resources, imported from the live project with `railway config pull`
 * on 16 Nov 2026:
 *   - `aegis-api`: the read API. Private network only (no public domain);
 *     StockViz's cron reaches it at `aegis-api.railway.internal:8000`.
 *     Sleeps on idle; migrations run before each deploy.
 *   - `aegis-daily`: the nightly ingestion job, 21:30 UTC, before the
 *     StockViz cron at 22:00 pulls from the API.
 *   - `aegis-raw`: the object store for raw provider payloads.
 *
 * The database is the shared `Postgres` service, owned by the `stockviz`
 * partial. Aegis reaches it through `AEGIS_DATABASE_URL`.
 *
 * Every secret is `preserve()`: the values live on Railway (and in Doppler)
 * and never in source. The two non-secret company-search settings on
 * `aegis-daily` are written here. Set or rotate them with `railway variable set`; a
 * re-apply keeps them. A variable that exists on Railway but is missing here
 * is planned for deletion, so add new ones here as `preserve()` first.
 *
 *   railway config plan     # read only
 *   railway config apply    # production change: owner approval first
 */

export const partial = "aegis";

const REPO = "itsmanudon/aegis-news";
const BRANCH = "main";

export default defineRailway(() => {
  const source = github(REPO, { branch: BRANCH, checkSuites: false });
  const region = { "asia-southeast1-eqsg3a": 1 };

  const raw = bucket("aegis-raw", { region: "sin" });

  // Shared by the API and the job.
  const common = {
    AEGIS_AI_PROFILE: preserve(),
    AEGIS_DATABASE_URL: preserve(),
    AEGIS_OIDC_PUBLIC_KEYS: preserve(),
    AEGIS_OTEL_ENABLED: preserve(),
    AEGIS_PROVENANCE_KEY_ID: preserve(),
    AEGIS_PROVENANCE_PUBLIC_KEY: preserve(),
    AEGIS_S3_ACCESS_KEY: preserve(),
    AEGIS_S3_ADDRESSING_STYLE: preserve(),
    AEGIS_S3_BUCKET: preserve(),
    AEGIS_S3_ENDPOINT_URL: preserve(),
    AEGIS_S3_REGION: preserve(),
    AEGIS_S3_SECRET_KEY: preserve(),
  };

  const api = service("aegis-api", {
    source,
    build: {
      buildEnvironment: "V3",
      builder: "DOCKERFILE",
      dockerfilePath: "infrastructure/docker/python.Dockerfile",
    },
    healthcheck: "/health",
    preDeploy: "alembic upgrade head",
    replicas: region,
    deploy: { restartPolicyMaxRetries: 3, sleepApplication: true },
    env: {
      ...common,
      AEGIS_CORS_ORIGINS: preserve(),
      AEGIS_ENVIRONMENT: preserve(),
      AEGIS_OIDC_ALGORITHMS: preserve(),
      AEGIS_OIDC_AUDIENCE: preserve(),
      AEGIS_OIDC_ISSUER: preserve(),
      AEGIS_OIDC_TOKEN_TYPES: preserve(),
      AEGIS_SECURITY_ENABLED: preserve(),
      AEGIS_SECURITY_RATE_BACKEND: preserve(),
      AEGIS_TEMPORAL_ENABLED: preserve(),
      PORT: preserve(),
    },
  });

  const daily = service("aegis-daily", {
    source,
    build: {
      buildEnvironment: "V3",
      builder: "DOCKERFILE",
      dockerfilePath: "infrastructure/docker/job.Dockerfile",
    },
    start: "python -m aegis.jobs.daily",
    replicas: region,
    deploy: { cronSchedule: "30 21 * * *", restartPolicyType: "NEVER" },
    env: {
      ...common,
      // Company searches (owner-approved NewsData allowance, 16 Nov 2026): 24
      // requests cover all 161 StockViz companies, under the 200/day budget.
      AEGIS_JOB_COMPANY_FILE: "data/instruments/stockviz.json",
      AEGIS_JOB_COMPANY_REQUESTS: "24",
      AEGIS_JOB_LIMIT: preserve(),
      AEGIS_JOB_PROVIDERS: preserve(),
      AEGIS_JOB_QUERY: preserve(),
      AEGIS_NEWSDATA_API_KEY: preserve(),
      AEGIS_PROVENANCE_SIGNING_KEY: preserve(),
      AEGIS_TEMPORAL_CLI_PATH: preserve(),
      DOPPLER_CONFIG: preserve(),
      DOPPLER_ENVIRONMENT: preserve(),
      DOPPLER_PROJECT: preserve(),
    },
  });

  return project("stockviz", {
    variables: { managed: true },
    resources: [api, daily, raw],
  });
});
