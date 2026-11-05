"use client";

/** API client. The access token lives in memory only (never localStorage), so a page
 *  reload restores the session through /api/auth/refresh using the httpOnly cookie. */

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onSessionLost: (() => void) | null = null;

export function setAccessToken(t: string | null) { accessToken = t; }
export function getAccessToken() { return accessToken; }
export function onLogout(cb: () => void) { onSessionLost = cb; }

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

/** One in-flight refresh shared by all callers: 10 parallel 401s cause ONE refresh,
 *  not 10 (which, with token rotation, would revoke each other). */
export function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch("/api/auth/refresh", { method: "POST" })
      .then(async (r) => {
        if (!r.ok) return false;
        setAccessToken((await r.json()).access_token);
        return true;
      })
      .catch(() => false)
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

export async function api<T = unknown>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const r = await fetch(`/api/v1${path}`, { ...init, headers });
  if (r.status === 401 && retry) {
    if (await refreshSession()) return api<T>(path, init, false);
    onSessionLost?.();
  }
  if (!r.ok) {
    let detail = r.statusText;
    try { const j = await r.json(); detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {}
    throw new ApiError(r.status, detail);
  }
  return (r.status === 204 ? undefined : await r.json()) as T;
}

export const post = <T,>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const patch = <T,>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const put = <T,>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
