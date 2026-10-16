# Cloudflare MCP tool contract

> **Rename (2026-10-16):** names below are the new `fresh-market-price-agent-*` / `FMPA_*` ones.
> Until [RENAME_MIGRATION.md](../RENAME_MIGRATION.md) has been carried out, the live Oracle host and Worker
> still use the old `tw01-*` names; before migration, operate or roll back with this file as of
> `main@1062818`.

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
(7-day RF, 14-day HGB); 57 new HGB models in the Docker
browser catalog are **not** MCP v1 tools. The same six
MCP cases were independently re-run from Windows after cutover:
**6/6 PASS**; original Docker RF/HGB hashes **2/2 match**.
See `VPC_LIVE_ACCEPTANCE.md` and fresh evidence at
`../../outputs/quality_runs/workers_mcp_docker_sync_20261015_131055_Windows5800X_c410f8`.

## get_market_quote

Input schema: required exact strings `crop_id`, `market_id`. Allowed
crop IDs: `cabbage`, `bok_choy`, `sponge_gourd`. Exact market names
in `src/contracts.js` (13 Taichung public markets).
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
