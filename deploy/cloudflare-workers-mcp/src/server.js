import { McpServer } from "@modelcontextprotocol/server";
import {
  ANNOTATIONS, TOOL_DESCRIPTIONS, TOOL_INPUTS, TOOL_NAMES, TOOL_OUTPUT,
  ContractError, validateArguments,
} from "./contracts.js";
import { UpstreamFailure, callForecastEngine } from "./oracle-client.js";
import { getAuthMode, ACCESS_AUTH_MODE } from "./auth.js";

const OUTPUT_MAX = 131072;
function safeLog(code, name) {
  // This is the entire diagnostic footprint: never log full input, price or tokens.
  console.warn(JSON.stringify({ system: "fresh-market-price-agent-mcp", code, tool: name }));
}

export function createServer(env, engineClient = callForecastEngine, requestSignal = null) {
  const server = new McpServer({
    name: "fresh-market-price-agent-forecastengine-remote",
    version: "0.1.0",
  }, {
    instructions: "僅供臺中指定市場的公開行情及匿名 A 模式 7/14 天推估。公開均價不等於即時店價。必須有有效 ForecastEngine 工具結果才可提供數值；禁止 B、保存、機率或因果推斷。",
  });
  // Exactly two tools. Do not register dynamic tools or untrusted names.
  for (const name of TOOL_NAMES) {
    server.registerTool(name, {
      description: TOOL_DESCRIPTIONS[name],
      inputSchema: TOOL_INPUTS[name],
      outputSchema: TOOL_OUTPUT,
      annotations: ANNOTATIONS,
      ...(getAuthMode(env) === ACCESS_AUTH_MODE
        ? { securitySchemes: [{ type: "oauth2", scopes: [] }] }
        : {}),
    }, async (untrusted) => {
      try {
        const args = validateArguments(name, untrusted);
        // Backend owns the complete v1 envelope, incl. fact_text/query_date,
        // original warnings, versions and price age. Never synthesize them.
        const result = await engineClient(name, args, env, undefined, requestSignal);
        const body = JSON.stringify(result);
        if (new TextEncoder().encode(body).length > OUTPUT_MAX)
          throw new UpstreamFailure("oversized_output", "工具輸出過大；已拒絕。");
        return {
          content: [{ type: "text", text: body }],
          structuredContent: result,
          isError: false,
        };
      } catch (err) {
        const known = err instanceof ContractError || err instanceof UpstreamFailure;
        const code = known ? err.code : "internal_error";
        safeLog(code, name);
        return {
          content: [{ type: "text", text: known ? err.message : "工具執行失敗；沒有可驗證的預測結果。" }],
          isError: true,
        };
      }
    });
  }
  return server;
}
