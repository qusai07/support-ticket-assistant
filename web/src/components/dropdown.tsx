"use client";

/** Accessible custom select: styled like the rest of the app (the native <select> popup is
 *  drawn by the OS and ignores theme, fonts and RTL). Keyboard: ↑ ↓ Home End Enter Esc,
 *  type to search. Logical CSS only, so it mirrors in Arabic. */
import { Check, ChevronDown, Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useI18n } from "@/lib/i18n";
import { cn } from "./ui";

export type Option = { value: string; label: string; hint?: string; group?: string; icon?: React.ReactNode; badge?: React.ReactNode };

export function Dropdown({ options, value, onChange, placeholder, searchable, disabled, className, size = "md", ariaLabel }: {
  options: Option[]; value: string | null; onChange: (v: string) => void; placeholder?: string; searchable?: boolean;
  disabled?: boolean; className?: string; size?: "sm" | "md"; ariaLabel?: string;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const id = useId();
  const selected = options.find((o) => o.value === value);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return needle ? options.filter((o) => `${o.label} ${o.hint ?? ""} ${o.group ?? ""}`.toLowerCase().includes(needle)) : options;
  }, [options, q]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(Math.max(0, options.findIndex((o) => o.value === value)));
    }
  }, [open, options, value]);

  useEffect(() => { list.current?.querySelector(`[data-i="${active}"]`)?.scrollIntoView({ block: "nearest" }); }, [active, open]);

  function choose(o: Option) { onChange(o.value); setOpen(false); }

  function onKey(e: React.KeyboardEvent) {
    if (!open && ["ArrowDown", "Enter", " "].includes(e.key)) { e.preventDefault(); setOpen(true); return; }
    if (!open) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(filtered.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(filtered.length - 1); }
    else if (e.key === "Enter") { e.preventDefault(); if (filtered[active]) choose(filtered[active]); }
    else if (e.key === "Escape") { e.preventDefault(); setOpen(false); }
  }

  let lastGroup: string | undefined;
  return (
    <div ref={root} className={cn("relative", className)} onKeyDown={onKey}>
      <button type="button" disabled={disabled} aria-haspopup="listbox" aria-expanded={open} aria-controls={id} aria-label={ariaLabel}
        onClick={() => setOpen((o) => !o)}
        className={cn("flex w-full items-center gap-2 rounded-lg border bg-surface px-3 text-start text-ink transition-colors disabled:cursor-not-allowed disabled:opacity-60",
          size === "sm" ? "h-8 text-xs" : "h-10 text-sm", open ? "border-primary ring-2 ring-primary/20" : "border-line hover:border-muted/50")}>
        {selected?.icon}
        <span className={cn("min-w-0 flex-1 truncate", !selected && "text-muted")}>{selected?.label ?? placeholder ?? "—"}</span>
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute inset-x-0 top-full z-50 mt-1.5 overflow-hidden rounded-xl border border-line bg-surface shadow-xl">
          {searchable && (
            <div className="relative border-b border-line p-2">
              <Search className="pointer-events-none absolute start-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input autoFocus value={q} onChange={(e) => { setQ(e.target.value); setActive(0); }} placeholder={t("common.search")}
                className="h-9 w-full rounded-lg bg-sunken pe-3 ps-8 text-sm outline-none placeholder:text-muted" />
            </div>
          )}
          <ul ref={list} id={id} role="listbox" className="max-h-72 overflow-y-auto p-1">
            {filtered.length === 0 && <li className="px-3 py-6 text-center text-sm text-muted">{t("common.none")}</li>}
            {filtered.map((o, i) => {
              const header = o.group && o.group !== lastGroup ? o.group : null;
              lastGroup = o.group;
              return (
                <li key={o.value}>
                  {header && <div className="px-3 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wider text-muted">{header}</div>}
                  <div role="option" aria-selected={o.value === value} data-i={i}
                    onMouseEnter={() => setActive(i)} onMouseDown={(e) => { e.preventDefault(); choose(o); }}
                    className={cn("flex cursor-pointer items-start gap-2.5 rounded-lg px-3 py-2 text-sm",
                      i === active ? "bg-primary-soft text-ink" : "text-ink")}>
                    {o.icon && <span className="mt-0.5 shrink-0 text-muted">{o.icon}</span>}
                    <span className="min-w-0 flex-1">
                      <span className="bidi block truncate font-medium">{o.label}</span>
                      {o.hint && <span className="bidi mt-0.5 block truncate text-xs text-muted">{o.hint}</span>}
                    </span>
                    {o.badge}
                    {o.value === value && <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Segmented choice (2-5 options): faster than a dropdown, every option visible. */
export function Segmented<T extends string>({ options, value, onChange }: {
  options: { value: T; label: string; icon?: React.ReactNode }[]; value: T; onChange: (v: T) => void;
}) {
  return (
    <div className="grid gap-1 rounded-xl bg-sunken p-1" style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }} role="radiogroup">
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={cn("flex items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-xs font-medium transition-colors sm:text-sm",
            value === o.value ? "bg-surface text-primary shadow-card" : "text-muted hover:text-ink")}>
          {o.icon}{o.label}
        </button>
      ))}
    </div>
  );
}
