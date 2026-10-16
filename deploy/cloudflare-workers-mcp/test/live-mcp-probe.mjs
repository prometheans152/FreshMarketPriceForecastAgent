// Runs against a REAL local workerd listener (wrangler dev --local), not Oracle.
// The .dev.vars synthetic testing secrets are not production credentials.
import assert from "node:assert/strict";
import { VALID_TEST_ENV } from "./fixtures.js";

const address = process.env.FMPA_LOCAL_PROBE_URL ?? process.env.TW01_LOCAL_PROBE_URL ?? "http://127.0.0.1:8797";
if (!address.startsWith("http://127.0.0.1:") && !address.startsWith("http://localhost:"))
  throw new Error("Refusing to send synthetic bearer credentials off loopback");

function rpc(method, params, id) {
  return JSON.stringify({ jsonrpc: "2.0", method, params, id });
}
async function runRpc(body, useToken = true) {
  const headers = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
  };
  if (useToken) headers.authorization = "Bearer " + VALID_TEST_ENV.MCP_CLIENT_BEARER_TOKEN;
  const response = await fetch(address + "/mcp", { method: "POST", headers, body });
  const text = await response.text();
  if (response.status !== 200)
    return { status: response.status, body: text };
  const json = response.headers.get("content-type")?.includes("text/event-stream")
    ? JSON.parse(text.split(/\r?\n/).find((v) => v.startsWith("data: ")).slice(6))
    : JSON.parse(text);
  return { status: response.status, body: json };
}
const results = {};
const health = await fetch(address + "/healthz");
results.health_http = health.status;
assert.equal(health.status, 200, "local test secrets must produce configured health");
const unauth = await runRpc(rpc("tools/list", {}, 1), false);
results.unauth_http = unauth.status;
assert.equal(unauth.status, 401);
const initialized = await runRpc(rpc("initialize", {
  protocolVersion: "2025-06-18",
  capabilities: {}, clientInfo: { name: "real-workerd-probe", version: "1.0.0" },
}, 2));
assert.equal(initialized.status, 200);
assert.equal(initialized.body.result?.serverInfo?.name, "fresh-market-price-agent-forecastengine-remote");
results.initialize = "PASS";
const listed = await runRpc(rpc("tools/list", {}, 3));
assert.equal(listed.status, 200);
const names = listed.body.result?.tools.map(t => t.name);
assert.deepEqual(names, ["get_market_quote", "post_forecast"]);
results.tools_list = names;
const denied = await runRpc(rpc("tools/call", {
  name: "post_forecast",
  arguments: {
    crop_id: "cabbage", market_id: "中義市場", current_price: 32,
    price_unit: "NTD_per_box", mode: "both", save_record: true,
  },
}, 4));
results.reject_b_save_invalid_unit = Boolean(denied.body.error || denied.body.result?.isError);
assert.equal(results.reject_b_save_invalid_unit, true);
const unknown = await runRpc(rpc("tools/call", {
  name: "save_record", arguments: { store_id: "A" },
}, 5));
results.reject_unknown_tool = Boolean(unknown.body.error || unknown.body.result?.isError);
assert.equal(results.reject_unknown_tool, true);
// Valid parameters still MUST fail when the mock upstream domain is not reachable.
// This deliberately does not assert success or invent a model prediction.
const noOracle = await runRpc(rpc("tools/call", {
  name: "get_market_quote", arguments: { crop_id: "cabbage", market_id: "中義市場" },
}, 6));
results.unavailable_backend_refused = noOracle.body.result?.isError === true;
assert.equal(results.unavailable_backend_refused, true);
console.log(JSON.stringify({ probe: "LOCAL_WORKERD_ONLY_NOT_ORACLE_E2E", results }, null, 2));
