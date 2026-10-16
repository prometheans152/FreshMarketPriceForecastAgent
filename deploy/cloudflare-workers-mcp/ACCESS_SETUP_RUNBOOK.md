# Remote MCP — Cloudflare Access Managed OAuth setup and remaining acceptance

> **HISTORICAL, NOT CURRENT.** The owner subsequently selected **No Auth**
> for one shared ChatGPT/Gemini MCP endpoint. The current working
> Cloudflare VPC → Oracle acceptance is documented in
> **`VPC_LIVE_ACCEPTANCE.md`**. Do not re-enable OAuth by following
> the old steps below without the owner's new authorization.

Status (2026-10-14): Worker **deployed and fail-closed**. The server-side
Oracle TLS endpoint has passed its own acceptance, but ChatGPT has not
authenticated through the new Worker and no Oracle POST via Worker is proven.

## Known non-secret identifiers

- MCP URL: `https://tw01-forecast-mcp.prometheans152.workers.dev/mcp`
- Dedicated Cloudflare Worker: `tw01-forecast-mcp`
- Access team domain: `https://falling-rain-7383.cloudflareaccess.com`
- Oracle HTTPS origin: `https://161.33.19.220`
- Access verification candidate version: `6aa73a74-fb09-458e-b3bc-10e02887b193`
- The **Application Audience / AUD** does **not** exist in Worker config yet.
- `FORECASTENGINE_API_TOKEN` has **not** been installed as a Worker Secret.

## Operator action A — configure ONLY this Worker's Access application

Cloudflare officially allows an individual `workers.dev` hostname to be
protected with a self-hosted Access application. Zero Trust **Free** is
already active. No new domain or upgraded plan is necessary.

1. Open the Zero Trust **Access controls → Applications** page:
   `https://dash.cloudflare.com/aacc8a3a24c5ef00efc530b6845878ce/one/access-controls/apps`.
2. Create a **Self-hosted** Access application named
   `TW01 Forecast MCP`, protecting **only**
   `tw01-forecast-mcp.prometheans152.workers.dev` (no scheme or path).
   Do **not** protect all Workers or alter unrelated Access applications.
3. Configure an **Allow** policy for your own login email first.
   Do not use Bypass or Everybody during initial verification.
   Your existing Cloudflare identity provider can authenticate via
   one-time PIN. Test a second user's independently allowed account
   only when explicitly ready for shared access.
4. Edit this app → **Advanced settings → Managed OAuth = On**.
   In its Managed OAuth settings, restrict **Allowed redirect URIs**
   to the actual HTTPS callback URI reported by ChatGPT when linking.
   Do not enable arbitrary localhost/loopback callbacks and do not
   make up an OAuth callback path. Leave short token lifetimes.
5. Save; copy the application's **Application Audience (AUD) tag**
   (non-secret) for setting `ACCESS_AUDIENCE` under `wrangler.jsonc`
   and redeploying this Worker only. Do not send any login session tokens
   or passwords. The Worker validates Access-signed RS256 JWT:
   issuer, AUD, signature, expiry and email claim, and fails closed
   without exact config.
6. Verify unauthenticated requests to `/mcp` are handled by Access
   Managed OAuth with a discovery-capable 401 challenge, not a bypass.

## Operator action B — manually install Oracle service token as a Secret

1. In **Workers & Pages** select ONLY `tw01-forecast-mcp`.
2. Under **Settings → Variables and Secrets**, add the secret named
   exactly `FORECASTENGINE_API_TOKEN`. Choose **Secret** (never plain Var).
3. Use the *Oracle owner's approved private handoff process* to put
   the TW01-only root-protected origin API token there. The Oracle name
   is `TW01_ORIGIN_API_TOKEN`; value must be identical, names differ.
   The Oracle owner retains root-only file ownership and can rotate keys.
4. Do not place the token into this conversation, command line,
   Markdown, Git, shared output or diagnostic logs. Do not reuse the
   older COS Tunnel key. When configured, use
   `npx wrangler secret list --name tw01-forecast-mcp` to confirm
   **the name only**; never display the value.

The automatic read-and-forward operation was explicitly prevented by a
safety check. Do not attempt to bypass that protection.

## Required acceptance after both operator actions

- Confirm Access OAuth discovery, login, callback and **authenticated**
  initialize/tools/list/tools/call through the real deployed Worker.
- Exactly two MCP tools: `get_market_quote` and anonymous-A
  `post_forecast`. Reject B mode, saving, reading private records, URL,
  files, arbitrary program execution, unknown tools and unknown fields.
- Verify legal `cabbage` / `中義市場`; 32 NTD/jin and 65 NTD/kg;
  explicit and omitted observed dates; accurate t+7/t+14 calendar dates;
  missing-weight boxes; very old dates; Oracle 401/403/429/5xx, timeout,
  request cancellation and recovery.
- Preserve and compare the entire **actual Oracle `engine_result`**
  for this call, including model/data versions, warnings, scopes, and
  deliberately null probability/interval. Do **not** use historical
  forecast fixture numbers as a new result or generate prices in Worker.
- Complete genuine **own ChatGPT → Cloudflare → Oracle → ChatGPT answer**
  first, then independently authenticate another person's ChatGPT to
  prove multi-user access. Mock, curl, SDK protocol or health alone
  must not be called ChatGPT E2E.
- Recheck per-user rate limiting and the oracle budget before other-user
  Access allowlisting. Check the short-lived Oracle TLS cert renewal.

## Known SDK/transport limitation

Current `@modelcontextprotocol/server@2.3.1` tool registration drops
the optional `securitySchemes` metadata in actual `tools/list`
(confirmed with a failing negative test). The design therefore relies
on Cloudflare Access **whole-resource Managed OAuth**, and its precise
behavior with a real ChatGPT Plugin client has not been verified.
Do not mark this limitation CLOSED until a real client connects.

## Fail-closed rollback

Only roll back the `tw01-forecast-mcp` Worker via its Cloudflare
deployment history. Known inert versions:
`51a7b747-dee5-48b9-95d9-b222aab3cdb8` (bearer test mode, no secrets)
and `6aa73a74-fb09-458e-b3bc-10e02887b193` (Access JWT mode, no AUD
or secret). Do not touch any other Worker, COS private Tunnel, Oracle
deployment or repository user edits.

## Official documentation

- https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/deploy/connect-chatgpt
