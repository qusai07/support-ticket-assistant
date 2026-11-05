import { NextRequest } from "next/server";
import { API_URL } from "../../auth/_shared";

// Dedicated SSE passthrough. The generic /api/v1/* rewrite buffers (and may compress)
// responses, which breaks streaming. A route handler takes precedence over rewrites and
// pipes FastAPI's stream through untouched. `no-transform` tells the compression layer
// to leave it alone.
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(req: NextRequest) {
  const upstream = await fetch(`${API_URL}/events`, {
    headers: { Authorization: req.headers.get("authorization") ?? "" },
    signal: req.signal, // client disconnect closes the upstream connection too
    cache: "no-store",
  }).catch(() => null);
  if (!upstream) return new Response("API unreachable", { status: 502 });
  if (!upstream.ok || !upstream.body) return new Response(await upstream.text(), { status: upstream.status });
  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
