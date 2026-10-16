// TW01 public MCP abuse protection. These counters are Cloudflare location
// local and eventually consistent, NOT an exact worldwide quota.
// No binding or any binding error => deny, NEVER silently allow.
export class RateLimitUnavailable extends Error {
  constructor() { super("Required Cloudflare Rate Limiting binding unavailable."); }
}

const REQUEST_BINDINGS = ["RL_REQUESTS_IP", "RL_REQUESTS_POP"];
const TOOL_BINDINGS = ["RL_TOOLS_IP", "RL_TOOLS_POP"];

export function validatePublicLimits(env) {
  for (const name of [...REQUEST_BINDINGS, ...TOOL_BINDINGS]) {
    if (typeof env?.[name]?.limit !== "function") throw new RateLimitUnavailable();
  }
}

function requestIdentity(request) {
  // In deployed Workers, Cloudflare overwrites Cf-Connecting-Ip at the edge.
  // If absent in a synthetic/atypical request, use a shared unattributed
  // bucket, rather than trusting spoofable X-Forwarded-For or user-agent.
  const ip = request.headers.get("cf-connecting-ip");
  if (!ip || !/^[a-f0-9:.]{3,64}$/i.test(ip)) return "unknown";
  return ip.toLowerCase();
}

export async function checkPublicLimits(request, env, isToolCall = false) {
  validatePublicLimits(env);
  const ip = requestIdentity(request);
  const checks = isToolCall ? TOOL_BINDINGS : REQUEST_BINDINGS;
  // Distinct namespaces, same per-IP identity for both request and tool.
  // Keep POP aggregate bounded independent of attacker-chosen IP values.
  const keys = [ip, "all-mcp-callers"];
  try {
    for (let i = 0; i < checks.length; i++) {
      const result = await env[checks[i]].limit({ key: keys[i] });
      if (result?.success === false) return false;
      if (result?.success !== true) throw new RateLimitUnavailable();
    }
    return true;
  } catch {
    throw new RateLimitUnavailable();
  }
}
