# Shared MCP — ChatGPT + Gemini Compatibility (2026-10-14)

> **Rename (2026-10-16/17):** names below are the new `fresh-market-price-agent-*` / `FMPA_*` ones.
> The Oracle host was migrated on 2026-10-17 except the certbot timer (`tw01-certbot-renew.*`);
> the new Worker `fresh-market-price-agent` is live (6/6 E2E), while ChatGPT still uses the old
> `tw01-forecast-mcp`, which stays up until the connector is switched. Progress: [RENAME_MIGRATION.md](../RENAME_MIGRATION.md).

> **CURRENT SERVER STATUS (2026-10-15):** The same public anonymous MCP
> URL has actually completed 6/6 live Cloudflare VPC → Oracle protocol
> and tool calls. The original Oracle backend Token is configured as a
> Cloudflare Secret and no end-user OAuth is required; the old Access
> application is no longer blocking requests. For current results and
> rollback, read **`VPC_LIVE_ACCEPTANCE.md`**. The interim statements
> farther below about inactive Access/Secret are historical. Separate
> ChatGPT/Gemini client UI linking and native model-triggered tools/call
> have NOT been independently tested in those apps.

## One endpoint, one model service

The intended **same remote MCP endpoint** is:

`https://fresh-market-price-agent.prometheans152.workers.dev/mcp`

Supported tools remain **exactly**:
- `get_market_quote` — current query of frozen public market data, not real-time individual shop prices.
- `post_forecast` — anonymous A-mode forecasts with exact observed-day t+7/t+14 from the frozen ForecastEngine.

No Gemini-specific ForecastEngine or additional Worker should be created.
Keep standard **Streamable HTTP MCP** transport, JSON-RPC initialize,
tools/list, tools/call, and tool schemas vendor-neutral.

## Google official documented support (not yet E2E tested for this project)

1. **Gemini API Interactions API**: Remote MCP over Streamable HTTP,
   `type: "mcp_server"`, `name: "fmpa_forecast"` (snake_case),
   `url` set to the endpoint above. Auth headers/credentials are
   optional and require proper user permission. No Gemini-specific model
   processing should be placed in Worker.
2. **Gemini CLI**: Remote MCP via `httpUrl` or
   `gemini mcp add --transport http fresh-market-price-agent-forecast <URL>`.
   The owner chose **public No Auth**, removing the need for
   Gemini-specific OAuth callback registration **once the separate
   Cloudflare Access app is disabled**.
3. **Gemini consumer web/mobile**: Official Google help describes a
   Custom Apps (Remote MCP URL) entry via gemini.google.com. Current
   eligibility requires a US adult personal Google account, Keep Activity
   enabled, and English; use may be tied to Gemini Spark.
   It is **not** safe to claim a Taiwan Google AI Pro consumer account
   has the custom-app entry. Also confirm its actual OAuth redirect URI
   rather than guessing one.
4. **ChatGPT**: Uses the same Remote MCP URL under No Auth after the
   edge Access application has been disabled and Oracle token provisioned.
   A genuine tools/call is still required to claim E2E.

Gemini CLI sample **config only** (do not put secrets into source):

```json
{
  "mcpServers": {
    "fresh-market-price-agent-forecast": {
      "httpUrl": "https://fresh-market-price-agent.prometheans152.workers.dev/mcp"
    }
  }
}
```

Gemini API Remote MCP Interactions example **tool descriptor only**:

```json
{
  "type": "mcp_server",
  "name": "fmpa_forecast",
  "url": "https://fresh-market-price-agent.prometheans152.workers.dev/mcp"
}
```

These examples are client connection instructions. The shared MCP
server has returned genuine Oracle values in standalone remote
protocol tests; it has **not** yet been exercised inside the
Gemini app or ChatGPT custom MCP UI.

## Owner-approved No Auth configuration and remaining blockers

Owner explicitly requested No Auth so both ChatGPT and Gemini
can use **the same remote MCP**. Worker version
`437553a8-3810-44a1-beef-6830e745f256` has
`AUTH_MODE=public_noauth` with four Cloudflare request/tool quota
bindings. Tests passed **39/39** and local Workerd demonstrated 429.

- **Cloudflare Access app `TW01 Forecast MCP` still ACTIVE:**
  it intercepts unauthenticated HTTP requests with OAuth 401.
  Disable/remove this exact app before No Auth is actually reachable;
  other Workers/Access apps must remain untouched.
- **Oracle backend Secret still missing:** the dedicated
  `FORECASTENGINE_API_TOKEN` must be manually added via approved
  private handling. **Never paste/token-log/share it**.
- **Client acceptance NOT RUN:** Gemini/ChatGPT cannot be marked
  E2E PASS until they really initialize/list and execute tools/call
  through the Worker to original Oracle ForecastEngine values.
- **Not an exact worldwide rate quota:** the Cloudflare rate limit
  binding is per location and eventually consistent. Strict request
  validation and Oracle's concurrency limits remain important.

No Auth means any HTTP client (not just Gemini and ChatGPT) may
consume the backend once enabled. Explicit owner approval and
resource limits are recorded in `PUBLIC_NOAUTH_HANDOFF.md`.

## Official source references

- https://ai.google.dev/gemini-api/docs/function-calling
- https://geminicli.com/docs/tools/mcp-server/
- https://support.google.com/gemini/answer/17209137
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/

## Current acceptance statement

Public No Auth Worker code deployed, but existing TW01 Access app
still performs OAuth 401 before the Worker. Oracle TLS health:
verified separately. Gemini MCP `tools/call` E2E:
**NOT VERIFIED**. ChatGPT MCP `tools/call` E2E:
**NOT VERIFIED**. Backend Worker Secret is still unprovisioned
at last verified check; recheck only secret **NAMES**, never values.
