# Lumora Support Desk: AI ticket resolution with humans in control

A bilingual (Arabic / English) support desk where an **AI pipeline triages every ticket, retrieves policy, and drafts a grounded reply**, while **hard-coded rules decide what must reach a human** and **reviewers approve, edit or escalate** before anything is sent. It runs fully **locally** (Ollama, CPU-only) and ships as a real multi-user product: login, role-based permissions, team queues, SLAs, live monitoring and an audit log.

> Portfolio project. The store ("Lumora"), customers, orders and policies are synthetic, and integrations (CRM, order system, email) are mocked. The architecture, AI pipeline, security model and evaluation are real.

![Inbox with a safety escalation](docs/screenshots/02-inbox-escalation.png)

---

## Why this problem

Support teams spend most of their time on repetitive tickets ("where is my order?", "how do I return this?") while the few that really matter (legal threats, chargebacks, safety hazards, furious VIPs) wait in the same queue. A useful assistant must:

1. **Never** auto-answer a ticket that needs a human.
2. **Never** state a policy, amount, date or promise that isn't backed by data.
3. Save real time on everything else, and **prove it with measurements**.
4. Work as well in **Arabic** (including dialects and Arabizi) as in English, which many tools handle poorly.

## What it does

| | |
|---|---|
| **Triage** | Category, priority, sentiment, language (`en` / `ar` / mixed / Arabizi), entities, missing info, prompt-injection detection: LLM + deterministic rules |
| **Retrieval** | Bilingual knowledge base + resolved past tickets (multilingual embeddings, cross-lingual search) |
| **Routing** | Pure-Python rules escalate P1, legal, chargeback, safety, fraud, large refunds, very angry customers and VIPs, and pick the owning **team** |
| **Agent** | Tool-using LLM drafts a reply with cited sources, in the customer's language |
| **Guardrails** | Every KB ID, order ID, amount, number and URL in a draft must trace to evidence |
| **Human review** | Approve / edit / reject / escalate; edits are stored as feedback |
| **Product** | Login, 4 roles × 11 editable permissions, teams, routing rules, SLAs, workflow timeline, monitoring, analytics, audit log: all in Arabic and English with full RTL |

## Screenshots

| | |
|---|---|
| ![Monitor](docs/screenshots/04-monitor.png) **Monitor**: ticket flow, SLA health, pipeline health | ![Arabic RTL workflow](docs/screenshots/07-workflow-ar-dark.png) **Arabic, dark mode**: per-ticket workflow timeline |
| ![Review gate](docs/screenshots/03-review-gate.png) **Review gate**: why a draft wasn't auto-sent | ![Agent view](docs/screenshots/09-agent-view.png) **Agent view**: only their team, grounded draft with sources |
| ![Roles](docs/screenshots/08-roles-ar-dark.png) **Roles & permissions** (Arabic): editable matrix | ![Routing rules](docs/screenshots/05-routing-rules.png) **Routing rules**: which team owns what |
| ![Monitor in Arabic](docs/screenshots/10-monitor-ar.png) **Monitor (Arabic)**: charts mirror for RTL | ![Login](docs/screenshots/01-login-ar-dark.png) **Login** (Arabic, dark) |

---

## Architecture

```mermaid
flowchart LR
    subgraph Browser
      UI[Next.js app<br/>AR/EN · RTL · dark mode]
    end
    subgraph Web["Next.js server (BFF)"]
      BFF[/api/auth/*<br/>httpOnly refresh cookie/]
      PX[/api/v1/* proxy<br/>+ SSE passthrough/]
    end
    subgraph API["FastAPI"]
      AUTH[Auth · RBAC · audit]
      TK[Tickets · KB · admin · settings]
      MON[Timeline · SLA · monitor · SSE events]
    end
    DB[(SQLite / Postgres<br/>tickets · runs · tool calls · LLM calls<br/>reviews · users · audit · jobs)]
    W[Worker<br/>claims jobs]
    subgraph Pipeline["LangGraph pipeline"]
      T[Triage<br/>LLM ∪ regex] --> R[Retrieve<br/>bge-m3 · Chroma]
      R --> RT{Rules<br/>Python}
      RT -- escalate --> E[Escalation<br/>+ team]
      RT -- clear --> AG[Prefetch → Agent<br/>tools → JSON]
      AG --> G[Guardrails] --> H{HITL gate}
    end
    OL[(Ollama<br/>qwen2.5 · bge-m3)]
    UI --> BFF & PX
    BFF & PX --> API
    API --> DB
    TK -- "ticket + job<br/>(one transaction)" --> DB
    W --> DB
    W --> Pipeline
    Pipeline --> OL
```

**Request path:** a ticket and its job are written in **one transaction** (outbox pattern), a separate **worker** claims the job with an atomic conditional `UPDATE`, runs the LangGraph pipeline, and persists every step. The UI updates live via **Server-Sent Events**.

---

## Key design decisions

### AI pipeline

| Decision | Why |
|---|---|
| **Routing is pure Python, not the LLM** | Escalation is the highest-stakes decision. Rules are auditable, unit-tested, and can't be prompt-injected. |
| **Triage = LLM ∪ regex** | The LLM handles language; regex handles exact high-stakes signals (`lawyer`, `chargeback`, `smoking`, Arabic `محامي`, `دخان`…). The union means a small model missing a word can't hide a legal threat. |
| **"Don't let the LLM decide what's deterministic"** | If triage found `ORD-10001` on a refund ticket, the pipeline itself calls `get_order` + `check_refund_eligibility` (*prefetch*). Small models skip "always call X" instructions. |
| **The refund policy is code** | `check_refund_eligibility` computes the 30-day window, final-sale and fees. The LLM only phrases the result. |
| **Tools are scoped to the ticket's customer** | The LLM picks *which* tool, never *whose* data: another customer's order returns `access_denied`. |
| **Deterministic groundedness guardrails** | KB IDs, order IDs, dollar amounts, **all numbers** (days, hours) and URLs in a draft must appear in the evidence. Caught invented return-label URLs and "5-7 business days" (policy says 3-7). |
| **Model confidence is an input, not the answer** | Final confidence = min(model confidence, caps for guardrail flags, tool failures, missing sources). |
| **Some situations always need a person** | A lost package or an order ≥ 5 business days late needs a reship / carrier trace, so the draft goes to review however confident the model is. *Found by the eval (two unsafe auto-sends).* |
| **Fail to human, retry transient errors** | An LLM timeout is retried by the queue (up to 3 attempts); any other failure sends the ticket to review with the error. A ticket is never lost and never auto-answered by a broken run. |

### Arabic & bilingual

| Decision | Why |
|---|---|
| **Normalize Arabic before matching** | `أ/إ/آ→ا`, `ة→ه`, `ى→ي`, strip diacritics and tatweel, Arabic-Indic digits → Latin. Substring matching (not `\b`) because Arabic attaches prefixes: `والمحامي` must match `محامي`. |
| **False-positive tests for Arabic signals** | `عذاب` ("torment") contains `ذاب` ("melted"), and "this isn't what I ordered" isn't fraud. Signals that force P1 are tested against both. |
| **Multilingual embeddings (bge-m3)** | Arabic retrieval recall@3 went from **2/8 → 8/8** vs. English-only MiniLM, with no loss on English (see below). |
| **One KB, two languages, one ID** | `KB-006` is indexed as `KB-006#en` and `KB-006#ar`; results are de-duplicated by ID and returned in the customer's language, so citations and guardrails work identically. |
| **Arabizi → English reply** | Arabizi writers read English comfortably and small models write poor Arabizi. A deliberate, documented choice. |

### Product & security

| Decision | Why |
|---|---|
| **Permissions enforced in the backend** | Every endpoint declares a permission; queries are scoped by team in SQL. The UI only hides what the API already forbids. |
| **Editable roles, locked admin** | Admins edit each role's permissions from the UI (applied within seconds, no restart). The admin role always keeps every permission, so no configuration can lock everyone out. |
| **Refresh token only in an httpOnly cookie** (BFF) | Page JavaScript (and any XSS) can never read it. Access tokens live in memory only. |
| **Refresh-token rotation + reuse detection** | Each refresh token works once; reusing an old one revokes all of that user's sessions, with a 30 s grace window so two open tabs refreshing together don't look like theft. |
| **Brute-force protection** | 5 failures per account+IP, 10 per account, 30 per IP per 15 min, counted from the audit log. `X-Forwarded-For` is only trusted from the Next.js proxy, so it can't be spoofed to dodge the limit. |
| **404, not 403, for other teams' tickets** | Doesn't reveal which ticket IDs exist. |
| **DB-backed job queue (no Redis)** | Outbox pattern + compare-and-set claiming + stale-lock recovery. One less service; works on SQLite and Postgres. |
| **SLA is deterministic** | Targets per priority (admin-editable), "at risk" at 75 % of the target, computed in code and shown as live countdowns. |

---

## Bilingual retrieval: measured

`python -m scripts.build_index` checks recall@3 on held-out queries:

| Query set | MiniLM (English-only) | **bge-m3** (multilingual) |
|---|---|---|
| English | 6/6 | **6/6** |
| Arabic (MSA + Gulf, Levantine, Egyptian) | 2/8 | **8/8** |
| Arabizi / mixed | 1/4 | 2/4 |

## Evaluation

`python -m evals.run_eval` runs a **66-ticket labeled set** (50 English + 16 Arabic/Arabizi) covering angry customers, missing info, multi-issue tickets, policy edge cases (day-30 returns, final sale, expired warranty), prompt injection in both languages, and false-positive traps. It reports:

- triage accuracy (category, priority), **language-detection accuracy**
- escalation precision / recall and an action confusion matrix
- **unsafe auto-sends**: drafts marked "ready to send" that should have gone to a human, the metric that matters most
- prompt-injection handling
- groundedness three ways: deterministic guardrails, claim-level LLM-as-judge, and a human spot-check sheet (the judge needs auditing too)
- **English vs Arabic** breakdown, latency and tokens per ticket

<!-- EVAL_RESULTS -->
*Full-run results are added after the overnight run.*

**What the evaluation has already caught** (from a partial run, 20/66 tickets): two **unsafe auto-sends**, a 6-business-day-late order and a lost package marked "ready to send" when both need human action. That led to the deterministic "human action required" check in the review gate, now covered by regression tests.

---

## Running it

**Requirements:** Python 3.11, Node 20+, [Ollama](https://ollama.com) with models pulled:

```bash
ollama pull qwen2.5:3b && ollama pull qwen2.5:7b && ollama pull bge-m3
```

### Windows, one command

```powershell
py -3.11 -m venv .venv; .venv\Scripts\pip install -e ".[dev]"   # first time only
.\run.ps1          # API + AI worker + web app (production build) → http://localhost:3000
.\run.ps1 -Dev     # same, with hot reload for development
```

`run.ps1` applies database migrations, creates demo accounts, builds the search index on first run, and opens the browser.

### Docker

```bash
cp .env.example .env      # set JWT_SECRET for anything shared
docker compose up --build # postgres · migrate · api · worker · web → http://localhost:3000
```

Ollama runs on the host by default; `docker compose --profile with-ollama up` runs it in a container instead.
Ports are configurable (`API_PORT`, `WEB_PORT`), e.g. to run next to a local dev copy.

*Verified:* the stack builds and starts from scratch, runs all Alembic migrations on PostgreSQL, passes the same end-to-end checks as the local setup (35/35), and the containerized worker processes tickets through Ollama on the host, both an AI-drafted reply and an Arabic safety escalation.

### Demo accounts

Password for all: `Lumora-demo-2026` (dev only)

| Account | Role | Sees |
|---|---|---|
| `admin@lumora.example` | Admin | Everything, including users, roles, teams, routing rules, settings, audit log |
| `lead.tech@lumora.example` | Team lead | All queues, escalations, reassignment, monitor, KB editing |
| `agent.tech@lumora.example` | Agent | Only Technical Support tickets; can't act on escalations |
| `analyst@lumora.example` | Analyst | Read-only tickets, analytics and monitor |

A step-by-step manual test plan (30 scenarios) is in [docs/test-scenarios-ar.md](docs/test-scenarios-ar.md).

**Performance note:** developed on a CPU-only laptop. Rule-escalated tickets finish in ~10-20 s; tickets the agent drafts take ~1-5 min (Arabic is slower: ~2-3× the tokens). On a GPU, or with a cloud model, drafts take seconds.

---

## Testing

```bash
pytest            # 59 deterministic tests, no LLM needed
```

Covered: routing rules, triage signals (EN + AR + Arabizi, including false-positive traps), refund policy edges, tool access control, groundedness guardrails, the review gate, auth (rotation, reuse detection, brute-force limits, spoofed headers), RBAC and team scoping, editable roles, teams and routing rules, the job queue (exclusive claims, stale-lock recovery, transient retries, fail-to-human), SLA states, timeline and monitoring.

The web app is type-checked and linted on every build; an end-to-end script exercises login through the BFF, the httpOnly cookie, permissions through the proxy, live SSE updates and logout.

## Tech stack

**Backend:** Python 3.11 · FastAPI · LangGraph · SQLModel · Alembic · PyJWT · Argon2 · SQLite / PostgreSQL
**AI:** Ollama (qwen2.5 3B/7B) · bge-m3 embeddings · Chroma · structured outputs (JSON schema)
**Frontend:** Next.js 15 · React 19 · TypeScript · Tailwind CSS · TanStack Query · Recharts
**Ops:** Docker Compose · DB-backed job queue · Server-Sent Events

## Repository structure

```
app/
  api/          tickets, KB, admin (roles, teams), settings, analytics, monitor, SSE events
  agent/        agent loop + guardrails (agent.py), customer-scoped tools (tools.py)
  auth/         JWT + refresh rotation, RBAC permissions, rate limiting, audit
  jobs/         DB-backed queue;  worker.py runs the pipeline
  llm/          Ollama client (structured output, retries, usage tracking) + prompts/*.md
  models/       enums, Pydantic schemas, SQLModel tables
  pipeline/     triage (+ Arabic rules), retrieval, routing, HITL gate, LangGraph graph
  rag/          Chroma store: bilingual KB + past tickets
  services/     mock CRM / orders / refund-policy engine
  sla.py        SLA computation;  runtime_settings.py  admin-editable settings
web/            Next.js app (BFF auth routes, i18n AR/EN, pages, components)
data/           seeded generator, bilingual KB, 66-ticket labeled eval set
evals/          run_eval, metrics, LLM judge, reports/
migrations/     Alembic migrations
tests/          59 deterministic tests
docs/           screenshots, manual test scenarios
```

## What I'd improve next (v2 roadmap)

1. **Conversation threads**: tickets as message threads, with the agent using the full history.
2. **Learning from reviewer edits**: turn edited drafts into few-shot examples per category, and measure the edit rate dropping.
3. **Real channels**: inbound email (IMAP) and sending approved replies (SMTP); API keys for web-form intake.
4. **Optional cloud model**: a switchable provider (e.g. Claude) for teams that want seconds instead of minutes, keeping local as the private default.
5. **Arabizi retrieval**: transliterate Arabizi to Arabic script before embedding (recall is 2/4 today).
6. **Ops**: CI (tests + a small eval on every PR), structured logging with PII masking, Postgres `LISTEN/NOTIFY` instead of polling for live events.
7. **Evaluation**: a larger, human-labeled Arabic set across more dialects; track model upgrades as a comparison table.

## Limitations

- Synthetic data and mocked integrations; nothing is actually emailed.
- CPU-only local models are slow, and the 3B model's Arabic writing is weak (7B is noticeably better).
- The LLM judge uses the same model family as the generator, so its groundedness scores are spot-checked by hand.
