# Fresh Market Price Forecast Agent Remote MCP — Cloudflare VPC → Oracle server E2E PASS

> **Rename (2026-10-16):** names below are the new `fresh-market-price-agent-*` / `FMPA_*` ones.
> Until [RENAME_MIGRATION.md](../RENAME_MIGRATION.md) has been carried out, the live Oracle host and Worker
> still use the old `tw01-*` names; before migration, operate or roll back with this file as of
> `main@1062818`.

This is ONLY the new **first-tier Cloudflare MCP adapter**. The Windows browser
and personal stdio/Tunnel plugin remain untouched. This project does not load
or train any model, store shop prices, or access the previous local record DB.

## Deployment status (2026-10-15)

**Current authoritative acceptance: [VPC_LIVE_ACCEPTANCE.md](VPC_LIVE_ACCEPTANCE.md).**
The older `PUBLIC_NOAUTH_HANDOFF.md` and `ACCESS_SETUP_RUNBOOK.md`
are historical setup notes, **not** the present status.

- **WORKING remote MCP server**, version
  `ba488561-76c3-4a3d-9479-e1b71340e401`:
  `https://fresh-market-price-agent.prometheans152.workers.dev/mcp`.
- **Production No Auth**: custom Streamable HTTP MCP clients can reach
  `initialize`, `tools/list` and `tools/call`. The owner-only
  Cloudflare Access gate has been removed from this route.
- **Dedicated VPC Service and Tunnel active**: the Worker uses
  `VPC_ORACLE_FORECAST` to reach Oracle's **private**
  `10.0.0.86:443`; `verify_full` checks the original Oracle
  `161.33.19.220` IP-SAN HTTPS certificate. No domain/DNS required.
- **Private backend credential present**: Cloudflare
  `FORECASTENGINE_API_TOKEN` exists as `secret_text`; its value
  has never been printed or committed.
- **Genuine end-to-end server acceptance: 6/6 PASS**, live public
  market quote and two synthetic anonymous A forecasts through
  Cloudflare VPC → Oracle. Strict full-envelope equality validated.
  Live production HTTP **429** observed in a bounded invalid-tool
  burst; approximate Cloudflare limits are **not** global hard quotas.
- **45/45** Node tests PASS; the original model/data hash baseline is
  **19/19 unchanged**; existing Oracle web page HTTP 200.
- **Client UI pending**: individual ChatGPT and Gemini apps have not
  independently connected and called tools in their own interfaces.
  Gemini CLI is not installed on the Windows host.
- **Oracle Docker Compose cutover reverified (2026-10-15)**:
  same Worker version, VPC and Bearer Secret remain valid without
  changes. Fresh real external MCP **6/6 PASS**, Docker original
  RF/HGB hashes **2/2 PASS**, Node tests **45/45 PASS**.
  See `VPC_LIVE_ACCEPTANCE.md` for new evidence and rollback.

The agreement of record is the owner-maintained read-only
`../../docs/deployment/FORECASTENGINE_API_V1.md`. It was created by the
independent Oracle conversation during this implementation; this project
only reads it and never edits that file.

## Current Oracle Origin network path (Docker Compose, 2026-10-15)

`fresh-market-price-agent` still uses the original `VPC_ORACLE_FORECAST`
binding (VPC Service `01a13a39-0554-7ca0-b29a-38c70d886752`).
The existing Tunnel `1aa5adeb-6df0-4ba0-ac66-356499e1d6ab`
delivers it to Oracle's **private NIC** `10.0.0.86:443`.
The Worker URL `https://161.33.19.220` provides the original
IP-SAN certificate identity; `verify_full` remains required.

Oracle's host Nginx terminates HTTPS 443 and now proxies
the original Bearer-protected `POST /v1/market-quote` and
`POST /v1/forecast` through host `127.0.0.1:8080` to
Docker Web Nginx `fresh-market-price-agent-oracle-web-1`, which calls
`fresh-market-price-agent-oracle-forecast-1` on the Docker-private network.
`fresh-market-price-agent-oracle-mcp-1` at Docker internal port 9000 is a **separate
self-hostable MCP, not the Cloudflare Workers upstream**.
Neither Docker 8767 nor 9000 is publicly/host published.
The old native `fresh-market-price-agent-forecastengine.service` is **inactive**.

Original Workers MCP v1 still has exactly `get_market_quote`
and `post_forecast` for `cabbage`, `bok_choy`,
`sponge_gourd`; anonymous A uses original RF (t+7)
and HGB (t+14), model `0.1.0`. The expanded 61-product
Docker web catalog and newly trained 57-crop HGB models do
**not** extend this v1 tool contract. No B, saving, private
records, arbitrary files or URLs are allowed.

**Oracle Docker stack:** `/opt/fresh-market-price-agent-docker/stacks/20261015_120629`.
**Fresh Windows verification:** 
`../../outputs/quality_runs/workers_mcp_docker_sync_20261015_131055_Windows5800X_c410f8`
(actual `remote_mcp_6cases_fresh.json` and report).
**Original Oracle Docker owner runbook:**
`../docker/oracle/ORACLE_DOCKER_OPERATIONS.md`.

**No Worker redeployment, VPC/Tunnel rebuilding, Token changes
or Docker-origin URL adjustments are needed.** For a Docker-only
fault first use `sudo python3 /opt/fresh-market-price-agent-docker/ops/rollback_oracle.py
--tag 20261015_120629 --check-only`, and execute a real
rollback only with owner authorization. Keep unrelated Workers,
prior SEALED/CORE, private records and current Origin Secrets.

## Layout

```
src/contracts.js        Strict tool input/output and frozen-response checks
src/server.js           Only two MCP tools (v2 SDK)
src/index.js            Worker ingress, auth gate, limits, /mcp transport
src/auth.js             Three explicit modes, public_noauth chosen for Worker
src/rate-limit.js       Mandatory Cloudflare source/PoP quotas, fail-closed
src/oracle-client.js    Fixed HTTPS/VPC Oracle API relay; no ML/record storage
wrangler.jsonc          Public No Auth, four limits, only this project's VPC binding
.dev.vars.example       Names only; never copy production secrets to Git
test/                   Mock, protocol, error, timeout and live workerd probes
VPC_LIVE_ACCEPTANCE.md  Current full 6/6 real public remote MCP acceptance
```

## Windows local reproduction

```powershell
cd C:\Users\prometheans\Documents\AIOT_FinishProject\deploy\cloudflare-workers-mcp
npm ci
npm test
npm run check
```

The 45 Node tests exercise simulated Cloudflare bindings and the
real MCP SDK without exposing any Oracle credentials. For actual
server acceptance, use the separate live remote script:

```powershell
node test/real-remote-acceptance.mjs 'C:\private\fresh-market-price-agent-real-remote-acceptance.json'
```

Its JSON contains **actual** Oracle tool envelopes; keep it in a
private quality_runs directory, not a public Git commit. The script
produces four tool calls and can intentionally hit the approximate
60-second public rate limit if rerun immediately. The old
`test/live-mcp-probe.mjs` is preserved as a **historical local
legacy-bearer probe** and does not represent the current No Auth VPC
production settings. Do not place the production Oracle Secret into
`.dev.vars`.

## Client connection (remaining per-app action)

Server deployment and real MCP/Oracle tool verification are complete.
To finish individual app integration, add the existing URL in
ChatGPT's **Add custom MCP server** UI with **No authentication**,
or in Gemini CLI use:

```bash
gemini mcp add --transport http fresh-market-price-agent-forecast https://fresh-market-price-agent.prometheans152.workers.dev/mcp
```

The ChatGPT/Gemini native client must itself call one of the two
tools before **client-level** E2E can be called PASS. Consumer Gemini
custom-app availability is account- and region-dependent.

## Rollback

Current successful VPC version is
`ba488561-76c3-4a3d-9479-e1b71340e401`. If an unsafe future
change occurs, roll back **only** `fresh-market-price-agent`
to this known-good version. A prior inert OAuth version
`51a7b747-dee5-48b9-95d9-b222aab3cdb8` can be used to
temporarily disable tool functionality if required. Keep the
Cloudflare Tunnel, original Oracle ForecastEngine and other Workers
untouched unless separately authorized.
No `git reset --hard`, `git clean`, blanket deletion, or old SEALED/CORE
backup restore is authorized. Existing dirty repository changes are owned by
the user and must remain intact.

## References checked

- https://developers.cloudflare.com/agents/model-context-protocol/apis/handler-api/
- https://developers.cloudflare.com/agents/model-context-protocol/guides/remote-mcp-server/
- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/deploy/submission
