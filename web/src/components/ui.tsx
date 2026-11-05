"use client";

/** Small design system. RTL rule: use logical utilities only (ms-/me-, ps-/pe-, start-/end-,
 *  text-start) and never ml-/mr-/left-/right-, so every component mirrors itself in Arabic. */
import clsx from "clsx";
import { Loader2 } from "lucide-react";
import { forwardRef } from "react";
import { useI18n, type TKey } from "@/lib/i18n";
import type { Status } from "@/lib/types";

export const cn = clsx;

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger"; size?: "sm" | "md"; loading?: boolean;
};
export const Button = forwardRef<HTMLButtonElement, BtnProps>(function Button(
  { variant = "secondary", size = "md", loading, className, children, disabled, ...p }, ref) {
  return (
    <button ref={ref} disabled={disabled || loading} className={cn(
      "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
      size === "sm" ? "h-8 px-3 text-sm" : "h-10 px-4 text-sm",
      variant === "primary" && "bg-primary text-primary-fg hover:bg-primary/90",
      variant === "secondary" && "border border-line bg-surface text-ink hover:bg-sunken",
      variant === "ghost" && "text-muted hover:bg-sunken hover:text-ink",
      variant === "danger" && "border border-danger/30 bg-danger-soft text-danger hover:bg-danger/15",
      className)} {...p}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
});

export function Card({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-xl border border-line bg-surface shadow-card", className)} {...p} />;
}

const field = "w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink placeholder:text-muted/70 focus:border-primary";
export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...p }, ref) { return <input ref={ref} className={cn(field, "h-10", className)} {...p} />; });
export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...p }, ref) { return <textarea ref={ref} className={cn(field, "bidi py-2 leading-relaxed", className)} {...p} />; });
export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, ...p }, ref) { return <select ref={ref} className={cn(field, "h-10", className)} {...p} />; });

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-ink">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted">{hint}</span>}
    </label>
  );
}

const TONES = {
  neutral: "border-line bg-sunken text-muted",
  primary: "border-primary/25 bg-primary-soft text-primary",
  danger: "border-danger/25 bg-danger-soft text-danger",
  warn: "border-warn/25 bg-warn-soft text-warn",
  ok: "border-ok/25 bg-ok-soft text-ok",
  info: "border-info/25 bg-info-soft text-info",
  solidDanger: "border-transparent bg-danger text-white",
  solidWarn: "border-transparent bg-orange-600 text-white",
} as const;
export type Tone = keyof typeof TONES;

export function Badge({ tone = "neutral", className, children, ...rest }: { tone?: Tone } & React.HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium", TONES[tone], className)} {...rest}>{children}</span>;
}

const STATUS_TONE: Record<Status, Tone> = {
  new: "primary", triaged: "primary", in_review: "warn", escalated: "danger", ready_to_send: "ok",
  approved: "info", rejected: "neutral", sent: "info",
};
export function StatusBadge({ status }: { status: Status }) {
  const { t } = useI18n();
  return <Badge tone={STATUS_TONE[status]}>{(status === "new" || status === "triaged") && <Loader2 className="h-3 w-3 animate-spin" />}{t(`status.${status}` as TKey)}</Badge>;
}

export function PriorityBadge({ p }: { p?: string | null }) {
  if (!p) return null;
  const tone: Tone = p === "P1" ? "solidDanger" : p === "P2" ? "solidWarn" : p === "P3" ? "primary" : "neutral";
  return <Badge tone={tone}>{p}</Badge>;
}

export function CategoryBadge({ c }: { c?: string | null }) {
  const { t } = useI18n();
  return c ? <Badge>{t(`cat.${c}` as TKey)}</Badge> : null;
}

const LANG_LABEL: Record<string, string> = { ar: "عربي", mixed: "عربي + EN", ar_latn: "Arabizi" };
export function LangBadge({ lang }: { lang?: string | null }) {
  return lang && lang !== "en" ? <Badge tone="info">{LANG_LABEL[lang] ?? lang}</Badge> : null;
}

export function TeamBadge({ team }: { team?: string | null }) {
  const { team: tr } = useI18n();
  return team ? <Badge tone="primary">{tr(team)}</Badge> : null;
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-5 w-5 animate-spin text-muted", className)} />;
}

export function Empty({ icon, text }: { icon?: React.ReactNode; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center text-muted">
      {icon}
      <p className="text-sm">{text}</p>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Kpi({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "danger" | "warn" | "ok" }) {
  return (
    <Card className="px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className={cn("mt-1 text-2xl font-semibold tabular-nums", tone === "danger" && "text-danger",
        tone === "warn" && "text-warn", tone === "ok" && "text-ok")}>{value}</div>
    </Card>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-line">
      {tabs.map((tb) => (
        <button key={tb.id} onClick={() => onChange(tb.id)} className={cn(
          "-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors",
          value === tb.id ? "border-primary text-primary" : "border-transparent text-muted hover:text-ink")}>
          {tb.label}
        </button>
      ))}
    </div>
  );
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 pt-[8vh]" onClick={onClose}>
      <Card className="w-full max-w-2xl p-6" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <h2 className="mb-4 text-lg font-semibold">{title}</h2>
        {children}
      </Card>
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{error instanceof Error ? error.message : String(error)}</div>;
}
