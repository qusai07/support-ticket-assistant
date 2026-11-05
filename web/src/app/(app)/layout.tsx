"use client";

import { useRouter } from "next/navigation";
import { Suspense, useEffect } from "react";
import { AppShell } from "@/components/shell";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

/** Client-side guard for all app pages. This is UX only: the real enforcement is the
 *  backend, which rejects every request without a valid token and permission. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { me, ready } = useAuth();
  const router = useRouter();
  useEffect(() => { if (ready && !me) router.replace("/login"); }, [ready, me, router]);
  if (!ready || !me) return <div className="grid h-screen place-items-center"><Spinner className="h-8 w-8" /></div>;
  return <Suspense><AppShell>{children}</AppShell></Suspense>;
}
