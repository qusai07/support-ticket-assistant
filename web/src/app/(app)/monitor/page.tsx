"use client";

/** Monitoring: workflow flow (where tickets went), SLA health, AI pipeline health,
 *  per-stage latency, team workload and a live activity feed. Refreshes on SSE events
 *  and every 15 s as a fallback. */
import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, CheckCircle2, Clock, Cpu, Inbox, ShieldAlert, Timer, XCircle } from "lucide-react";
import Link from "next/link";
import { SlaBadge } from "@/components/workflow";
import { Badge, Card, cn, Empty, Kpi, PageHeader, PriorityBadge, Spinner, TeamBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { timeAgo, useI18n, type TKey } from "@/lib/i18n";
import { DECISIONS, label } from "@/lib/labels";
import type { Sla } from "@/lib/types";

type Overview = {
  flow: { received: number; links: { from: string; to: string; n: number }[] };
  sla: { priority: string; target_hours: number; on_track: number; at_risk: number; breached: number; met: number; missed: number }[];
  at_risk: ({ id: string; subject: string; priority: string; team: string; status: string } & Sla)[];
  queue: { queued: number; running: number; done: number; failed: number; oldest_wait_s: number; longest_running_s: number;
    workers: string[]; last_completed_at: string | null };
  stages: { stage: string; avg_ms: number; p95_ms: number; n: number }[];
  teams: { team: string; open: number; oldest_open_s: number; breached: number }[];
  activity: { at: string; kind: string; ticket_id: string; detail: string; actor?: string }[];
  open: number;
};

// Semantic colors for workflow states (status meaning, always paired with a text label).
const NODE_COLOR: Record<string, string> = {
  received: "#4F46E5", processing: "#8B5CF6", escalated: "#DC2626", in_review: "#D97706", ready_to_send: "#059669",
  approved: "#059669", edited: "#0284C7", rejected: "#6B7280", open: "#D97706",
};
const MID = ["processing", "escalated", "in_review", "ready_to_send"];
const END = ["approved", "edited", "rejected", "open"];

function secs(s: number, lang: string) {
  if (s < 60) return lang === "ar" ? `${Math.round(s)} ث` : `${Math.round(s)}s`;
  if (s < 3600) return lang === "ar" ? `${Math.round(s / 60)} د` : `${Math.round(s / 60)}m`;
  if (s < 172800) return lang === "ar" ? `${(s / 3600).toFixed(1)} س` : `${(s / 3600).toFixed(1)}h`;
  return lang === "ar" ? `${Math.round(s / 86400)} يوم` : `${Math.round(s / 86400)}d`;
}

/** Three-column flow (Sankey-style): Received -> AI outcome -> final outcome. */
function FlowDiagram({ flow }: { flow: Overview["flow"] }) {
  const { t, dir } = useI18n();
  const W = 880, H = 300, NODE_W = 14, GAP = 14, PAD = 8, M = 150;
  const rtl = dir === "rtl";
  const total = Math.max(1, flow.received);
  const sumBy = (key: "from" | "to", id: string) => flow.links.filter((l) => l[key] === id).reduce((a, l) => a + l.n, 0);
  const mid = MID.map((id) => ({ id, n: sumBy("from", id) })).filter((x) => x.n > 0);
  const end = END.map((id) => ({ id, n: sumBy("to", id) })).filter((x) => x.n > 0);
  const scale = (H - PAD * 2 - GAP * (Math.max(mid.length, end.length) - 1)) / total;
  // Columns flow in reading direction: left->right in English, right->left in Arabic.
  const xs = rtl ? [W - M - NODE_W, W / 2 - NODE_W / 2, M] : [M, W / 2 - NODE_W / 2, W - M - NODE_W];
  const outEdge = (x: number) => (rtl ? x : x + NODE_W);
  const inEdge = (x: number) => (rtl ? x + NODE_W : x);

  const layout = (nodes: { id: string; n: number }[]) => {
    let y = PAD;
    return Object.fromEntries(nodes.map((nd) => { const h = Math.max(3, nd.n * scale); const r = { y, h }; y += h + GAP; return [nd.id, r]; }));
  };
  const L0 = { received: { y: PAD, h: Math.max(3, total * scale) } };
  const L1 = layout(mid), L2 = layout(end);
  const off0: Record<string, number> = { received: 0 }, off1In: Record<string, number> = {}, off1Out: Record<string, number> = {}, off2: Record<string, number> = {};
  const ribbon = (xA: number, yA: number, xB: number, yB: number, h: number) => {
    const c = (xB - xA) / 2;
    return `M${xA},${yA} C${xA + c},${yA} ${xB - c},${yB} ${xB},${yB} L${xB},${yB + h} C${xB - c},${yB + h} ${xA + c},${yA + h} ${xA},${yA + h} Z`;
  };
  const paths: React.ReactNode[] = [];
  for (const m of mid) { // received -> mid
    const h = m.n * scale, y0 = L0.received.y + off0.received, y1 = L1[m.id].y + (off1In[m.id] ?? 0);
    off0.received += h; off1In[m.id] = (off1In[m.id] ?? 0) + h;
    paths.push(<path key={`r-${m.id}`} d={ribbon(outEdge(xs[0]), y0, inEdge(xs[1]), y1, h)} fill={NODE_COLOR[m.id]} opacity={0.22}><title>{`${t("flow.received")} → ${t(`flow.${m.id}` as TKey)}: ${m.n}`}</title></path>);
  }
  for (const l of flow.links) { // mid -> end
    if (!L1[l.from] || !L2[l.to]) continue;
    const h = l.n * scale, y0 = L1[l.from].y + (off1Out[l.from] ?? 0), y1 = L2[l.to].y + (off2[l.to] ?? 0);
    off1Out[l.from] = (off1Out[l.from] ?? 0) + h; off2[l.to] = (off2[l.to] ?? 0) + h;
    paths.push(<path key={`${l.from}-${l.to}`} d={ribbon(outEdge(xs[1]), y0, inEdge(xs[2]), y1, h)} fill={NODE_COLOR[l.from]} opacity={0.22}><title>{`${t(`flow.${l.from}` as TKey)} → ${t(`flow.${l.to}` as TKey)}: ${l.n}`}</title></path>);
  }
  // side "start": label sits before the node in reading order; "end": after it.
  const node = (id: string, x: number, r: { y: number; h: number }, n: number, side: "start" | "end") => {
    const onLeft = (side === "start") !== rtl;
    const textX = onLeft ? x - 8 : x + NODE_W + 8;
    return (
      <g key={id}>
        <rect x={x} y={r.y} width={NODE_W} height={r.h} rx={4} fill={NODE_COLOR[id]} />
        <text x={textX} y={r.y + r.h / 2} dominantBaseline="middle" textAnchor={onLeft ? "end" : "start"}
          className="fill-ink text-[12px] font-medium" style={{ unicodeBidi: "plaintext" }}>
          {t(`flow.${id}` as TKey)} <tspan className="fill-muted">{n} · {Math.round((n / total) * 100)}%</tspan>
        </text>
      </g>
    );
  };
  if (flow.received === 0) return <Empty text="—" />;
  return (
    // dir="ltr" on the drawing: SVG text-anchor flips meaning under an inherited RTL direction,
    // which pushed labels on top of the bars. Mirroring is done with coordinates instead.
    <div className="overflow-x-auto" dir="ltr">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full min-w-[640px]" role="img" aria-label={t("mon.flow")}>
        {paths}
        {node("received", xs[0], L0.received, flow.received, "start")}
        {mid.map((m) => node(m.id, xs[1], L1[m.id], m.n, "end"))}
        {end.map((e) => node(e.id, xs[2], L2[e.id], e.n, "end"))}
      </svg>
    </div>
  );
}

export default function MonitorPage() {
  const { t, lang, team } = useI18n();
  const { can } = useAuth();
  const q = useQuery({ queryKey: ["monitor"], queryFn: () => api<Overview>("/monitor/overview"), enabled: can("analytics:view"), refetchInterval: 15_000 });
  if (!can("analytics:view")) return <p className="p-6 text-sm text-muted">{t("common.noAccess")}</p>;
  if (q.isLoading || !q.data) return <div className="grid place-items-center py-24"><Spinner /></div>;
  const o = q.data;
  const atRisk = o.at_risk.filter((x) => x.state === "at_risk").length, breached = o.at_risk.filter((x) => x.state === "breached").length;
  const busy = o.queue.running > 0;
  const maxStage = Math.max(1, ...o.stages.map((s) => s.avg_ms));
  const maxOpen = Math.max(1, ...o.teams.map((x) => x.open));

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6">
      <PageHeader title={t("nav.monitor")} subtitle={t("mon.subtitle")} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Kpi label={t("mon.open")} value={o.open} />
        <Kpi label={t("mon.atRisk")} value={atRisk} tone={atRisk ? "warn" : undefined} />
        <Kpi label={t("mon.breached")} value={breached} tone={breached ? "danger" : "ok"} />
        <Kpi label={t("mon.queue")} value={o.queue.queued + o.queue.running} />
        <Kpi label={t("mon.failed")} value={o.queue.failed} tone={o.queue.failed ? "danger" : "ok"} />
      </div>

      <Card className="p-5">
        <div className="mb-3"><h2 className="font-semibold">{t("mon.flow")}</h2><p className="text-sm text-muted">{t("mon.flowHint")}</p></div>
        <FlowDiagram flow={o.flow} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="p-5 lg:col-span-3">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4 text-warn" />{t("mon.atRiskList")}</h2>
          {o.at_risk.length === 0 ? (
            <div className="flex items-center gap-2 rounded-lg bg-ok-soft px-3 py-4 text-sm text-ok"><CheckCircle2 className="h-4 w-4" />{t("mon.allGood")}</div>
          ) : (
            <ul className="divide-y divide-line">
              {o.at_risk.map((x) => (
                <li key={x.id}>
                  <Link href={`/inbox?status=all&t=${x.id}`} className="flex items-center gap-3 py-2.5 hover:bg-sunken/60">
                    <PriorityBadge p={x.priority} />
                    <span className="bidi min-w-0 flex-1 truncate text-sm font-medium">{x.subject}</span>
                    <span className="hidden sm:block"><TeamBadge team={x.team} /></span>
                    <SlaBadge sla={x} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5 lg:col-span-2">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><Clock className="h-4 w-4 text-muted" />{t("mon.slaByPriority")}</h2>
          <div className="space-y-3">
            {o.sla.map((r) => {
              const tot = r.on_track + r.at_risk + r.breached + r.met + r.missed;
              const seg = [["met", r.met, "bg-ok"], ["on_track", r.on_track, "bg-ok/50"], ["at_risk", r.at_risk, "bg-warn"],
                ["breached", r.breached, "bg-danger"], ["missed", r.missed, "bg-danger/50"]] as const;
              return (
                <div key={r.priority}>
                  <div className="mb-1 flex items-center gap-2 text-sm">
                    <PriorityBadge p={r.priority} /><span className="text-xs text-muted">{t("sla.target")} <span dir="ltr">{r.target_hours}h</span></span>
                    <span className="ms-auto text-xs tabular-nums text-muted">{tot}</span>
                  </div>
                  <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full bg-sunken">
                    {tot > 0 && seg.map(([k, n, c]) => n > 0 && <div key={k} className={c} style={{ width: `${(n / tot) * 100}%` }} title={`${t(`sla.${k}` as TKey)}: ${n}`} />)}
                  </div>
                </div>
              );
            })}
            <div className="flex flex-wrap gap-3 pt-1 text-[11px] text-muted">
              {([["met", "bg-ok"], ["on_track", "bg-ok/50"], ["at_risk", "bg-warn"], ["breached", "bg-danger"]] as const).map(([k, c]) => (
                <span key={k} className="flex items-center gap-1"><span className={cn("h-2 w-2 rounded-full", c)} />{t(`sla.${k}` as TKey)}</span>))}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="p-5">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><Cpu className="h-4 w-4 text-muted" />{t("mon.pipeline")}</h2>
          <div className="mb-4 flex items-center gap-2">
            <span className={cn("h-2.5 w-2.5 rounded-full", busy ? "animate-pulse bg-ok" : "bg-muted/50")} />
            <span className="text-sm font-medium">{t("mon.worker")}: {busy ? t("mon.workerBusy") : t("mon.workerIdle")}</span>
          </div>
          <dl className="space-y-2 text-sm">
            {[[t("mon.queue"), `${o.queue.queued} + ${o.queue.running}`], [t("mon.oldestWait"), o.queue.queued ? secs(o.queue.oldest_wait_s, lang) : "—"],
              [t("mon.lastDone"), o.queue.last_completed_at ? timeAgo(o.queue.last_completed_at, lang) : "—"],
              [t("mon.failed"), String(o.queue.failed)]].map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-line pb-2 last:border-0"><dt className="text-muted">{k}</dt><dd className="tabular-nums">{v}</dd></div>))}
          </dl>
        </Card>

        <Card className="p-5">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><Timer className="h-4 w-4 text-muted" />{t("mon.stages")}</h2>
          <div className="space-y-2.5">
            {o.stages.map((s) => (
              <div key={s.stage}>
                <div className="mb-1 flex justify-between text-xs"><span className="font-medium">{t(`mon.stage.${s.stage}` as TKey)}</span>
                  <span className="tabular-nums text-muted" dir="ltr">{(s.avg_ms / 1000).toFixed(1)}s · p95 {(s.p95_ms / 1000).toFixed(1)}s</span></div>
                <div className="h-2 overflow-hidden rounded-full bg-sunken"><div className="h-full rounded-full bg-primary" style={{ width: `${(s.avg_ms / maxStage) * 100}%` }} /></div>
              </div>
            ))}
            {o.stages.length === 0 && <p className="text-sm text-muted">—</p>}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="mb-3 flex items-center gap-2 font-semibold"><Inbox className="h-4 w-4 text-muted" />{t("mon.workload")}</h2>
          <div className="space-y-2.5">
            {o.teams.map((w) => (
              <div key={w.team}>
                <div className="mb-1 flex items-center gap-2 text-xs">
                  <span className="min-w-0 flex-1 truncate font-medium">{team(w.team)}</span>
                  {w.breached > 0 && <Badge tone="danger">{w.breached} {t("sla.breached")}</Badge>}
                  <span className="tabular-nums text-muted">{w.open} · {t("mon.oldest")} {secs(w.oldest_open_s, lang)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-sunken"><div className={cn("h-full rounded-full", w.breached ? "bg-danger" : "bg-primary")} style={{ width: `${(w.open / maxOpen) * 100}%` }} /></div>
              </div>
            ))}
            {o.teams.length === 0 && <p className="text-sm text-muted">—</p>}
          </div>
        </Card>
      </div>

      <Card className="p-5">
        <h2 className="mb-3 flex items-center gap-2 font-semibold"><Activity className="h-4 w-4 text-muted" />{t("mon.activity")}</h2>
        <ul className="divide-y divide-line text-sm">
          {o.activity.map((a, i) => {
            const Icon = a.kind === "received" ? Inbox : a.kind === "ai_done" ? (a.detail === "escalated" ? ShieldAlert : Cpu) : a.detail === "reject" ? XCircle : CheckCircle2;
            return (
              <li key={i}>
                <Link href={`/inbox?status=all&t=${a.ticket_id}`} className="flex items-center gap-3 py-2 hover:bg-sunken/60">
                  <Icon className={cn("h-4 w-4 shrink-0", a.detail === "escalated" ? "text-danger" : a.kind === "reviewed" ? "text-ok" : "text-muted")} />
                  <span className="min-w-0 flex-1 truncate">
                    {a.kind === "reviewed" ? <>{a.actor} {t("act.reviewed")} · {label(DECISIONS, a.detail, lang)}</>
                      : a.kind === "ai_done" ? <>{t("act.ai_done")} → {t(`flow.${a.detail}` as TKey)}</> : t("act.received")}
                  </span>
                  <span className="font-mono text-xs text-muted" dir="ltr">{a.ticket_id}</span>
                  <span className="w-20 text-end text-xs text-muted">{timeAgo(a.at, lang)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
