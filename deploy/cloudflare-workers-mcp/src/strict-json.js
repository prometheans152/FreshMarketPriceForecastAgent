// Small bounded read-only JSON validator; rejects duplicate members at every
// nesting level before the MCP SDK's JSON.parse can silently overwrite them.
// This does NOT build a second copy of the request payload.
import { ContractError } from "./contracts.js";

export function rejectDuplicateJsonKeys(source) {
  if (typeof source !== "string" || source.length > 16384)
    throw new ContractError("invalid_json", "JSON-RPC 主體無效。");
  let at = 0;
  const spaces = () => { while (at < source.length && /\s/.test(source[at])) at++; };
  function stringValue() {
    const first = at++;
    if (source[first] !== '"') throw new ContractError("invalid_json", "JSON 字串格式不正確。");
    let escaped = false;
    while (at < source.length) {
      const char = source[at++];
      if (escaped) { escaped = false; continue; }
      if (char === "\\") { escaped = true; continue; }
      if (char === '"') {
        try { return JSON.parse(source.slice(first, at)); }
        catch { throw new ContractError("invalid_json", "JSON 字串編碼無效。"); }
      }
      if (char.charCodeAt(0) < 32) throw new ContractError("invalid_json", "JSON 字串包含控制字元。");
    }
    throw new ContractError("invalid_json", "JSON 字串未結束。");
  }
  function value(depth) {
    if (depth > 20) throw new ContractError("too_deep", "JSON-RPC 巢狀深度過大。");
    spaces();
    const ch = source[at];
    if (ch === '"') { stringValue(); return; }
    if (ch === "{") {
      ++at; spaces();
      const keys = new Set();
      if (source[at] === "}") { ++at; return; }
      while (at < source.length) {
        spaces();
        if (source[at] !== '"') throw new ContractError("invalid_json", "JSON 欄位名稱必須是字串。");
        const key = stringValue();
        if (keys.has(key)) throw new ContractError("duplicate_json_key", "JSON 欄位名稱重複，已拒絕。");
        keys.add(key);
        spaces();
        if (source[at++] !== ":") throw new ContractError("invalid_json", "JSON 欄位格式無效。");
        value(depth + 1);
        spaces();
        const separator = source[at++];
        if (separator === "}") return;
        if (separator !== ",") throw new ContractError("invalid_json", "JSON object 分隔符號無效。");
      }
    } else if (ch === "[") {
      ++at; spaces();
      if (source[at] === "]") { ++at; return; }
      while (at < source.length) {
        value(depth + 1);
        spaces();
        const separator = source[at++];
        if (separator === "]") return;
        if (separator !== ",") throw new ContractError("invalid_json", "JSON array 分隔符號無效。");
      }
    } else {
      const remainder = source.slice(at);
      const match = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(remainder);
      if (match && match[0] !== "") {
        at += match[0].length;
        return;
      }
      throw new ContractError("invalid_json", "JSON 數值或布林格式無效。");
    }
    throw new ContractError("invalid_json", "JSON 容器未結束。");
  }
  value(0);
  spaces();
  if (at !== source.length) throw new ContractError("invalid_json", "JSON 包含額外內容。");
}
