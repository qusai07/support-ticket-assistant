"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, Settings2, ShieldAlert, Tags, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Dropdown } from "@/components/dropdown";
import { Button, Card, ErrorNote, PageHeader, Spinner } from "@/components/ui";
import { api, patch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n, type TKey } from "@/lib/i18n";
import { desc, label, ROUTING_KEYS } from "@/lib/labels";

type Routing = { signals: Record<string, string>; rules: Record<string, string>; categories: Record<string, string> };
type Section = keyof Routing;
const SECTIONS: { id: Section; title: TKey; hint: TKey; icon: React.ElementType; keys: string[] }[] = [
  { id: "signals", title: "routing.signals", hint: "routing.signalsHint", icon: ShieldAlert, keys: ["safety", "legal", "fraud", "chargeback"] },
  { id: "rules", title: "routing.rules", hint: "routing.rulesHint", icon: TriangleAlert, keys: ["vip_customer", "very_negative_sentiment", "refund_over_threshold"] },
  { id: "categories", title: "routing.categories", hint: "routing.categoriesHint", icon: Tags, keys: ["billing", "refund", "shipping", "technical", "account", "other"] },
];

export default function RoutingPage() {
  const { t, lang, team } = useI18n();
  const { can } = useAuth();
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<{ values: { team_routing: Routing } }>("/settings"), enabled: can("settings:manage") });
  const teams = useQuery({ queryKey: ["teams"], queryFn: () => api<{ name: string; is_active: boolean }[]>("/admin/teams") });
  const [draft, setDraft] = useState<Routing | null>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => { if (settings.data) setDraft(settings.data.values.team_routing); }, [settings.data]);

  const save = useMutation({
    mutationFn: (r: Routing) => patch("/settings", { values: { team_routing: r } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["settings"] }); qc.invalidateQueries({ queryKey: ["teams"] }); setSaved(true); setTimeout(() => setSaved(false), 2500); },
  });

  if (!can("settings:manage")) return <p className="text-sm text-muted">{t("common.noAccess")}</p>;
  if (!draft) return <div className="grid place-items-center py-16"><Spinner /></div>;
  const options = (teams.data ?? []).filter((x) => x.is_active).map((x) => ({ value: x.name, label: team(x.name) }));
  const dirty = JSON.stringify(draft) !== JSON.stringify(settings.data?.values.team_routing);

  return (
    <div className="space-y-5">
      <PageHeader title={t("nav.routing")} subtitle={t("routing.subtitle")}
        actions={<Link href="/settings"><Button variant="ghost"><Settings2 className="h-4 w-4" />{t("routing.thresholds")}</Button></Link>} />
      {SECTIONS.map((sec, i) => {
        const Icon = sec.icon;
        return (
          <div key={sec.id}>
            <Card className="p-5">
              <div className="mb-4 flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary-soft text-primary"><Icon className="h-[18px] w-[18px]" /></span>
                <div><h2 className="font-semibold">{t(sec.title)}</h2><p className="text-sm text-muted">{t(sec.hint)}</p></div>
              </div>
              <div className="divide-y divide-line">
                {sec.keys.map((k) => (
                  <div key={k} className="flex flex-wrap items-center gap-3 py-3">
                    <div className="min-w-[200px] flex-1">
                      <div className="font-medium">{label(ROUTING_KEYS, k, lang)}</div>
                      {desc(ROUTING_KEYS, k, lang) && <div className="text-xs text-muted">{desc(ROUTING_KEYS, k, lang)}</div>}
                    </div>
                    <span className="text-muted" aria-hidden>{lang === "ar" ? "←" : "→"}</span>
                    <Dropdown className="w-64" searchable value={draft[sec.id][k]} options={options}
                      onChange={(v) => setDraft({ ...draft, [sec.id]: { ...draft[sec.id], [k]: v } })} />
                  </div>
                ))}
              </div>
            </Card>
            {i < SECTIONS.length - 1 && <div className="flex justify-center py-1.5 text-muted"><ArrowDown className="h-4 w-4" /></div>}
          </div>
        );
      })}
      <ErrorNote error={save.error} />
      <div className="sticky bottom-0 flex items-center justify-end gap-3 border-t border-line bg-bg/90 py-3 backdrop-blur">
        {saved && <span className="text-sm text-ok">✓ {t("common.saved")}</span>}
        {dirty && <span className="text-sm text-warn">{t("roles.unsaved")}</span>}
        <Button variant="primary" disabled={!dirty} loading={save.isPending} onClick={() => save.mutate(draft)}>{t("common.save")}</Button>
      </div>
    </div>
  );
}
