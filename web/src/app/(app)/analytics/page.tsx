"use client";

/** Analytics. Chart rules (dataviz method): one hue for single-measure charts, the first three
 *  validated categorical slots (blue, orange, aqua) for the 3-series comparison with a legend AND
 *  value labels (aqua is < 3:1 on white, so labels are the required relief), one y-axis per chart,
 *  recessive grid, thin bars with 4px rounded data-ends. Charts mirror in RTL. */
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, Empty, Kpi, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n, type TKey } from "@/lib/i18n";
import { DECISIONS, label, LANGUAGES } from "@/lib/labels";
import { useTheme } from "@/lib/theme";

type Ops = {
  daily: ({ date: string } & Record<string, number | string>)[]; by_team: Record<string, number>;
  by_language: Record<string, number>; by_priority: Record<string, number>; reviews: Record<string, number>;
  edit_rate: number | null; avg_latency_s: number | null; auto_resolved: number; total: number;
};
type Slice = { n: number; category: number; priority: number; action: number };
type Evaluation = {
  available: boolean; n: number; category_acc: number; priority_acc: number; action_acc: number;
  escalation: { precision: number; recall: number; tp: number; fp: number; fn: number };
  auto_send: { auto_resolution_rate: number; unsafe_auto_sent: number; unsafe_ids: string[] };
  groundedness: { claim_support_rate: number; fully_grounded_rate: number; judged: number };
  latency: { mean: number; p50: number; p95: number };
  confusion: Record<string, Record<string, number>>; by_language: Record<string, Slice>;
  by_tag: Record<string, { n: number; action_acc: number }>;
};

const PALETTE = {
  light: { s1: "#2a78d6", s2: "#eb6834", s3: "#1baf7a", grid: "#e4e4ee", axis: "#666a80" },
  dark: { s1: "#3987e5", s2: "#d95926", s3: "#199e70", grid: "#2c2e3e", axis: "#969ab0" },
};
// Sequential blue ramp (light -> dark) for the confusion-matrix cells.
const SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"];
const pct = (x: number) => `${Math.round(x * 100)}%`;

function useChart() {
  const { theme } = useTheme();
  const { dir } = useI18n();
  const c = PALETTE[theme];
  const rtl = dir === "rtl";
  const tooltip = {
    contentStyle: { background: "rgb(var(--surface))", border: "1px solid rgb(var(--line))", borderRadius: 8, fontSize: 12 },
    labelStyle: { color: "rgb(var(--ink))", fontWeight: 600 }, itemStyle: { color: "rgb(var(--ink))" },
    cursor: { fill: "rgb(var(--sunken))" },
  };
  return { c, rtl, tooltip, tick: { fill: c.axis, fontSize: 12 } };
}

function ChartCard({ title, children, height = 240 }: { title: string; children: React.ReactElement; height?: number }) {
  return (
    <Card className="p-4">
      <h3 className="mb-3 text-sm font-semibold">{title}</h3>
      {/* dir="ltr": under an inherited RTL direction SVG text-anchor flips and labels get clipped.
          RTL mirroring is done through reversed axes / right-side orientation instead. */}
      <div style={{ height }} dir="ltr"><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>
    </Card>
  );
}

function HBars({ title, data }: { title: string; data: { name: string; value: number }[] }) {
  const { c, rtl, tooltip, tick } = useChart();
  const sorted = [...data].sort((a, b) => b.value - a.value);
  return (
    <ChartCard title={title} height={Math.max(140, sorted.length * 34 + 30)}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 8, right: 24 }} barCategoryGap={6}>
        <CartesianGrid horizontal={false} stroke={c.grid} />
        <XAxis type="number" allowDecimals={false} reversed={rtl} tick={tick} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="name" width={150} orientation={rtl ? "right" : "left"} tick={tick} axisLine={false} tickLine={false} />
        <Tooltip {...tooltip} />
        <Bar dataKey="value" fill={c.s1} radius={rtl ? [4, 0, 0, 4] : [0, 4, 4, 0]} maxBarSize={18} />
      </BarChart>
    </ChartCard>
  );
}

export default function AnalyticsPage() {
  const { t, team, lang } = useI18n();
  const { can } = useAuth();
  const { c, rtl, tooltip, tick } = useChart();
  const ops = useQuery({ queryKey: ["ops"], queryFn: () => api<Ops>("/analytics/ops"), enabled: can("analytics:view"), refetchInterval: 30_000 });
  const ev = useQuery({ queryKey: ["eval"], queryFn: () => api<Evaluation>("/analytics/eval"), enabled: can("analytics:view") });

  if (!can("analytics:view")) return <p className="p-6 text-sm text-muted">{t("common.noAccess")}</p>;
  const o = ops.data, e = ev.data;
  const toRows = (r?: Record<string, number>, label: (k: string) => string = (k) => k) =>
    Object.entries(r ?? {}).map(([k, v]) => ({ name: label(k), value: v }));

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-4 sm:p-6">
      <PageHeader title={t("an.title")} />

      <section className="space-y-4">
        <h2 className="font-semibold">{t("an.ops")}</h2>
        {ops.isLoading ? <Spinner /> : o && (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Kpi label={t("inbox.kpi.total")} value={o.total} />
              <Kpi label={t("an.autoResolved")} value={o.total ? pct(o.auto_resolved / o.total) : "–"} tone="ok" />
              <Kpi label={t("an.editRate")} value={o.edit_rate == null ? "–" : pct(o.edit_rate)} />
              <Kpi label={t("inbox.kpi.latency")} value={o.avg_latency_s == null ? "–" : `${o.avg_latency_s.toFixed(1)}s`} />
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <ChartCard title={t("an.daily")}>
                <BarChart data={o.daily.map((d) => ({ date: d.date.slice(5), total: Object.entries(d).filter(([k]) => k !== "date").reduce((s, [, v]) => s + Number(v), 0) }))}>
                  <CartesianGrid vertical={false} stroke={c.grid} />
                  <XAxis dataKey="date" reversed={rtl} tick={tick} axisLine={{ stroke: c.grid }} tickLine={false} />
                  <YAxis allowDecimals={false} orientation={rtl ? "right" : "left"} tick={tick} axisLine={false} tickLine={false} width={32} />
                  <Tooltip {...tooltip} />
                  <Bar dataKey="total" name={t("inbox.kpi.total")} fill={c.s1} radius={[4, 4, 0, 0]} maxBarSize={28} />
                </BarChart>
              </ChartCard>
              <HBars title={t("an.byTeam")} data={toRows(o.by_team, team)} />
              <HBars title={t("an.byLanguage")} data={toRows(o.by_language, (k) => label(LANGUAGES, k, lang))} />
              <HBars title={t("an.reviews")} data={toRows(o.reviews, (k) => label(DECISIONS, k, lang))} />
            </div>
          </>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="font-semibold">{t("an.eval")}{e?.available && <span className="ms-2 text-sm font-normal text-muted">n = {e.n}</span>}</h2>
        {ev.isLoading ? <Spinner /> : !e?.available ? <Card><Empty text={t("an.evalNone")} /></Card> : (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Kpi label={t("an.catAcc")} value={pct(e.category_acc)} />
              <Kpi label={t("an.priAcc")} value={pct(e.priority_acc)} />
              <Kpi label={t("an.actionAcc")} value={pct(e.action_acc)} />
              {/* "–" when undefined: with no expected escalations in the sample, recall isn't 0%, it's unknown. */}
              <Kpi label={t("an.escRecall")} value={e.escalation.tp + e.escalation.fn ? pct(e.escalation.recall) : "–"}
                tone={e.escalation.tp + e.escalation.fn ? (e.escalation.recall >= 0.95 ? "ok" : "warn") : undefined} />
              <Kpi label={t("an.escPrecision")} value={e.escalation.tp + e.escalation.fp ? pct(e.escalation.precision) : "–"} />
              <Kpi label={t("an.unsafe")} value={e.auto_send.unsafe_auto_sent} tone={e.auto_send.unsafe_auto_sent ? "danger" : "ok"} />
              <Kpi label={t("an.grounded")} value={e.groundedness.judged ? pct(e.groundedness.claim_support_rate) : "–"} />
              <Kpi label={t("an.autoResolved")} value={pct(e.auto_send.auto_resolution_rate)} />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <ChartCard title={t("an.byLang")} height={280}>
                <BarChart data={Object.entries(e.by_language).map(([k, v]) => ({ name: `${k} (n=${v.n})`, ...v }))} barGap={2} margin={{ top: 18 }}>
                  <CartesianGrid vertical={false} stroke={c.grid} />
                  <XAxis dataKey="name" reversed={rtl} tick={tick} axisLine={{ stroke: c.grid }} tickLine={false} interval={0} />
                  <YAxis domain={[0, 1]} tickFormatter={pct} orientation={rtl ? "right" : "left"} tick={tick} axisLine={false} tickLine={false} width={40} />
                  <Tooltip {...tooltip} formatter={(v: number) => pct(v)} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {([["category", "an.catAcc", c.s1], ["priority", "an.priAcc", c.s2], ["action", "an.actionAcc", c.s3]] as const).map(([k, label, color]) => (
                    <Bar key={k} dataKey={k} name={t(label as TKey)} fill={color} radius={[4, 4, 0, 0]} maxBarSize={22}>
                      <LabelList dataKey={k} position="top" formatter={pct} style={{ fill: "rgb(var(--muted))", fontSize: 10 }} />
                    </Bar>
                  ))}
                </BarChart>
              </ChartCard>

              <Card className="p-4">
                <h3 className="mb-3 text-sm font-semibold">{t("an.confusion")}</h3>
                <ConfusionTable m={e.confusion} />
                <p className="mt-3 text-xs text-muted" dir="ltr">latency p50 {e.latency.p50?.toFixed(0)}s · p95 {e.latency.p95?.toFixed(0)}s
                  {e.auto_send.unsafe_ids.length > 0 && ` · unsafe: ${e.auto_send.unsafe_ids.join(", ")}`}</p>
              </Card>
            </div>

            <Card className="overflow-x-auto p-4">
              <h3 className="mb-3 text-sm font-semibold">{t("an.byTag")}</h3>
              <table className="w-full text-sm" dir="ltr">
                <tbody>
                  {Object.entries(e.by_tag).sort((a, b) => a[1].action_acc - b[1].action_acc).map(([tag, v]) => (
                    <tr key={tag} className="border-t border-line first:border-0">
                      <td className="w-48 py-1.5 font-mono text-xs">{tag}</td>
                      <td className="w-12 py-1.5 text-xs text-muted tabular-nums">n={v.n}</td>
                      <td className="py-1.5">
                        <div className="flex items-center gap-2">
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-sunken"><div className="h-full rounded-full" style={{ width: pct(v.action_acc), background: c.s1 }} /></div>
                          <span className="w-10 text-end text-xs tabular-nums">{pct(v.action_acc)}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </>
        )}
      </section>
    </div>
  );
}

function ConfusionTable({ m }: { m: Record<string, Record<string, number>> }) {
  const keys = ["send", "human_review", "escalate"];
  const max = Math.max(1, ...keys.flatMap((r) => keys.map((col) => m[r]?.[col] ?? 0)));
  return (
    <table className="w-full table-fixed text-sm" dir="ltr">
      <thead><tr><th className="w-28" />{keys.map((k) => <th key={k} className="pb-2 text-center text-xs font-medium text-muted">{k}</th>)}</tr></thead>
      <tbody>
        {keys.map((r) => (
          <tr key={r}>
            <td className="py-1 pe-2 text-xs font-medium text-muted">{r}</td>
            {keys.map((col) => {
              const v = m[r]?.[col] ?? 0;
              const step = v === 0 ? -1 : Math.min(SEQ.length - 1, Math.floor((v / max) * (SEQ.length - 1)));
              return (
                <td key={col} className="p-1">
                  <div className="grid h-12 place-items-center rounded-md text-sm font-semibold tabular-nums"
                    style={{ background: step < 0 ? "rgb(var(--sunken))" : SEQ[step], color: step >= 3 ? "#fff" : step < 0 ? "rgb(var(--muted))" : "#0b0b0b",
                      outline: r === col ? "2px solid rgb(var(--ok))" : undefined }}>
                    {v}
                  </div>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
