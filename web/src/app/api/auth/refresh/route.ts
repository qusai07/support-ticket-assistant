import { NextRequest, NextResponse } from "next/server";
import { accessOnly, API_URL, REFRESH_COOKIE, TokenPair, withRefreshCookie } from "../_shared";

export async function POST(req: NextRequest) {
  const token = req.cookies.get(REFRESH_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: "No session" }, { status: 401 });

  const r = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: token }),
    cache: "no-store",
  }).catch(() => null);
  if (!r) return NextResponse.json({ detail: "API unreachable" }, { status: 502 });
  if (!r.ok) return withRefreshCookie(NextResponse.json({ detail: "Session expired" }, { status: 401 }), null);

  const pair = (await r.json()) as TokenPair; // rotated: the old refresh token is now revoked
  return withRefreshCookie(NextResponse.json(accessOnly(pair)), pair.refresh_token);
}
