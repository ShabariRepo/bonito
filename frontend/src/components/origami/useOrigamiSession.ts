"use client";

/**
 * useOrigamiSession — single source of truth for the Origami workspace.
 *
 * Owns:
 * - chat messages (user / assistant / plan)
 * - resources being built (agents, KBs, projects, gateway keys)
 * - activity log (every tool call)
 * - current plan card + execution progress
 * - result preview after a deploy completes
 *
 * Exposes a `send(message)` function plus state slices the workspace
 * components render off of.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/auth";
import { API_URL } from "@/lib/utils";
import type { PlanCardData, PlanChange } from "./PlanCard";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "plan";
  text: string;
  streaming?: boolean;
  plan?: PlanCardData;
};

export type ResourceState = "queued" | "creating" | "done" | "error";

export type Resource = {
  id: string;                  // local id until real one assigned
  type: "agent" | "kb" | "project" | "gateway_key" | "link" | "unknown";
  name: string;
  state: ResourceState;
  realId?: string;             // populated when tool succeeds
  meta?: Record<string, unknown>;
  error?: string;
};

export type ActivityEntry = {
  id: string;
  tool: string;
  status: "running" | "success" | "error";
  startedAt: number;
  completedAt?: number;
  summary?: Record<string, unknown>;
  error?: string;
};

export type ExecutionProgress = {
  planCardId: string;
  totalSteps: number;
  currentStep: number;
} | null;

export type ResultPreview = {
  planCardId: string;
  status: "success" | "partial" | "failed";
  succeeded: number;
  failed: number;
  resources: Resource[];
} | null;

export type OrigamiEvent =
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
  | { type: "plan_ready"; plan_card: PlanCardData }
  | { type: "awaiting_confirmation"; plan_card_id: string }
  | { type: "execution_started"; plan_card_id: string; total_steps: number }
  | { type: "execution_done"; plan_card_id: string; status: string; failed_count: number; succeeded_count: number; results?: unknown[] }
  | { type: "done"; finish_reason?: string }
  | { type: "error"; code: string; message: string };

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

/** Map a tool name to the kind of resource it produces. Used to drive the Resources grid. */
function resourceTypeFor(toolName: string): Resource["type"] {
  switch (toolName) {
    case "create_agent":
    case "update_agent":
      return "agent";
    case "create_kb":
    case "upload_to_kb":
      return "kb";
    case "create_project":
      return "project";
    case "mint_gateway_key":
      return "gateway_key";
    case "link_kb_to_agent":
      return "link";
    default:
      return "unknown";
  }
}

function nameFromParams(action: string, params: Record<string, unknown>): string {
  if (typeof params.name === "string" && params.name) return params.name as string;
  if (action === "link_kb_to_agent") return `link KB ↔ agent`;
  if (action === "upload_to_kb") {
    const docs = params.documents;
    if (Array.isArray(docs)) return `upload ${docs.length} doc${docs.length === 1 ? "" : "s"}`;
  }
  if (action === "delegate_provider_connection" && typeof params.provider_type === "string") {
    return `connect ${params.provider_type}`;
  }
  if (action === "update_agent") return `update agent`;
  return action;
}

export function useOrigamiSession() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [execution, setExecution] = useState<ExecutionProgress>(null);
  const [result, setResult] = useState<ResultPreview>(null);
  const [busy, setBusy] = useState(false);
  const [tier, setTier] = useState<string | null>(null);
  const [conversationId] = useState<string>(() => uid());

  // Stable ref so handlers don't churn
  const planCardIdToResources = useRef<Map<string, string[]>>(new Map());

  function dispatch(ev: OrigamiEvent) {
    switch (ev.type) {
      case "turn_started":
        if (ev.tier) setTier(ev.tier);
        setResult(null);
        break;

      case "message_token":
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last?.role === "assistant" && last.streaming) {
            return [...m.slice(0, -1), { ...last, text: last.text + ev.token }];
          }
          return [...m, { id: uid(), role: "assistant", text: ev.token, streaming: true }];
        });
        break;

      case "message_complete":
        setMessages((m) => {
          const last = m[m.length - 1];
          const finalText = (ev.text || "").trim();
          // If the entire streamed message was raw tool-call markup that the
          // orchestrator stripped, drop the streaming bubble entirely. Without
          // this, users see leftover <tool_call>…</tool_call> text.
          if (last?.role === "assistant" && last.streaming && !finalText) {
            return m.slice(0, -1);
          }
          if (last?.role === "assistant" && last.streaming) {
            return [...m.slice(0, -1), { ...last, text: ev.text, streaming: false }];
          }
          if (!finalText) return m;
          return [...m, { id: uid(), role: "assistant", text: ev.text }];
        });
        break;

      case "plan_ready": {
        const plan = ev.plan_card;
        setMessages((m) => [...m, { id: uid(), role: "plan", text: "", plan }]);
        // Pre-populate the Resources grid as queued cards.
        const queuedIds: string[] = [];
        const newResources: Resource[] = plan.changes
          .filter((c: PlanChange) => c.is_write !== false)
          .map((c, idx) => {
            const localId = `pending-${plan.id}-${idx}`;
            queuedIds.push(localId);
            return {
              id: localId,
              type: resourceTypeFor(c.action),
              name: nameFromParams(c.action, c.params),
              state: "queued",
              meta: { action: c.action, step: idx },
            };
          });
        planCardIdToResources.current.set(plan.id, queuedIds);
        setResources((r) => [...r, ...newResources]);
        break;
      }

      case "awaiting_confirmation":
        break;

      case "execution_started":
        setExecution({
          planCardId: ev.plan_card_id,
          totalSteps: ev.total_steps,
          currentStep: 0,
        });
        break;

      case "tool_started": {
        const stepIdx = ev.step;
        // During execute_plan: mark the matching pending resource as creating
        setResources((rs) =>
          rs.map((r) => {
            if (r.state !== "queued") return r;
            const meta = r.meta as { action?: string; step?: number } | undefined;
            const actionMatches = meta?.action === ev.tool_name;
            const stepMatches = stepIdx === undefined || meta?.step === stepIdx;
            if (actionMatches && stepMatches) {
              return { ...r, state: "creating" };
            }
            return r;
          }),
        );
        setExecution((exec) =>
          exec ? { ...exec, currentStep: (ev.step ?? exec.currentStep) + 1 } : exec,
        );
        const actId = ev.tool_call_id ?? `step-${ev.step ?? Date.now()}`;
        setActivity((a) => [
          ...a,
          { id: actId, tool: ev.tool_name, status: "running", startedAt: Date.now() },
        ]);
        break;
      }

      case "tool_completed": {
        const stepIdx = ev.step;
        setResources((rs) =>
          rs.map((r) => {
            const meta = r.meta as { action?: string; step?: number } | undefined;
            const actionMatches = meta?.action === ev.tool_name;
            const stepMatches = stepIdx === undefined || meta?.step === stepIdx;
            if (r.state === "creating" && actionMatches && stepMatches) {
              const summary = ev.result_summary || {};
              const realId =
                (summary["agent_id"] as string) ||
                (summary["kb_id"] as string) ||
                (summary["project_id"] as string) ||
                (summary["key_id"] as string);
              return {
                ...r,
                state: "done",
                realId,
                meta: { ...(r.meta || {}), summary },
              };
            }
            return r;
          }),
        );
        const actId = ev.tool_call_id ?? `step-${ev.step}`;
        setActivity((a) =>
          a.map((entry) =>
            entry.id === actId || (entry.tool === ev.tool_name && entry.status === "running")
              ? {
                  ...entry,
                  status: "success",
                  completedAt: Date.now(),
                  summary: ev.result_summary,
                }
              : entry,
          ),
        );
        break;
      }

      case "tool_failed": {
        const stepIdx = ev.step;
        setResources((rs) =>
          rs.map((r) => {
            const meta = r.meta as { action?: string; step?: number } | undefined;
            const actionMatches = meta?.action === ev.tool_name;
            const stepMatches = stepIdx === undefined || meta?.step === stepIdx;
            if ((r.state === "creating" || r.state === "queued") && actionMatches && stepMatches) {
              return { ...r, state: "error", error: ev.error };
            }
            return r;
          }),
        );
        const actId = ev.tool_call_id ?? `step-${ev.step}`;
        setActivity((a) =>
          a.map((entry) =>
            entry.id === actId || (entry.tool === ev.tool_name && entry.status === "running")
              ? { ...entry, status: "error", completedAt: Date.now(), error: ev.error }
              : entry,
          ),
        );
        break;
      }

      case "execution_done": {
        const overallStatus =
          ev.status === "success" ? "success" : ev.status === "partial" ? "partial" : "failed";
        // Build the result preview from the resources tied to this plan
        const resourceIds = planCardIdToResources.current.get(ev.plan_card_id) || [];
        setResources((current) => {
          const tied = current.filter((r) => resourceIds.includes(r.id));
          setResult({
            planCardId: ev.plan_card_id,
            status: overallStatus,
            succeeded: ev.succeeded_count,
            failed: ev.failed_count,
            resources: tied,
          });
          return current;
        });
        setExecution(null);
        break;
      }

      case "done":
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last?.role === "assistant" && last.streaming) {
            return [...m.slice(0, -1), { ...last, streaming: false }];
          }
          return m;
        });
        break;

      case "error":
        setMessages((m) => [
          ...m,
          { id: uid(), role: "assistant", text: `Origami error (${ev.code}): ${ev.message}` },
        ]);
        break;
    }
  }

  const send = useCallback(
    async (message: string) => {
      const trimmed = message.trim();
      if (!trimmed || busy) return;
      setMessages((m) => [...m, { id: uid(), role: "user", text: trimmed }]);
      setBusy(true);

      const token = getAccessToken();
      if (!token) {
        dispatch({ type: "error", code: "no_auth", message: "You're not signed in." });
        setBusy(false);
        return;
      }

      try {
        const res = await fetch(`${API_URL}/api/origami/turn`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ message: trimmed, conversation_id: conversationId }),
        });
        if (!res.ok || !res.body) {
          const txt = await res.text();
          dispatch({
            type: "error",
            code: `http_${res.status}`,
            message: txt.slice(0, 200),
          });
          setBusy(false);
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const parts = buf.split("\n\n");
          buf = parts.pop() ?? "";
          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith("data: ")) continue;
            try {
              dispatch(JSON.parse(line.slice(6)) as OrigamiEvent);
            } catch {
              /* skip bad chunk */
            }
          }
        }
      } catch (e) {
        dispatch({
          type: "error",
          code: "network",
          message: e instanceof Error ? e.message : String(e),
        });
      } finally {
        setBusy(false);
      }
    },
    [busy, conversationId],
  );

  // Re-export dispatch for the PlanCard's execute_plan stream
  const handleExternalEvent = useCallback((ev: OrigamiEvent) => dispatch(ev), []);

  return {
    messages,
    resources,
    activity,
    execution,
    result,
    busy,
    tier,
    conversationId,
    send,
    handleExternalEvent,
  };
}
