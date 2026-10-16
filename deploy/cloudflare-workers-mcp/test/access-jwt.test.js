import assert from "node:assert/strict";
import { test } from "node:test";
import { SignJWT, createLocalJWKSet, exportJWK, generateKeyPair } from "jose";
import { getAccessConfig, getAuthMode, verifyAccessJWT, verifyIncomingRequest } from "../src/auth.js";
import { getOracleConfig } from "../src/oracle-client.js";
import worker from "../src/index.js";
import { createServer } from "../src/server.js";
import { createMcpHandler } from "agents/mcp/server";
import { VALID_TEST_ENV, forecastArgs } from "./fixtures.js";
import { validateArguments } from "../src/contracts.js";

const env = {
  ...VALID_TEST_ENV,
  AUTH_MODE: "access_jwt",
  ACCESS_TEAM_DOMAIN: "https://falling-rain-7383.cloudflareaccess.com",
  ACCESS_AUDIENCE: "tw01-test-audience-not-real-20261014",
};

test("strict auth modes, config and owner price maximum", () => {
  assert.equal(getAuthMode(VALID_TEST_ENV), "legacy_bearer");
  assert.equal(getAuthMode(env), "access_jwt");
  assert.throws(() => getAuthMode({ AUTH_MODE: "noauth" }));
  assert.equal(getAccessConfig(env).aud, env.ACCESS_AUDIENCE);
  for (const change of [
    { ACCESS_AUDIENCE: undefined },
    { ACCESS_TEAM_DOMAIN: "http://falling-rain-7383.cloudflareaccess.com" },
    { ACCESS_TEAM_DOMAIN: "https://wrong.example" },
    { ACCESS_TEAM_DOMAIN: "https://falling-rain-7383.cloudflareaccess.com/evil" },
    { AUTH_MODE: "unknown" },
  ]) assert.throws(() => getOracleConfig({ ...env, ...change }));
  assert.deepEqual(getOracleConfig({
    ...env, MCP_CLIENT_BEARER_TOKEN: undefined,
  }).base, env.FORECASTENGINE_BASE_URL);
  assert.throws(() => validateArguments("post_forecast", { ...forecastArgs, current_price: 1_000_000.01 }));
  assert.equal(validateArguments("post_forecast", { ...forecastArgs, current_price: 1_000_000 }).current_price, 1_000_000);
});

test("Access JWT must be signed by expected key, with exact iss, aud, expiry, and email", async () => {
  const { publicKey, privateKey } = await generateKeyPair("RS256", { extractable: true });
  const publicJwk = { ...(await exportJWK(publicKey)), kid: "test", alg: "RS256", use: "sig" };
  const keys = createLocalJWKSet({ keys: [publicJwk] });
  const sign = async (overrides = {}) => {
    const content = { email: "tester@example.invalid", ...overrides };
    const iss = content.iss ?? env.ACCESS_TEAM_DOMAIN;
    const aud = content.aud ?? env.ACCESS_AUDIENCE;
    delete content.iss; delete content.aud;
    return new SignJWT(content).setProtectedHeader({ alg: "RS256", kid: "test" })
      .setIssuer(iss).setAudience(aud).setIssuedAt()
      .setExpirationTime("5m").sign(privateKey);
  };
  const authorized = new Request("https://mcp.example.test/mcp", {
    headers: { "cf-access-jwt-assertion": await sign() },
  });
  assert.equal(await verifyAccessJWT(authorized, env, keys), true);
  for (const change of [
    { aud: "different-audience" },
    { iss: "https://attacker.cloudflareaccess.com" },
    { email: "" },
    { email: 4 },
  ]) {
    const denied = new Request("https://mcp.example.test/mcp", {
      headers: { "cf-access-jwt-assertion": await sign(change) },
    });
    assert.equal(await verifyAccessJWT(denied, env, keys), false);
  }
  const expired = await new SignJWT({ email: "tester@example.invalid" })
    .setProtectedHeader({ alg: "RS256", kid: "test" })
    .setIssuer(env.ACCESS_TEAM_DOMAIN).setAudience(env.ACCESS_AUDIENCE)
    .setIssuedAt(1).setExpirationTime(2).sign(privateKey);
  assert.equal(await verifyAccessJWT(new Request("https://mcp.example.test/mcp", {
    headers: { "cf-access-jwt-assertion": expired },
  }), env, keys), false);

  const another = await generateKeyPair("RS256");
  const forged = await new SignJWT({ email: "tester@example.invalid" })
    .setProtectedHeader({ alg: "RS256", kid: "test" })
    .setIssuer(env.ACCESS_TEAM_DOMAIN).setAudience(env.ACCESS_AUDIENCE)
    .setIssuedAt().setExpirationTime("5m").sign(another.privateKey);
  assert.equal(await verifyAccessJWT(new Request("https://mcp.example.test/mcp", {
    headers: { "cf-access-jwt-assertion": forged },
  }), env, keys), false);
  assert.equal(await verifyAccessJWT(new Request("https://mcp.example.test/mcp"), env, keys), false);
});

test("Managed Access mode rejects legacy bearer, no token, and missing configuration", async () => {
  const rpc = JSON.stringify({
    jsonrpc: "2.0", id: 1, method: "initialize", params: {
      protocolVersion: "2025-06-18", capabilities: {},
      clientInfo: { name: "access-test", version: "1" },
    },
  });
  const req = (headers) => new Request("https://localhost/mcp", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: rpc,
  });
  const legacy = await worker.fetch(req({
    authorization: "Bearer " + VALID_TEST_ENV.MCP_CLIENT_BEARER_TOKEN,
  }), env, {});
  assert.equal(legacy.status, 401);
  assert.equal((await legacy.json()).code, "unauthorized");
  const noToken = await worker.fetch(req({}), env, {});
  assert.equal(noToken.status, 401);
  const unconfigured = await worker.fetch(req({}), { ...env, ACCESS_AUDIENCE: undefined }, {});
  assert.equal(unconfigured.status, 503);
  assert.equal(await verifyIncomingRequest(req({}), env), false);
});

test("Managed Access keeps exactly two tools and truthful read-only annotations", async () => {
  const handler = createMcpHandler(() => createServer(env, async () => {
    throw new Error("No model should run during list test");
  }), { corsOptions: false });
  const response = await handler(new Request("https://localhost/mcp", {
    method: "POST",
    headers: { "content-type": "application/json", "accept": "application/json, text/event-stream", host: "localhost" },
    body: JSON.stringify({ jsonrpc: "2.0", method: "tools/list", params: {}, id: 42 }),
  }), env, {});
  assert.equal(response.status, 200);
  let payload = await response.text();
  if (payload.startsWith("event:")) payload = payload.split(/\r?\n/).find(s => s.startsWith("data: ")).slice(6);
  const parsed = JSON.parse(payload);
  assert.deepEqual(parsed.result.tools.map(t => t.name), ["get_market_quote", "post_forecast"]);
  assert.deepEqual(parsed.result.tools.map(t => t.annotations.readOnlyHint), [true, true]);
  // Important: SDK @modelcontextprotocol/server 2.3.1 omits per-tool
  // securitySchemes from tools/list. Whole-resource OAuth MUST be enforced
  // upstream by Cloudflare Access Managed OAuth plus Worker JWT verification.
  // ChatGPT tool-level linking remains an actual-E2E acceptance item.
});
