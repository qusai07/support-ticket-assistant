"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Badge, Card, Input, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { UserRow } from "@/lib/types";

type Entry = { id: number; user_id: number | null; action: string; target_type: string | null; target_id: string | null;
  detail: Record<string, unknown>; ip: string | null; created_at: string };

function tone(action: string) {
  if (action.includes("failed") || action.includes("reuse")) return "danger" as const;
  if (action.startsWith("user.") || action.startsWith("settings.")) return "warn" as const;
  if (action.startsWith("auth.")) return "neutral" as const;
  return "primary" as const;
}

export default function AuditPage() {
  const { t, lang } = useI18n();
  const { can } = useAuth();
  const [filter, setFilter] = useState("");
  const log = useQuery({ queryKey: ["audit"], queryFn: () => api<Entry[]>("/users/audit?limit=500"), enabled: can("audit:view"), refetchInterval: 15_000 });
  const users = useQuery({ queryKey: ["users"], queryFn: () => api<UserRow[]>("/users"), enabled: can("users:manage") });
  const names = useMemo(() => Object.fromEntries((users.data ?? []).map((u) => [u.id, u.full_name])), [users.data]);
  const rows = (log.data ?? []).filter((e) => !filter || JSON.stringify(e).toLowerCase().includes(filter.toLowerCase()));
  const fmt = new Intl.DateTimeFormat(lang, { dateStyle: "short", timeStyle: "medium" });

  if (!can("audit:view")) return <p className="p-6 text-sm text-muted">{t("common.noAccess")}</p>;
  return (
    <div>
      <PageHeader title={t("audit.title")} actions={<Input className="w-64" placeholder={t("common.search")} value={filter} onChange={(e) => setFilter(e.target.value)} />} />
      <Card className="overflow-x-auto">
        {log.isLoading ? <div className="grid place-items-center py-12"><Spinner /></div> : (
          <table className="w-full text-sm">
            <thead className="bg-sunken text-xs text-muted">
              <tr>{[t("audit.when"), t("audit.who"), t("audit.action"), t("audit.target"), t("audit.detail")].map((h) => <th key={h} className="px-4 py-2.5 text-start font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id} className="border-t border-line align-top">
                  <td className="whitespace-nowrap px-4 py-2 text-xs text-muted">{fmt.format(new Date(e.created_at.endsWith("Z") ? e.created_at : e.created_at + "Z"))}</td>
                  <td className="px-4 py-2">{e.user_id ? names[e.user_id] ?? `#${e.user_id}` : "—"}</td>
                  <td className="px-4 py-2"><Badge tone={tone(e.action)} dir="ltr">{e.action}</Badge></td>
                  <td className="px-4 py-2 font-mono text-xs" dir="ltr">{e.target_type ? `${e.target_type}:${e.target_id ?? ""}` : "—"}</td>
                  <td className="max-w-md truncate px-4 py-2 font-mono text-xs text-muted" dir="ltr" title={JSON.stringify(e.detail)}>
                    {Object.keys(e.detail).length ? JSON.stringify(e.detail) : ""}{e.ip ? ` · ${e.ip}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
