import { createRemoteJWKSet, jwtVerify } from "jose";

// This module uses Cloudflare Access Managed OAuth (not a homemade OAuth
// provider). Access authenticates users at the edge, then the Worker
// independently verifies the signed application JWT before routing MCP.
export const ACCESS_AUTH_MODE = "access_jwt";
export const LOCAL_AUTH_MODE = "legacy_bearer";
// Public *transport* only; anonymous callers are still constrained by
// mandatory Cloudflare Rate Limiting bindings and Oracle's private token.
export const PUBLIC_AUTH_MODE = "public_noauth";
const accessJwksCache = new Map();

export function getAuthMode(env) {
  const mode = env?.AUTH_MODE ?? LOCAL_AUTH_MODE;
  if (mode !== ACCESS_AUTH_MODE && mode !== LOCAL_AUTH_MODE && mode !== PUBLIC_AUTH_MODE)
    throw new Error("Unsupported explicit authentication mode.");
  return mode;
}

export function getAccessConfig(env) {
  if (getAuthMode(env) !== ACCESS_AUTH_MODE)
    throw new Error("Cloudflare Access mode is not enabled.");
  const issuer = env?.ACCESS_TEAM_DOMAIN;
  const aud = env?.ACCESS_AUDIENCE;
  if (typeof issuer !== "string" ||
      !/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/.test(issuer) ||
      typeof aud !== "string" || !/^[a-zA-Z0-9_-]{16,128}$/.test(aud))
    throw new Error("Cloudflare Access issuer/audience are missing or malformed.");
  return { issuer, aud, jwksUrl: issuer + "/cdn-cgi/access/certs" };
}

function remoteKeys(url) {
  let keys = accessJwksCache.get(url);
  if (!keys) {
    keys = createRemoteJWKSet(new URL(url), {
      timeoutDuration: 3000,
      cooldownDuration: 30_000,
      cacheMaxAge: 300_000,
    });
    accessJwksCache.set(url, keys);
  }
  return keys;
}

function constantTimeEquals(x, y) {
  const a = new Uint8Array(x), b = new Uint8Array(y);
  if (a.length !== b.length) return false;
  let differences = 0;
  for (let i = 0; i < a.length; i++) differences |= a[i] ^ b[i];
  return differences === 0;
}

export async function verifyLegacyBearer(request, env) {
  const configured = env?.MCP_CLIENT_BEARER_TOKEN;
  const match = /^Bearer ([A-Za-z0-9._~+\/-]{1,512})$/.exec(request.headers.get("authorization") ?? "");
  if (match === null || typeof configured !== "string" || configured.length < 32) return false;
  const bytes = (str) => new TextEncoder().encode(str);
  const digests = await Promise.all([
    crypto.subtle.digest("SHA-256", bytes(match[1])),
    crypto.subtle.digest("SHA-256", bytes(configured)),
  ]);
  return constantTimeEquals(digests[0], digests[1]);
}

export async function verifyAccessJWT(request, env, verifierKeys) {
  const { issuer, aud, jwksUrl } = getAccessConfig(env);
  const token = request.headers.get("cf-access-jwt-assertion");
  if (!token || token.length > 8192) return false;
  try {
    const { payload } = await jwtVerify(token, verifierKeys ?? remoteKeys(jwksUrl), {
      issuer,
      audience: aud,
      algorithms: ["RS256"],
      clockTolerance: "5 seconds",
    });
    return typeof payload.email === "string" &&
      payload.email.length > 3 && payload.email.length <= 254;
  } catch {
    // Never print tokens, user email, signed payload or parser messages.
    return false;
  }
}

export async function verifyIncomingRequest(request, env) {
  const mode = getAuthMode(env);
  if (mode === PUBLIC_AUTH_MODE) return true;
  return mode === ACCESS_AUTH_MODE ? verifyAccessJWT(request, env)
    : verifyLegacyBearer(request, env);
}
