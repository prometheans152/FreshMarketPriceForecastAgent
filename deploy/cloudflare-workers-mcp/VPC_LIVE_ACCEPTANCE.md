# TW01 — Cloudflare Workers VPC Remote MCP final server acceptance

**Original Worker acceptance: 2026-10-15 (Asia/Taipei).**
**Independently re-verified after Docker cutover: 2026-10-15.**

**Result: SERVER-TO-ORACLE REMOTE MCP E2E PASS.**
**ChatGPT and Gemini application-level user connection: NOT YET VERIFIED.**

This is the **current** source of truth for the Workers deployment.
Older `ACCESS_SETUP_RUNBOOK.md`, `PUBLIC_NOAUTH_HANDOFF.md`,
and earlier dated evidence describe historical blocked states only.
The Oracle API contract is owned by the independent Oracle project:
`../../docs/deployment/FORECASTENGINE_API_V1.md` (READ ONLY).

## Live deployed architecture (no privately managed DNS)

```text
ChatGPT / Gemini / any standards-compliant Streamable HTTP MCP client
       |
       | Anonymous HTTPS, /mcp (no OAuth; public)
       v
Cloudflare Worker: tw01-forecast-mcp
       | Four mandatory Cloudflare approximate per-IP/per-PoP rate limits
       | Exactly get_market_quote and post_forecast, no B, no records
       | PRIVATE FORECASTENGINE_API_TOKEN Secret, never returned
       v
VPC_ORACLE_FORECAST binding (Workers VPC, Free Beta)
       | VPC service 01a13a39-0554-7ca0-b29a-38c70d886752
       | Destination 10.0.0.86:443 (Oracle private NIC)
       | HTTPS with verify_full, Host/SNI from 161.33.19.220 IP-SAN
       v
Cloudflare Tunnel 1aa5adeb-6df0-4ba0-ac66-356499e1d6ab
       | Cloudflared service installed on Oracle VPS, QUIC
       v
Oracle HOST Nginx HTTPS 443 (original Let's Encrypt IP-SAN)
       | Fixed Bearer-protected /v1/market-quote and /v1/forecast
       v
HOST 127.0.0.1:8080 -> tw01-oracle-web-1 (Docker Nginx)
       | Internal Docker network; no public 8767/9000
       v
tw01-oracle-forecast-1 (Docker internal API 8767)
       | Original frozen 3-crop RF 7-day / HGB 14-day v0.1.0
       |
       +-- Separate tw01-oracle-mcp-1 at Docker internal 9000:
           NOT used by the Cloudflare Worker
```

The URL used **inside the Worker** is
`https://161.33.19.220/v1/market-quote` or
`https://161.33.19.220/v1/forecast`, for HTTP Host/SNI and the
publicly trusted IP-SAN certificate. The bound VPC Service—not
internet DNS—fixes the physical network destination to
`10.0.0.86:443`. The Worker never falls back to global public
`fetch()` if VPC fails.

**Public MCP URL (one URL for both platforms):**
`https://tw01-forecast-mcp.prometheans152.workers.dev/mcp`

**Deployed Worker version:** `ba488561-76c3-4a3d-9479-e1b71340e401`
(Cloudflare deployment 100%; Wrangler 4.151.0).

No account upgrade, domain purchase, DNS setup, model retraining,
model-data changes, Git commit or Git push were performed.

## Oracle Docker Compose cutover — fresh 2026-10-15 verification

The old native `tw01-forecastengine.service` is now **inactive**.
Oracle runs three Docker Compose containers from
`/opt/tw01-docker/stacks/20261015_120629`:
`tw01-oracle-forecast-1` (original RF/HGB and separate new web
models), `tw01-oracle-web-1` (Nginx and API proxy), and
`tw01-oracle-mcp-1` (separate self-hosted MCP).
Oracle HOST Nginx remains on HTTPS 443 and proxies its nine fixed
TW01 API/web routes to host loopback `127.0.0.1:8080`.
No host/public Docker API 8767 or MCP 9000 listener exists.

**No Worker code, `wrangler.jsonc`, VPC Service, Tunnel, Bearer
Secret or Cloudflare deployment change was needed.**
`VPC_ORACLE_FORECAST` still targets Oracle private
`10.0.0.86:443` with `verify_full`, preserving TLS IP-SAN
identity from `https://161.33.19.220`. The existing Worker
continues to call only `POST /v1/market-quote` and
`POST /v1/forecast`. It does NOT switch to Docker's
private `/mcp` nor expose the new 57 HGB web-model crops.

**Fresh Windows external MCP suite (2026-10-15 05:13:45 UTC):**
`initialize`, `tools/list` (exactly two), a new public quote,
two anonymous A forecast calls (32 NTD/taiwan-jin and
65 NTD/kg), and rejection of B/save fields: **6/6 PASS**.
All successful original Oracle response envelopes matched the
validator, with `model_version=0.1.0`,
`data_version=172dffc76e82`, observed `t=2026-10-14`,
and exact `t+7=2026-10-21` / `t+14=2026-10-28`.
The public market quote is observed 2026-10-02, is **not**
a live store price, and there is **no real-store due-date
accuracy validation**.

Two original Docker-container model SHA-256 values matched
the Oracle migration baseline **2/2**; `/web/` returned 200,
direct Oracle `/mcp` 404, and Bearer-less POSTs to
the two original API paths both 401 (security **4/4 PASS**).
Local Node regressions **45/45 PASS**, Wrangler dry-run exit 0.
No model training, token rotation or Worker deployment occurred.

Latest evidence:
`../../outputs/quality_runs/workers_mcp_docker_sync_20261015_131055_Windows5800X_c410f8`
(new complete `remote_mcp_6cases_fresh.json` and
`ACCEPTANCE_REPORT.md`). Original Oracle migration evidence:
`../../outputs/quality_runs/oracle_docker_migration_20261015_120629_Windows5800X`.

**Rollback:** No Cloudflare rollback is needed. In an authorized
Oracle Docker incident, follow
`../docker-tw01/oracle/ORACLE_DOCKER_OPERATIONS.md`:
first run
`sudo python3 /opt/tw01-docker/ops/rollback_oracle.py --tag 20261015_120629 --check-only`.
Only when explicitly authorized execute without `--check-only`
to restore the original native ForecastEngine and Nginx backup
`/etc/nginx/sites-available/tw01-tls.conf.pre-docker-20261015_120629`.
Do not delete or rotate existing Workers, Tunnel, Tokens,
private data or other services.

## Real external HTTP acceptance

Actual separate Windows Node client -> Cloudflare Workers.dev ->
VPC binding -> Oracle ForecastEngine, **not mocked**.

| Case | Expected / actual |
| --- | --- |
| JSON-RPC `initialize` | HTTP 200 PASS, server `tw01-forecastengine-remote` |
| JSON-RPC `tools/list` | HTTP 200 PASS, exactly `get_market_quote` and `post_forecast` |
| `get_market_quote` Taichung 中義市場 / cabbage | HTTP 200 PASS, public average **30 NTD/taiwan jin**, observed **2026-10-02**, queried 2026-10-15 |
| `post_forecast` anonymous A, synthetic shop input 32 NTD/taiwan jin, observed 2026-10-14 | HTTP 200 PASS; 2026-10-21 t+7 **30.4** and 2026-10-28 t+14 **30.7** NTD/taiwan jin |
| `post_forecast` anonymous A, synthetic shop input 65 NTD/kg, observed 2026-10-14 | HTTP 200 PASS; 2026-10-21 t+7 **61.8** and 2026-10-28 t+14 **62.3** NTD/kg |
| Reject forbidden `mode=both` and `save_record=true` | HTTP 200 with MCP `isError=true`, PASS, no structured result |

**Real remote positive/negative suite: 6/6 PASS.** Every successful
`tools/call` was checked against the local READ-ONLY Oracle v1
envelope validator; `input_echo`, `engine_result`, original
content text, full raw metadata, observation day and t+7/t+14 calendar
dates passed. Quote is NOT a real-time shop price, and synthetic
shop-price examples are NOT validated against a real shop.

Forecast metadata: model_version `0.1.0`,
data_version `172dffc76e82`,
public_data_cutoff `2026-10-02`; classification `flat` in both
test cases; probability and intervals remain `null`;
validation_scope is `unvalidated`. No new values, forecasts,
trends or confidence were calculated inside Workers.

An independent invalid `delete_record` request returned JSON-RPC
error **-32602** (Tool not found), without structured result.

## Rate limiting

| Cloudflare Workers Rate Limit binding | Nominal threshold |
| --- | --- |
| `RL_REQUESTS_IP` | 12 requests / 60 seconds / ingress IP |
| `RL_REQUESTS_POP` | 60 requests / 60 seconds / Cloudflare location |
| `RL_TOOLS_IP` | 4 `tools/call` / 60 seconds / ingress IP |
| `RL_TOOLS_POP` | 20 `tools/call` / 60 seconds / Cloudflare location |

**Live external HTTP 429 PASS**: after six bounded no-op,
unrecognized-tool requests in the second rate-limit test, the
sixth returned 429 with `Retry-After: 60` and code `rate_limited`.
No Oracle work or private record access was performed in this test.

The *first* brief burst of three invalid tool calls did not show 429.
This is consistent with Cloudflare's documented **per-location,
eventually-consistent, deliberately permissive** counters: they are
not precise accounting or an exact global hard quota. All bindings
fail closed if unavailable. It is public No Auth, so anonymous abuse
remains a residual risk; the existing Oracle resource limits must
remain in force.

## Security and operations

- `FORECASTENGINE_API_TOKEN` is a Cloudflare `secret_text`;
  only its name/type was queried. No value was printed or archived.
- Valid publicly trusted HTTPS/IP-SAN was independently confirmed
  from Windows and Oracle; VPC Service `verify_full` remains enabled.
- VPC `fetch()` uses `redirect:"manual"` because Cloudflare's VPC
  binding does not accept `redirect:"error"`. ALL returned HTTP 3xx
  are rejected in code without following the redirect. This was the
  **verified root cause** of the initially failing legitimate tools.
- Initial VPC target `127.0.0.1:443` was changed to Oracle private
  NIC `10.0.0.86:443`; both IPs passed independent Oracle local TLS
  tests. Do not claim that loopback address was proven defective;
  the exact VPC error was the unsupported redirect setting.
- **At the original pre-Docker snapshot only:** Oracle
  `tw01-cloudflared.service`, `tw01-forecastengine.service` and
  `nginx.service` were active. **Current Docker state:**
  `tw01-forecastengine.service` is inactive; `tw01-cloudflared.service`,
  `docker.service`, `containerd.service` and `nginx.service` are
  active. The three Docker containers replace the old native process.
- Existing public Oracle browser site
  `https://161.33.19.220/web/`: HTTP 200 text/html.
- SEALED historical model/data/web baseline hashes and sizes:
  **19/19 match**, no changed protected files.
- Node tests after real redirect fix: **45/45 PASS**,
  Wrangler bundle dry-run exit 0. Prior historical failing tests
  and HTTP failures were preserved rather than overwritten.
- No original Windows A/B model, local records, old COS personal
  Tunnel or unrelated Cloudflare Worker were modified.

### Failure/recovery and rollback

If Oracle output stops, check (without exposing tokens):

```text
ssh -i "$env:USERPROFILE\.ssh\oracle_amd_ed25519" ubuntu@161.33.19.220
systemctl is-active tw01-cloudflared.service nginx.service docker.service containerd.service
cd /opt/tw01-docker/stacks/20261015_120629
sudo docker compose -p tw01-oracle -f compose.yaml -f compose.oracle.yaml ps
sudo nginx -t
systemctl show tw01-cloudflared.service -p NRestarts -p MemoryCurrent
npx wrangler vpc service get 01a13a39-0554-7ca0-b29a-38c70d886752
npx wrangler secret list --name tw01-forecast-mcp
```

Run the last two Wrangler commands from the Windows COS project, not
inside Ubuntu. Never include secret values in diagnostic output.
Back out **only** the TW01 Worker/VPC changes if necessary;
known earlier VPC version:
`9c50fdb4-8e99-4895-aa33-37a2ddad5e16` (before HTTPS redirect fix,
not a working forecast version). Previous public plain Worker version:
`437553a8-3810-44a1-beef-6830e745f256` (not working with IP URL).
Keep Oracle ForecastEngine and Nginx unchanged. Preserve SEALED/CORE.

## Actual evidence, immutable run folder

Root:
`C:\Users\prometheans\Documents\AIOT_FinishProject\outputs\quality_runs\workers_vpc_live_acceptance_20261014_234747_Windows5800X_a8839a`

- `real_full_remote_mcp_acceptance_final.json` — complete actual
  six-case full MCP envelopes, output text and pass criteria.
- `real_full_remote_mcp_acceptance_final.log` — six real HTTP cases,
  exit 0.
- `real_vpc_forecast_32jin_65kg.json` — two independent actual
  Oracle forecast responses, contract checked, exit 0.
- `real_rate_limit_bounded_second_pass.json` — actual production
  429 after 6 invalid calls; first unsuccessful rate probe preserved
  as `real_cloudflare_public_rate_limit.json`.
- `protected_19_sha256_check.json` — 19/19 unchanged.
- `npm_test_redirect_fix_final.log` — 45/45 node tests.
- `wrangler_check_redirect_fix_final.log` — four rate-limit bindings
  + VPC binding.
- `wrangler_deploy_redirect_fix_final.log` — exact deployed Worker
  version and successful deployment.
- `vpc_service_private_ip_verified.log` — fixed private destination,
  TLS verify_full; `vpc_service_before_private_ip_update.log` records
  original destination for historical comparison.
- Initial 3/6 test failure and safe VPC redirect troubleshooting
  were retained in earlier log filenames, not rewritten.

## Remaining non-server acceptance

**ChatGPT UI and Gemini consumer/CLI application E2E have not been
independently verified in this round.** Users can now configure
the SAME anonymous Remote MCP URL without OAuth, where their client
supports custom Remote MCP. Actual ChatGPT application linking
requires the user to add a custom MCP server in ChatGPT and accept
its warnings; Gemini CLI is not installed on Windows 5800X.
Consumer Gemini custom MCP eligibility varies by region/account.
Do **not** say those separate applications have executed
`tools/call` until proven from the respective clients.

### Client configuration

In ChatGPT's Add custom MCP server interface:
`TW01 菜價預測`, description
`臺中市場公開行情與匿名 A 模式 7／14 天預測`,
Server URL `https://tw01-forecast-mcp.prometheans152.workers.dev/mcp`,
authentication `No authentication`.

In Gemini CLI:
`gemini mcp add --transport http tw01-forecast https://tw01-forecast-mcp.prometheans152.workers.dev/mcp`.

This is a public untrusted-client endpoint with approximate rate
limits; it requires no per-user OAuth, but any HTTP client can call it.
