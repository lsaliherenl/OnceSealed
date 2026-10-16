/**
 * Server-side proxy to the FastAPI service (api/app.py). It forwards only the routes the operator and
 * auditor screens use and adds the role token here, so the token never reaches the browser.
 *
 * Demo only: anyone who can open this web server can act as the operator and the auditor, so do not
 * expose it publicly with the role tokens configured. The public pages do not use this proxy.
 */
import { readFileSync } from "node:fs";
import path from "node:path";

const API = process.env.ONCESEALED_API_URL ?? "http://127.0.0.1:8000";

type Route = { method: "GET" | "POST"; pattern: RegExp; role?: "operator" | "auditor" };

const ROUTES: Route[] = [
  { method: "GET", pattern: /^health$/ },
  { method: "GET", pattern: /^projects\/[A-Za-z0-9]+\/batches$/ },
  { method: "GET", pattern: /^retirements$/ },
  { method: "GET", pattern: /^retirements\/\d+$/ },
  { method: "POST", pattern: /^retirements$/, role: "operator" },
  { method: "POST", pattern: /^audit\/\d+\/open$/, role: "auditor" },
  { method: "POST", pattern: /^audit\/\d+\/attest$/, role: "auditor" },
];

const TOKEN_ENV = { operator: "OPERATOR_API_TOKEN", auditor: "AUDITOR_API_TOKEN" } as const;

/** Reads a token from the environment, falling back to the repository's .env (one level up). */
function token(role: "operator" | "auditor") {
  const name = TOKEN_ENV[role];
  if (process.env[name]) return process.env[name]!;
  try {
    const env = readFileSync(path.resolve(process.cwd(), "..", ".env"), "utf8");
    const line = env.split(/\r?\n/).find((l) => l.startsWith(`${name}=`));
    return line?.slice(name.length + 1).trim().replace(/^["']|["']$/g, "") ?? "";
  } catch {
    return "";
  }
}

async function forward(request: Request, segments: string[], method: "GET" | "POST") {
  const sub = segments.join("/");
  const route = ROUTES.find((r) => r.method === method && r.pattern.test(sub));
  if (!route) return Response.json({ error: "NotFound", message: `no proxy route for ${method} ${sub}` }, { status: 404 });

  const headers: Record<string, string> = { "content-type": "application/json" };
  if (route.role) {
    const t = token(route.role);
    if (!t) {
      return Response.json(
        { error: "NotConfigured", message: `${TOKEN_ENV[route.role]} is not set (run scripts/gen_api_tokens.py)` },
        { status: 503 },
      );
    }
    headers["x-role-token"] = t;
  }
  const query = new URL(request.url).search;
  try {
    const res = await fetch(`${API}/api/${sub}${query}`, {
      method,
      headers,
      body: method === "POST" ? await request.text() : undefined,
      cache: "no-store",
    });
    return new Response(await res.text(), { status: res.status, headers: { "content-type": "application/json" } });
  } catch {
    return Response.json(
      { error: "ApiUnavailable", message: `OnceSealed API not reachable at ${API} (start it with uvicorn api.server:app)` },
      { status: 503 },
    );
  }
}

export async function GET(request: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await ctx.params).path, "GET");
}

export async function POST(request: Request, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await ctx.params).path, "POST");
}
