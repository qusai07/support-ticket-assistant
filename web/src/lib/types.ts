export type Status = "new" | "triaged" | "in_review" | "escalated" | "ready_to_send" | "approved" | "rejected" | "sent";
export type Role = "admin" | "lead" | "agent" | "analyst";

export interface Me {
  id: number; email: string; full_name: string; role: Role; team: string | null;
  preferred_language: "en" | "ar"; is_active: boolean; permissions: string[]; last_login_at: string | null;
}

export interface TicketRow {
  id: string; subject: string; body: string; customer_email: string; channel: string; created_at: string;
  updated_at: string; status: Status; team: string | null; priority: string | null; language: string | null;
  assignee_id: number | null; assignee_name: string | null; category: string | null; sentiment: string | null;
  sla?: Sla;
}

export interface Sla { target_hours: number; due_at: string; elapsed_s: number; fraction: number;
  state: "on_track" | "at_risk" | "breached" | "met" | "missed" }

export interface TimelineEvent { kind: string; at: string; actor: string;
  actor_type: "ai" | "rules" | "human" | "system" | "customer"; detail: Record<string, unknown>; duration_ms: number | null }

export interface Timeline { ticket_id: string; status: Status; events: TimelineEvent[]; sla: Sla; resolved_at: string | null }

export interface Triage {
  language: string; category: string; secondary_categories: string[]; priority: string; sentiment: string;
  sentiment_score: number; urgency_signals: string[];
  entities: { order_ids: string[]; products: string[]; dates: string[]; amounts: number[] };
  missing_info: string[]; injection_suspected: boolean; rationale: string;
}

export interface AgentOutput {
  draft_reply: string; clarifying_question: string | null; actions_taken: string[]; sources: string[];
  confidence: number; recommended_action: "send" | "human_review" | "escalate";
}

export interface Run {
  retrieved: { source_id: string; source_type: "kb" | "past_ticket"; lang: string; title: string; snippet: string; score: number }[];
  routing: { escalate?: boolean; hits?: { rule: string; detail: string }[]; team?: string };
  agent_output: AgentOutput | null; status_reasons: string[]; guardrail_flags: string[];
  raw_confidence: number | null; timings_ms: Record<string, number>; final_status: Status; total_latency_ms: number;
}

export interface ToolCallRow { seq: number; step: "prefetch" | "agent"; tool: string; args: Record<string, unknown>;
  result: unknown; error: string | null; latency_ms: number }

export interface TicketDetail {
  ticket: TicketRow; assignee: { id: number; full_name: string } | null; triage: Triage | null; run: Run | null;
  tool_calls: ToolCallRow[];
  llm_calls: { purpose: string; model: string; input_tokens: number; output_tokens: number; latency_ms: number }[];
  escalations: { reason: string; summary: string; source: string; created_at: string }[];
  reviews: { decision: string; original_reply: string; final_reply: string | null; reviewer: string;
    comment: string | null; created_at: string }[];
}

export interface Stats {
  tickets: number; by_status: Record<string, number>; by_team: Record<string, number>;
  by_language: Record<string, number>; avg_latency_s: number; avg_tokens_per_ticket: number;
  reviews: Record<string, number>; queue: Record<string, number>;
}

export interface KbArticle { id: string; category: string; title: string; body: string; title_ar: string;
  body_ar: string; policy_tags: string[]; updated_at: string }

export interface UserRow extends Me { created_at?: string }
