"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, onLogout, refreshSession, setAccessToken } from "./api";
import { useI18n } from "./i18n";
import type { Me } from "./types";

type AuthCtx = {
  me: Me | null; ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (perm: string) => boolean;
  setMe: (m: Me) => void;
};
const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const qc = useQueryClient();
  const { setLang } = useI18n();

  const clear = useCallback(() => {
    setAccessToken(null);
    setMe(null);
    qc.clear(); // never show the previous user's cached data to the next one
  }, [qc]);

  const loadMe = useCallback(async () => {
    const m = await api<Me>("/auth/me");
    setMe(m);
    setLang(m.preferred_language); // the UI follows the user's saved language
  }, [setLang]);

  // Restore the session on page load (refresh cookie -> new access token).
  useEffect(() => {
    onLogout(() => { clear(); router.replace("/login"); });
    refreshSession()
      .then(async (ok) => { if (ok) await loadMe(); })
      .catch(() => {})
      .finally(() => setReady(true));
  }, [clear, loadMe, router]);

  const login = useCallback(async (email: string, password: string) => {
    const r = await fetch("/api/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? "Login failed");
    setAccessToken((await r.json()).access_token);
    await loadMe();
  }, [loadMe]);

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    clear();
    router.replace("/login");
  }, [clear, router]);

  const can = useCallback((perm: string) => !!me?.permissions.includes(perm), [me]);

  return <Ctx.Provider value={{ me, ready, login, logout, can, setMe }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}
