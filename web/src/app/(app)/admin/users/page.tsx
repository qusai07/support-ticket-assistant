"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, UserX } from "lucide-react";
import { useMemo, useState } from "react";
import { Dropdown } from "@/components/dropdown";
import { Badge, Button, Card, cn, Empty, ErrorNote, Field, Input, Modal, PageHeader, Spinner } from "@/components/ui";
import { api, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { timeAgo, useI18n } from "@/lib/i18n";
import { desc, label, PERMISSIONS, ROLE_INFO } from "@/lib/labels";
import type { Role, UserRow } from "@/lib/types";

const ROLES: Role[] = ["admin", "lead", "agent", "analyst"];
const ROLE_TONE = { admin: "danger", lead: "primary", agent: "ok", analyst: "info" } as const;
type Meta = { roles: Record<Role, string[]>; teams: string[] };

function Avatar({ name }: { name: string }) {
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  return <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary-soft text-xs font-semibold text-primary">{initials}</span>;
}

export default function UsersPage() {
  const { t, lang, team } = useI18n();
  const { can, me } = useAuth();
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["users"], queryFn: () => api<UserRow[]>("/users"), enabled: can("users:manage") });
  const meta = useQuery({ queryKey: ["users-meta"], queryFn: () => api<Meta>("/users/meta"), staleTime: 30_000 });
  const [creating, setCreating] = useState(false);
  const [query, setQuery] = useState("");
  const [roleF, setRoleF] = useState("");
  const [teamF, setTeamF] = useState("");
  const empty = { email: "", full_name: "", password: "", role: "agent" as Role, team: "Technical Support" };
  const [form, setForm] = useState(empty);

  const roleOptions = ROLES.map((r) => ({ value: r, label: label(ROLE_INFO, r, lang), hint: desc(ROLE_INFO, r, lang) }));
  const teamOptions = (meta.data?.teams ?? []).map((tm) => ({ value: tm, label: team(tm) }));

  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) => patch(`/users/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const create = useMutation({
    mutationFn: () => post("/users", { ...form, team: form.role === "agent" || form.role === "lead" ? form.team : null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setCreating(false); setForm(empty); },
  });

  const rows = useMemo(() => (users.data ?? []).filter((u) =>
    (!roleF || u.role === roleF) && (!teamF || u.team === teamF) &&
    (!query || `${u.full_name} ${u.email}`.toLowerCase().includes(query.toLowerCase()))), [users.data, roleF, teamF, query]);

  if (!can("users:manage")) return <p className="text-sm text-muted">{t("common.noAccess")}</p>;

  return (
    <div className="space-y-5">
      <PageHeader title={t("nav.users")} subtitle={t("users.subtitle")}
        actions={<Button variant="primary" onClick={() => setCreating(true)}><Plus className="h-4 w-4" />{t("users.new")}</Button>} />

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input className="ps-9" placeholder={t("users.search")} value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <Dropdown className="w-44" value={roleF} onChange={setRoleF} options={[{ value: "", label: t("users.allRoles") }, ...roleOptions.map(({ value, label }) => ({ value, label }))]} />
        <Dropdown className="w-56" value={teamF} onChange={setTeamF} searchable options={[{ value: "", label: t("users.allTeams") }, ...teamOptions]} />
      </div>
      <ErrorNote error={update.error} />

      <Card>
        {users.isLoading ? <div className="grid place-items-center py-12"><Spinner /></div> :
          rows.length === 0 ? <Empty icon={<UserX className="h-8 w-8" />} text={t("common.none")} /> : (
            <ul className="divide-y divide-line">
              {rows.map((u) => {
                const self = u.id === me?.id;
                return (
                  <li key={u.id} className={cn("flex flex-wrap items-center gap-4 px-4 py-3.5", !u.is_active && "opacity-50")}>
                    <div className="flex min-w-[220px] flex-1 items-center gap-3">
                      <Avatar name={u.full_name} />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 font-medium">
                          <span className="truncate">{u.full_name}</span>
                          {self && <Badge tone="primary">{t("users.you")}</Badge>}
                          {!u.is_active && <Badge>{t("teams.inactive")}</Badge>}
                        </div>
                        <div className="truncate text-xs text-muted" dir="ltr">{u.email}</div>
                      </div>
                    </div>
                    <Dropdown className="w-40" size="sm" value={u.role} disabled={self} ariaLabel={t("users.role")}
                      options={roleOptions} onChange={(role) => update.mutate({ id: u.id, body: { role, team: u.team } })} />
                    <Dropdown className="w-52" size="sm" value={u.team ?? ""} searchable ariaLabel={t("users.team")}
                      options={[{ value: "", label: "—" }, ...teamOptions]}
                      onChange={(tm) => update.mutate({ id: u.id, body: { team: tm || null } })} />
                    <div className="w-24 text-xs text-muted">{u.last_login_at ? timeAgo(u.last_login_at, lang) : t("users.never")}</div>
                    <Button size="sm" variant={u.is_active ? "ghost" : "primary"} disabled={self}
                      onClick={() => update.mutate({ id: u.id, body: { is_active: !u.is_active } })}>
                      {u.is_active ? t("users.deactivate") : t("users.activate")}
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
      </Card>

      <Modal open={creating} onClose={() => setCreating(false)} title={t("users.new")}>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("users.name")}><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <Field label={t("auth.email")}><Input dir="ltr" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
          </div>
          <Field label={t("users.role")}>
            <Dropdown value={form.role} options={roleOptions} onChange={(r) => setForm({ ...form, role: r as Role })} />
          </Field>
          {(form.role === "agent" || form.role === "lead") && (
            <Field label={t("users.team")}><Dropdown searchable value={form.team} options={teamOptions} onChange={(tm) => setForm({ ...form, team: tm })} /></Field>
          )}
          <Field label={t("users.password")}><Input dir="ltr" type="password" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
          {meta.data && (
            <div className="rounded-lg bg-sunken p-3">
              <div className="mb-2 text-xs font-medium text-muted">{label(ROLE_INFO, form.role, lang)}</div>
              <div className="flex flex-wrap gap-1">{meta.data.roles[form.role].map((p) => <Badge key={p} tone={ROLE_TONE[form.role]}>{label(PERMISSIONS, p, lang)}</Badge>)}</div>
            </div>
          )}
          <ErrorNote error={create.error} />
          <div className="flex justify-end gap-2 border-t border-line pt-4">
            <Button onClick={() => setCreating(false)}>{t("common.cancel")}</Button>
            <Button variant="primary" loading={create.isPending} onClick={() => create.mutate()}>{t("common.create")}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
