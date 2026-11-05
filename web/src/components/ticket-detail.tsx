"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bot, CheckCircle2, Cog, Loader2, Lock, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { api, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { timeAgo, useI18n } from "@/lib/i18n";
import { ACTIONS, DECISIONS, ESC_SOURCES, label, LANGUAGES, ROUTING_KEYS, SENTIMENTS, SIGNALS } from "@/lib/labels";
import type { TicketDetail } from "@/lib/types";
import { Dropdown } from "./dropdown";
import { SlaBadge, useTimeline, WorkflowPanel, WorkflowStepper } from "./workflow";
import { Badge, Button, CategoryBadge, cn, ErrorNote, Input, LangBadge, PriorityBadge, Spinner, StatusBadge, Tabs, TeamBadge, Textarea } from "./ui";

type Tab = "reply" | "workflow" | "triage" | "trace" | "context" | "history";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line py-2 text-sm last:border-0">
      <span className="text-muted">{label}</span><span className="text-end">{children}</span>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 0.85 ? "bg-ok" : value >= 0.6 ? "bg-warn" : "bg-danger";
  return <div className="h-2 w-full overflow-hidden rounded-full bg-sunken"><div className={cn("h-full rounded-full", color)} style={{ width: `${value * 100}%` }} /></div>;
}

export function TicketDetailPanel({ id }: { id: string }) {
  const { t, lang, team } = useI18n();
  const { can } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("reply");
  const { data: d, isLoading, error } = useQuery({
    queryKey: ["ticket", id], queryFn: () => api<TicketDetail>(`/tickets/${id}`),
    refetchInterval: (q) => (q.state.data?.ticket.status === "new" ? 5000 : false),
  });

  const original = d?.run?.agent_output?.draft_reply ?? "";
  const [draft, setDraft] = useState("");
  const [note, setNote] = useState("");
  useEffect(() => { setDraft(original); setNote(""); }, [id, original]);

  const timeline = useTimeline(id);
  const review = useMutation({
    mutationFn: (body: Record<string, unknown>) => post(`/tickets/${id}/review`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ticket", id] });
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      qc.invalidateQueries({ queryKey: ["monitor"] });
    },
  });

  if (isLoading) return <div className="grid place-items-center py-24"><Spinner /></div>;
  if (error || !d) return <div className="p-6"><ErrorNote error={error ?? "Not found"} /></div>;

  const tk = d.ticket, tri = d.triage, run = d.run, out = run?.agent_output;
  const actionable = ["in_review", "ready_to_send", "escalated"].includes(tk.status);
  const mayReview = can("tickets:review") && (tk.status !== "escalated" || can("tickets:handle_escalated"));
  const changed = draft.trim() !== original.trim();

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-4 sm:p-6">
      {/* header */}
      <div>
        <div className="flex flex-wrap items-center gap-1.5">
          <StatusBadge status={tk.status} />
          <PriorityBadge p={tri?.priority ?? tk.priority} />
          <CategoryBadge c={tri?.category} />
          <LangBadge lang={tri?.language ?? tk.language} />
          <TeamBadge team={tk.team} />
          {tri?.injection_suspected && <Badge tone="danger"><AlertTriangle className="h-3 w-3" />{t("ticket.injection")}</Badge>}
          <span className="ms-auto"><SlaBadge sla={timeline.data?.sla} /></span>
        </div>
        <h2 className="bidi mt-2 text-lg font-semibold">{tk.subject}</h2>
        <p className="mt-1 text-xs text-muted">
          {t("ticket.from")} <span dir="ltr">{tk.customer_email}</span> · {t("ticket.via")} {tk.channel} · {timeAgo(tk.created_at, lang)} · <span dir="ltr">{tk.id}</span>
          {" · "}{t("ticket.assignee")}: {d.assignee?.full_name ?? t("ticket.unassigned")}
        </p>
      </div>

      {timeline.data && (
        <button type="button" onClick={() => setTab("workflow")} className="block w-full rounded-xl border border-line bg-surface px-2 py-4 transition-colors hover:border-primary/40">
          <WorkflowStepper tl={timeline.data} />
        </button>
      )}

      <div className="bidi rounded-xl border border-line bg-surface p-4 text-sm leading-relaxed">{tk.body}</div>

      {tk.status === "new" && (
        <div className="flex items-center gap-2 rounded-xl border border-primary/30 bg-primary-soft p-4 text-sm text-primary">
          <Loader2 className="h-4 w-4 animate-spin" />{t("ticket.processing")}
        </div>
      )}

      {d.escalations.map((e, i) => (
        <div key={i} className="rounded-xl border border-danger/30 bg-danger-soft/60 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-danger">
            <ShieldAlert className="h-4 w-4" />{t("ticket.escalatedBy")} {label(ESC_SOURCES, e.source, lang)}
            <span className="flex flex-wrap gap-1">{e.reason.split(",").map((r) => <Badge key={r} tone="danger">{label(ROUTING_KEYS, r.trim().replace(/_language$/, ""), lang)}</Badge>)}</span>
          </div>
          <pre className="bidi mt-2 font-sans text-sm text-ink/90">{e.summary}</pre>
        </div>
      ))}

      {can("tickets:reassign") && <Reassign id={id} currentTeam={tk.team} assignee={tk.assignee_id} />}

      <Tabs<Tab> value={tab} onChange={setTab} tabs={[
        { id: "reply", label: t("ticket.tab.reply") }, { id: "workflow", label: t("ticket.tab.workflow") },
        { id: "triage", label: t("ticket.tab.triage") },
        { id: "trace", label: t("ticket.tab.trace") }, { id: "context", label: t("ticket.tab.context") },
        { id: "history", label: `${t("ticket.tab.history")}${d.reviews.length ? ` · ${d.reviews.length}` : ""}` },
      ]} />

      {tab === "reply" && (
        <div className="space-y-4">
          {out && (
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-muted">{t("ticket.confidence")} <span className="font-semibold text-ink">{out.confidence.toFixed(2)}</span></div>
                <ConfidenceBar value={out.confidence} />
                <div className="text-xs text-muted">{t("ticket.modelSaid")} {run?.raw_confidence ?? "–"}</div>
              </div>
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-muted">{t("ticket.recommends")}</div>
                <Badge tone={out.recommended_action === "send" ? "ok" : out.recommended_action === "escalate" ? "danger" : "warn"}>{label(ACTIONS, out.recommended_action, lang)}</Badge>
              </div>
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-muted">{t("ticket.sources")}</div>
                <div className="flex flex-wrap gap-1">{out.sources.length ? out.sources.map((s) => <Badge key={s} dir="ltr">{s}</Badge>) : <span className="text-xs text-muted">{t("ticket.noSources")}</span>}</div>
              </div>
            </div>
          )}
          {run && tk.status === "in_review" && run.status_reasons.length > 0 && (
            <p className="text-xs text-muted"><span className="font-medium">{t("ticket.whyReview")}:</span> <span dir="ltr">{run.status_reasons.join(" · ")}</span></p>
          )}
          {run && run.guardrail_flags.length > 0 && (
            <div className="rounded-lg border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn" dir="ltr">⚠ {t("ticket.guardrails")}: {run.guardrail_flags.join(", ")}</div>
          )}
          {!out && tk.status === "escalated" && <p className="text-sm text-muted">{t("ticket.noAgent")}</p>}

          <Textarea rows={12} value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t("ticket.replyPlaceholder")}
            readOnly={!actionable || !mayReview} />

          {actionable && !mayReview && (
            <p className="flex items-center gap-2 text-sm text-muted"><Lock className="h-4 w-4" />
              {tk.status === "escalated" && can("tickets:review") ? t("ticket.escalatedLeadOnly") : t("ticket.readOnly")}</p>
          )}
          {actionable && mayReview && (
            <div className="space-y-3">
              <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder={t("ticket.note")} />
              <ErrorNote error={review.error} />
              <div className="flex flex-wrap gap-2">
                {changed ? (
                  <Button variant="primary" loading={review.isPending} disabled={!draft.trim()}
                    onClick={() => review.mutate({ decision: "edit", edited_reply: draft, comment: note || null })}>{t("ticket.saveEdit")}</Button>
                ) : (
                  <Button variant="primary" loading={review.isPending} disabled={!original}
                    onClick={() => review.mutate({ decision: "approve", comment: note || null })}><CheckCircle2 className="h-4 w-4" />{t("ticket.approve")}</Button>
                )}
                <Button onClick={() => review.mutate({ decision: "reject", comment: note || null })} disabled={review.isPending}>{t("ticket.reject")}</Button>
                {tk.status !== "escalated" && (
                  <Button variant="danger" onClick={() => review.mutate({ decision: "escalate", comment: note || null })} disabled={review.isPending}>{t("ticket.escalate")}</Button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "workflow" && <WorkflowPanel id={id} />}

      {tab === "triage" && (
        <div className="grid gap-6 md:grid-cols-2">
          {tri ? (
            <>
              <div>
                <Row label={t("ticket.language")}>{label(LANGUAGES, tri.language, lang)}</Row>
                <Row label={t("ticket.team")}>{team(run?.routing.team ?? tk.team)}</Row>
                <Row label={t("ticket.category")}><span className="flex flex-wrap justify-end gap-1"><CategoryBadge c={tri.category} />{tri.secondary_categories.map((c) => <CategoryBadge key={c} c={c} />)}</span></Row>
                <Row label={t("ticket.priority")}><PriorityBadge p={tri.priority} /></Row>
                <Row label={t("ticket.sentiment")}>{label(SENTIMENTS, tri.sentiment, lang)} <span dir="ltr" className="text-muted">({tri.sentiment_score.toFixed(1)})</span></Row>
                <Row label={t("ticket.injection")}>{tri.injection_suspected ? <Badge tone="danger">{t("ticket.suspected")}</Badge> : t("common.no")}</Row>
              </div>
              <div>
                <Row label={t("ticket.signals")}><span className="flex flex-wrap justify-end gap-1">{tri.urgency_signals.length ? tri.urgency_signals.map((s) => (
                  <Badge key={s} tone={["legal", "chargeback", "safety", "fraud"].includes(s) ? "danger" : "neutral"}>{label(SIGNALS, s, lang)}</Badge>)) : "–"}</span></Row>
                <Row label={t("ticket.orders")}><span dir="ltr">{tri.entities.order_ids.join(", ") || "–"}</span></Row>
                <Row label={t("ticket.amounts")}><span dir="ltr">{tri.entities.amounts.map((a) => `$${a}`).join(", ") || "–"}</span></Row>
                <Row label={t("ticket.missing")}>{tri.missing_info.join(", ") || "–"}</Row>
                {tri.rationale && <p className="mt-3 text-xs text-muted" dir="ltr">{tri.rationale}</p>}
              </div>
            </>
          ) : <p className="text-sm text-muted">{t("ticket.processing")}</p>}
          <div className="md:col-span-2">
            <h3 className="mb-2 text-sm font-semibold">{t("ticket.rules")}</h3>
            {run?.routing.hits?.length ? (
              <ul className="space-y-1.5">{run.routing.hits.map((h) => (
                <li key={h.rule} className="flex items-start gap-2 text-sm"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
                  <span><span className="font-medium">{label(ROUTING_KEYS, h.rule.replace(/_language$/, ""), lang)}</span>
                    <span className="ms-2 text-muted" dir="ltr">{h.detail}</span></span></li>))}</ul>
            ) : run ? <p className="flex items-center gap-2 text-sm text-muted"><CheckCircle2 className="h-4 w-4 text-ok" />{t("ticket.noRules")}</p> : null}
          </div>
        </div>
      )}

      {tab === "trace" && (
        <div className="space-y-4">
          <ol className="space-y-2">
            {d.tool_calls.map((c) => {
              const err = c.error ?? (c.result && typeof c.result === "object" && "error" in (c.result as object) ? String((c.result as Record<string, unknown>).error) : null);
              return (
                <li key={c.seq} className="rounded-lg border border-line bg-surface">
                  <details>
                    <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm">
                      {c.step === "prefetch" ? <Cog className="h-4 w-4 text-muted" /> : <Bot className="h-4 w-4 text-primary" />}
                      <code dir="ltr" className="truncate">{c.tool}({Object.entries(c.args).map(([k, v]) => `${k}=${v}`).join(", ")})</code>
                      {err && <Badge tone="danger" dir="ltr">{err}</Badge>}
                      <span className="ms-auto shrink-0 text-xs text-muted">{c.step === "prefetch" ? t("ticket.prefetch") : t("ticket.agentCall")} · {c.latency_ms} ms</span>
                    </summary>
                    <pre dir="ltr" className="max-h-80 overflow-auto border-t border-line bg-sunken p-3 text-xs">{JSON.stringify(c.error ?? c.result, null, 2)}</pre>
                  </details>
                </li>
              );
            })}
          </ol>
          {d.llm_calls.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">{t("ticket.llmCalls")}</h3>
              <div className="overflow-x-auto rounded-lg border border-line">
                <table className="w-full text-sm" dir="ltr">
                  <thead className="bg-sunken text-xs text-muted"><tr>{["purpose", "model", "in", "out", "ms"].map((h) => <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>)}</tr></thead>
                  <tbody>{d.llm_calls.map((c, i) => (
                    <tr key={i} className="border-t border-line"><td className="px-3 py-1.5">{c.purpose}</td><td className="px-3 py-1.5">{c.model}</td>
                      <td className="px-3 py-1.5 tabular-nums">{c.input_tokens}</td><td className="px-3 py-1.5 tabular-nums">{c.output_tokens}</td>
                      <td className="px-3 py-1.5 tabular-nums">{c.latency_ms}</td></tr>))}</tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "context" && (
        <ul className="space-y-2">
          {run?.retrieved.map((doc) => (
            <li key={doc.source_id} className="rounded-lg border border-line bg-surface">
              <details>
                <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 px-3 py-2 text-sm">
                  <Badge dir="ltr">{doc.source_id}</Badge>
                  <span className="bidi font-medium">{doc.title}</span>
                  <span className="text-xs text-muted">{doc.source_type === "kb" ? t("ticket.helpArticle") : t("ticket.pastTicket")} · {doc.score.toFixed(2)}</span>
                  {out?.sources.includes(doc.source_id) && <Badge tone="ok">✓ {t("ticket.cited")}</Badge>}
                </summary>
                <p className="bidi border-t border-line p-3 text-sm text-ink/90">{doc.snippet}</p>
              </details>
            </li>
          ))}
        </ul>
      )}

      {tab === "history" && (
        <ul className="space-y-3">
          {d.reviews.map((r, i) => (
            <li key={i} className="rounded-lg border border-line bg-surface p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={r.decision === "reject" ? "neutral" : r.decision === "escalate" ? "danger" : "ok"}>{label(DECISIONS, r.decision, lang)}</Badge>
                <span className="text-muted">{t("ticket.reviewedBy")} {r.reviewer} · {timeAgo(r.created_at, lang)}</span>
              </div>
              {r.comment && <p className="bidi mt-2">{r.comment}</p>}
              {r.decision === "edit" && (
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div><div className="mb-1 text-xs text-muted">{t("ticket.original")}</div><div className="bidi rounded-lg bg-sunken p-3 text-xs">{r.original_reply}</div></div>
                  <div><div className="mb-1 text-xs text-muted">{t("ticket.sent")}</div><div className="bidi rounded-lg bg-ok-soft p-3 text-xs">{r.final_reply}</div></div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Reassign({ id, currentTeam, assignee }: { id: string; currentTeam: string | null; assignee: number | null }) {
  const { t, team } = useI18n();
  const qc = useQueryClient();
  const meta = useQuery({ queryKey: ["users-meta"], queryFn: () => api<{ teams: string[] }>("/users/meta"), staleTime: Infinity });
  const people = useQuery({ queryKey: ["assignable"], queryFn: () => api<{ id: number; full_name: string; team: string }[]>("/users/assignable"), staleTime: 60_000 });
  const m = useMutation({
    mutationFn: (body: Record<string, unknown>) => post(`/tickets/${id}/assign`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ticket", id] }); qc.invalidateQueries({ queryKey: ["tickets"] }); },
  });
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-line bg-surface p-3 text-sm">
      <span className="font-medium">{t("ticket.reassign")}</span>
      <Dropdown className="w-56" size="sm" searchable value={currentTeam ?? ""} ariaLabel={t("ticket.moveTo")}
        options={(meta.data?.teams ?? []).map((tm) => ({ value: tm, label: team(tm) }))}
        onChange={(tm) => m.mutate({ team: tm })} />
      <Dropdown className="w-64" size="sm" searchable value={assignee ? String(assignee) : null} placeholder={`${t("ticket.assignTo")}…`} ariaLabel={t("ticket.assignTo")}
        options={(people.data ?? []).map((p) => ({ value: String(p.id), label: p.full_name, hint: team(p.team), group: team(p.team) }))}
        onChange={(id) => m.mutate({ assignee_id: Number(id) })} />
      {m.isPending && <Spinner className="h-4 w-4" />}
      <ErrorNote error={m.error} />
    </div>
  );
}
