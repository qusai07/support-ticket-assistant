import { NextResponse } from "next/server";

export const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
export const REFRESH_COOKIE = "lumora_rt";

/** The refresh token lives ONLY in this httpOnly cookie: page JavaScript (and any XSS)
 *  can never read it. It's scoped to /api/auth so it isn't even sent with other requests. */
export function withRefreshCookie(res: NextResponse, token: string | null): NextResponse {
  res.cookies.set(REFRESH_COOKIE, token ?? "", {
    httpOnly: true,
    // Secure by default in production. COOKIE_SECURE=false only for plain-HTTP setups (e.g. a LAN demo);
    // browsers treat http://localhost as secure, so local dev works either way.
    secure: process.env.COOKIE_SECURE ? process.env.COOKIE_SECURE === "true" : process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/api/auth",
    maxAge: token ? 60 * 60 * 24 * 7 : 0,
  });
  return res;
}

export type TokenPair = { access_token: string; refresh_token: string; expires_in: number };

/** Return only the short-lived access token to the browser. */
export function accessOnly(pair: TokenPair) {
  return { access_token: pair.access_token, expires_in: pair.expires_in };
}
