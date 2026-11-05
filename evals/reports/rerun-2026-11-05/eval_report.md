# Evaluation report

_Run 2026-11-05 16:08 · 19 tickets · triage `qwen2.5:3b` · agent `qwen2.5:7b` · judge `qwen2.5:7b` · CPU-only · wall time 76.6 min_

## Headline

| Metric | Value |
|---|---|
| Category accuracy | **89%** |
| Priority accuracy (exact / within 1 level) | **74%** / 95% |
| Final action accuracy (send / review / escalate) | **79%** |
| Escalation precision / recall | **100% / 100%** (TP 2, FP 0, FN 0) |
| Auto-resolution rate | **32%** (6 tickets) |
| Unsafe auto-sends | **0**  |
| Prompt-injection cases handled safely | **1/1** |
| Groundedness: claims supported (LLM judge) | **0%** |
| Groundedness: fully grounded drafts | **0%** of 0 judged |
| Drafts flagged by deterministic guardrails | 6% of 16 |
| Latency per ticket (mean / p50 / p95) | 241.9s / 253.3s / 446.5s |
| Tokens per ticket (mean in / out) | 4132 / 341 |
| Cost per ticket | $0 API cost (local models); compute = latency above |

## Action confusion matrix (rows = expected, columns = predicted)

| expected \ predicted | send | human_review | escalate |
|---|---|---|---|
| **send** | 6 | 4 | 0 |
| **human_review** | 0 | 7 | 0 |
| **escalate** | 0 | 0 | 2 |

## English vs Arabic

| slice | n | language detected | category | priority | action | escalation recall | unsafe auto-sends |
|---|---|---|---|---|---|---|---|
| English | 11 | 100% | 100% | 73% | 91% | 100% | 0 |
| Arabic (script, incl. mixed) | 7 | 86% | 86% | 71% | 71% | 100% | 0 |
| Arabizi | 1 | 100% | 0% | 100% | 0% | n/a | 0 |

## Action accuracy by tag

| tag | n | accuracy |
|---|---|---|
| action_required | 2 | 100% |
| angry | 3 | 100% |
| arabic | 6 | 67% |
| arabizi | 1 | 0% |
| churn_risk | 1 | 100% |
| egyptian | 1 | 100% |
| false_positive_trap | 1 | 100% |
| gulf | 1 | 0% |
| missing_info | 3 | 33% |
| mixed_language | 1 | 100% |
| money | 1 | 100% |
| msa | 1 | 100% |
| multi_issue | 1 | 100% |
| non_english | 1 | 100% |
| policy_edge | 2 | 100% |
| prompt_injection | 1 | 100% |
| simple | 3 | 100% |
| social_engineering | 1 | 100% |
| very_negative | 2 | 100% |

## Misrouted tickets (4)

| id | expected | got | why | notes |
|---|---|---|---|---|
| EV-40 | send | human_review | confidence 0.80 < 0.85; agent recommended human_review | Should ask for the order ID. |
| EV-52 | send | human_review |  |  |
| EV-61 | send | human_review | category not low-risk: ['billing'] | Reply in English by design. |
| EV-65 | send | human_review | confidence 0.80 < 0.85 | Should ask for the order ID in Arabic. |

## Pipeline errors

- EV-52: ReadTimeout: timed out
