"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Globe, Mail, MessageSquare, Phone, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { api, post } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { CHANNELS, label, TAGS } from "@/lib/labels";
import { Dropdown, Segmented } from "./dropdown";
import { Badge, Button, ErrorNote, Field, Input, Modal, Textarea } from "./ui";

type Example = { id: string; tags: string[]; subject: string; body: string; customer_email: string; channel: string };
type Channel = "email" | "chat" | "web_form" | "phone";
const CHANNEL_ICONS: Record<Channel, React.ReactNode> = {
  email: <Mail className="h-4 w-4" />, chat: <MessageSquare className="h-4 w-4" />,
  web_form: <Globe className="h-4 w-4" />, phone: <Phone className="h-4 w-4" />,
};
const LANG_TAGS = new Set(["arabic", "arabizi", "mixed_language", "non_english", "msa", "gulf", "levantine", "egyptian"]);

export function NewTicketModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (id: string) => void }) {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const examples = useQuery({ queryKey: ["examples"], queryFn: () => api<Example[]>("/tickets/examples"), enabled: open, staleTime: Infinity });
  const [picked, setPicked] = useState<string | null>(null);
  const [form, setForm] = useState({ customer_email: "omar.khalil@example.com", subject: "", body: "", channel: "email" as Channel });

  const options = useMemo(() => (examples.data ?? []).map((ex) => {
    const group = ex.tags.includes("arabizi") ? t("form.groupArabizi")
      : ex.tags.some((x) => LANG_TAGS.has(x)) ? t("form.groupArabic") : t("form.groupEnglish");
    const scenario = ex.tags.filter((x) => !LANG_TAGS.has(x) || x === "arabizi").map((x) => label(TAGS, x, lang));
    return {
      value: ex.id, label: ex.subject, hint: ex.body, group,
      badge: <span className="flex shrink-0 flex-col items-end gap-1">
        <span className="text-[10px] text-muted" dir="ltr">{ex.id}</span>
        {scenario[0] && <Badge className="text-[10px]">{scenario[0]}</Badge>}
      </span>,
    };
  }).sort((a, b) => a.group.localeCompare(b.group)), [examples.data, t, lang]);

  const create = useMutation({
    mutationFn: () => post<{ ticket_id: string }>("/tickets", form),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      setForm({ ...form, subject: "", body: "" });
      setPicked(null);
      onCreated(r.ticket_id);
    },
  });

  return (
    <Modal open={open} onClose={onClose} title={t("inbox.newTicket")}>
      <div className="space-y-5">
        <div className="rounded-xl border border-dashed border-primary/30 bg-primary-soft/40 p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-primary"><Sparkles className="h-4 w-4" />{t("form.example")}</div>
          <Dropdown searchable options={options} value={picked} placeholder={t("form.examplePlaceholder")}
            onChange={(id) => {
              const ex = examples.data?.find((x) => x.id === id);
              if (!ex) return;
              setPicked(id);
              setForm({ customer_email: ex.customer_email, subject: ex.subject, body: ex.body, channel: ex.channel as Channel });
            }} />
        </div>
        <Field label={t("form.channel")}>
          <Segmented<Channel> value={form.channel} onChange={(channel) => setForm({ ...form, channel })}
            options={(Object.keys(CHANNELS) as Channel[]).map((c) => ({ value: c, label: label(CHANNELS, c, lang), icon: CHANNEL_ICONS[c] }))} />
        </Field>
        <Field label={t("form.customerEmail")}><Input dir="ltr" type="email" value={form.customer_email} onChange={(e) => setForm({ ...form, customer_email: e.target.value })} /></Field>
        <Field label={t("form.subject")}><Input className="bidi" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} /></Field>
        <Field label={t("form.message")}><Textarea rows={6} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></Field>
        <ErrorNote error={create.error} />
        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button onClick={onClose}>{t("common.cancel")}</Button>
          <Button variant="primary" loading={create.isPending} disabled={!form.subject.trim() || !form.body.trim()} onClick={() => create.mutate()}>{t("form.submit")}</Button>
        </div>
      </div>
    </Modal>
  );
}
