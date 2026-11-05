"use client";

import { Activity, BarChart3, BookOpen, Inbox, KeyRound, Languages, LogOut, Menu, Moon, Route, ScrollText, Settings, ShieldAlert, Sun, UserCheck, Users, UsersRound, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { patch } from "@/lib/api";
import { useI18n, type TKey } from "@/lib/i18n";
import { useLiveTickets } from "@/lib/live";
import { useTheme } from "@/lib/theme";
import type { Me } from "@/lib/types";
import { Badge, Button, cn, TeamBadge } from "./ui";

type NavItem = { href: string; label: TKey; icon: React.ElementType; perm: string; match?: (p: string, q: URLSearchParams) => boolean };

const WORKSPACE: NavItem[] = [
  { href: "/inbox", label: "nav.inbox", icon: Inbox, perm: "tickets:view",
    match: (p, q) => p === "/inbox" && !q.get("status") && !q.get("mine") },
  { href: "/inbox?status=escalated", label: "nav.escalations", icon: ShieldAlert, perm: "tickets:view",
    match: (p, q) => p === "/inbox" && q.get("status") === "escalated" },
  { href: "/inbox?mine=1", label: "nav.mine", icon: UserCheck, perm: "tickets:view",
    match: (p, q) => p === "/inbox" && q.get("mine") === "1" },
  { href: "/monitor", label: "nav.monitor", icon: Activity, perm: "analytics:view" },
  { href: "/kb", label: "nav.kb", icon: BookOpen, perm: "tickets:view" },
  { href: "/analytics", label: "nav.analytics", icon: BarChart3, perm: "analytics:view" },
];
const ADMIN: NavItem[] = [
  { href: "/admin/users", label: "nav.users", icon: Users, perm: "users:manage" },
  { href: "/admin/roles", label: "nav.roles", icon: KeyRound, perm: "users:manage" },
  { href: "/admin/teams", label: "nav.teams", icon: UsersRound, perm: "users:manage" },
  { href: "/admin/routing", label: "nav.routing", icon: Route, perm: "settings:manage" },
  { href: "/settings", label: "nav.settings", icon: Settings, perm: "analytics:view" },
  { href: "/admin/audit", label: "nav.audit", icon: ScrollText, perm: "audit:view" },
];

function NavLinks({ items, onNavigate }: { items: NavItem[]; onNavigate: () => void }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const path = usePathname();
  const q = useSearchParams();
  return (
    <>
      {items.filter((i) => can(i.perm)).map((i) => {
        const active = i.match ? i.match(path, q) : path.startsWith(i.href);
        const Icon = i.icon;
        return (
          <Link key={i.href} href={i.href} onClick={onNavigate} className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            active ? "bg-primary-soft text-primary" : "text-muted hover:bg-sunken hover:text-ink")}>
            <Icon className="h-4 w-4 shrink-0" />{t(i.label)}
          </Link>
        );
      })}
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, logout, can, setMe } = useAuth();
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const [open, setOpen] = useState(false);
  const live = useLiveTickets(!!me);

  async function switchLang() {
    const next = lang === "ar" ? "en" : "ar";
    setLang(next);
    try { setMe(await patch<Me>("/auth/me", { preferred_language: next })); } catch { /* cookie still applied */ }
  }

  const showAdmin = ADMIN.some((i) => can(i.perm));
  const sidebar = (
    <nav className="flex h-full flex-col gap-1 p-3">
      <div className="mb-4 flex items-center gap-2 px-2 pt-1">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-sm font-bold text-primary-fg">L</div>
        <span className="font-semibold">{t("appName")}</span>
      </div>
      <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted/80">{t("nav.workspace")}</div>
      <NavLinks items={WORKSPACE} onNavigate={() => setOpen(false)} />
      {showAdmin && <>
        <div className="mt-4 px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted/80">{t("nav.admin")}</div>
        <NavLinks items={ADMIN} onNavigate={() => setOpen(false)} />
      </>}
      <div className="mt-auto space-y-3 border-t border-line px-2 pt-3">
        <div>
          <div className="truncate text-sm font-medium">{me?.full_name}</div>
          <div className="mt-1 flex flex-wrap gap-1">
            <Badge>{me && t(`role.${me.role}` as TKey)}</Badge><TeamBadge team={me?.team} />
          </div>
        </div>
        <Button variant="ghost" size="sm" className="w-full justify-start" onClick={logout}>
          <LogOut className="h-4 w-4 rtl:-scale-x-100" />{t("auth.signOut")}
        </Button>
      </div>
    </nav>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden w-60 shrink-0 border-e border-line bg-surface lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <aside className="absolute inset-y-0 start-0 w-64 bg-surface shadow-xl" onClick={(e) => e.stopPropagation()}>
            <button className="absolute end-3 top-3 text-muted" onClick={() => setOpen(false)} aria-label={t("common.close")}><X className="h-5 w-5" /></button>
            {sidebar}
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line bg-surface px-4">
          <button className="text-muted lg:hidden" onClick={() => setOpen(true)} aria-label="Menu"><Menu className="h-5 w-5" /></button>
          <div className="ms-auto flex items-center gap-1">
            <span className={cn("me-2 hidden items-center gap-1.5 text-xs sm:flex", live ? "text-ok" : "text-muted")} title={live ? t("common.live") : t("common.offline")}>
              <span className={cn("h-2 w-2 rounded-full", live ? "animate-pulse bg-ok" : "bg-muted/50")} />
              {live ? t("common.live") : t("common.offline")}
            </span>
            <Button variant="ghost" size="sm" onClick={switchLang} title={t("common.language")}>
              <Languages className="h-4 w-4" />{lang === "ar" ? "English" : "العربية"}
            </Button>
            <Button variant="ghost" size="sm" onClick={toggle} aria-label={t("common.theme")}>
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
