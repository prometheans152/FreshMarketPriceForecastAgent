# Cloudflare Workers — Security assessment

> **HISTORICAL assessment, superseded 2026-10-15.**
> This file's blocked/secret-missing statements below describe an
> earlier deployment and should not be treated as the current state.
> The current verified server-to-Oracle E2E, No Auth resource controls,
> residual limits and rollback are in **`VPC_LIVE_ACCEPTANCE.md`**.
> Current successful Worker version:
> `ba488561-76c3-4a3d-9479-e1b71340e401`.

Assessment date: 2026-10-14. Current status:
**public_noauth Worker deployed with 4 Cloudflare rate-limit bindings,
but dedicated Access still intercepts; Oracle Secret missing; NO E2E**.
See `PUBLIC_NOAUTH_HANDOFF.md`.

## Trust boundaries

1. ChatGPT/third-party clients are untrusted; the Worker only accepts
   `/mcp` via a protocol-compliant SDK and enforces bounded requests.
2. Cloudflare Worker owns the MCP schema, fails closed on unknown tools,
   B mode, previous prices, arbitrary URL/files/commands or record storage.
3. Fixed HTTPS POST paths go to the owner-configured ForecastEngine only,
   using a **distinct** backend bearer token. Backend must have valid
   CA-verified HTTPS/TLS. Never disable certificate verification.
4. Oracle backend is trusted for model values, provenance, versions,
   raw warnings and complete response envelope; the Worker **validates**
   basic consistency but never revises or predicts model numbers.

## Locally verified controls

- Strict allowlist of 3 crops, 13 markets, two price units and two tools.
- Date uses Asia/Taipei when unspecified; explicit impossible/future dates
  rejected; target dates cross-checked against t+7 and t+14.
- Reject JSON extra fields, non-finite or non-positive prices, missing
  weight for box/piece/bunch, user-selected URL/command/file or B mode.
- Public mode does not expose or require an end-user authentication token.
  The **one** Oracle backend Token remains necessary and private.
  Previous legacy bearer mode remains limited to synthetic tests.
- Fixed upstream origin; rejects non-HTTPS, URL credentials, query,
  path, fragments, redirects and private/reserved IP literals; public IP
  requires public-trust TLS.
- 16 KiB input cap, nesting depth limit, 128 KiB upstream/tool caps,
  owner-recommended 20-second fetch deadline, abort propagation,
  no unconditional retry and no model-value fallback.
- Error classification covers Oracle 401/403/429/5xx, invalid JSON,
  no data, timeout, cancelled calls and downstream recovery.
- No D1/R2/KV/Durable Object binding; no persistence code. Diagnostic
  `console.warn` emits only tool names and categorical error codes.
  No request body, token, raw private shop price or stack trace.
- `.dev.vars` and `node_modules` ignored by Git. Secret values must
  never be checked in or put in `wrangler.jsonc`.

## OPEN defects / blockers

**S1 — ChatGPT user authentication is NOT finished.**
The owner explicitly selected public No Auth to serve multiple MCP clients
including Gemini and ChatGPT. The Worker now uses
`AUTH_MODE=public_noauth` and mandates 4 Cloudflare rate limit
bindings (12/60s per-IP requests, 60/60s per-PoP requests,
4/60s per-IP `tools/call`, 20/60s per-PoP tool calls).
Missing/failed bindings deny service; blocked calls return HTTP 429.
Actual local Workerd emitted 429, and Node tests passed 39/39.
Cloudflare's separate Access app still intercepts HTTP 401 and has
not been disabled. Live anonymous 429/initialization and client E2E
are **not** verified.

**S2 — Cloudflare auth and deployment CLOSED.**
After user explicitly authorized device OAuth, `wrangler whoami`
confirmed the account. Scoped Worker was deployed once as
`tw01-forecast-mcp`, version
`51a7b747-dee5-48b9-95d9-b222aab3cdb8`.
Public URL: `https://tw01-forecast-mcp.prometheans152.workers.dev`.
Latest No Auth code deployed at
`437553a8-3810-44a1-beef-6830e745f256` with no Origin Secret;
separate TW01 Access continues to respond 401 at the edge.

**S3 — Oracle HTTPS origin verified; API token / true E2E OPEN.**
Owner-maintained `FORECASTENGINE_API_V1.md` now identifies
`https://161.33.19.220` with a public-trust certificate; independent
Windows HTTPS `/healthz` got 200 ready. Worker config pins this exact
origin, but origin bearer has not been handed off, so no real Oracle
POST through Workers has succeeded. The certificate renews on a
short schedule; its owner is responsible for renewal validation.

**S4 — Public anti-abuse controls deployed; global assurances limited.**
The 4 Cloudflare Rate Limiting bindings are included in live deployment
and local Workerd checks. Counters are per Cloudflare location and
eventually consistent, so not an exact global hard budget. Source IPs
may be shared by NAT/Google/ChatGPT clients. Before activating a
real Oracle backend ensure Oracle concurrency guards and TLS renewal
remain functional; verify production 429 after Access is removed.

**S5 — Third-party audit and end-to-end user tests outstanding.**
This is a same-session implementation + self-test only, not an
independent security review. Runtime tests do not establish production
Cloudflare security or ChatGPT client compatibility.

## Known limitations

- The strict JSON ingress preflight bounds size/depth and rejects duplicate
  JSON member names at all nesting levels before delegating protocol parsing
  to the official SDK. The Oracle owner separately rejects duplicate keys.
- Cloudflare `wrangler secret list` confirmed zero configured secrets
  on this **new** Worker. Real upstream origin is configured but cannot be
  called through Worker while protected secrets are absent.
- `/healthz` means `configured` if required values appear syntactically
  present, not that the Oracle API has been reached. Response states
  `upstream_live:not_probed`, `oracle_e2e:not_verified`.
- Remote API requests are anonymous A; the original Windows B-mode
  local web page and private records are unaffected and not reachable.

## Rollback / leak response

The new public Worker code currently cannot reach Oracle because its
private Secret is absent. Its fail-closed rollback baseline is version
`51a7b747-dee5-48b9-95d9-b222aab3cdb8`; the OAuth rollback version is
`ef1e515e-0c2c-4d8c-a9a2-681d7b85ff91`.
Preserve evidence and leave all original user files unchanged.
In any future compromise:
revoke the **TW01-only** Cloudflare Worker secrets and Oracle service
token, disable or roll back **only** the deployed `tw01-forecast-mcp`;
do not rotate unrelated COS/private-plugin keys without authorization.

Official sources:
https://developers.cloudflare.com/agents/model-context-protocol/apis/handler-api/
https://developers.openai.com/plugins/build/auth
https://developers.openai.com/plugins/deploy/submission
