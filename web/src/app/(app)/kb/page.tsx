"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Pencil, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Dropdown } from "@/components/dropdown";
import { Badge, Button, Card, CategoryBadge, Empty, ErrorNote, Field, Input, Modal, PageHeader, Spinner, Textarea } from "@/components/ui";
import { api, put } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n, type TKey } from "@/lib/i18n";
import type { KbArticle } from "@/lib/types";

const CATS = ["billing", "refund", "shipping", "technical", "account", "other"];
type Draft = Omit<KbArticle, "updated_at">;

export default function KbPage() {
  const { t, lang } = useI18n();
  const { can } = useAuth();
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [cat, setCat] = useState("");
  const [editing, setEditing] = useState<Draft | null>(null);
  const [isNew, setIsNew] = useState(false);
  const kb = useQuery({ queryKey: ["kb"], queryFn: () => api<KbArticle[]>("/kb") });

  const items = useMemo(() => (kb.data ?? []).filter((a) => {
    const hay = `${a.id} ${a.title} ${a.body} ${a.title_ar} ${a.body_ar}`.toLowerCase();
    return (!cat || a.category === cat) && (!query || hay.includes(query.toLowerCase()));
  }), [kb.data, query, cat]);

  const save = useMutation({
    mutationFn: (a: Draft) => put<KbArticle>(`/kb/${a.id}`, {
      category: a.category, title: a.title, body: a.body, title_ar: a.title_ar, body_ar: a.body_ar, policy_tags: a.policy_tags,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["kb"] }); setEditing(null); },
  });

  function startNew() {
    const next = Math.max(0, ...(kb.data ?? []).map((a) => Number(a.id.slice(3)))) + 1;
    setIsNew(true);
    setEditing({ id: `KB-${String(next).padStart(3, "0")}`, category: "other", title: "", body: "", title_ar: "", body_ar: "", policy_tags: [] });
  }

  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6">
      <PageHeader title={t("kb.title")} subtitle={t("kb.subtitle")}
        actions={can("kb:manage") && <Button variant="primary" onClick={startNew}><Plus className="h-4 w-4" />{t("kb.new")}</Button>} />
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input className="ps-9" placeholder={t("common.search")} value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <Dropdown className="w-48" value={cat} onChange={setCat}
          options={[{ value: "", label: t("common.all") }, ...CATS.map((c) => ({ value: c, label: t(`cat.${c}` as TKey) }))]} />
      </div>

      {kb.isLoading && <div className="grid place-items-center py-16"><Spinner /></div>}
      {kb.data && items.length === 0 && <Empty icon={<BookOpen className="h-8 w-8" />} text={t("inbox.empty")} />}
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((a) => {
          const title = lang === "ar" && a.title_ar ? a.title_ar : a.title;
          const body = lang === "ar" && a.body_ar ? a.body_ar : a.body;
          return (
            <Card key={a.id} className="flex flex-col p-4">
              <div className="flex items-center gap-2">
                <Badge dir="ltr">{a.id}</Badge><CategoryBadge c={a.category} />
                {!a.body_ar && <Badge tone="warn">{t("kb.missingAr")}</Badge>}
                {can("kb:manage") && (
                  <Button variant="ghost" size="sm" className="ms-auto" onClick={() => { setIsNew(false); setEditing(a); }} aria-label={t("common.edit")}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                )}
              </div>
              <h3 className="bidi mt-2 font-medium">{title}</h3>
              <p className="bidi mt-1 line-clamp-4 text-sm text-muted">{body}</p>
            </Card>
          );
        })}
      </div>

      <Modal open={!!editing} onClose={() => setEditing(null)} title={isNew ? t("kb.new") : `${t("common.edit")} ${editing?.id}`}>
        {editing && (
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("kb.id")}><Input dir="ltr" value={editing.id} disabled={!isNew} onChange={(e) => setEditing({ ...editing, id: e.target.value.toUpperCase() })} /></Field>
              <Field label={t("kb.category")}>
                <Dropdown value={editing.category} onChange={(category) => setEditing({ ...editing, category })}
                  options={CATS.map((c) => ({ value: c, label: t(`cat.${c}` as TKey) }))} />
              </Field>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-3" dir="ltr">
                <div className="text-xs font-semibold uppercase tracking-wide text-muted">{t("kb.english")}</div>
                <Input placeholder={t("kb.titleField")} value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} />
                <Textarea rows={9} placeholder={t("kb.body")} value={editing.body} onChange={(e) => setEditing({ ...editing, body: e.target.value })} />
              </div>
              <div className="space-y-3" dir="rtl">
                <div className="text-xs font-semibold uppercase tracking-wide text-muted">{t("kb.arabic")}</div>
                <Input placeholder={t("kb.titleField")} value={editing.title_ar} onChange={(e) => setEditing({ ...editing, title_ar: e.target.value })} />
                <Textarea rows={9} placeholder={t("kb.body")} value={editing.body_ar} onChange={(e) => setEditing({ ...editing, body_ar: e.target.value })} />
              </div>
            </div>
            <ErrorNote error={save.error} />
            <div className="flex justify-end gap-2">
              <Button onClick={() => setEditing(null)}>{t("common.cancel")}</Button>
              <Button variant="primary" loading={save.isPending} onClick={() => save.mutate(editing)}>{t("common.save")}</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
