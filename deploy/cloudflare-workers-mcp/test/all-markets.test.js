import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ALL_MARKETS, ALL_MARKETS_WARNING, ContractError, MARKETS,
  validateArguments, verifyEngineResult, verifyOracleEnvelope,
} from "../src/contracts.js";
import { forecastEnvelopeFixture } from "./fixtures.js";

const today = new Date("2026-10-14T08:00:00Z");
const args = {
  crop_id: "cabbage", market_id: ALL_MARKETS,
  current_price: 32, price_unit: "NTD_per_taiwan_jin",
  observed_on: "2026-10-14",
};
const sample = [
  [0.01, -0.20], [0.02, -0.14], [0.12, -0.08], [0.20, -0.01], [0.24, 0.02],
];
function fixture() {
  const envelope = forecastEnvelopeFixture(args);
  const raw = envelope.engine_result;
  raw.market_id = ALL_MARKETS;
  raw.valid_market_count = sample.length;
  raw.market_predictions = sample.map(([r7, r14], i) => ({
    market_id: MARKETS[i],
    results: [
      { horizon_days: 7, relative_change_estimate: r7,
        direction: r7 > 0.05 ? "up" : "flat" },
      { horizon_days: 14, relative_change_estimate: r14,
        direction: r14 < -0.05 ? "down" : "flat" },
    ],
  }));
  raw.results[0] = {
    ...raw.results[0], relative_change_estimate: 0.12, direction: "up",
    price_estimate: 35.8, relative_change_min: 0.01, relative_change_max: 0.24,
  };
  raw.results[1] = {
    ...raw.results[1], relative_change_estimate: -0.08, direction: "down",
    price_estimate: 29.4, relative_change_min: -0.20, relative_change_max: 0.02,
  };
  raw.error = null;
  raw.warnings = [ALL_MARKETS_WARNING];
  envelope.limits.push(ALL_MARKETS_WARNING);
  envelope.fact_text += ALL_MARKETS_WARNING;
  return envelope;
}

test("D49 forecast input accepts all_markets without requiring a named market; quote rejects it", () => {
  assert.deepEqual(validateArguments("post_forecast", args, today), args);
  assert.throws(() => validateArguments("get_market_quote", {
    crop_id: "cabbage", market_id: ALL_MARKETS,
  }, today), ContractError);
  assert.throws(() => validateArguments("post_forecast", {
    ...args, market_id: "all-markets",
  }, today), ContractError);
});

test("D49 strict aggregate: valid 5-market median envelope is returned unchanged", () => {
  const envelope = fixture();
  assert.strictEqual(verifyEngineResult("post_forecast", args, envelope.engine_result),
    envelope.engine_result);
  assert.strictEqual(verifyOracleEnvelope("post_forecast", args, envelope), envelope);
  assert.deepEqual(envelope.engine_result.market_predictions.map(e => e.market_id), MARKETS.slice(0, 5));
});

test("D49 rejects a tampered median, even if attacker also fixes price and direction", () => {
  const envelope = fixture();
  const mean = sample.reduce((sum, row) => sum + row[0], 0) / sample.length;
  const corrupt = structuredClone(envelope);
  corrupt.engine_result.results[0].relative_change_estimate = mean;
  corrupt.engine_result.results[0].price_estimate = Math.round(args.current_price * (1 + mean) * 10) / 10;
  assert.throws(() => verifyOracleEnvelope("post_forecast", args, corrupt), ContractError);
});

test("D49 rejects missing/duplicate markets, insufficient count and inconsistent min/max", () => {
  for (const tamper of [
    x => { x.engine_result.valid_market_count = 2; },
    x => { x.engine_result.valid_market_count = 4; },
    x => { x.engine_result.market_predictions.pop(); },
    x => { x.engine_result.market_predictions[1].market_id = MARKETS[0]; },
    x => { x.engine_result.market_predictions[0].market_id = ALL_MARKETS; },
    x => { x.engine_result.market_predictions[0].results.pop(); },
    x => { x.engine_result.market_predictions[0].results[0].direction = "down"; },
    x => { x.engine_result.results[1].relative_change_min = -0.21; },
    x => { x.engine_result.results[0].relative_change_max = 0.23; },
    x => { x.engine_result.results[0].price_estimate += 0.2; },
    x => { x.engine_result.results[0].direction = "flat"; },
    x => { x.engine_result.market_predictions[1].results[0].relative_change_estimate = NaN; },
    x => { x.engine_result.warnings = []; },
    x => { x.limits = ["missing warning"]; },
    x => { x.fact_text = "missing warning"; },
    x => { x.normalized_request.market_id = MARKETS[0]; },
  ]) {
    const broken = fixture();
    tamper(broken);
    assert.throws(() => verifyOracleEnvelope("post_forecast", args, broken), ContractError);
  }
});

test("D49 accepts a three-market median and rejects two markets", () => {
  const envelope = fixture();
  const entries = envelope.engine_result.market_predictions;
  const three = [entries[0], entries[2], entries[4]];
  envelope.engine_result.market_predictions = three;
  envelope.engine_result.valid_market_count = 3;
  envelope.engine_result.results[0].relative_change_min = 0.01;
  envelope.engine_result.results[1].relative_change_max = 0.02;
  assert.strictEqual(verifyOracleEnvelope("post_forecast", args, envelope), envelope);
  const tooFew = structuredClone(envelope);
  tooFew.engine_result.market_predictions = three.slice(0, 2);
  tooFew.engine_result.valid_market_count = 2;
  assert.throws(() => verifyOracleEnvelope("post_forecast", args, tooFew), ContractError);
});
