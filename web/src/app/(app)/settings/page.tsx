"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button, Card, cn, ErrorNote, Field, Input, PageHeader, Spinner } from "@/components/ui";
import { api, patch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n, type TKey } from "@/lib/i18n";

type Values = {
  refund_escalation_threshold: number; auto_send_confidence: number; very_negative_sentiment: number;
  low_risk_categories: string[]; auto_send_enabled: boolean; triage_model: string; agent_model: string;
  sla_hours: Record<"P1" | "P2" | "P3" | "P4", number>;
};
const CATS = ["shipping", "technical", "account", "other", "billing", "refund"];
const LOCKED = ["billing", "refund"]; // never auto-sendable (enforced by the backend too)

export default function SettingsPage() {
  const { t } = useI18n();
  const { can } = useAuth();
  const editable = can("settings:manage");
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["settings"], queryFn: () => api<{ values: Values; defaults: Values }>("/settings"), enabled: can("analytics:view") });
  const [v, setV] = useState<Values | null>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => { if (q.data) setV(q.data.values); }, [q.data]);

  const save = useMutation({
    mutationFn: (values: Values) => patch("/settings", { values }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["settings"] }); setSaved(true); setTimeout(() => setSaved(false), 2500); },
  });

  if (!can("analytics:view")) return <p className="p-6 text-sm text-muted">{t("common.noAccess")}</p>;
  if (!v || !q.data) return <div className="grid place-items-center py-24"><Spinner /></div>;
  const d = q.data.defaults;
  const num = (k: keyof Values) => (e: React.ChangeEvent<HTMLInputElement>) => setV({ ...v, [k]: Number(e.target.value) });
  const hint = (k: TKey, key: keyof Values) => `${t(k)} · ${t("set.default")}: ${String(d[key])}`;

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6">
      <PageHeader title={t("set.title")} subtitle={t("set.subtitle")} />
      <Card className="space-y-6 p-6">
        <label className="flex items-start gap-3">
          <input type="checkbox" className="mt-1 h-4 w-4 accent-[rgb(var(--primary))]" checked={v.auto_send_enabled} disabled={!editable}
            onChange={(e) => setV({ ...v, auto_send_enabled: e.target.checked })} />
          <span><span className="block text-sm font-medium">{t("set.autoSend")}</span><span className="text-xs text-muted">{t("set.autoSendHint")}</span></span>
        </label>
        <div className="grid gap-6 sm:grid-cols-3">
          <Field label={t("set.refund")} hint={hint("set.refundHint", "refund_escalation_threshold")}>
            <Input type="number" min={0} step={10} dir="ltr" value={v.refund_escalation_threshold} onChange={num("refund_escalation_threshold")} disabled={!editable} />
          </Field>
          <Field label={t("set.conf")} hint={hint("set.confHint", "auto_send_confidence")}>
            <Input type="number" min={0.5} max={1} step={0.01} dir="ltr" value={v.auto_send_confidence} onChange={num("auto_send_confidence")} disabled={!editable} />
          </Field>
          <Field label={t("set.neg")} hint={hint("set.negHint", "very_negative_sentiment")}>
            <Input type="number" min={-1} max={0} step={0.05} dir="ltr" value={v.very_negative_sentiment} onChange={num("very_negative_sentiment")} disabled={!editable} />
          </Field>
        </div>
        <div>
          <div className="text-sm font-medium">{t("set.lowRisk")}</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {CATS.map((c) => {
              const on = v.low_risk_categories.includes(c), locked = LOCKED.includes(c);
              return (
                <button key={c} type="button" disabled={!editable || locked}
                  onClick={() => setV({ ...v, low_risk_categories: on ? v.low_risk_categories.filter((x) => x !== c) : [...v.low_risk_categories, c] })}
                  className={cn("rounded-full border px-3 py-1 text-sm transition-colors disabled:cursor-not-allowed",
                    on ? "border-primary bg-primary-soft text-primary" : "border-line text-muted", locked && "opacity-50")}>
                  {t(`cat.${c}` as TKey)}{locked && " 🔒"}
                </button>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-muted">{t("set.lowRiskHint")}</p>
        </div>
        <div>
          <div className="text-sm font-medium">{t("set.sla")}</div>
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(["P1", "P2", "P3", "P4"] as const).map((p) => (
              <label key={p} className="flex items-center gap-2 rounded-lg border border-line px-3 py-2">
                <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", p === "P1" ? "bg-danger text-white" : p === "P2" ? "bg-orange-600 text-white" : "bg-sunken text-muted")}>{p}</span>
                <Input type="number" min={0.25} step={0.25} dir="ltr" className="h-8 border-0 px-1" value={v.sla_hours[p]} disabled={!editable}
                  onChange={(e) => setV({ ...v, sla_hours: { ...v.sla_hours, [p]: Number(e.target.value) } })} />
                <span className="text-xs text-muted">h</span>
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted">{t("set.slaHint")}</p>
        </div>
        <div className="grid gap-6 sm:grid-cols-2">
          <Field label={t("set.triageModel")} hint={`${t("set.default")}: ${d.triage_model}`}>
            <Input dir="ltr" value={v.triage_model} onChange={(e) => setV({ ...v, triage_model: e.target.value })} disabled={!editable} />
          </Field>
          <Field label={t("set.agentModel")} hint={`${t("set.default")}: ${d.agent_model}`}>
            <Input dir="ltr" value={v.agent_model} onChange={(e) => setV({ ...v, agent_model: e.target.value })} disabled={!editable} />
          </Field>
        </div>
        <ErrorNote error={save.error} />
        {editable ? (
          <div className="flex items-center justify-end gap-3">
            {saved && <span className="text-sm text-ok">✓ {t("common.saved")}</span>}
            <Button variant="primary" loading={save.isPending} onClick={() => save.mutate(v)}>{t("common.save")}</Button>
          </div>
        ) : <p className="text-xs text-muted">🔒 {t("ticket.readOnly")}</p>}
      </Card>
    </div>
  );
}
