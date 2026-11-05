"use client";

import { KeyRound, Route, ScrollText, Users, UsersRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { useI18n, type TKey } from "@/lib/i18n";

const TABS: { href: string; label: TKey; icon: React.ElementType; perm: string }[] = [
  { href: "/admin/users", label: "nav.users", icon: Users, perm: "users:manage" },
  { href: "/admin/roles", label: "nav.roles", icon: KeyRound, perm: "users:manage" },
  { href: "/admin/teams", label: "nav.teams", icon: UsersRound, perm: "users:manage" },
  { href: "/admin/routing", label: "nav.routing", icon: Route, perm: "settings:manage" },
  { href: "/admin/audit", label: "nav.audit", icon: ScrollText, perm: "audit:view" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const path = usePathname();
  const tabs = TABS.filter((x) => can(x.perm));
  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6">
      <div className="mb-6">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted">{t("admin.title")}</div>
        <nav className="mt-3 flex gap-1 overflow-x-auto rounded-xl bg-sunken p-1">
          {tabs.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={cn("flex items-center gap-2 whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-medium transition-colors",
              path.startsWith(href) ? "bg-surface text-primary shadow-card" : "text-muted hover:text-ink")}>
              <Icon className="h-4 w-4" />{t(label)}
            </Link>
          ))}
        </nav>
      </div>
      {children}
    </div>
  );
}
