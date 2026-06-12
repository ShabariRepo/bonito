"use client";

/**
 * useStudioSession — chat state for Bonito Studio.
 *
 * Wraps the same SSE event vocabulary as Origami (backend reuses
 * run_origami_turn) but POSTs to /api/studio/turn and additionally
 * fetches /api/studio/init on mount so the empty state can be
 * snapshot-aware ("you have 3 providers — want to spin up an agent?").
 *
 * Kept separate from useOrigamiSession so the surfaces can diverge —
 * Studio's BDR voice and snapshot-aware opener are first-class concerns
 * here that Origami's workspace doesn't share.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/auth";
import { API_URL } from "@/lib/utils";
import type { PlanCardData, PlanChange } from "../origami/PlanCard";
import type { StudioEvent, StudioMessage, StudioSnapshot } from "./types";

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function useStudioSession() {
  const [messages, setMessages] = useState<StudioMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [snapshot, setSnapshot] = useState<StudioSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(true);
  const [tier, setTier] = useState<string | null>(null);
  const [conversationId] = useState<string>(() => uid());
  const planCardIdToResources = useRef<Map<string, string[]>>(new Map());

  // ── Snapshot fetch on mount ───────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      const token = getAccessToken();
      if (!token) {
        setSnapshotLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_URL}/api/studio/init`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
        if (!res.ok) {
          setSnapshotLoading(false);
          return;
        }
        const data = (await res.json()) as StudioSnapshot;
        if (!cancelled) {
          setSnapshot(data);
          if (data.billing?.tier) setTier(data.billing.tier);
        }
      } catch {
        /* fail open — empty-state copy falls back to a generic opener */
      } finally {
        if (!cancelled) setSnapshotLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── SSE event dispatcher ──────────────────────────────────────────
  const dispatch = useCallback((ev: StudioEvent) => {
    switch (ev.type) {
      case "turn_started":
        if (ev.tier) setTier(ev.tier);
        break;

      case "message_token":
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last?.role === "assistant" && last.streaming) {
            return [...m.slice(0, -1), { ...last, text: last.text + ev.token }];
          }
          return [
            ...m,
            { id: uid(), role: "assistant", text: ev.token, streaming: true },
          ];
        });
        break;

      case "message_complete":
        setMessages((m) => {
          const last = m[m.length - 1];
          const finalText = (ev.text || "").trim();
          if (last?.role === "assistant" && last.streaming && !finalText) {
            return m.slice(0, -1);
          }
          if (last?.role === "assistant" && last.streaming) {
            return [
              ...m.slice(0, -1),
              { ...last, text: ev.text, streaming: false },
            ];
          }
          if (!finalText) return m;
          return [...m, { id: uid(), role: "assistant", text: ev.text }];
        });
        break;

      case "plan_ready": {
        const plan = ev.plan_card;
        setMessages((m) => [...m, { id: uid(), role: "plan", text: "", plan }]);
        const queuedIds: string[] = plan.changes
          .filter((c: PlanChange) => c.is_write !== false)
          .map((_, idx) => `pending-${plan.id}-${idx}`);
        planCardIdToResources.current.set(plan.id, queuedIds);
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
          {
            id: uid(),
            role: "assistant",
            text: `Hmm — ${ev.message} (${ev.code})`,
          },
        ]);
        break;

      // execution_started / tool_started / tool_completed / tool_failed /
      // tool_retried / execution_done / awaiting_confirmation are
      // surfaced through the PlanCard's own onEvent handler. Studio's
      // chat surface doesn't need to mirror them as message bubbles.
      default:
        break;
    }
  }, []);

  // ── Send a turn ───────────────────────────────────────────────────
  const send = useCallback(
    async (message: string) => {
      const trimmed = message.trim();
      if (!trimmed || busy) return;
      setMessages((m) => [...m, { id: uid(), role: "user", text: trimmed }]);
      setBusy(true);

      const token = getAccessToken();
      if (!token) {
        dispatch({
          type: "error",
          code: "no_auth",
          message: "You're not signed in.",
        });
        setBusy(false);
        return;
      }

      try {
        const res = await fetch(`${API_URL}/api/studio/turn`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            message: trimmed,
            conversation_id: conversationId,
          }),
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
              dispatch(JSON.parse(line.slice(6)) as StudioEvent);
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
    [busy, conversationId, dispatch],
  );

  const handleExternalEvent = useCallback(
    (ev: StudioEvent) => dispatch(ev),
    [dispatch],
  );

  return {
    messages,
    busy,
    snapshot,
    snapshotLoading,
    tier,
    conversationId,
    send,
    handleExternalEvent,
  };
}

export type StudioSessionAPI = ReturnType<typeof useStudioSession>;

// Re-exported here so consumers don't need to deep-import.
export type { PlanCardData };
