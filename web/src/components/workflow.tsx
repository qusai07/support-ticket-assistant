"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Check, Clock, Cog, Inbox, Server, ShieldAlert, User, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n, type TKey } from "@/lib/i18n";
import { ACTIONS, DECISIONS, label, LANGUAGES, ROUTING_KEYS } from "@/lib/labels";
import type { Sla, Timeline, TimelineEvent } from "@/lib/types";
import { Badge, cn, Spinner, TeamBadge } from "./ui";

/* ------------------------------------------------------------------ SLA badge */

function fmtDuration(sec: number, lang: string) {
  const s = Math.abs(sec);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  if (h >= 48) return lang === "ar" ? `${Math.floor(h / 24)} يوم` : `${Math.floor(h / 24)}d`;
  if (h >= 1) return lang === "ar" ? `${h} س ${m} د` : `${h}h ${m}m`;
  return lang === "ar" ? `${Math.max(1, m)} د` : `${Math.max(1, m)}m`;
}

/** Live countdown: re-renders every 30 s so "12m left" stays true without refetching. */
export function SlaBadge({ sla, compact }: { sla?: Sla; compact?: boolean }) {
  const { t, lang } = useI18n();
  const [, tick] = useState(0);
  useEffect(() => { const h = setInterval(() => tick((x) => x + 1), 30_000); return () => clearInterval(h); }, []);
  if (!sla) return null;
  const tone = { on_track: "ok", at_risk: "warn", breached: "danger", met: "ok", missed: "danger" }[sla.state] as "ok" | "warn" | "danger";
  const open = ["on_track", "at_risk", "breached"].includes(sla.state);
  const left = (new Date(sla.due_at).getTime() - Date.now()) / 1000;
  const text = open ? `${fmtDuration(left, lang)} ${left >= 0 ? t("sla.left") : t("sla.over")}` : t(`sla.${sla.state}` as TKey);
  if (compact && sla.state === "on_track") return <span className="flex items-center gap-1 text-xs text-muted"><Clock className="h-3 w-3" />{text}</span>;
  return <Badge tone={tone} title={`${t("sla.target")}: ${sla.target_hours}h`}><Clock className="h-3 w-3" />{text}</Badge>;
}

/* ------------------------------------------------------------------ stepper */

type StepState = "done" | "current" | "skipped" | "pending" | "alert";
const ACTOR_ICON = { ai: Bot, rules: Cog, human: User, system: Server, customer: Inbox };

function steps(tl: Timeline): { key: TKey; state: StepState; icon: React.ElementType }[] {
  const kinds = new Set(tl.events.map((e) => e.kind));
  const escalated = kinds.has("escalated") || kinds.has("ai_escalate") || tl.status === "escalated";
  const resolved = !!tl.resolved_at;
  const reviewed = kinds.has("reviewed");
  const s = tl.status;
  return [
    { key: "wf.received", state: "done", icon: Inbox },
    { key: "wf.triage", state: kinds.has("ai_triage") ? "done" : s === "new" ? "current" : "pending", icon: Bot },
    { key: "wf.routing", state: kinds.has("ai_route") ? (escalated ? "alert" : "done") : "pending", icon: Cog },
    { key: escalated ? "wf.escalated" : "wf.draft", state: escalated ? "alert" : kinds.has("ai_agent") ? "done" : kinds.has("ai_route") ? "current" : "pending",
      icon: escalated ? ShieldAlert : Bot },
    { key: "wf.review", state: reviewed ? "done" : ["in_review", "ready_to_send", "escalated"].includes(s) ? "current" : "pending", icon: User },
    { key: "wf.resolved", state: resolved ? "done" : "pending", icon: Check },
  ];
}

const STEP_STYLE: Record<StepState, string> = {
  done: "border-ok bg-ok text-white", current: "border-primary bg-primary-soft text-primary animate-pulse",
  alert: "border-danger bg-danger text-white", skipped: "border-line bg-sunken text-muted", pending: "border-line bg-surface text-muted",
};

export function WorkflowStepper({ tl }: { tl: Timeline }) {
  const { t } = useI18n();
  const st = steps(tl);
  return (
    <ol className="flex items-start">
      {st.map((s, i) => {
        const Icon = s.icon;
        const nextDone = i < st.length - 1 && ["done", "alert"].includes(st[i + 1].state);
        return (
          <li key={s.key} className="relative flex flex-1 flex-col items-center text-center">
            {i < st.length - 1 && (
              <span className={cn("absolute top-4 h-0.5 w-full ltr:left-1/2 rtl:right-1/2", nextDone ? "bg-ok" : "bg-line")} aria-hidden />
            )}
            <span className={cn("relative z-10 grid h-8 w-8 place-items-center rounded-full border-2", STEP_STYLE[s.state])}>
              <Icon className="h-4 w-4" />
            </span>
            <span className={cn("mt-1.5 px-1 text-[11px] font-medium leading-tight", s.state === "pending" ? "text-muted" : "text-ink")}>{t(s.key)}</span>
          </li>
        );
      })}
    </ol>
  );
}

/* ------------------------------------------------------------------ event log */

function EventDetail({ e }: { e: TimelineEvent }) {
  const { lang } = useI18n();
  const d = e.detail as Record<string, unknown>;
  switch (e.kind) {
    case "ai_triage":
      return <span className="flex flex-wrap gap-1">
        {!!d.priority && <Badge>{String(d.priority)}</Badge>}{!!d.category && <Badge>{String(d.category)}</Badge>}
        {!!d.language && <Badge tone="info">{label(LANGUAGES, String(d.language), lang)}</Badge>}
        {(d.signals as string[] | undefined)?.map((s) => <Badge key={s} tone="danger">{label(ROUTING_KEYS, s, lang)}</Badge>)}
      </span>;
    case "ai_retrieve": return <span className="text-muted">{String(d.documents)} docs</span>;
    case "ai_route":
      return <span className="flex flex-wrap items-center gap-1"><TeamBadge team={d.team as string} />
        {(d.rules as string[] | undefined)?.map((r) => <Badge key={r} tone="danger">{label(ROUTING_KEYS, r.replace(/_language$/, ""), lang)}</Badge>)}</span>;
    case "ai_agent":
      return <span className="text-muted" dir="ltr">{String(d.tool_calls)} tools · conf {d.confidence == null ? "–" : Number(d.confidence).toFixed(2)}</span>;
    case "ai_hitl": return <Badge tone={d.status === "ready_to_send" ? "ok" : "warn"}>{label(ACTIONS, d.status === "ready_to_send" ? "send" : "human_review", lang)}</Badge>;
    case "assigned": return <span className="flex gap-1">{!!d.team && <TeamBadge team={String(d.team)} />}</span>;
    case "reviewed": return <span className="flex flex-wrap items-center gap-1"><Badge tone={d.decision === "reject" ? "neutral" : "ok"}>{label(DECISIONS, String(d.decision), lang)}</Badge>
      {!!d.comment && <span className="bidi text-muted">“{String(d.comment)}”</span>}</span>;
    case "escalated": return <span className="flex flex-wrap gap-1">{String(d.reason ?? "").split(",").filter(Boolean).map((r) =>
      <Badge key={r} tone="danger">{label(ROUTING_KEYS, r.trim().replace(/_language$/, ""), lang)}</Badge>)}</span>;
    case "failed": return <span className="text-danger" dir="ltr">{String(d.error)}</span>;
    default: return null;
  }
}

export function WorkflowPanel({ id }: { id: string }) {
  const { t, lang } = useI18n();
  const q = useQuery({ queryKey: ["ticket", id, "timeline"], queryFn: () => api<Timeline>(`/tickets/${id}/timeline`), refetchInterval: 15_000 });
  if (q.isLoading || !q.data) return <div className="grid place-items-center py-10"><Spinner /></div>;
  const tl = q.data;
  // 24-hour clock: an AM/PM marker ("م") inside a bidi line of numbers renders confusingly.
  const fmt = new Intl.DateTimeFormat(lang === "ar" ? "ar-u-nu-latn" : "en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
  const t0 = new Date(tl.events[0]?.at ?? Date.now()).getTime();

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface p-4">
        <span className="text-sm font-medium">{t("sla.title")}</span>
        <SlaBadge sla={tl.sla} />
        <span className="text-xs text-muted">{t("sla.target")}: <span dir="ltr">{tl.sla.target_hours}h</span></span>
        <div className="h-2 min-w-[120px] flex-1 overflow-hidden rounded-full bg-sunken">
          <div className={cn("h-full rounded-full", tl.sla.fraction >= 1 ? "bg-danger" : tl.sla.fraction >= 0.75 ? "bg-warn" : "bg-ok")}
            style={{ width: `${Math.min(100, tl.sla.fraction * 100)}%` }} />
        </div>
      </div>
      <ol className="relative space-y-0">
        {tl.events.map((e, i) => {
          const Icon = ACTOR_ICON[e.actor_type] ?? Cog;
          const offset = (new Date(e.at).getTime() - t0) / 1000;
          return (
            <li key={i} className="relative flex gap-3 pb-4">
              {i < tl.events.length - 1 && <span className="absolute start-[15px] top-8 h-[calc(100%-1.5rem)] w-px bg-line" aria-hidden />}
              <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-full",
                e.actor_type === "ai" ? "bg-primary-soft text-primary" : e.actor_type === "human" ? "bg-ok-soft text-ok"
                  : e.kind === "failed" || e.kind === "escalated" ? "bg-danger-soft text-danger" : "bg-sunken text-muted")}>
                {e.kind === "failed" ? <X className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
              </span>
              <div className="min-w-0 flex-1 pt-1">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="text-sm font-medium">{t(`ev.${e.kind}` as TKey)}</span>
                  <span className="text-xs text-muted">{t(`actor.${e.actor_type}` as TKey)}{e.actor_type === "human" ? ` · ${e.actor}` : ""}</span>
                  <span className="ms-auto text-xs tabular-nums text-muted" dir="ltr">
                    {fmt.format(new Date(e.at))}{i > 0 && ` · +${fmtDuration(offset, "en")}`}
                    {e.duration_ms != null && ` · ${e.duration_ms >= 1000 ? `${(e.duration_ms / 1000).toFixed(1)}s` : `${e.duration_ms}ms`}`}
                  </span>
                </div>
                <div className="mt-1 text-xs"><EventDetail e={e} /></div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function useTimeline(id: string) {
  return useQuery({ queryKey: ["ticket", id, "timeline"], queryFn: () => api<Timeline>(`/tickets/${id}/timeline`), refetchInterval: 15_000 });
}
