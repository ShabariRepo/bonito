/**
 * Studio types — mirrors Origami's SSE event shapes since the backend
 * reuses run_origami_turn() under both routes (see backend commit a2ed485).
 *
 * Kept separate from Origami's types so the two surfaces can evolve
 * independently. If you change either side's event shape, update the
 * other to match — the backend emits the same vocabulary for both.
 */

import type { PlanCardData } from "../origami/PlanCard";

export type StudioSnapshot = {
  org_id: string;
  org_name: string | null;
  providers: Array<{ provider_type: string; status: string }>;
  agent_count: number;
  agent_active_count: number;
  kb_count: number;
  kb_total_documents: number;
  gateway: {
    requests_7d: number;
    cost_7d_usd: number;
    top_models: Array<{ model: string; requests: number }>;
  };
  billing: { tier: string; days_since_signup: number };
  project_count: number;
  generated_at: string;
};

export type StudioMessage = {
  id: string;
  role: "user" | "assistant" | "plan";
  text: string;
  streaming?: boolean;
  plan?: PlanCardData;
};

export type StudioEvent =
  | { type: "turn_started"; conversation_id?: string; session_id?: string; tier?: string }
  | { type: "message_token"; token: string }
  | { type: "message_complete"; text: string }
  | { type: "tool_started"; tool_name: string; tool_call_id?: string; step?: number; total?: number }
  | {
      type: "tool_completed";
      tool_name: string;
      tool_call_id?: string;
      step?: number;
      result_summary?: Record<string, unknown>;
    }
  | { type: "tool_failed"; tool_name: string; tool_call_id?: string; step?: number; error?: string; code?: string }
  | { type: "tool_retried"; tool_name: string; step?: number; repair: string }
  | { type: "plan_ready"; plan_card: PlanCardData }
  | { type: "awaiting_confirmation"; plan_card_id: string }
  | { type: "execution_started"; plan_card_id: string; total_steps: number }
  | {
      type: "execution_done";
      plan_card_id: string;
      status: string;
      failed_count: number;
      succeeded_count: number;
      results?: unknown[];
    }
  | { type: "done"; finish_reason?: string }
  | { type: "error"; code: string; message: string };
