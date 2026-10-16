# TW01 Public No Auth MCP — 2026-10-14 deployment handoff

> **HISTORICAL / SUPERSEDED 2026-10-15.** This describes the interim
> state before Cloudflare Access was removed, the Oracle Secret was
> configured, and Workers VPC passed real E2E. For the live, verified
> deployment and rollback use **`VPC_LIVE_ACCEPTANCE.md`**.
> Do **not** repeat the obsolete Access/Secret setup steps below.

## Precise status

**LIVE WORKER UPDATED / FREE RATE LIMITS DEPLOYED / NOT YET PUBLICLY USABLE.**

- Worker: `tw01-forecast-mcp`, only this Worker was deployed.
- URL: `https://tw01-forecast-mcp.prometheans152.workers.dev/mcp`
- Deployed Worker version after final health-rate-limit fix:
  `437553a8-3810-44a1-beef-6830e745f256`.
- Worker environment: `AUTH_MODE=public_noauth`; no inbound OAuth or
  end-user static Bearer required **within the Worker**.
- Cloudflare's **separate** Access app `TW01 Forecast MCP`, id
  `41e4b7ac-b87e-4add-b212-898aa2f07de7`, remains ACTIVE and
  currently returns **HTTP 401 OAuth** before requests reach Worker.
  Until this dedicated Access app is disabled/removed, the MCP is **not
  publicly usable**, regardless of the Worker code.
- Cloudflare Worker Secret `FORECASTENGINE_API_TOKEN` still has **not
  been installed**. The Oracle endpoint is healthy, but Worker forecast
  responses are **fail closed 503** until this private backend Secret is
  configured; do not claim real Oracle or ChatGPT/Gemini E2E.

The user explicitly authorized the No Auth direction after comparing
OAuth and unauthenticated access, with the intention that both ChatGPT
and Gemini share one remote MCP endpoint. This is an anonymous PUBLIC
MCP: other HTTP clients may use it too after activation.

## Rate limiting actually deployed

The 4 independently configured Cloudflare **Rate Limiting bindings**
are attached to `tw01-forecast-mcp`:

| Binding | Allowed per 60-second window | Key |
| --- | --- | --- |
| `RL_REQUESTS_IP` | 12 | Cloudflare-reported source IP |
| `RL_REQUESTS_POP` | 60 | All sources in one Cloudflare location |
| `RL_TOOLS_IP` | 4 | Same source IP, just MCP `tools/call` |
| `RL_TOOLS_POP` | 20 | All MCP tool calls in that Cloudflare location |

These limits include anonymous MCP initialization/listing; public
`GET /healthz` is also metered. Rate-limit denial returns
**429** and `Retry-After: 60`. Missing/broken binding returns **503**,
never permissively falls back to no rate limit. Worker ingress also
limits body to 16KiB, validates UTF-8/duplicate JSON keys, restricts
original 2 tools and 3 crops/13 markets/2 comparable units, and
rejects B mode, saving, private data, arbitrary URLs/programs.

**Accuracy warning:** these bindings are eventually consistent and
enforced **per Cloudflare location**, not an exact global accounting or
unbypassable guarantee. Source IP limits may group NAT users. Oracle's
own concurrency and resource safety must remain active.

Cloudflare references:
- https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- https://developers.cloudflare.com/workers/platform/limits/

## Tests to date

- Node protocol/auth/security/model-envelope tests: **39/39 PASS**
  (after the additional public health-endpoint limit test).
- Wrangler bundle check: exit 0 and exactly four real Rate Limit
  bindings present.
- **Actual local Workerd** on `127.0.0.1:8797`: the fifth synthetic
  `tools/call` produced 429; the thirteenth ordinary request also
  produced 429. Local Origin URL fixture mismatched the pinned
  `FORECASTENGINE_ALLOWED_HOSTNAME`, therefore no actual predicted
  numbers were obtained or claimed. Workerd was stopped afterward.
- Cloudflare Wrangler live deployment: exit 0, version above.
- **Live remote 429**: MUST STILL BE CHECKED after TW01 Access policy
  is disabled; before that, Cloudflare returns OAuth 401.
- Oracle real TLS `GET /healthz`: 200 ready (previously checked).
- Real Oracle POST through Workers: **0**; ChatGPT and Gemini
  authenticated/anonymous tools calls: **0**.

## Remaining owner action 1 — disable only TW01 Cloudflare Access

The Windows COS Desktop browser interface refused access with
`CALLER_IDENTITY_REQUIRED` / `BROWSER_IDENTITY_REQUIRED`: chat
attribution or **Allow unattributed calls** is required. Do not use
ad-hoc browser interception to bypass tool permissions.

For owner-performed change, open the Cloudflare Zero Trust Free
[Access Applications](https://dash.cloudflare.com/aacc8a3a24c5ef00efc530b6845878ce/one/access-controls/apps)
page. Find **exactly** `TW01 Forecast MCP` (the app associated only
with `tw01-forecast-mcp`). From its context menu choose **Disable**
if available, otherwise delete **only that application** after
confirming the name. Do not disable account-wide Access, remove
unrelated applications, or delete the Worker. The leftover
`TW01 Owner Only` *policy* need not be deleted.

Afterward check with an ordinary HTTP client that GET /mcp does
**not** return Cloudflare's Managed OAuth `401` challenge; with
missing Oracle Secret it should safely return Worker `503`.
Run bounded anonymous POST requests to validate the real 429 quotas.
If any limiter is unavailable or the endpoint unexpectedly executes
without safeguards, re-enable the TW01-only Access protection or
roll back only this Worker's new version.

## Remaining owner action 2 — manually configure private Oracle Secret

In Cloudflare Dashboard, **Workers & Pages** →
`tw01-forecast-mcp` → **Settings → Variables and Secrets**,
create a **Secret** (not ordinary variable) named exactly
`FORECASTENGINE_API_TOKEN`.
Use the same TW01-only origin token protected by Oracle root-only
`/etc/tw01-forecastengine/origin.env` as
`TW01_ORIGIN_API_TOKEN`. This is the *backend service credential*
and **must never be shown in chat, logs, source, Markdown, or shell
arguments**. Do not reuse the older COS private Tunnel secret.
The attempted automated transfer was explicitly blocked by a safety
check, so use the owner's approved protected handling.

Use `npx wrangler secret list --name tw01-forecast-mcp` to
verify only the secret **NAME**, without printing its value.

## Acceptance after both actions

1. Remote anonymous `POST /mcp` initialize: 200; `tools/list`
   exactly `get_market_quote`, `post_forecast`; no login and
   no OAuth requirement.
2. Remote `tools/call`: actual upstream public market quote and
   synthetic **anonymous A** price forecasts for 32 NTD/taiwan-jin
   and 65 NTD/kg, explicit/omitted observation date, correct t+7/t+14.
3. Negative checks: B/store/previous price/save/file/url/unknown tool,
   impossible and very old dates, uncomparable box, bad JSON,
   429 rate limit and upstream 401/403/429/5xx/timeout.
4. Verify **the actual tool response** field-for-field against Oracle
   `engine_result`, warning/disclaimer, model/data versions and
   deliberate null probability/interval. No invented numerical value.
5. Attach same MCP URL to ChatGPT and Gemini CLI/API. A genuine
   model-initiated successful call is required before claiming
   either client passes E2E. Consumer Gemini custom apps depend on
   account eligibility and cannot be assumed for the user's plan.

Gemini CLI registration (once URL is actually usable):
`gemini mcp add --transport http tw01-forecast https://tw01-forecast-mcp.prometheans152.workers.dev/mcp`

Gemini API Remote MCP name must be snake_case `tw01_forecast`,
with that exact Streamable HTTP URL. Unlike SSE-only endpoint,
this Worker speaks stateless Streamable HTTP.

## Rollback and environmental constraints

Previous OAuth/JWT Worker version:
`ef1e515e-0c2c-4d8c-a9a2-681d7b85ff91`.
Previous intentionally inert initial version:
`51a7b747-dee5-48b9-95d9-b222aab3cdb8`.
Rollback only `tw01-forecast-mcp`, and restore its restricted Access
application if needed. Never modify other Workers, old COS Tunnel,
Oracle model/data/records, SEALED/CORE, or reset/commit/push Git.
