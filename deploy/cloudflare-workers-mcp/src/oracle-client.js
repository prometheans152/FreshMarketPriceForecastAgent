import { ContractError, verifyOracleEnvelope } from "./contracts.js";
import { getAccessConfig, getAuthMode, ACCESS_AUTH_MODE, LOCAL_AUTH_MODE } from "./auth.js";

export const UPSTREAM_RESPONSE_MAX = 131072;
const UPSTREAM_TIMEOUT_DEFAULT = 20000;
const UPSTREAM_TIMEOUT_MAX = 22000;
const API_PATHS = Object.freeze({
  get_market_quote: "/v1/market-quote",
  post_forecast: "/v1/forecast",
});

export class UpstreamFailure extends Error {
  constructor(code, safeText) {
    super(safeText);
    this.name = "UpstreamFailure";
    this.code = code;
  }
}

// Workers VPC may throw ProxyError while establishing a connection.
// Expose ONLY one of Cloudflare's finite, documented categorical codes;
// never return or log the raw exception (may contain URLs/headers/tokens).
const SAFE_VPC_FAILURE_CODES = new Set([
  "connection_refused", "connection_terminated", "connection_timeout",
  "connection_limit_reached", "destination_unavailable",
  "destination_not_found", "destination_ip_prohibited",
  "destination_ip_unroutable", "proxy_loop_detected", "dns_error",
  "dns_timeout", "tls_protocol_error", "tls_certificate_error",
  "http_request_error", "http_upgrade_failed", "http_request_denied",
  "http_protocol_error", "http_response_incomplete",
  "connection_read_timeout", "connection_write_timeout", "rate_limited",
  "proxy_internal_error",
]);
export function classifyVPCError(err) {
  const raw = typeof err?.message === "string" ? err.message : "";
  const m = /\bProxyError:\s*([a-z_]+)\b/i.exec(raw);
  const label = m?.[1]?.toLowerCase() ?? "";
  return SAFE_VPC_FAILURE_CODES.has(label) ? label : "unclassified";
}

// Temporary on-demand diagnostic for an owner-operated VPC deployment.
// Redact URI, numbers, long sequences and secret-like words before logging.
// Disabled unless FORECASTENGINE_VPC_DIAGNOSTICS is explicitly enabled.
export function safeVPCDiagnostic(err) {
  const src = typeof err?.message === "string" ? err.message : "";
  const safe = src
    .replace(/https?:\/\/\S+/gi, "[ENDPOINT]")
    .replace(/(?:bearer|authorization|token|secret)\s*[:= ]\s*[^\s,;]+/gi, "[CREDENTIAL_REDACTED]")
    .replace(/[A-Za-z0-9_+/=.-]{24,}/g, "[LONG_REDACTED]")
    .replace(/[0-9]+/g, "#")
    .replace(/[\r\n\t\u0000-\u001f]/g, " ")
    .slice(0, 180);
  const name = ["TypeError", "Error", "DOMException"].includes(err?.name) ? err.name : "other";
  return { error_name: name, message_chars: src.length, redacted_category: safe };
}

function isUnsafeHostname(hostname) {
  const host = hostname.toLowerCase().replace(/\.$/, "");
  if (!host || host === "localhost" || host.endsWith(".localhost") ||
      host.endsWith(".local") || host.endsWith(".internal") ||
      host.endsWith(".example") || host === "[::1]" || host.startsWith("["))
    return true;
  // HTTPS with a *public* IP and a publicly trusted IP-SAN certificate is
  // allowed by the owner API contract; reject private/reserved IPv4 blocks.
  if (/^\d+\.\d+\.\d+\.\d+$/.test(host)) {
    const a = host.split(".").map(Number);
    if (a.some(x => x < 0 || x > 255)) return true;
    if (a[0] === 0 || a[0] === 10 || a[0] === 127 ||
        a[0] >= 224 || (a[0] === 100 && a[1] >= 64 && a[1] <= 127) ||
        (a[0] === 169 && a[1] === 254) ||
        (a[0] === 172 && a[1] >= 16 && a[1] <= 31) ||
        (a[0] === 192 && (a[1] === 0 || a[1] === 168)) ||
        (a[0] === 198 && (a[1] === 18 || a[1] === 19 || (a[1] === 51 && a[2] === 100))) ||
        (a[0] === 203 && a[1] === 0 && a[2] === 113)) return true;
  }
  return false;
}

export function getOracleConfig(env) {
  const base = env?.FORECASTENGINE_BASE_URL;
  const backendToken = env?.FORECASTENGINE_API_TOKEN;
  const clientToken = env?.MCP_CLIENT_BEARER_TOKEN;
  // Workers VPC keeps TLS end-to-end without public DNS:
  // https://161.33.19.220 is used only as HTTPS Host/SNI + IP-SAN
  // verification name; the VPC Service forces the network destination.
  // A missing VPC binding must NEVER fall back to the public fetch().
  const transport = env?.FORECASTENGINE_TRANSPORT ?? "direct_https";
  if (transport !== "direct_https" && transport !== "vpc_service")
    throw new UpstreamFailure("bad_configuration", "ForecastEngine transport 設定不合法。");
  if (transport === "vpc_service" &&
      typeof env?.VPC_ORACLE_FORECAST?.fetch !== "function")
    throw new UpstreamFailure("not_configured", "ForecastEngine 專用 VPC Service 尚未連接。");
  const authMode = getAuthMode(env);
  if (authMode === ACCESS_AUTH_MODE) getAccessConfig(env);
  const needsLocalToken = authMode === LOCAL_AUTH_MODE;
  if (typeof backendToken !== "string" || backendToken.length < 32 ||
      (needsLocalToken && (typeof clientToken !== "string" || clientToken.length < 32 ||
       backendToken === clientToken)))
    throw new UpstreamFailure("not_configured", "ForecastEngine 專用 Secret 或必要認證設定尚未完成。");
  if (typeof base !== "string")
    throw new UpstreamFailure("not_configured", "ForecastEngine HTTPS 位址尚未設定。");
  let url;
  try { url = new URL(base); }
  catch { throw new UpstreamFailure("bad_configuration", "ForecastEngine HTTPS 位址不合法。"); }
  if (url.protocol !== "https:" || isUnsafeHostname(url.hostname) ||
      url.username || url.password || url.search || url.hash ||
      (url.pathname !== "/" && url.pathname !== "") ||
      url.port !== "")
    throw new UpstreamFailure("bad_configuration", "ForecastEngine 必須是可驗證 TLS 憑證的公網 HTTPS 入口，不得指向內部主機。");
  const explicitHost = env?.FORECASTENGINE_ALLOWED_HOSTNAME;
  if (explicitHost && (typeof explicitHost !== "string" || explicitHost !== url.hostname))
    throw new UpstreamFailure("bad_configuration", "ForecastEngine 主機不在管理員設定的白名單。");
  const t = Number(env?.UPSTREAM_TIMEOUT_MS ?? UPSTREAM_TIMEOUT_DEFAULT);
  if (!Number.isInteger(t) || t < 100 || t > UPSTREAM_TIMEOUT_MAX)
    throw new UpstreamFailure("bad_configuration", "ForecastEngine timeout 設定無效。");
  return { base: url.origin, backendToken, timeoutMs: t, transport };
}

async function readBounded(response) {
  const declared = response.headers.get("content-length");
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > UPSTREAM_RESPONSE_MAX))
    throw new UpstreamFailure("oversized_upstream", "ForecastEngine 回應過大。");
  if (!/\bapplication\/json\b/i.test(response.headers.get("content-type") ?? ""))
    throw new UpstreamFailure("wrong_content_type", "ForecastEngine 未提供 JSON 結果。");
  if (!response.body)
    throw new UpstreamFailure("empty_upstream", "ForecastEngine 回應為空。");
  const chunks = [];
  const reader = response.body.getReader();
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > UPSTREAM_RESPONSE_MAX)
        throw new UpstreamFailure("oversized_upstream", "ForecastEngine 回應大於允許上限。");
      chunks.push(value);
    }
  } finally {
    try { await reader.cancel(); } catch { /* already closed */ }
    reader.releaseLock();
  }
  const data = new Uint8Array(size);
  let cursor = 0;
  for (const chunk of chunks) { data.set(chunk, cursor); cursor += chunk.byteLength; }
  let raw;
  try { raw = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(data)); }
  catch { throw new UpstreamFailure("invalid_json", "ForecastEngine 回應不是有效 JSON。"); }
  return raw;
}

export async function callForecastEngine(name, argumentsObject, env, fetchImpl = fetch, requestSignal = null) {
  const config = getOracleConfig(env);
  // Only the pinned service binding can reach the Oracle origin in VPC mode.
  // Never use regular global fetch as an automatic alternative.
  const upstreamFetch = config.transport === "vpc_service"
    ? env.VPC_ORACLE_FORECAST.fetch.bind(env.VPC_ORACLE_FORECAST)
    : fetchImpl;
  const path = API_PATHS[name];
  if (!path) throw new ContractError("unknown_tool", "未知工具。");
  // Exact POST body from the read-only FORECASTENGINE_API_V1.md owner contract.
  // No B/store fields; no caller-provided arbitrary URL, filepath or command.
  const body = JSON.stringify(argumentsObject);
  const controller = new AbortController();
  let timedOut = false;
  let clientCancelled = Boolean(requestSignal?.aborted);
  const onClientCancel = () => {
    clientCancelled = true;
    controller.abort();
  };
  requestSignal?.addEventListener("abort", onClientCancel, { once: true });
  if (clientCancelled) controller.abort();
  const deadline = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, config.timeoutMs);
  try {
    let response;
    if (clientCancelled)
      throw new UpstreamFailure("cancelled", "MCP 客戶端已取消請求；停止轉送。");
    try {
      response = await upstreamFetch(config.base + path, {
        method: "POST",
        // Workers VPC binding rejects redirect:"error" at runtime.
        // "manual" is supported and we deny ALL 3xx below before
        // consuming the response. The ambient HTTPS transport retains
        // "error" when outside VPC.
        redirect: config.transport === "vpc_service" ? "manual" : "error",
        headers: {
          "content-type": "application/json",
          "accept": "application/json",
          "authorization": `Bearer ${config.backendToken}`,
        },
        body,
        signal: controller.signal,
      });
    } catch (err) {
      const reason = clientCancelled ? "cancelled" : timedOut ? "timeout" : "unavailable";
      if (reason === "unavailable" && config.transport === "vpc_service") {
        const vpcCode = classifyVPCError(err);
        if (env.FORECASTENGINE_VPC_DIAGNOSTICS === "enabled") {
          console.warn(JSON.stringify({
            system: "tw01-vpc", event: "sanitized_connection_failure",
            ...safeVPCDiagnostic(err),
          }));
        }
        throw new UpstreamFailure(
          "vpc_" + vpcCode,
          "ForecastEngine VPC 連線失敗（" + vpcCode + "），沒有取得結果。"
        );
      }
      throw new UpstreamFailure(reason,
        clientCancelled ? "MCP 請求已取消，沒有取得結果。" :
        timedOut ? "ForecastEngine 請求逾時，沒有取得預測結果。" :
        "ForecastEngine 連線失敗，沒有取得結果。");
    }
    if (response.status >= 300 && response.status < 400)
      throw new UpstreamFailure("redirect_rejected",
        "ForecastEngine 嘗試重新導向，已拒絕；未取得任何預測結果。");
    if (!response.ok) {
      // DO NOT show body: reverse proxies might echo credentials or user prices.
      const code = response.status === 401 ? "backend_401" :
                   response.status === 403 ? "backend_403" :
                   response.status === 429 ? "backend_429" :
                   response.status >= 500 ? "backend_5xx" :
                   response.status === 422 || response.status === 404 ? "insufficient_data" : "backend_error";
      throw new UpstreamFailure(code, `ForecastEngine 回應 HTTP ${response.status}；未取得有效工具結果。`);
    }
    let raw;
    try { raw = await readBounded(response); }
    catch (err) {
      if (clientCancelled) throw new UpstreamFailure("cancelled", "MCP 請求已取消。");
      if (timedOut) throw new UpstreamFailure("timeout", "ForecastEngine 回應逾時。");
      throw err;
    }
    if (clientCancelled)
      throw new UpstreamFailure("cancelled", "MCP 請求已取消，忽略遲到結果。");
    if (timedOut || controller.signal.aborted)
      throw new UpstreamFailure("timeout", "ForecastEngine 已逾時，忽略遲到結果。");
    // Distinguish the specific no-data structure of the existing Python tool.
    if (raw?.error || raw?.engine_result?.ok === false || raw?.engine_result?.error)
      throw new UpstreamFailure("insufficient_data", "ForecastEngine 資料不足或拒絕此日期；不提供猜測值。");
    try { return verifyOracleEnvelope(name, argumentsObject, raw); }
    catch (err) {
      if (err instanceof ContractError)
        throw new UpstreamFailure(err.code, err.message);
      throw new UpstreamFailure("bad_upstream", "ForecastEngine 結果格式無法驗證，已拒絕。");
    }
  } finally {
    clearTimeout(deadline);
    requestSignal?.removeEventListener("abort", onClientCancel);
    controller.abort();
  }
}
