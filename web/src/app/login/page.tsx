"use client";

import { Languages, Moon, Sun } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Card, ErrorNote, Field, Input } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { useTheme } from "@/lib/theme";

const DEMO = ["agent.tech", "lead.tech", "agent.refunds", "lead.safety", "analyst", "admin"];

export default function LoginPage() {
  const { login, me, ready } = useAuth();
  const { t, lang, setLang } = useI18n();
  const { theme, toggle } = useTheme();
  const router = useRouter();
  const [email, setEmail] = useState("agent.tech@lumora.example");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (ready && me) router.replace("/inbox"); }, [ready, me, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/inbox");
    } catch (err) {
      setError(err instanceof Error && err.message === "too_many_attempts" ? t("auth.tooMany") : t("auth.invalid"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex justify-end gap-1 p-4">
        <Button variant="ghost" size="sm" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
          <Languages className="h-4 w-4" />{lang === "ar" ? "English" : "العربية"}
        </Button>
        <Button variant="ghost" size="sm" onClick={toggle} aria-label={t("common.theme")}>
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
      <div className="flex flex-1 items-center justify-center px-4 pb-16">
        <div className="w-full max-w-sm">
          <div className="mb-6 flex flex-col items-center gap-3 text-center">
            <div className="grid h-12 w-12 place-items-center rounded-xl bg-primary text-xl font-bold text-primary-fg">L</div>
            <div>
              <h1 className="text-xl font-semibold">{t("appName")}</h1>
              <p className="mt-1 text-sm text-muted">{t("auth.title")}</p>
            </div>
          </div>
          <Card className="p-6">
            <form onSubmit={submit} className="space-y-4">
              <Field label={t("auth.email")}>
                <Input type="email" dir="ltr" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </Field>
              <Field label={t("auth.password")}>
                <Input type="password" dir="ltr" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </Field>
              <ErrorNote error={error} />
              <Button type="submit" variant="primary" className="w-full" loading={busy}>{t("auth.signIn")}</Button>
            </form>
          </Card>
          <div className="mt-6 rounded-xl border border-dashed border-line p-4 text-xs text-muted">
            <div className="mb-2 font-medium text-ink">{t("auth.demo")}</div>
            <div className="flex flex-wrap gap-1.5">
              {DEMO.map((d) => (
                <button key={d} type="button" onClick={() => setEmail(`${d}@lumora.example`)}
                  className="rounded-md border border-line bg-surface px-2 py-1 hover:border-primary hover:text-primary" dir="ltr">{d}</button>
              ))}
            </div>
            <div className="mt-3">{t("auth.demoHint")} <code dir="ltr" className="rounded bg-sunken px-1.5 py-0.5 text-ink">Lumora-demo-2026</code></div>
          </div>
        </div>
      </div>
    </div>
  );
}
