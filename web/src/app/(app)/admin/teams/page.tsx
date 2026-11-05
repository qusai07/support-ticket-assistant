"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Inbox, Plus, Users } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Card, cn, ErrorNote, Field, Input, Modal, PageHeader, Spinner } from "@/components/ui";
import { api, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

type Team = { name: string; name_ar: string; description: string; is_active: boolean; members: number; open_tickets: number };

export default function TeamsPage() {
  const { t, lang } = useI18n();
  const { can } = useAuth();
  const qc = useQueryClient();
  const teams = useQuery({ queryKey: ["teams"], queryFn: () => api<Team[]>("/admin/teams") });
  const [editing, setEditing] = useState<Team | null>(null);
  const [isNew, setIsNew] = useState(false);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["teams"] }); qc.invalidateQueries({ queryKey: ["users-meta"] }); };

  const save = useMutation({
    mutationFn: (tm: Team) => isNew
      ? post("/admin/teams", { name: tm.name, name_ar: tm.name_ar, description: tm.description })
      : patch(`/admin/teams/${encodeURIComponent(tm.name)}`, { name_ar: tm.name_ar, description: tm.description }),
    onSuccess: () => { refresh(); setEditing(null); },
  });
  const toggle = useMutation({
    mutationFn: (tm: Team) => patch(`/admin/teams/${encodeURIComponent(tm.name)}`, { is_active: !tm.is_active }),
    onSuccess: refresh,
  });

  if (!can("users:manage")) return <p className="text-sm text-muted">{t("common.noAccess")}</p>;

  return (
    <div className="space-y-5">
      <PageHeader title={t("nav.teams")} subtitle={t("teams.subtitle")}
        actions={<Button variant="primary" onClick={() => { setIsNew(true); setEditing({ name: "", name_ar: "", description: "", is_active: true, members: 0, open_tickets: 0 }); }}>
          <Plus className="h-4 w-4" />{t("teams.new")}</Button>} />
      <ErrorNote error={toggle.error} />
      {teams.isLoading && <div className="grid place-items-center py-16"><Spinner /></div>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {teams.data?.map((tm) => (
          <Card key={tm.name} className={cn("flex flex-col p-4", !tm.is_active && "opacity-60")}>
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold">{lang === "ar" && tm.name_ar ? tm.name_ar : tm.name}</div>
                <div className="truncate text-xs text-muted" dir={lang === "ar" ? "ltr" : "rtl"}>{lang === "ar" ? tm.name : tm.name_ar}</div>
              </div>
              {!tm.is_active && <Badge>{t("teams.inactive")}</Badge>}
            </div>
            {tm.description && <p className="mt-2 text-sm text-muted">{tm.description}</p>}
            <div className="mt-4 flex gap-4 text-sm">
              <span className="flex items-center gap-1.5 text-muted"><Users className="h-4 w-4" /><span className="font-semibold tabular-nums text-ink">{tm.members}</span> {t("teams.members")}</span>
              <span className="flex items-center gap-1.5 text-muted"><Inbox className="h-4 w-4" /><span className="font-semibold tabular-nums text-ink">{tm.open_tickets}</span> {t("teams.open")}</span>
            </div>
            <div className="mt-4 flex gap-2 border-t border-line pt-3">
              <Button size="sm" variant="ghost" onClick={() => { setIsNew(false); setEditing(tm); }}>{t("common.edit")}</Button>
              <Button size="sm" variant="ghost" className="ms-auto" loading={toggle.isPending && toggle.variables?.name === tm.name} onClick={() => toggle.mutate(tm)}>
                {tm.is_active ? t("users.deactivate") : t("users.activate")}
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <Modal open={!!editing} onClose={() => setEditing(null)} title={isNew ? t("teams.new") : `${t("common.edit")} · ${editing?.name}`}>
        {editing && (
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("teams.nameEn")}><Input dir="ltr" value={editing.name} disabled={!isNew} onChange={(e) => setEditing({ ...editing, name: e.target.value })} /></Field>
              <Field label={t("teams.nameAr")}><Input dir="rtl" value={editing.name_ar} onChange={(e) => setEditing({ ...editing, name_ar: e.target.value })} /></Field>
            </div>
            <Field label={t("teams.description")}><Input className="bidi" value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} /></Field>
            <ErrorNote error={save.error} />
            <div className="flex justify-end gap-2 border-t border-line pt-4">
              <Button onClick={() => setEditing(null)}>{t("common.cancel")}</Button>
              <Button variant="primary" loading={save.isPending} disabled={editing.name.trim().length < 2} onClick={() => save.mutate(editing)}>{t("common.save")}</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
