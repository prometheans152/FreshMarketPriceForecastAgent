# Cloudflare MCP tool contract

> **D47 (2026-10-28):** the tools accept the 60 catalog items the website forecasts
> (`CROP_NAMES` in `src/contracts.js`, with Chinese names in the schema description),
> still A mode only. Oracle serves the extra items through the `/v1` full-catalog
> extension (`../oracle-forecastengine/v1_full_catalog/`). Worker version `e84d636c`;
> rollback version `fe4614d6`. Remote acceptance: original 6/6 plus catalog 5/5.

> **D49 (deployed 2026-11-05, Worker `db4c59d8`, rollback `e84d636c`):** `post_forecast` accepts
> `market_id="all_markets"` when the user sees a price at an ordinary roadside
> shop or does not identify a public market. It is a median of independently
> predicted *relative changes* from up to 13 Taichung public markets, with at
> least three valid contributors. No evaluation exists for this aggregation:
> it is **not** an actual quote for any shop or public market. Keep the existing
> Oracle /v1 auth, timeout, version and model integrity checks unchanged.

> **Rename (2026-10-16/17):** names below are the new `fresh-market-price-agent-*` / `FMPA_*` ones.
> The Oracle host is fully migrated (2026-10-17; the certbot timer, renamed last, on 2026-10-20);
> the new Worker `fresh-market-price-agent` is live (6/6 E2E), while ChatGPT still uses the old
> `tw01-forecast-mcp`, which stays up until the connector is switched. Progress: [RENAME_MIGRATION.md](../RENAME_MIGRATION.md).

Status (2026-10-15): **PUBLIC NO AUTH REMOTE MCP LIVE** through Cloudflare
Workers VPC → Oracle HTTPS, 6/6 genuine remote server protocol/tool
acceptance PASS, 45/45 Node tests PASS, production HTTP 429 observed.
Oracle credential installed as a Worker Secret and kept private.
**Native ChatGPT/Gemini app-level calls are still unverified.**
See current `VPC_LIVE_ACCEPTANCE.md` for evidence and limitations.
Source of truth for the **upstream**: immutable-for-this-conversation
`../../docs/deployment/FORECASTENGINE_API_V1.md` (Oracle owner).

## Transport

- Exact entry: `https://fresh-market-price-agent.prometheans152.workers.dev/mcp`,
  public No Auth stateless Streamable HTTP. Actual initialize/list/
  Oracle quote/forecast calls have all succeeded in a standalone
  real remote MCP client, but ChatGPT's own UI is not connected yet.
- JSON-RPC initialize, tools/list, tools/call supported; exactly two tools.
- No save, delete, previous price, store ID, arbitrary network or file tool.
- Owner-approved No Auth transport requires **four** mandatory Cloudflare
  IP/PoP rate-limit bindings with fail-closed missing-binding behavior.
  No Cloudflare Access OAuth gate remains on this dedicated Worker route.
  The legacy bearer and Access JWT routes are retained for rollback/test,
  not used by the current Worker source.
- Max inbound JSON 16,384 bytes; max upstream response and tool output
  131,072 bytes each; max JSON nesting 20. Backend fetch uses AbortSignal.

### Oracle Docker Compose Origin (2026-10-15 verified)

The Worker **did not change any upstream path or schema** after
the Docker migration. `VPC_ORACLE_FORECAST` still goes through
the existing Cloudflare Tunnel to Oracle private `10.0.0.86:443`;
`verify_full` validates the original HTTPS IP-SAN certificate
for `161.33.19.220`. Host Nginx forwards the same fixed,
Bearer-protected `/v1/market-quote` and `/v1/forecast`
to host `127.0.0.1:8080` → Docker Web Nginx →
Docker ForecastEngine. Docker's separate self-hosted
`fresh-market-price-agent-oracle-mcp-1`, internal port 9000, is **not** used
by this Worker. Internal Docker ports 8767/9000 are not
publicly exposed.

The three original crop IDs remain on frozen model `0.1.0`
(7-day RF, 14-day HGB); since D47 the other catalog items use
the same 57-item pooled HGB as the browser. The same six
MCP cases were independently re-run from Windows after cutover:
**6/6 PASS**; original Docker RF/HGB hashes **2/2 match**.
See `VPC_LIVE_ACCEPTANCE.md` and fresh evidence at
`../../outputs/quality_runs/workers_mcp_docker_sync_20261015_131055_Windows5800X_c410f8`.

## get_market_quote

Input schema: required exact strings `crop_id`, `market_id`. Allowed
crop IDs: the 60 IDs in `CROP_NAMES` (`src/contracts.js`; `taichung_25` has no public price and is excluded). Exact market names
in `src/contracts.js` (13 Taichung public markets).
The special `all_markets` value is always rejected for `get_market_quote`.
No extra properties. Fixed HTTPS upstream POST `/v1/market-quote`.

On HTTP 200 the verified Oracle **complete** envelope is returned as
`structuredContent`, including original `tool`, `input_echo`,
`normalized_request:null`, `query_date`, `engine_result`, provenance
dates, `price_age_days_at_query`, `limits`, `fact_text` and any additional
metadata. Raw engine_result must match requested crop/market, return a
positive finite public quote per Taiwan jin, valid observation and cutoff
dates, consistent age. Quote is **not a real-time individual shop price**.

## post_forecast

Input schema required: exact `crop_id`, `market_id`, `current_price`
(finite positive JSON number), `price_unit` either
`NTD_per_taiwan_jin` or `NTD_per_kg`. Optional exact `observed_on`
`YYYY-MM-DD`, interpreted in Asia/Taipei when missing. Invalid/impossible
or future date is denied; historical date only succeeds if Oracle returns
validated source data. Strict extra-property rejection prohibits B mode,
last-week price, private store, saving, arbitrary URL and shell.

D49 adds the exact value `all_markets` to the forecast tool's market enum.
When the user supplies no named market, or is at a roadside store, **do not ask
which market**: send `market_id="all_markets"`. If a named supported market is
given, keep using that precise market. The assistant must still obtain a
supported crop ID, the observed current shop price and its comparably weighted
unit before calling the tool. It must never substitute an official market
average for a missing shop price.

In `all_markets` responses the Worker verifies, without modifying numbers:

- `valid_market_count` is an integer between 3 and 13 and equals the length
  of `market_predictions`; markets are distinct members of the original 13.
- Each market has exactly t+7 and t+14 relative changes and directions.
  Each aggregate result's relative change is the median of the respective
  market changes (allowing only four-decimal rounding), and its min/max,
  classified direction and shop-price estimate agree with the inputs.
- Complete A-mode envelope, `market_id`, `store_id=null`,
  `mode_executed="without_last_week"`, dates, units and null probabilities
  and intervals still pass the original strict checks.
- `warnings`, `limits` and `fact_text` include:
  「全臺中參考：13 個公有市場各自預測的中位數；這種用法沒有經過評估；不是任何市場或店家的真值。」

Insufficient usable markets or altered figures are hard errors: no numeric
response. This median is **unvalidated**, not a measured improvement; existing
frozen model scores and point-estimate warnings remain unchanged.

Fixed HTTPS upstream POST `/v1/forecast` with these validated fields.
Oracle API owner creates canonical noon `observed_at` and
`mode=without_last_week`, `store_id=null`; Worker cross-checks this
response against input. Oracle must provide exact target dates of t+7 and
t+14 calendar days; both results are `store_price_estimate`,
`validation_scope=unvalidated`, each has original warnings and null
uncalibrated intervals and probabilities. Worker **never calculates** any
forecast, trend, probability or predicted price. It only verifies date
and raw-result consistency and preserves the complete envelope.

## Failure semantics

All invalid inputs and unsupported tools fail safely and never trigger an
upstream forecast. Oracle 401/403/429/5xx, insufficient data, timeout,
truncated/oversized JSON, invalid origin TLS or malformed result return
MCP `isError:true`, no synthetic result. HTTPS redirects are rejected.
The request and response JSON Schema and upstream error status codes are
governed by the Oracle owner's document, not by this Workers README.

## D49 deployment / rollback

Deployed 2026-11-05 in this order: Oracle override first (healthy after 40 s), then
Worker `db4c59d8`. On Oracle the 13-market run took 3.9–7.8 s for the 3 frozen crops
and 0.3–1.2 s for pooled items (limit 15 s). Remote acceptance: original 6/6, D49 5/5.

1. Independently review the D49 diff and run `npm ci && npm test` in
   `deploy/cloudflare-workers-mcp`. Run both real-model D49 probes against
   portable and repo sources and check the <15s requirement before deployment.
2. Make the D49 Oracle override available on the host **first**, following
   `deploy/docker/oracle/ORACLE_DOCKER_OPERATIONS.md` and its exact compose
   command. Check health and the existing named-market cases plus all_markets
   before exposing the new Worker contract.
3. Record the current `fresh-market-price-agent` deployment version in
   Cloudflare's Worker Deployments page. From
   `deploy/cloudflare-workers-mcp/`, after review, use `npm run check`
   (the package's Wrangler dry run) and `npm run deploy` (the package's
   production deploy). Recheck tools/list, named-market requests, and
   no-market requests. No Wrangler command or live deploy was executed
   as part of this candidate.

To roll back, use the Cloudflare Worker Deployments page to restore the
recorded previous production version, then remove Oracle's D49 compose override;
D47/D48 continue serving the same original named-market values. Cloudflare
credentials, model files, rolling-data versions and timers are not changed.
