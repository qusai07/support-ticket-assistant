import { NextRequest, NextResponse } from "next/server";
import { accessOnly, API_URL, TokenPair, withRefreshCookie } from "../_shared";

export async function POST(req: NextRequest) {
  const { email, password } = await req.json().catch(() => ({}));
  if (!email || !password) return NextResponse.json({ detail: "Email and password required" }, { status: 422 });

  // Forward the browser's IP so the API's rate limit is per client, not per Next server.
  // (The API only trusts this header because the request comes from a trusted proxy.)
  const clientIp = req.headers.get("x-forwarded-for")?.split(",").pop()?.trim() || req.headers.get("x-real-ip") || "";
  const r = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded", ...(clientIp ? { "X-Forwarded-For": clientIp } : {}) },
    body: new URLSearchParams({ username: email, password }),
    cache: "no-store",
  }).catch(() => null);
  if (!r) return NextResponse.json({ detail: "API unreachable" }, { status: 502 });
  if (r.status === 429) return NextResponse.json({ detail: "too_many_attempts" }, { status: 429, headers: { "Retry-After": r.headers.get("Retry-After") ?? "900" } });
  if (!r.ok) return NextResponse.json({ detail: "Invalid email or password" }, { status: 401 });

  const pair = (await r.json()) as TokenPair;
  return withRefreshCookie(NextResponse.json(accessOnly(pair)), pair.refresh_token);
}
