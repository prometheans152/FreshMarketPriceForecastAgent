/** Self-hostable TW01 MCP Streamable HTTP adapter, internal Docker network.
 *
 * Exactly two tools from the user-approved first-version MCP contract.
 * NOT a general file/browser/shell/records interface. The existing Cloudflare
 * VPC Workers server is a separate deployment and is intentionally not copied.
 */
import http from "node:http";
import { readFileSync } from "node:fs";
import { timingSafeEqual } from "node:crypto";
import {
  McpServer, WebStandardStreamableHTTPServerTransport,
} from "@modelcontextprotocol/server";
import {
  TOOL_NAMES, TOOL_INPUTS, TOOL_OUTPUT, TOOL_DESCRIPTIONS, ANNOTATIONS,
  validateArguments, verifyOracleEnvelope,
} from "./contracts.js";
import { rejectDuplicateJsonKeys } from "./strict-json.js";

const PORT = 9000;
const MAX_BODY = 16384;
const MAX_OUTPUT = 131072;
const AUTH_MODE = process.env.TW01_MCP_AUTH_MODE ?? "bearer";
const ENGINE_URL = "http://forecast:8767";
const DEFAULT_ERROR = "ForecastEngine 沒有可驗證的結果；拒絕提供數值。";
if (!["bearer", "public_noauth"].includes(AUTH_MODE))
  throw new Error("TW01 MCP mode unsupported");
if (process.env.TW01_ENGINE_URL && process.env.TW01_ENGINE_URL !== ENGINE_URL)
  throw new Error("TW01 backend route must be fixed to internal forecast only");

function readSecret(name) {
  const path = process.env[name];
  if (typeof path !== "string" || !path.startsWith("/run/secrets/"))
    throw new Error("Required Docker secret path missing: " + name);
  const token = readFileSync(path, "utf8").trim();
  if (token.length < 32 || token.length > 512 || /\s/.test(token))
    throw new Error("Required Docker secret malformed");
  return token;
}
const ORIGIN_TOKEN = readSecret("TW01_ORIGIN_TOKEN_FILE");
const CLIENT_TOKEN = readSecret("TW01_MCP_TOKEN_FILE");
if (ORIGIN_TOKEN === CLIENT_TOKEN)
  throw new Error("Origin and MCP client secrets must not match");

// Secrets are read once at startup, BEFORE dropping UID/GID permanently.
// No HTTP request is handled while the process still has root privileges.
if (process.getuid?.() === 0) {
  process.setgroups([]);
  process.setgid(1000);
  process.setuid(1000);
}

function tokenMatches(header) {
  if (typeof header !== "string" || !header.startsWith("Bearer ") || header.length > 560)
    return false;
  const sent = Buffer.from(header.slice(7));
  const known = Buffer.from(CLIENT_TOKEN);
  return sent.length === known.length && timingSafeEqual(sent, known);
}

function jsonStatus(code, status) {
  return new Response(JSON.stringify({ ok: false, code }), {
    status,
    headers: { "content-type": "application/json; charset=utf-8",
               "cache-control": "no-store" },
  });
}

async function callEngine(name, args) {
  const path = name === "get_market_quote" ? "/v1/market-quote" : "/v1/forecast";
  const response = await fetch(ENGINE_URL + path, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + ORIGIN_TOKEN,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(args),
    signal: AbortSignal.timeout(20500),
  });
  if (response.status !== 200) throw new Error("upstream_not_ready");
  const length = response.headers.get("content-length");
  if (length && Number(length) > MAX_OUTPUT) throw new Error("upstream_too_large");
  const raw = await response.text();
  if (Buffer.byteLength(raw, "utf8") > MAX_OUTPUT)
    throw new Error("upstream_too_large");
  const body = JSON.parse(raw);
  // Reuse the exact upstream verifier already used by the real Workers MCP.
  return verifyOracleEnvelope(name, args, body);
}

function newMcpServer() {
  const server = new McpServer({
    name: "tw01-portable-docker-mcp",
    version: "1.0.0",
  }, {
    instructions: "臺中公開行情及匿名A 7／14天預測；公開均價不是即時店價。" +
      "僅兩項工具，拒絕B、保存、私人紀錄、任意URL、機率與自行補算。",
  });
  for (const name of TOOL_NAMES) {
    server.registerTool(name, {
      description: TOOL_DESCRIPTIONS[name],
      inputSchema: TOOL_INPUTS[name],
      outputSchema: TOOL_OUTPUT,
      annotations: ANNOTATIONS,
    }, async (rawArgs) => {
      try {
        const args = validateArguments(name, rawArgs);
        const result = await callEngine(name, args);
        const json = JSON.stringify(result);
        if (Buffer.byteLength(json, "utf8") > MAX_OUTPUT)
          throw new Error("response_too_large");
        return {
          content: [{ type: "text", text: json }],
          structuredContent: result,
          isError: false,
        };
      } catch {
        // Do not log token, caller input or upstream model errors verbatim.
        return { content: [{ type: "text", text: DEFAULT_ERROR }],
                 isError: true };
      }
    });
  }
  return server;
}

async function boundedJson(req) {
  const declared = Number(req.headers["content-length"] ?? 0);
  if (!Number.isInteger(declared) || declared > MAX_BODY)
    return { tooBig: true };
  const chunks = [];
  let n = 0;
  for await (const chunk of req) {
    n += chunk.length;
    if (n > MAX_BODY) return { tooBig: true };
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw || raw.includes("\ufffd")) return { invalid: true };
  try {
    rejectDuplicateJsonKeys(raw);
    const obj = JSON.parse(raw);
    if (typeof obj !== "object" || obj === null) return { invalid: true };
  } catch {
    return { invalid: true };
  }
  return { body: raw };
}

async function serve(req) {
  if (req.url === "/healthz" && req.method === "GET")
    return new Response(JSON.stringify({
      status: "configured", service: "tw01-portable-mcp",
      upstream_live: "not_probed", auth_mode: AUTH_MODE,
    }), { status: 200, headers: { "content-type": "application/json" } });
  if (req.url !== "/mcp") return jsonStatus("not_found", 404);
  if (!["POST", "GET", "DELETE"].includes(req.method))
    return jsonStatus("method_not_allowed", 405);
  if (AUTH_MODE === "bearer" && !tokenMatches(req.headers.authorization))
    return new Response(JSON.stringify({ ok: false, code: "unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json",
                 "www-authenticate": 'Bearer realm="tw01-portable-mcp"' },
    });
  const data = req.method === "POST" ? await boundedJson(req) : { body: undefined };
  if (data.tooBig) return jsonStatus("payload_too_large", 413);
  if (data.invalid) return jsonStatus("invalid_request", 400);

  // Stateless official MCP Streamable HTTP transport; new server per POST.
  const server = newMcpServer();
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined, enableJsonResponse: true,
  });
  try {
    await server.connect(transport);
    const url = "http://localhost:9000/mcp";
    const request = new Request(url, {
      method: req.method, headers: new Headers(req.headers),
      ...(data.body !== undefined ?
        { body: data.body, duplex: "half" } : {}),
    });
    const answer = await transport.handleRequest(request);
    // Read fully while the stateless MCP transport/server is still alive.
    const bytes = await answer.arrayBuffer();
    return new Response(bytes, {
      status: answer.status, headers: answer.headers,
    });
  } finally {
    await server.close();
  }
}

http.createServer(async (req, res) => {
  let response;
  try {
    response = await serve(req);
  } catch {
    response = jsonStatus("internal_error", 503);
  }
  let outgoing = Buffer.from(await response.arrayBuffer());
  if (outgoing.length > MAX_OUTPUT) {
    response = jsonStatus("oversized_output", 502);
    outgoing = Buffer.from(await response.arrayBuffer());
  }
  res.writeHead(response.status, {
    ...Object.fromEntries(response.headers),
    "content-length": String(outgoing.length),
    "cache-control": "no-store",
  });
  res.end(outgoing);
}).listen(PORT, "0.0.0.0");
