import { createMcpHandler } from "agents/mcp/server";
import { ContractError } from "./contracts.js";
import { getOracleConfig } from "./oracle-client.js";
import { createServer } from "./server.js";
import { rejectDuplicateJsonKeys } from "./strict-json.js";
import { verifyIncomingRequest, getAuthMode, ACCESS_AUTH_MODE, PUBLIC_AUTH_MODE } from "./auth.js";
import { checkPublicLimits, validatePublicLimits, RateLimitUnavailable } from "./rate-limit.js";

const INGRESS_MAX = 16384;
const jsonHeaders = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };

function plain(code, status = 400) {
  // Do not reflect request headers, request bodies or worker secrets.
  return new Response(JSON.stringify({ ok: false, code }), { status, headers: jsonHeaders });
}
function rateLimited() {
  return new Response(JSON.stringify({ ok: false, code: "rate_limited" }), {
    status: 429, headers: { ...jsonHeaders, "retry-after": "60" },
  });
}

// Bounded input before the SDK sees untrusted JSON-RPC, independent of any
// model prompts. Streaming consumes <= INGRESS_MAX+1 bytes even without CL.
async function boundedMcpPost(request) {
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? ""))
    throw new ContractError("bad_content_type", "請使用 application/json。");
  const declared = request.headers.get("content-length");
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > INGRESS_MAX))
    throw new ContractError("oversized_request", "請求超過大小上限。");
  if (!request.body) throw new ContractError("empty_request", "JSON-RPC 主體不可為空。");
  const reader = request.body.getReader();
  const parts = [];
  let bytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > INGRESS_MAX)
        throw new ContractError("oversized_request", "請求超過大小上限。");
      parts.push(value);
    }
  } finally {
    try { await reader.cancel(); } catch { /* already closed */ }
    reader.releaseLock();
  }
  const encoded = new Uint8Array(bytes);
  let off = 0;
  for (const p of parts) { encoded.set(p, off); off += p.byteLength; }
  let string;
  try { string = new TextDecoder("utf-8", { fatal: true }).decode(encoded); }
  catch { throw new ContractError("invalid_utf8", "JSON-RPC UTF-8 格式錯誤。"); }
  // Avoid pathological nesting before the SDK JSON parser consumes input.
  let depth = 0, inString = false, escaping = false;
  for (const ch of string) {
    if (inString) {
      if (escaping) escaping = false;
      else if (ch === "\\") escaping = true;
      else if (ch === '"') inString = false;
    } else if (ch === '"') inString = true;
    else if (ch === "{" || ch === "[") { if (++depth > 20) throw new ContractError("too_deep", "JSON-RPC 巢狀深度過大。"); }
    else if (ch === "}" || ch === "]") depth--;
  }
  if (depth !== 0 || inString)
    throw new ContractError("invalid_json", "JSON-RPC 主體格式無效。");
  rejectDuplicateJsonKeys(string);
  const bounded = new Request(request.url, {
    method: "POST",
    headers: request.headers,
    body: encoded,
    signal: request.signal,
  });
  // Parser has already verified UTF-8 and duplicate JSON member names;
  // recognize expensive tool calls for a stricter independent rate bucket.
  let isToolCall = false;
  try { isToolCall = JSON.parse(string)?.method === "tools/call"; }
  catch { throw new ContractError("invalid_json", "JSON-RPC 主體格式無效。"); }
  return { bounded, isToolCall };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/healthz" && request.method === "GET") {
      // Public health-check floods also consume the same finite Worker's
      // quota; never let a missing limiter silently expose the endpoint.
      try {
        if (getAuthMode(env) === PUBLIC_AUTH_MODE &&
          !(await checkPublicLimits(request, env))) return rateLimited();
      } catch { return plain("rate_limit_unavailable", 503); }
      let ready = true;
      try {
        getOracleConfig(env);
        if (getAuthMode(env) === PUBLIC_AUTH_MODE) validatePublicLimits(env);
      } catch { ready = false; }
      return new Response(JSON.stringify({
        service: "fresh-market-price-agent-workers-mcp", status: ready ? "configured" : "blocked",
        upstream_live: "not_probed", oracle_e2e: "not_verified",
      }), { status: ready ? 200 : 503, headers: jsonHeaders });
    }
    if (url.pathname !== "/mcp") return plain("not_found", 404);
    if (!["POST", "GET", "DELETE"].includes(request.method)) return plain("method_not_allowed", 405);
    let mode;
    try { mode = getAuthMode(env); }
    catch { return plain("service_not_configured", 503); }
    // Anonymous mode requires BOTH rate-limit layers to operate even when
    // the Oracle backend secret is not installed. This permits safe remote
    // 429 probes without permitting forecast computations.
    if (mode === PUBLIC_AUTH_MODE) {
      try {
        if (!(await checkPublicLimits(request, env))) return rateLimited();
      } catch { return plain("rate_limit_unavailable", 503); }
    }
    if (mode !== PUBLIC_AUTH_MODE) {
      try { getOracleConfig(env); }
      catch { return plain("service_not_configured", 503); }
    }
    if (mode !== PUBLIC_AUTH_MODE && !(await verifyIncomingRequest(request, env))) {
      const managed = mode === ACCESS_AUTH_MODE;
      return new Response(JSON.stringify({ ok: false, code: "unauthorized" }), {
        status: 401,
        headers: { ...jsonHeaders, "www-authenticate": managed
          ? 'Bearer realm="fresh-market-price-agent-managed-access"'
          : 'Bearer realm="fresh-market-price-agent-mcp"' },
      });
    }
    let bounded = request;
    if (request.method === "POST") {
      try {
        const checked = await boundedMcpPost(request);
        bounded = checked.bounded;
        if (mode === PUBLIC_AUTH_MODE && checked.isToolCall &&
          !(await checkPublicLimits(request, env, true))) return rateLimited();
      }
      catch (err) {
        if (mode === PUBLIC_AUTH_MODE && err instanceof RateLimitUnavailable)
          return plain("rate_limit_unavailable", 503);
        return plain(err instanceof ContractError ? err.code : "invalid_request",
          err?.code === "oversized_request" ? 413 : 400);
      }
    }
    try { getOracleConfig(env); }
    catch { return plain("service_not_configured", 503); }
    // New stateless MCP 2026 SDK v2 server per request; current SDK also
    // accepts legacy Streamable HTTP initialize/tools/list/tools/call.
    return createMcpHandler(() => createServer(env, undefined, request.signal), { corsOptions: false })(bounded, env, ctx);
  },
};
