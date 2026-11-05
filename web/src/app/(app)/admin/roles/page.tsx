"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Lock, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, cn, ErrorNote, PageHeader, Spinner } from "@/components/ui";
import { api, post, put } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { desc, label, PERMISSION_GROUPS, PERMISSIONS, ROLE_INFO } from "@/lib/labels";

type RoleRow = { role: string; permissions: string[]; defaults: string[]; editable: boolean; users: number };

export default function RolesPage() {
  const { t, lang } = useI18n();
  const { can } = useAuth();
  const qc = useQueryClient();
  const roles = useQuery({ queryKey: ["roles"], queryFn: () => api<RoleRow[]>("/admin/roles"), enabled: can("users:manage") });
  const [draft, setDraft] = useState<Record<string, string[]>>({});
  useEffect(() => { if (roles.data) setDraft(Object.fromEntries(roles.data.map((r) => [r.role, r.permissions]))); }, [roles.data]);

  const done = () => { qc.invalidateQueries({ queryKey: ["roles"] }); qc.invalidateQueries({ queryKey: ["users-meta"] }); };
  const save = useMutation({ mutationFn: (role: string) => put(`/admin/roles/${role}`, { permissions: draft[role] }), onSuccess: done });
  const reset = useMutation({ mutationFn: (role: string) => post(`/admin/roles/${role}/reset`, {}), onSuccess: done });

  if (!can("users:manage")) return <p className="text-sm text-muted">{t("common.noAccess")}</p>;
  if (!roles.data) return <div className="grid place-items-center py-16"><Spinner /></div>;

  const toggle = (role: string, perm: string) => setDraft((d) => {
    const cur = new Set(d[role]);
    if (cur.has(perm)) cur.delete(perm); else cur.add(perm);
    return { ...d, [role]: [...cur].sort() };
  });
  const same = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));

  return (
    <div className="space-y-5">
      <PageHeader title={t("nav.roles")} subtitle={t("roles.subtitle")} />
      <ErrorNote error={save.error ?? reset.error} />

      {/* role cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {roles.data.map((r) => {
          const dirty = !same(draft[r.role] ?? [], r.permissions);
          const custom = !same(r.permissions, r.defaults);
          return (
            <Card key={r.role} className={cn("flex flex-col p-4", dirty && "ring-2 ring-warn/40")}>
              <div className="flex items-center gap-2">
                <span className="font-semibold">{label(ROLE_INFO, r.role, lang)}</span>
                {!r.editable && <Lock className="h-3.5 w-3.5 text-muted" />}
                {custom && <Badge tone="warn">{t("roles.custom")}</Badge>}
              </div>
              <p className="mt-1 flex-1 text-xs text-muted">{desc(ROLE_INFO, r.role, lang)}</p>
              <div className="mt-3 text-xs text-muted"><span className="font-semibold text-ink tabular-nums">{r.users}</span> {t("roles.users")} · <span className="tabular-nums">{(draft[r.role] ?? []).length}</span>/11</div>
              {r.editable && (dirty || custom) && (
                <div className="mt-3 flex gap-2">
                  {dirty && <Button size="sm" variant="primary" loading={save.isPending && save.variables === r.role} onClick={() => save.mutate(r.role)}>{t("common.save")}</Button>}
                  {custom && !dirty && <Button size="sm" variant="ghost" onClick={() => reset.mutate(r.role)}><RotateCcw className="h-3.5 w-3.5" />{t("roles.reset")}</Button>}
                </div>
              )}
              {dirty && <div className="mt-2 text-xs text-warn">{t("roles.unsaved")}</div>}
            </Card>
          );
        })}
      </div>

      {/* matrix */}
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="sticky top-0 bg-sunken text-xs text-muted">
            <tr>
              <th className="px-4 py-3 text-start font-medium" />
              {roles.data.map((r) => <th key={r.role} className="w-28 px-2 py-3 text-center font-semibold text-ink">{label(ROLE_INFO, r.role, lang)}</th>)}
            </tr>
          </thead>
          <tbody>
            {PERMISSION_GROUPS.map((g) => (
              <PermissionGroup key={g.id} title={label({ x: g.label }, "x", lang)}>
                {g.perms.map((p) => (
                  <tr key={p} className="border-t border-line hover:bg-sunken/50">
                    <td className="px-4 py-2.5">
                      <div className="font-medium">{label(PERMISSIONS, p, lang)}</div>
                      <div className="text-xs text-muted">{desc(PERMISSIONS, p, lang)}</div>
                    </td>
                    {roles.data.map((r) => {
                      const on = (draft[r.role] ?? []).includes(p);
                      const locked = !r.editable || p === "tickets:view";
                      if (locked) {
                        // Locked = always granted. A dimmed switch read as "off"; show it unambiguously.
                        return (
                          <td key={r.role} className="px-2 py-2.5 text-center">
                            <span className="inline-flex items-center gap-1 rounded-full bg-primary-soft px-2 py-0.5 text-primary" title={t("roles.locked")}>
                              <Check className="h-3.5 w-3.5" /><Lock className="h-3 w-3 opacity-70" />
                            </span>
                          </td>
                        );
                      }
                      return (
                        <td key={r.role} className="px-2 py-2.5 text-center">
                          <button type="button" role="switch" aria-checked={on} disabled={locked} onClick={() => toggle(r.role, p)}
                            aria-label={`${label(ROLE_INFO, r.role, lang)}: ${label(PERMISSIONS, p, lang)}`}
                            className={cn("relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                              on ? "bg-primary" : "bg-line")}>
                            <span className={cn("absolute h-4 w-4 rounded-full bg-white shadow transition-all", on ? "start-[18px]" : "start-0.5")} />
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </PermissionGroup>
            ))}
          </tbody>
        </table>
      </Card>
      <p className="flex items-center gap-1.5 text-xs text-muted"><Lock className="h-3.5 w-3.5" />{t("roles.locked")}</p>
    </div>
  );
}

function PermissionGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <>
      <tr className="border-t border-line bg-sunken/40"><td colSpan={5} className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted">{title}</td></tr>
      {children}
    </>
  );
}
