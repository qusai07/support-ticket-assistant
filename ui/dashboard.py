"""Streamlit review dashboard. Talks to the FastAPI backend only (no direct DB access),
so the UI could be swapped for React without touching the backend.

    streamlit run ui/dashboard.py
"""
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
EVAL_FILE = Path(__file__).resolve().parent.parent / "data" / "eval_set.json"

STATUS_LABEL = {"new": "Processing", "triaged": "Processing", "in_review": "In review", "escalated": "Escalated",
                "ready_to_send": "Ready to send", "approved": "Approved", "rejected": "Rejected", "sent": "Sent"}
FILTERS = ["in_review", "escalated", "ready_to_send", "approved", "rejected", "new", "all"]

st.set_page_config(page_title="Lumora Support Desk", page_icon="🎫", layout="wide")

# ------------------------------------------------------------------ styles
# Semi-transparent tints so badges read well on light and dark themes alike.
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1500px;}
h1, h2, h3 {letter-spacing: -0.01em;}

.badge {display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.72rem; font-weight:600;
        line-height:1.6; margin:0 6px 4px 0; white-space:nowrap; border:1px solid transparent;}
.s-in_review     {background:rgba(245,158,11,.14); color:#B45309; border-color:rgba(245,158,11,.35);}
.s-escalated     {background:rgba(239,68,68,.12);  color:#B91C1C; border-color:rgba(239,68,68,.35);}
.s-ready_to_send {background:rgba(16,185,129,.13); color:#047857; border-color:rgba(16,185,129,.35);}
.s-approved, .s-sent {background:rgba(59,130,246,.12); color:#1D4ED8; border-color:rgba(59,130,246,.35);}
.s-rejected      {background:rgba(107,114,128,.13); color:#4B5563; border-color:rgba(107,114,128,.35);}
.s-new, .s-triaged {background:rgba(139,92,246,.13); color:#6D28D9; border-color:rgba(139,92,246,.35);}
.p-P1 {background:#DC2626; color:#fff;} .p-P2 {background:#EA580C; color:#fff;}
.p-P3 {background:rgba(79,70,229,.12); color:#4338CA;} .p-P4 {background:rgba(107,114,128,.13); color:#4B5563;}
.cat  {background:transparent; color:inherit; border-color:rgba(128,128,128,.35); font-weight:500;}
.team {background:rgba(14,165,233,.12); color:#0369A1; border-color:rgba(14,165,233,.35);}
.lang {background:rgba(20,184,166,.12); color:#0F766E; border-color:rgba(20,184,166,.35);}
textarea, .msg, .t-title {unicode-bidi: plaintext;}  /* each paragraph picks LTR/RTL from its own text */
.warn {background:rgba(239,68,68,.12); color:#B91C1C; border-color:rgba(239,68,68,.35);}

.kpi {border:1px solid rgba(128,128,128,.2); border-radius:14px; padding:14px 18px;
      background:var(--secondary-background-color, #fff);}
.kpi .v {font-size:1.7rem; font-weight:700; line-height:1.2;}
.kpi .l {font-size:.78rem; opacity:.65; text-transform:uppercase; letter-spacing:.04em;}

.t-title {font-weight:600; font-size:.95rem; margin:2px 0 4px 0;}
.t-meta  {font-size:.78rem; opacity:.6;}
[class*="st-key-sel-"] {border-left:4px solid #4F46E5 !important; background:rgba(79,70,229,.05);}

.msg {border:1px solid rgba(128,128,128,.2); border-radius:12px; padding:14px 16px; white-space:pre-wrap;
      background:var(--secondary-background-color, #fff); font-size:.92rem;}
.esc {border:1px solid rgba(239,68,68,.35); background:rgba(239,68,68,.06); border-radius:12px;
      padding:14px 16px; margin:10px 0;}
.esc pre {white-space:pre-wrap; margin:6px 0 0 0; font-size:.85rem; background:transparent;}
.bar {height:8px; border-radius:99px; background:rgba(128,128,128,.18); overflow:hidden; margin:4px 0 2px 0;}
.bar > div {height:100%; border-radius:99px;}
.kv {display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid rgba(128,128,128,.12);
     font-size:.88rem;}
.kv span:first-child {opacity:.6;}
.step {border-left:2px solid rgba(79,70,229,.35); padding:2px 0 10px 14px; margin-left:6px;}
.empty {text-align:center; padding:60px 20px; opacity:.55;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def _refresh() -> bool:
    rt = st.session_state.get("refresh_token")
    if not rt:
        return False
    r = httpx.post(f"{API}/auth/refresh", json={"refresh_token": rt}, timeout=10)
    if r.status_code != 200:
        return False
    st.session_state.update(access_token=r.json()["access_token"], refresh_token=r.json()["refresh_token"])
    return True


def api(method: str, path: str, **kw):
    """Authenticated API call; transparently refreshes an expired access token once."""
    try:
        for attempt in (1, 2):
            headers = {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
            r = httpx.request(method, f"{API}{path}", timeout=30, headers=headers, **kw)
            if r.status_code == 401 and attempt == 1 and _refresh():
                continue
            break
        if r.status_code == 401:
            st.session_state.clear()
            st.rerun()
        if r.status_code >= 400:
            st.error(f"{r.status_code}: {r.json().get('detail', r.text) if r.content else ''}")
            return None
        return r.json() if r.content else {}
    except httpx.HTTPError as e:
        st.error(f"Can't reach the API at {API} ({e}). Is `uvicorn app.main:app` running?")
        return None


def can(perm: str) -> bool:
    return perm in st.session_state.get("me", {}).get("permissions", [])


# ------------------------------------------------------------------ login gate
if "access_token" not in st.session_state:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("## 🎫 Lumora Support Desk")
        st.caption("Sign in to continue")
        with st.form("login"):
            email = st.text_input("Email", "agent.tech@lumora.example")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                try:
                    r = httpx.post(f"{API}/auth/login", data={"username": email, "password": password}, timeout=10)
                except httpx.HTTPError as e:
                    st.error(f"Can't reach the API at {API} ({e})")
                    st.stop()
                if r.status_code == 200:
                    st.session_state.update(access_token=r.json()["access_token"],
                                            refresh_token=r.json()["refresh_token"])
                    st.session_state["me"] = api("GET", "/auth/me")
                    st.rerun()
                st.error("Invalid email or password")
        st.caption("Demo accounts (run `python -m scripts.seed_users`): admin@ · lead.tech@ · agent.tech@ · "
                   "agent.refunds@ · analyst@ … all `@lumora.example`")
    st.stop()

ME = st.session_state["me"]


def esc(s) -> str:
    return html.escape(str(s or ""))


def badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{esc(text)}</span>'


def status_badge(s: str) -> str:
    return badge(STATUS_LABEL.get(s, s), f"s-{s}")


def priority_badge(p: str | None) -> str:
    return badge(p, f"p-{p}") if p else ""


LANG_LABEL = {"en": "EN", "ar": "عربي", "mixed": "عربي + EN", "ar_latn": "Arabizi"}


def lang_badge(lang: str | None) -> str:
    return badge(LANG_LABEL.get(lang, lang), "lang") if lang and lang != "en" else ""


def team_badge(team: str | None) -> str:
    return badge("→ " + team, "team") if team else ""


def ago(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        sec = int((datetime.now(timezone.utc) - dt).total_seconds())
    except ValueError:
        return ts
    for unit, n in (("d", 86400), ("h", 3600), ("m", 60)):
        if sec >= n:
            return f"{sec // n}{unit} ago"
    return "just now"


def confidence_bar(c: float) -> str:
    color = "#10B981" if c >= 0.85 else "#F59E0B" if c >= 0.6 else "#EF4444"
    return f'<div class="bar"><div style="width:{c * 100:.0f}%; background:{color}"></div></div>'


def kv(label: str, value: str) -> str:
    return f'<div class="kv"><span>{esc(label)}</span><span>{value}</span></div>'


# ------------------------------------------------------------------ sidebar: submit
with st.sidebar:
    st.markdown("## 🎫 Lumora Support Desk")
    st.markdown(f"**{esc(ME['full_name'])}**<br>{badge(ME['role'], 'cat')}{team_badge(ME.get('team'))}",
                unsafe_allow_html=True)
    if st.button("Sign out", use_container_width=True):
        api("POST", "/auth/logout", json={"refresh_token": st.session_state.get("refresh_token", "")})
        st.session_state.clear()
        st.rerun()
    st.divider()


def new_ticket_form() -> None:
    st.markdown("#### New ticket")
    examples = json.loads(EVAL_FILE.read_text("utf-8")) if EVAL_FILE.exists() else []
    labels = ["Write my own"] + [f"{e['id']} · {e['ticket']['subject']}" for e in examples]
    pick = st.selectbox("Start from an example", labels)
    ex = examples[labels.index(pick) - 1]["ticket"] if pick != labels[0] else {}
    with st.form("submit", border=False):
        email = st.text_input("Customer email", ex.get("customer_email", "omar.khalil@example.com"))
        subject = st.text_input("Subject", ex.get("subject", ""))
        body = st.text_area("Message", ex.get("body", ""), height=140)
        channel = st.selectbox("Channel", ["email", "chat", "web_form", "phone"])
        if st.form_submit_button("Submit ticket", type="primary", use_container_width=True):
            if subject.strip() and body.strip():
                res = api("POST", "/tickets", json={"subject": subject, "body": body,
                                                    "customer_email": email, "channel": channel})
                if res:
                    st.session_state["selected"] = res["ticket_id"]
                    st.session_state["filter"] = "new"
                    st.toast(f"Queued {res['ticket_id']}: the worker will process it shortly")
            else:
                st.warning("Subject and message are required.")


with st.sidebar:
    if can("tickets:create"):
        new_ticket_form()
        st.divider()
    st.caption(f"API: `{API}`")

# ------------------------------------------------------------------ header + KPIs
stats = api("GET", "/tickets/stats") or {}
by_status = stats.get("by_status", {})

h1, h2 = st.columns([6, 1])
h1.markdown("## Ticket queue")
if h2.button("↻ Refresh", use_container_width=True):
    st.rerun()

reviewed = sum(stats.get("reviews", {}).values())
edited = stats.get("reviews", {}).get("edit", 0)
kpis = [
    ("Tickets", stats.get("tickets", 0)),
    ("Needs review", by_status.get("in_review", 0)),
    ("Escalated", by_status.get("escalated", 0)),
    ("Ready to send", by_status.get("ready_to_send", 0)),
    ("Avg latency", f"{stats.get('avg_latency_s', 0)}s"),
    ("Edit rate", f"{100 * edited / reviewed:.0f}%" if reviewed else "–"),
]
for col, (label, value) in zip(st.columns(len(kpis)), kpis):
    col.markdown(f'<div class="kpi"><div class="l">{label}</div><div class="v">{value}</div></div>',
                 unsafe_allow_html=True)
st.write("")

# ------------------------------------------------------------------ layout: queue | detail
q_col, d_col = st.columns([2, 3], gap="large")

with q_col:
    def label(f: str) -> str:
        n = stats.get("tickets", 0) if f == "all" else by_status.get(f, 0)
        return f"{'All' if f == 'all' else STATUS_LABEL[f]} · {n}"

    current = st.session_state.get("filter", "in_review")
    choice = st.pills("Filter", FILTERS, format_func=label, default=current, label_visibility="collapsed")
    st.session_state["filter"] = choice or "all"
    params = {} if st.session_state["filter"] == "all" else {"status": st.session_state["filter"]}
    tickets = api("GET", "/tickets", params=params) or []

    if not tickets:
        st.markdown('<div class="empty">Nothing here yet.<br>Submit a ticket from the sidebar.</div>',
                    unsafe_allow_html=True)
    with st.container(height=640, border=False):
        for t in tickets:
            selected = st.session_state.get("selected") == t["id"]
            with st.container(border=True, key=f"{'sel' if selected else 'card'}-{t['id']}"):
                left, right = st.columns([6, 1], vertical_alignment="center")
                badges = status_badge(t["status"]) + priority_badge(t.get("priority")) + \
                    (badge(t["category"], "cat") if t.get("category") else "") + lang_badge(t.get("language"))
                left.markdown(
                    f'<div>{badges}</div><div class="t-title" dir="auto">{esc(t["subject"])}</div>'
                    f'<div class="t-meta">{esc(t["customer_email"])} · {ago(t["created_at"])} · {t["id"]}'
                    f'{" · → " + esc(t["team"]) if t.get("team") else ""}</div>',
                    unsafe_allow_html=True)
                if right.button("›", key=f"open-{t['id']}", use_container_width=True,
                                type="primary" if selected else "secondary"):
                    st.session_state["selected"] = t["id"]
                    st.rerun()

with d_col:
    sel = st.session_state.get("selected")
    d = api("GET", f"/tickets/{sel}") if sel else None
    if not d:
        st.markdown('<div class="empty">Select a ticket to review it.</div>', unsafe_allow_html=True)
        st.stop()

    t, tri, run = d["ticket"], d["triage"], d["run"]
    agent_out = (run or {}).get("agent_output")

    # ---- header
    head = status_badge(t["status"])
    if tri:
        head += priority_badge(tri["priority"]) + badge(tri["category"], "cat") + lang_badge(tri.get("language"))
    if run and run.get("routing", {}).get("team"):
        head += team_badge(run["routing"]["team"])
    if tri:
        if tri.get("injection_suspected"):
            head += badge("⚠ prompt injection", "warn")
    st.markdown(f"<div>{head}</div>", unsafe_allow_html=True)
    st.markdown(f'<h3 dir="auto">{esc(t["subject"])}</h3>', unsafe_allow_html=True)
    st.caption(f"{t['customer_email']} · via {t['channel']} · {ago(t['created_at'])} · {t['id']}")
    st.markdown(f'<div class="msg" dir="auto">{esc(t["body"])}</div>', unsafe_allow_html=True)

    if t["status"] in ("new", "triaged"):
        st.info("⏳ The pipeline is still working on this ticket. Hit Refresh in a moment.")

    for e in d["escalations"]:
        st.markdown(f'<div class="esc"><b>🚨 Escalated by {esc(e["source"]).replace("_", " ")}</b> · '
                    f'{esc(e["reason"])}<pre>{esc(e["summary"])}</pre></div>', unsafe_allow_html=True)

    tab_reply, tab_triage, tab_trace, tab_ctx = st.tabs(["✉️ Reply", "🧭 Triage & routing", "🛠 Tool trace", "📚 Context"])

    # ---- reply
    with tab_reply:
        if agent_out:
            c = agent_out["confidence"]
            m1, m2, m3 = st.columns(3)
            m1.markdown(f"**Confidence {c:.2f}**{confidence_bar(c)}"
                        f"<span class='t-meta'>model said {run.get('raw_confidence')}</span>", unsafe_allow_html=True)
            m2.markdown(f"**Recommends**<br>{badge(agent_out['recommended_action'].replace('_', ' '), 'cat')}",
                        unsafe_allow_html=True)
            m3.markdown("**Sources**<br>" + ("".join(badge(s, "cat") for s in agent_out["sources"]) or
                                             "<span class='t-meta'>none cited</span>"), unsafe_allow_html=True)
            if run.get("status_reasons") and t["status"] == "in_review":
                st.caption("Why it needs review: " + " · ".join(run["status_reasons"]))
            if run.get("guardrail_flags"):
                st.warning("Guardrails flagged: " + ", ".join(run["guardrail_flags"]))
        elif run and t["status"] == "escalated":
            st.caption("Escalated before the agent ran. Write the reply yourself, or approve once handled.")

        original = (agent_out or {}).get("draft_reply", "")
        draft = st.text_area("Reply to customer", original, height=300, key=f"draft-{sel}",
                             label_visibility="collapsed", placeholder="Write a reply…")

        may_review = can("tickets:review") and (t["status"] != "escalated" or can("tickets:handle_escalated"))
        if t["status"] in ("in_review", "ready_to_send", "escalated") and not may_review:
            st.caption("🔒 Your role can view this ticket but not act on it.")
        if t["status"] in ("in_review", "ready_to_send", "escalated") and may_review:
            comment = st.text_input("Note for the log (optional)", key=f"c-{sel}", placeholder="Reviewer note…")
            changed = draft.strip() != original.strip()
            b1, b2, b3 = st.columns([2, 1, 1])
            decision = None
            if changed:
                if b1.button("✏️ Save edit & approve", type="primary", use_container_width=True,
                             disabled=not draft.strip()):
                    decision = {"decision": "edit", "edited_reply": draft}
            elif b1.button("✅ Approve & send", type="primary", use_container_width=True, disabled=not original):
                decision = {"decision": "approve"}
            if b2.button("Reject", use_container_width=True):
                decision = {"decision": "reject"}
            if b3.button("Escalate", use_container_width=True, disabled=t["status"] == "escalated"):
                decision = {"decision": "escalate"}
            if decision and api("POST", f"/tickets/{sel}/review", json={**decision, "comment": comment or None}):
                st.toast(f"Saved: {decision['decision']}")
                st.rerun()

        for rv in d["reviews"]:
            st.success(f"**{rv['decision'].title()}** by {rv['reviewer']} · {ago(rv['created_at'])}"
                       + (f" · {rv['comment']}" if rv["comment"] else ""))
            if rv["decision"] == "edit":
                with st.expander("Show original draft vs. sent reply"):
                    a, b = st.columns(2)
                    a.caption("Agent draft")
                    a.markdown(f'<div class="msg" dir="auto">{esc(rv["original_reply"])}</div>', unsafe_allow_html=True)
                    b.caption("Sent")
                    b.markdown(f'<div class="msg" dir="auto">{esc(rv["final_reply"])}</div>', unsafe_allow_html=True)

    # ---- triage
    with tab_triage:
        if not tri:
            st.caption("No triage yet.")
        else:
            a, b = st.columns(2)
            a.markdown(
                kv("Language", esc(LANG_LABEL.get(tri.get("language", "en"), "EN"))) +
                kv("Team", team_badge((run or {}).get("routing", {}).get("team")) or "–") +
                kv("Category", badge(tri["category"], "cat") +
                   "".join(badge(c, "cat") for c in tri.get("secondary_categories", []))) +
                kv("Priority", priority_badge(tri["priority"])) +
                kv("Sentiment", f"{esc(tri['sentiment']).replace('_', ' ')} ({tri['sentiment_score']:+.1f})") +
                kv("Prompt injection", "⚠ suspected" if tri["injection_suspected"] else "no"),
                unsafe_allow_html=True)
            ent = tri["entities"]
            b.markdown(
                kv("Signals", "".join(badge(s, "warn" if s in ("legal", "chargeback", "safety", "fraud") else "cat")
                                      for s in tri["urgency_signals"]) or "–") +
                kv("Order IDs", esc(", ".join(ent["order_ids"])) or "–") +
                kv("Amounts", esc(", ".join(f"${x:g}" for x in ent["amounts"])) or "–") +
                kv("Missing info", esc(", ".join(tri["missing_info"])) or "–"),
                unsafe_allow_html=True)
            if tri.get("rationale"):
                st.caption(f"Model rationale: {tri['rationale']}")

        hits = (run or {}).get("routing", {}).get("hits", [])
        st.markdown("##### Routing rules")
        if hits:
            for h in hits:
                st.markdown(f"🚨 `{h['rule']}`: {esc(h['detail'])}")
        elif run:
            st.markdown("✅ No escalation rule fired, so the ticket went to the agent.")

    # ---- tool trace
    with tab_trace:
        calls = d["tool_calls"]
        if not calls:
            st.caption("No tool calls (the ticket was escalated before the agent ran).")
        for tc in calls:
            who = "⚙️ pipeline prefetch" if tc["step"] == "prefetch" else "🤖 agent"
            args = ", ".join(f"{k}={v}" for k, v in tc["args"].items())
            err = tc["error"] or (tc["result"].get("error") if isinstance(tc["result"], dict) else None)
            st.markdown(f'<div class="step"><span class="t-meta">{who} · {tc["latency_ms"]} ms</span><br>'
                        f'<code>{esc(tc["tool"])}({esc(args)})</code> {badge("error: " + str(err), "warn") if err else ""}'
                        f'</div>', unsafe_allow_html=True)
            with st.expander("result", expanded=False):
                st.json(tc["error"] or tc["result"], expanded=1)
        if d["llm_calls"]:
            st.markdown("##### LLM calls")
            df = pd.DataFrame(d["llm_calls"])[["purpose", "model", "input_tokens", "output_tokens", "latency_ms"]]
            st.dataframe(df, hide_index=True, use_container_width=True)

    # ---- context
    with tab_ctx:
        docs = (run or {}).get("retrieved", [])
        if not docs:
            st.caption("No retrieved context.")
        cited = set((agent_out or {}).get("sources", []))
        for doc in docs:
            kind = "Help article" if doc["source_type"] == "kb" else "Past ticket"
            mark = " ✅ cited" if doc["source_id"] in cited else ""
            with st.expander(f"{doc['source_id']} · {doc['title']}  ({kind}, score {doc['score']:.2f}){mark}"):
                st.write(doc["snippet"])
