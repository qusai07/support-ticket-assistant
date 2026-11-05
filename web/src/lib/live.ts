"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getAccessToken, refreshSession } from "./api";

/** Subscribes to /events (Server-Sent Events) and invalidates ticket queries when the
 *  worker finishes processing or someone reviews a ticket. Uses fetch streaming instead
 *  of EventSource because EventSource can't send an Authorization header. Reconnects
 *  with backoff; React Query's interval polling remains as a safety net. */
export function useLiveTickets(enabled: boolean) {
  const qc = useQueryClient();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let stop = false;
    let ctrl: AbortController | null = null;
    let backoff = 1000;

    async function run() {
      while (!stop) {
        ctrl = new AbortController();
        try {
          const r = await fetch("/api/v1/events", {
            headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` }, signal: ctrl.signal,
          });
          if (r.status === 401) { await refreshSession(); throw new Error("auth"); }
          if (!r.ok || !r.body) throw new Error(String(r.status));
          setConnected(true);
          backoff = 1000;
          const reader = r.body.pipeThrough(new TextDecoderStream()).getReader();
          let buf = "";
          while (!stop) {
            const { value, done } = await reader.read();
            if (done) break;
            buf += value;
            let i;
            while ((i = buf.indexOf("\n\n")) >= 0) {
              const chunk = buf.slice(0, i);
              buf = buf.slice(i + 2);
              if (chunk.includes("event: tickets")) {
                const data = chunk.split("\n").find((l) => l.startsWith("data: "))?.slice(6);
                const changed: { id: string }[] = data ? JSON.parse(data) : [];
                qc.invalidateQueries({ queryKey: ["tickets"] });
                qc.invalidateQueries({ queryKey: ["stats"] });
                qc.invalidateQueries({ queryKey: ["monitor"] });
                changed.forEach((t) => qc.invalidateQueries({ queryKey: ["ticket", t.id] }));
              }
            }
          }
        } catch {
          /* fall through to reconnect */
        }
        setConnected(false);
        if (stop) break;
        await new Promise((res) => setTimeout(res, backoff));
        backoff = Math.min(backoff * 2, 30000);
      }
    }
    run();
    return () => { stop = true; ctrl?.abort(); };
  }, [enabled, qc]);

  return connected;
}
