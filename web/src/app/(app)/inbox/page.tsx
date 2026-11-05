"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, ClipboardCheck, Inbox as InboxIcon, Layers, Loader2, Plus, Search, Send, ShieldAlert, Timer } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { NewTicketModal } from "@/components/new-ticket";
import { TicketDetailPanel } from "@/components/ticket-detail";
import { SlaBadge } from "@/components/workflow";
import { Button, CategoryBadge, cn, Empty, Input, LangBadge, PriorityBadge, Spinner, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { timeAgo, useI18n, type TKey } from "@/lib/i18n";
import type { Stats, TicketRow } from "@/lib/types";

type QueueId = "in_review" | "escalated" | "ready_to_send" | "new" | "done" | "all";
type Tone = "warn" | "danger" | "ok" | "primary" | "info" | "neutral";

const QUEUES: { id: QueueId; label: TKey; hint: TKey; icon: React.ElementType; tone: Tone; statuses?: string }[] = [
  { id: "in_review", label: "status.in_review", hint: "queue.review.hint", icon: ClipboardCheck, tone: "warn" },
  { id: "escalated", label: "status.escalated", hint: "queue.escalated.hint", icon: ShieldAlert, tone: "danger" },
  { id: "ready_to_send", label: "status.ready_to_send", hint: "queue.ready.hint", icon: Send, tone: "ok" },
  { id: "new", label: "status.new", hint: "queue.processing.hint", icon: Loader2, tone: "primary", statuses: "new,triaged" },
  { id: "done", label: "queue.done", hint: "queue.done.hint", icon: CheckCircle2, tone: "info", statuses: "approved,rejected,sent" },
  { id: "all", label: "queue.all", hint: "queue.all.hint", icon: Layers, tone: "neutral" },
];

// Full class strings (Tailwind can only see literal class names).
const TONE: Record<Tone, { icon: string; active: string; bar: string; count: string }> = {
  warn: { icon: "bg-warn-soft text-warn", active: "border-warn/60 ring-warn/20 bg-warn-soft/40", bar: "bg-warn", count: "text-warn" },
  danger: { icon: "bg-danger-soft text-danger", active: "border-danger/60 ring-danger/20 bg-danger-soft/40", bar: "bg-danger", count: "text-danger" },
  ok: { icon: "bg-ok-soft text-ok", active: "border-ok/60 ring-ok/20 bg-ok-soft/40", bar: "bg-ok", count: "text-ok" },
  primary: { icon: "bg-primary-soft text-primary", active: "border-primary/60 ring-primary/20 bg-primary-soft/40", bar: "bg-primary", count: "text-primary" },
  info: { icon: "bg-info-soft text-info", active: "border-info/60 ring-info/20 bg-info-soft/40", bar: "bg-info", count: "text-info" },
  neutral: { icon: "bg-sunken text-muted", active: "border-muted/50 ring-muted/15 bg-sunken", bar: "bg-muted", count: "text-ink" },
};

function countFor(id: QueueId, s?: Stats) {
  if (!s) return undefined;
  const b = s.by_status;
  switch (id) {
    case "all": return s.tickets;
    case "new": return (b.new ?? 0) + (b.triaged ?? 0);
    case "done": return (b.approved ?? 0) + (b.rejected ?? 0) + (b.sent ?? 0);
    default: return b[id] ?? 0;
  }
}

export default function InboxPage() {
  const { t, lang, team } = useI18n();
  const { can, me } = useAuth();
  const router = useRouter();
  const path = usePathname();
  const q = useSearchParams();
  const mine = q.get("mine") === "1";
  const queue = (q.get("status") as QueueId | null) ?? (mine ? "all" : "in_review");
  const selected = q.get("t");
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => { const h = setTimeout(() => setDebounced(search), 250); return () => clearTimeout(h); }, [search]);

  function setParams(updates: Record<string, string | null>) {
    const p = new URLSearchParams(q.toString());
    for (const [k, v] of Object.entries(updates)) { if (v === null) p.delete(k); else p.set(k, v); }
    router.replace(`${path}?${p.toString()}`, { scroll: false });
  }

  const stats = useQuery({ queryKey: ["stats"], queryFn: () => api<Stats>("/tickets/stats"), refetchInterval: 30_000 });
  const def = QUEUES.find((x) => x.id === queue) ?? QUEUES[0];
  const params = new URLSearchParams();
  if (queue !== "all") params.set("status", def.statuses ?? queue);
  if (mine) params.set("mine", "true");
  if (debounced.trim()) params.set("q", debounced.trim());
  const tickets = useQuery({
    queryKey: ["tickets", queue, mine, debounced],
    queryFn: () => api<TicketRow[]>(`/tickets?${params.toString()}`),
    refetchInterval: 30_000, // safety net; live updates arrive via SSE
  });
  const s = stats.data;

  return (
    <div className="flex h-full flex-col">
      {/* header + queue cards */}
      <div className="border-b border-line px-4 pb-4 pt-5 sm:px-6">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-semibold tracking-tight">{mine ? t("nav.mine") : t("nav.inbox")}</h1>
            <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
              {me?.team ? team(me.team) : t("queue.all.hint")}
              {s && <><span aria-hidden>·</span><Timer className="h-3.5 w-3.5" />{t("inbox.avgTime")}: <span className="tabular-nums" dir="ltr">{s.avg_latency_s}s</span></>}
            </p>
          </div>
          {can("tickets:create") && (
            <Button variant="primary" onClick={() => setCreating(true)}><Plus className="h-4 w-4" />{t("inbox.newTicket")}</Button>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
          {QUEUES.map((qd) => {
            const n = countFor(qd.id, s), active = queue === qd.id, tone = TONE[qd.tone], Icon = qd.icon;
            return (
              <button key={qd.id} onClick={() => setParams({ status: qd.id, t: null })} aria-pressed={active}
                className={cn("group relative overflow-hidden rounded-xl border bg-surface p-4 text-start shadow-card transition-all hover:-translate-y-0.5 hover:shadow-md",
                  active ? cn("ring-2", tone.active) : "border-line")}>
                {active && <span className={cn("absolute inset-x-0 top-0 h-1", tone.bar)} />}
                <div className="flex items-start justify-between gap-2">
                  <span className={cn("grid h-9 w-9 place-items-center rounded-lg", tone.icon)}>
                    <Icon className={cn("h-[18px] w-[18px]", qd.id === "new" && (n ?? 0) > 0 && "animate-spin")} />
                  </span>
                  <span className={cn("text-3xl font-semibold tabular-nums leading-none", (n ?? 0) > 0 ? tone.count : "text-muted/60")}>{n ?? "–"}</span>
                </div>
                <div className="mt-3 font-medium">{t(qd.label)}</div>
                <div className="mt-0.5 line-clamp-1 text-xs text-muted">{t(qd.hint)}</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* queue list */}
        <section className={cn("flex w-full min-w-0 flex-col border-e border-line bg-surface/60 md:w-[420px] md:shrink-0", selected && "hidden md:flex")}>
          <div className="border-b border-line p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <Input className="ps-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("inbox.searchList")} />
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {tickets.isLoading && <div className="grid place-items-center py-16"><Spinner /></div>}
            {tickets.data?.length === 0 && <Empty icon={<InboxIcon className="h-8 w-8" />} text={t("inbox.empty")} />}
            <ul>
              {tickets.data?.map((tk) => (
                <li key={tk.id}>
                  <button onClick={() => setParams({ t: tk.id })} className={cn(
                    "relative block w-full border-b border-line px-4 py-3.5 text-start transition-colors hover:bg-sunken",
                    selected === tk.id && "bg-primary-soft/60")}>
                    {selected === tk.id && <span className="absolute inset-y-0 start-0 w-1 bg-primary" />}
                    <div className="flex items-center gap-2">
                      <span className="bidi min-w-0 flex-1 truncate font-medium">{tk.subject}</span>
                      <span className="shrink-0 text-xs text-muted">{timeAgo(tk.created_at, lang)}</span>
                    </div>
                    <div className="mt-1 truncate text-xs text-muted">
                      <span dir="ltr">{tk.customer_email}</span>{tk.team && <> · {team(tk.team)}</>}
                      {tk.assignee_name && <> · {tk.assignee_name}</>}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <StatusBadge status={tk.status} />
                      <PriorityBadge p={tk.priority} />
                      <CategoryBadge c={tk.category} />
                      <LangBadge lang={tk.language} />
                      <span className="ms-auto"><SlaBadge sla={tk.sla} compact /></span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* detail */}
        <section className={cn("min-w-0 flex-1 overflow-y-auto", !selected && "hidden md:block")}>
          {selected ? (
            <>
              <button className="flex items-center gap-1 px-4 pt-3 text-sm text-muted md:hidden" onClick={() => setParams({ t: null })}>
                <ArrowLeft className="h-4 w-4 rtl:-scale-x-100" />{t("nav.inbox")}
              </button>
              <TicketDetailPanel id={selected} />
            </>
          ) : (
            <Empty icon={<InboxIcon className="h-10 w-10" />} text={t("inbox.select")} />
          )}
        </section>
      </div>

      <NewTicketModal open={creating} onClose={() => setCreating(false)} onCreated={(id) => { setCreating(false); setParams({ status: "new", t: id }); }} />
    </div>
  );
}
