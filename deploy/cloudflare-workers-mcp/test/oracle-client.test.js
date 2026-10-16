import assert from "node:assert/strict";
import { test } from "node:test";
import { callForecastEngine, getOracleConfig, classifyVPCError, safeVPCDiagnostic, UpstreamFailure } from "../src/oracle-client.js";
import { VALID_TEST_ENV, quoteArgs, forecastArgs, quoteFixture, forecastFixture, quoteEnvelopeFixture, forecastEnvelopeFixture, fakeResponse } from "./fixtures.js";

const checkFail = async (fn, code) => {
  await assert.rejects(fn, (err) => err instanceof UpstreamFailure && err.code === code);
};

test("configuration requires distinct secrets and verified HTTPS base", () => {
  assert.equal(getOracleConfig(VALID_TEST_ENV).base, VALID_TEST_ENV.FORECASTENGINE_BASE_URL);
  assert.equal(getOracleConfig({ ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://8.8.8.8" }).base, "https://8.8.8.8");
  for (const env of [
    { ...VALID_TEST_ENV, MCP_CLIENT_BEARER_TOKEN: "" },
    { ...VALID_TEST_ENV, FORECASTENGINE_API_TOKEN: VALID_TEST_ENV.MCP_CLIENT_BEARER_TOKEN },
    { ...VALID_TEST_ENV, FORECASTENGINE_API_TOKEN: "" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "http://example.net" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://127.0.0.1" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://10.0.0.3" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://172.16.0.1" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://100.64.0.1" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://169.254.0.1" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://198.51.100.15" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://example.net/path" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://username:password@example.net" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://example.net?token=secret" },
    { ...VALID_TEST_ENV, FORECASTENGINE_BASE_URL: "https://placeholder.example" },
    { ...VALID_TEST_ENV, FORECASTENGINE_ALLOWED_HOSTNAME: "wrong.example.com" },
    { ...VALID_TEST_ENV, UPSTREAM_TIMEOUT_MS: "99999" },
  ]) assert.throws(() => getOracleConfig(env), UpstreamFailure);
});

test("VPC-only Oracle connection routes via pinned service and preserves original HTTPS IP-SAN URL", async () => {
  let boundCalls = 0;
  let ambientFetchCalls = 0;
  const vpc = {
    async fetch(url, options) {
      boundCalls++;
      assert.equal(url, "https://161.33.19.220/v1/market-quote");
      assert.equal(options.method, "POST");
      assert.equal(options.redirect, "manual");
      assert.equal(options.headers.authorization, "Bearer " + VALID_TEST_ENV.FORECASTENGINE_API_TOKEN);
      assert.deepEqual(JSON.parse(options.body), quoteArgs);
      return fakeResponse(quoteEnvelopeFixture());
    },
  };
  const env = {
    ...VALID_TEST_ENV,
    FORECASTENGINE_BASE_URL: "https://161.33.19.220",
    FORECASTENGINE_ALLOWED_HOSTNAME: "161.33.19.220",
    FORECASTENGINE_TRANSPORT: "vpc_service",
    VPC_ORACLE_FORECAST: vpc,
  };
  assert.equal(getOracleConfig(env).transport, "vpc_service");
  const result = await callForecastEngine("get_market_quote", quoteArgs, env, () => {
    ambientFetchCalls++;
    throw new Error("PUBLIC FETCH MUST NEVER RUN");
  });
  assert.deepEqual(result, quoteEnvelopeFixture());
  assert.equal(boundCalls, 1);
  assert.equal(ambientFetchCalls, 0);
});

test("VPC mode fails closed on missing binding; no token or unsupported transport cannot bypass", async () => {
  const env = { ...VALID_TEST_ENV, FORECASTENGINE_TRANSPORT: "vpc_service" };
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, env,
    async () => { throw new Error("public internet fallback forbidden"); }), "not_configured");
  assert.throws(() => getOracleConfig({
    ...env, VPC_ORACLE_FORECAST: { fetch: false },
  }), UpstreamFailure);
  assert.throws(() => getOracleConfig({
    ...env, FORECASTENGINE_TRANSPORT: "disabled",
  }), UpstreamFailure);
  assert.throws(() => getOracleConfig({
    ...env,
    VPC_ORACLE_FORECAST: { async fetch() { throw new Error("must not reach when unconfigured"); } },
    FORECASTENGINE_API_TOKEN: undefined,
  }), UpstreamFailure);
});

test("VPC fetch rejection is a sanitized failure, never retries or falls back", async () => {
  let count = 0;
  const env = {
    ...VALID_TEST_ENV,
    FORECASTENGINE_TRANSPORT: "vpc_service",
    VPC_ORACLE_FORECAST: {
      async fetch() {
        count++;
        throw new Error("TLS tunnel not yet connected");
      },
    },
  };
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, env,
    () => { throw new Error("Never use ambient fallback"); }), "vpc_unclassified");
  assert.equal(count, 1);
});

test("VPC manual redirect does not follow any 3xx and never leaks backend credential to redirect target", async () => {
  let requests = 0;
  const env = {
    ...VALID_TEST_ENV,
    FORECASTENGINE_TRANSPORT: "vpc_service",
    VPC_ORACLE_FORECAST: { async fetch(_url, init) {
      requests++;
      assert.equal(init.redirect, "manual");
      return new Response(null, {
        status: 302,
        headers: { location: "https://other-origin.example/steal-auth" },
      });
    } },
  };
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, env,
    async () => { throw Error("Ambient fetch must never be called"); }), "redirect_rejected");
  assert.equal(requests, 1);
});

test("VPC error classification exposes only documented category, never unsafe exception", async () => {
  assert.equal(classifyVPCError(new Error("Error: ProxyError: destination_ip_prohibited")), "destination_ip_prohibited");
  assert.equal(classifyVPCError(new Error("ProxyError: tls_certificate_error; authorization Bearer NEVER_LOG_SECRET")), "tls_certificate_error");
  assert.equal(classifyVPCError(new Error("Token SECRET and https://untrusted.example/private")), "unclassified");
  const env = {
    ...VALID_TEST_ENV,
    FORECASTENGINE_TRANSPORT: "vpc_service",
    VPC_ORACLE_FORECAST: { async fetch() {
      throw new Error("ProxyError: destination_unavailable bearer DO_NOT_REFLECT_TOKEN");
    } },
  };
  try {
    await callForecastEngine("get_market_quote", quoteArgs, env);
    assert.fail("Network errors must fail closed");
  } catch (e) {
    assert.equal(e.code, "vpc_destination_unavailable");
    assert.match(e.message, /destination_unavailable/);
    assert.doesNotMatch(e.message, /DO_NOT_REFLECT_TOKEN/);
  }
});

test("temporary VPC diagnostic log redacts URLs, numerals, token words and long values", () => {
  const err = new TypeError(
    "VPC service https://161.33.19.220/v1/forecast failed: " +
    "Bearer abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 " +
    "token=abcdefghijklmnopqrstuvwxyz01234567890123456789 error 403"
  );
  const record = safeVPCDiagnostic(err);
  assert.equal(record.error_name, "TypeError");
  assert.doesNotMatch(JSON.stringify(record), /161\.33\.19\.220|abcde|0123456789|403|Bearer/);
  assert.match(record.redacted_category, /ENDPOINT/);
});
test("quote uses POST /v1/market-quote; raw original response survives byte-for-byte values", async () => {
  const raw = quoteEnvelopeFixture();
  let count = 0;
  const actual = await callForecastEngine("get_market_quote", quoteArgs, VALID_TEST_ENV, async (url, opt) => {
    ++count;
    assert.equal(url, VALID_TEST_ENV.FORECASTENGINE_BASE_URL + "/v1/market-quote");
    assert.equal(opt.method, "POST");
    assert.equal(opt.redirect, "error");
    assert.equal(opt.headers.authorization, "Bearer " + VALID_TEST_ENV.FORECASTENGINE_API_TOKEN);
    assert.deepEqual(JSON.parse(opt.body), quoteArgs);
    return fakeResponse(raw);
  });
  assert.strictEqual(count, 1);
  assert.deepEqual(actual, raw);
});
test("forecast 32/jin and 65/kg do NOT change Oracle's numerical model values", async () => {
  for (const price of [32, 65]) {
    const args = { ...forecastArgs, current_price: price, price_unit: price === 32 ? "NTD_per_taiwan_jin" : "NTD_per_kg" };
    const raw = forecastEnvelopeFixture(args);
    const result = await callForecastEngine("post_forecast", args, VALID_TEST_ENV, async (url, opt) => {
      assert.equal(url, VALID_TEST_ENV.FORECASTENGINE_BASE_URL + "/v1/forecast");
      assert.deepEqual(JSON.parse(opt.body), args);
      return fakeResponse(raw);
    });
    assert.deepEqual(result, raw);
    assert.strictEqual(result.engine_result.results[0].price_estimate, raw.engine_result.results[0].price_estimate);
    assert.deepEqual(result.engine_result.untouched_extra_metadata, raw.engine_result.untouched_extra_metadata);
    assert.deepEqual(result.unknown_metadata_preserved, raw.unknown_metadata_preserved);
  }
});
test("2000-01-01 / no data: return hard failure, no guessed value", async () => {
  await checkFail(() => callForecastEngine("post_forecast",
    { ...forecastArgs, observed_on: "2000-01-01" }, VALID_TEST_ENV,
    async () => fakeResponse({ error: { message: "insufficient historical data" } }, 422)
  ), "insufficient_data");
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, VALID_TEST_ENV,
    async () => fakeResponse({ ...quoteEnvelopeFixture(), engine_result: { ok: false, reason: "no public data" } })), "insufficient_data");
});
test("backend 401, 403, 429, 5xx (and missing token) never return a value", async () => {
  const statuses = { 401: "backend_401", 403: "backend_403", 429: "backend_429", 500: "backend_5xx", 503: "backend_5xx" };
  for (const [status, code] of Object.entries(statuses)) {
    await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, VALID_TEST_ENV,
      async () => fakeResponse({ message: "do not print body or Token abc" }, Number(status))
    ), code);
  }
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs,
    { ...VALID_TEST_ENV, FORECASTENGINE_API_TOKEN: "wrong" },
    async () => { throw Error("should not run"); }), "not_configured");
  const wrongButLong = "wrong-upstream-token-with-sufficient-length-for-failed-auth";
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs,
    { ...VALID_TEST_ENV, FORECASTENGINE_API_TOKEN: wrongButLong },
    async (_url, options) => {
      assert.equal(options.headers.authorization, "Bearer " + wrongButLong);
      return fakeResponse({ error: { code: "unauthorized" } }, 401);
    }), "backend_401");
});
test("response type, oversized body, corrupted JSON and altered output hard fail", async () => {
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, VALID_TEST_ENV,
    async () => new Response("not JSON", { headers: { "content-type": "text/plain" } })), "wrong_content_type");
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, VALID_TEST_ENV,
    async () => new Response("not JSON", { headers: { "content-type": "application/json" } })), "invalid_json");
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, VALID_TEST_ENV,
    async () => fakeResponse(quoteEnvelopeFixture(), 200, { "content-length": "9999999" })), "oversized_upstream");
  await checkFail(() => callForecastEngine("post_forecast", forecastArgs, VALID_TEST_ENV,
    async () => fakeResponse({ ...forecastEnvelopeFixture(), engine_result: { ...forecastFixture(), mode_executed: "both" } })), "insufficient_data");
});
test("timeout aborts and independent new request recovers", async () => {
  let signalSawAbort = false;
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs,
    { ...VALID_TEST_ENV, UPSTREAM_TIMEOUT_MS: "100" }, async (_url, opt) => {
      return new Promise((_resolve, reject) => {
        opt.signal.addEventListener("abort", () => {
          signalSawAbort = true;
          reject(new Error("aborted"));
        }, { once: true });
      });
    }), "timeout");
  assert.equal(signalSawAbort, true);
  const recovered = await callForecastEngine("get_market_quote", quoteArgs, VALID_TEST_ENV,
    async () => fakeResponse(quoteEnvelopeFixture()));
  assert.deepEqual(recovered, quoteEnvelopeFixture());
});
test("caller rejection or cancelled request does not trigger an unsafe retry", async () => {
  let calls = 0;
  await checkFail(() => callForecastEngine("get_market_quote", quoteArgs, VALID_TEST_ENV,
    async () => { calls++; throw new Error("Socket cancelled"); }), "unavailable");
  assert.equal(calls, 1);
});
test("client-initiated HTTP abort cancels upstream and a subsequent request resumes", async () => {
  const outer = new AbortController();
  let wentUpstream = 0;
  const pending = callForecastEngine("post_forecast", forecastArgs, VALID_TEST_ENV,
    async (_url, options) => {
      wentUpstream++;
      return await new Promise((_resolve, reject) => {
        options.signal.addEventListener("abort", () => reject(new Error("request aborted")),
          { once: true });
      });
    }, outer.signal);
  outer.abort();
  await checkFail(() => pending, "cancelled");
  assert.ok(wentUpstream <= 1);
  const response = await callForecastEngine("post_forecast", forecastArgs, VALID_TEST_ENV,
    async () => fakeResponse(forecastEnvelopeFixture()));
  assert.deepEqual(response, forecastEnvelopeFixture());
});
