import assert from "node:assert/strict";
import { test } from "node:test";
import worker from "../src/index.js";
import { getAuthMode, verifyIncomingRequest, PUBLIC_AUTH_MODE } from "../src/auth.js";
import { getOracleConfig } from "../src/oracle-client.js";
import { checkPublicLimits, RateLimitUnavailable } from "../src/rate-limit.js";
import { VALID_TEST_ENV } from "./fixtures.js";

const context = { waitUntil(p) { Promise.resolve(p).catch(() => {}); }, passThroughOnException() {} };
function fakeLimiter(max) {
  const counters = new Map();
  return { counters, async limit({ key }) {
    const count = 1 + (counters.get(key) || 0);
    counters.set(key, count);
    return { success: count <= max };
  } };
}
function publicEnv(overrides = {}) {
  return {
    ...VALID_TEST_ENV,
    MCP_CLIENT_BEARER_TOKEN: undefined,
    AUTH_MODE: PUBLIC_AUTH_MODE,
    RL_REQUESTS_IP: fakeLimiter(12),
    RL_REQUESTS_POP: fakeLimiter(60),
    RL_TOOLS_IP: fakeLimiter(4),
    RL_TOOLS_POP: fakeLimiter(20),
    ...overrides,
  };
}
function req(method, body = undefined, ip = "203.0.113.10") {
  return new Request("https://localhost/mcp", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "accept": "application/json, text/event-stream",
      host: "localhost",
      "cf-connecting-ip": ip,
    },
    body: JSON.stringify({ jsonrpc: "2.0", id: 3, method, params: body || {} }),
  });
}

test("noauth is explicit; public mode does not accept missing Oracle backend secret", async () => {
  const env = publicEnv();
  assert.equal(getAuthMode(env), PUBLIC_AUTH_MODE);
  assert.equal(getOracleConfig(env).base, VALID_TEST_ENV.FORECASTENGINE_BASE_URL);
  assert.equal(await verifyIncomingRequest(req("tools/list"), env), true);
  assert.throws(() => getOracleConfig({ ...env, FORECASTENGINE_API_TOKEN: undefined }));
  assert.throws(() => getAuthMode({ AUTH_MODE: "none" }));
  const locked = publicEnv({ FORECASTENGINE_API_TOKEN: undefined });
  assert.equal((await worker.fetch(req("tools/list"), locked, context)).status, 503);
  assert.equal((await worker.fetch(new Request("https://localhost/healthz"), locked, context)).status, 503);
});

test("production noauth fails closed when ANY rate limit binding is missing or broken", async () => {
  for (const binding of ["RL_REQUESTS_IP", "RL_REQUESTS_POP", "RL_TOOLS_IP", "RL_TOOLS_POP"]) {
    const env = publicEnv({ [binding]: undefined });
    assert.equal((await worker.fetch(req("tools/list"), env, context)).status, 503);
    assert.equal((await worker.fetch(new Request("https://localhost/healthz"), env, context)).status, 503);
  }
  const broken = publicEnv({ RL_REQUESTS_IP: { async limit() { throw Error("cannot reach Cloudflare counter"); } } });
  const res = await worker.fetch(req("tools/list"), broken, context);
  assert.equal(res.status, 503);
  assert.equal((await res.json()).code, "rate_limit_unavailable");
  const malformed = publicEnv({ RL_REQUESTS_POP: { async limit() { return {}; } } });
  assert.equal((await worker.fetch(req("tools/list"), malformed, context)).status, 503);
});

test("anonymous MCP initialize and tools/list work without Authorization or client token", async () => {
  const env = publicEnv();
  const initialized = await worker.fetch(req("initialize", {
    protocolVersion: "2025-06-18", capabilities: {},
    clientInfo: { name: "fresh-market-price-agent-public-test", version: "1" },
  }), env, context);
  assert.equal(initialized.status, 200);
  const listed = await worker.fetch(req("tools/list"), env, context);
  assert.equal(listed.status, 200);
  let text = await listed.text();
  if (text.startsWith("event:")) text = text.split(/\r?\n/).find(s => s.startsWith("data: ")).slice(6);
  const result = JSON.parse(text);
  assert.deepEqual(result.result.tools.map(tool => tool.name), ["get_market_quote", "post_forecast"]);
  assert.ok(result.result.tools.every(t => t.securitySchemes === undefined), "no OAuth requirement advertised");
});

test("anonymous ordinary requests limited to 12/IP/min (simulated binding semantics)", async () => {
  const env = publicEnv({ FORECASTENGINE_API_TOKEN: undefined });
  for (let i = 0; i < 12; i++)
    assert.equal((await worker.fetch(req("tools/list"), env, context)).status, 503);
  const rate = await worker.fetch(req("tools/list"), env, context);
  assert.equal(rate.status, 429);
  assert.equal(rate.headers.get("retry-after"), "60");
  assert.equal((await rate.json()).code, "rate_limited");
  assert.equal((await worker.fetch(req("tools/list", undefined, "203.0.113.11"), env, context)).status, 503,
    "different IP has independent quota");
});

test("anonymous health endpoint also participates in source rate limiting", async () => {
  const env = publicEnv({ FORECASTENGINE_API_TOKEN: undefined });
  const health = new Request("https://localhost/healthz", {
    headers: { "cf-connecting-ip": "203.0.113.55" },
  });
  for (let i = 0; i < 12; i++)
    assert.equal((await worker.fetch(health, env, context)).status, 503);
  const blocked = await worker.fetch(health, env, context);
  assert.equal(blocked.status, 429);
  assert.equal(blocked.headers.get("retry-after"), "60");
});

test("tool calls have independent stricter 4/IP/min limit before private Oracle token check", async () => {
  const env = publicEnv({ FORECASTENGINE_API_TOKEN: undefined });
  const params = { name: "get_market_quote", arguments: { crop_id: "cabbage", market_id: "中義市場" } };
  for (let i = 0; i < 4; i++)
    assert.equal((await worker.fetch(req("tools/call", params), env, context)).status, 503);
  const blocked = await worker.fetch(req("tools/call", params), env, context);
  assert.equal(blocked.status, 429);
  assert.equal((await blocked.json()).code, "rate_limited");
  assert.equal(env.RL_TOOLS_IP.counters.get("203.0.113.10"), 5);
  assert.equal(env.RL_TOOLS_POP.counters.get("all-mcp-callers"), 4);
});

test("aggregate PoP quotas remain in force across source IPs", async () => {
  const env = publicEnv({ RL_REQUESTS_POP: fakeLimiter(3) });
  for (const ip of ["203.0.113.12", "203.0.113.13", "203.0.113.14"]) {
    assert.equal(await checkPublicLimits(req("tools/list", undefined, ip), env), true);
  }
  assert.equal(await checkPublicLimits(req("tools/list", undefined, "203.0.113.15"), env), false);
  assert.equal(env.RL_REQUESTS_POP.counters.get("all-mcp-callers"), 4);
});

test("forged X-Forwarded-For never chooses the bucket and missing Cloudflare IP uses shared unknown", async () => {
  const env = publicEnv();
  const r = new Request("https://localhost/mcp", { headers: { "x-forwarded-for": "1.2.3.4" } });
  assert.equal(await checkPublicLimits(r, env), true);
  assert.equal(env.RL_REQUESTS_IP.counters.get("unknown"), 1);
  const broken = publicEnv({ RL_REQUESTS_IP: null });
  await assert.rejects(() => checkPublicLimits(r, broken), RateLimitUnavailable);
});
