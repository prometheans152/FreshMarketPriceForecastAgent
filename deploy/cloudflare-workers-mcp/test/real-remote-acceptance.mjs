// REAL external Cloudflare MCP -> Oracle ForecastEngine HTTP acceptance.
// This deliberately does not use mocked results or backend credentials.
// Input cases are synthetic shop prices; not real store verification.
// Usage: node test/real-remote-acceptance.mjs <absolute-output-file.json>
import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import { verifyOracleEnvelope, TOOL_NAMES } from "../src/contracts.js";

const endpoint = "https://fresh-market-price-agent.prometheans152.workers.dev/mcp";
const output = process.argv[2];
if (!output || !/\.json$/i.test(output))
  throw new Error("Provide a private output JSON file path under outputs/quality_runs.");

const quoteArgs = { crop_id: "cabbage", market_id: "中義市場" };
const forecastCases = [
  { ...quoteArgs, current_price: 32, price_unit: "NTD_per_taiwan_jin", observed_on: "2026-10-14" },
  { ...quoteArgs, current_price: 65, price_unit: "NTD_per_kg", observed_on: "2026-10-14" },
];
const testCases = [
  ["initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: {
    name: "windows-fresh-market-price-agent-real-remote-acceptance", version: "1.0",
  } }],
  ["tools/list", {}],
  ["tools/call", { name: "get_market_quote", arguments: quoteArgs }],
  ...forecastCases.map(args => ["tools/call", { name: "post_forecast", arguments: args }]),
  ["tools/call", { name: "post_forecast", arguments: {
    ...forecastCases[0], mode: "both", save_record: true,
  } }],
];

function parseHttpBody(body, type) {
  if (type?.includes("text/event-stream")) {
    const data = body.split(/\r?\n/).find(x => x.startsWith("data: "));
    if (!data) throw new Error("Missing SSE data event");
    return JSON.parse(data.slice("data: ".length));
  }
  return JSON.parse(body);
}

const results = [];
let allPass = true;
for (let i = 0; i < testCases.length; i++) {
  const [method, params] = testCases[i];
  const record = { case: i + 1, method, tool_name: params.name ?? null };
  try {
    const rpc = { jsonrpc: "2.0", id: i + 1, method, params };
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { accept: "application/json, text/event-stream", "content-type": "application/json" },
      body: JSON.stringify(rpc),
      signal: AbortSignal.timeout(25_000),
      redirect: "error",
    });
    record.http = response.status;
    record.content_type = response.headers.get("content-type");
    record.retry_after_seconds = response.headers.get("retry-after");
    const text = await response.text();
    const payload = parseHttpBody(text, record.content_type);
    record.rpc_id_matches = payload.id === rpc.id;
    record.rpc_error = payload.error ?? null;
    record.rpc_tool_is_error = payload.result?.isError ?? null;
    if (method === "initialize") {
      record.serverInfo = payload.result?.serverInfo ?? null;
      record.pass = response.status === 200 &&
        record.serverInfo?.name === "fresh-market-price-agent-forecastengine-remote";
    } else if (method === "tools/list") {
      record.tool_names = payload.result?.tools?.map(x => x.name) ?? [];
      record.tool_annotations = payload.result?.tools?.map(x => x.annotations) ?? [];
      record.pass = response.status === 200 &&
        JSON.stringify(record.tool_names) === JSON.stringify(TOOL_NAMES);
    } else if (i === testCases.length - 1) {
      record.error_text = payload.result?.content?.[0]?.text?.slice(0, 700) ?? "";
      record.pass = response.status === 200 && payload.result?.isError === true &&
        payload.result?.structuredContent == null;
    } else {
      const content = payload.result?.structuredContent;
      record.real_oracle_envelope = content ?? null;
      record.response_text_equals_structured_content =
        payload.result?.content?.[0]?.text === JSON.stringify(content);
      record.tool_name_matches = content?.tool === params.name;
      record.input_echo_matches = content != null &&
        Object.keys(params.arguments).length === Object.keys(content.input_echo ?? {}).length &&
        Object.entries(params.arguments).every(([key,value]) => content.input_echo[key] === value);
      try {
        assert.deepEqual(verifyOracleEnvelope(params.name, params.arguments, content), content);
        record.local_envelope_verification = true;
      } catch (e) {
        record.local_envelope_verification = false;
        record.validation_failure = e?.code ?? String(e);
      }
      record.pass = response.status === 200 && payload.result?.isError === false &&
        record.tool_name_matches && record.input_echo_matches &&
        record.local_envelope_verification &&
        record.response_text_equals_structured_content;
      record.query_date = content?.query_date ?? null;
      record.model_version = content?.engine_result?.model_version ?? null;
      record.data_version = content?.engine_result?.data_version ?? null;
      record.public_quote = content?.engine_result?.price ?? null;
      record.public_quote_observed = content?.engine_result?.observed_date ?? null;
      record.prediction_targets = content?.engine_result?.results?.map(x => ({
        horizon_days: x.horizon_days,
        target_date: x.target_date,
        direction: x.direction,
        relative_change_estimate: x.relative_change_estimate,
        price_estimate: x.price_estimate,
        price_estimate_unit: x.price_estimate_unit,
        probability: x.probability,
        interval_low: x.interval_low,
        interval_high: x.interval_high,
        validation_scope: x.validation_scope,
      })) ?? null;
    }
  } catch (e) {
    record.pass = false;
    record.error_type = e?.name ?? "unknown";
    record.error_message = String(e?.message ?? e).slice(0, 500);
  }
  if (!record.pass) allPass = false;
  results.push(record);
  // The logs contain no Oracle API token and no authentication headers.
  console.log(JSON.stringify(Object.fromEntries(
    Object.entries(record).filter(([name]) => name !== "real_oracle_envelope"))));
}

const summary = {
  verification: "REAL_CLOUDFLARE_REMOTE_MCP_TO_ORACLE_NOT_MOCK",
  endpoint,
  completed_utc: new Date().toISOString(),
  synthetic_shop_price_inputs_not_real_shop_truth: true,
  total: results.length,
  passed: results.filter(x => x.pass).length,
  result: allPass ? "PASS" : "FAIL",
  cases: results,
};
writeFileSync(output, JSON.stringify(summary, null, 2), { encoding: "utf8", flag: "wx", mode: 0o600 });
console.log("FULL_EVIDENCE_FILE_WRITTEN=" + output);
if (!allPass) process.exitCode = 1;
