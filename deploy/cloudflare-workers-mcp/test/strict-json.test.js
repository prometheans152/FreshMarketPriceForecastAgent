import assert from "node:assert/strict";
import { test } from "node:test";
import { rejectDuplicateJsonKeys } from "../src/strict-json.js";
import { ContractError } from "../src/contracts.js";

test("reject deeply nested duplicate JSON members before MCP parses", () => {
  for (const source of [
    '{"jsonrpc":"2.0","jsonrpc":"1.0"}',
    '{"arguments":{"price_unit":"NTD_per_kg","price_unit":"NTD_per_taiwan_jin"}}',
    '{"params":[{"a":1},{"a":2,"a":3}]}',
    '{"params":{"\u0061":1,"a":2}}',
    '{"key":1,"k\u0065y":2}',
  ]) {
    assert.throws(() => rejectDuplicateJsonKeys(source),
      err => err instanceof ContractError && err.code === "duplicate_json_key");
  }
});
test("accept valid escaped strings and arrays with repeated keys across objects", () => {
  for (const source of [
    '{"a":1,"b":true,"c":null,"d":-0.5e3}',
    '{"params":[{"a":1},{"a":2}]}',
    '{"escaped\\\"key":1,"escaped\\\\key":2}',
    '[]',
  ]) assert.doesNotThrow(() => rejectDuplicateJsonKeys(source));
});
test("invalid JSON syntax and excessive nesting reject before SDK", () => {
  for (const source of [
    '{"params":,}', '{"a": 1,}', '{"a": 1', 'NaN', 'Infinity',
    '{"a": tru}', '{"a":"unterminated}', '{}{}', '{"a":0xFF}',
  ]) {
    assert.throws(() => rejectDuplicateJsonKeys(source), ContractError);
  }
  assert.throws(() => rejectDuplicateJsonKeys("[".repeat(25) + "0" + "]".repeat(25)), ContractError);
});
