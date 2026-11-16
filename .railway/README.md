# Railway configuration

Aegis News is deployed on Railway from `.railway/railway.ts` (Railway
Infrastructure as Code, which replaced `railway.json` / `railway.toml`). The
`railway` root devDependency is the SDK the CLI evaluates.

Aegis shares the Railway project `stockviz` with StockViz, so each repository
owns a named partial:

| Partial | File | Resources |
| --- | --- | --- |
| `aegis` | this repository, `.railway/railway.ts` | aegis-api, aegis-daily, aegis-raw |
| `stockviz` | `itsmanudon/stock-viz-simulator`, `.railway/railway.ts` | Postgres, api, web, cron |

Keep `export const partial = "aegis"`. Without it the file is planned as the
whole project, and an apply would delete the StockViz services.

## Commands

```bash
railway link -p <project-id> -e production   # once per checkout
railway config plan                           # read only, safe
railway config apply                          # production change: owner approval first
railway config partials list                  # which partial owns which resource
```

## Variables

Every variable is `preserve()`: values live on Railway and Doppler, never in
source. Variables are managed, so a variable present on Railway but missing
from the file is planned for deletion. Add a new variable here as
`preserve()` before setting it with `railway variable set`.
