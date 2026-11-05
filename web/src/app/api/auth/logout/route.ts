import { NextRequest, NextResponse } from "next/server";
import { API_URL, REFRESH_COOKIE, withRefreshCookie } from "../_shared";

export async function POST(req: NextRequest) {
  const token = req.cookies.get(REFRESH_COOKIE)?.value;
  if (token) {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token }),
      cache: "no-store",
    }).catch(() => null);
  }
  return withRefreshCookie(new NextResponse(null, { status: 204 }), null);
}
