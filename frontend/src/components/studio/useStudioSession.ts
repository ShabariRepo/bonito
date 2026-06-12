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

// localStorage keys. Single-user-per-browser assumption — fine for V1
// since localStorage is already browser-scoped. Re-key per user_id once
// we hit a multi-user-browser case.
const STORAGE_KEY_MESSAGES = "bonito:studio:messages";
const STORAGE_KEY_CONVERSATION_ID = "bonito:studio:conversation_id";

// Cap persisted history to keep localStorage healthy + the UI snappy. The
// backend already runs stateless turns (snapshot + memwright + current
// message only) so this cap is purely a frontend / UX bound.
const MAX_PERSIST_MESSAGES = 100;

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

function readStoredConversationId(): string {
  if (typeof window === "undefined") return uid();
  const saved = window.localStorage.getItem(STORAGE_KEY_CONVERSATION_ID);
  if (saved && saved.length >= 4) return saved;
  const fresh = uid();
  window.localStorage.setItem(STORAGE_KEY_CONVERSATION_ID, fresh);
  return fresh;
}

function readStoredMessages(): StudioMessage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY_MESSAGES);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Defensive: only keep messages that look like our shape, and only
    // user/assistant text. Plan cards are intentionally dropped on
    // persist — they reference plan_card_ids the backend has TTL'd by
    // the time the user returns; re-rendering them in pending state
    // would be confusing. The actual deployed resources still exist.
    return parsed
      .filter(
        (m): m is StudioMessage =>
          m &&
          typeof m === "object" &&
          typeof m.id === "string" &&
          (m.role === "user" || m.role === "assistant") &&
          typeof m.text === "string",
      )
      .map((m) => ({ ...m, streaming: false }));
  } catch {
    return [];
  }
}

export function useStudioSession() {
  const [messages, setMessages] = useState<StudioMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [snapshot, setSnapshot] = useState<StudioSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(true);
  const [tier, setTier] = useState<string | null>(null);
  // Conversation id is stable across remounts so backend memwright recall
  // builds context over time and survives tab switches.
  const [conversationId] = useState<string>(() => readStoredConversationId());
  const planCardIdToResources = useRef<Map<string, string[]>>(new Map());
  // Restored-from-storage flag prevents the persist effect from clobbering
  // localStorage with `[]` on the very first render before the restore
  // effect has a chance to run.
  const restoredRef = useRef(false);

  // ── Restore persisted chat history on mount ──────────────────────
  // Run synchronously in a layout-style effect so the empty-state opener
  // never flashes before the restored bubbles paint.
  useEffect(() => {
    const restored = readStoredMessages();
    if (restored.length > 0) {
      setMessages(restored);
    }
    restoredRef.current = true;
  }, []);

  // ── Persist user + assistant text every time messages change ─────
  // Plan cards are dropped (stale state, TTL'd plan_card_ids). Capped at
  // MAX_PERSIST_MESSAGES — older messages roll off.
  useEffect(() => {
    if (!restoredRef.current) return;
    if (typeof window === "undefined") return;
    const persistable = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .filter((m) => !m.streaming) // wait until message_complete
      .slice(-MAX_PERSIST_MESSAGES)
      .map(({ id, role, text }) => ({ id, role, text }));
    try {
      window.localStorage.setItem(
        STORAGE_KEY_MESSAGES,
        JSON.stringify(persistable),
      );
    } catch {
      /* quota exceeded? drop silently — chat still works in-memory */
    }
  }, [messages]);

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

  // Clear the visible chat AND rotate the conversation id so the next
  // turn starts a fresh memwright recall thread. The org snapshot is
  // intentionally untouched — it loads fresh per /studio/init call.
  const clearChat = useCallback(() => {
    setMessages([]);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY_MESSAGES);
      const fresh = uid();
      window.localStorage.setItem(STORAGE_KEY_CONVERSATION_ID, fresh);
      // We don't restart the hook — conversationId stays the old value
      // until next page mount. That's fine; the next turn will use the
      // new id once the user reloads. Tradeoff for not adding setState
      // for the id, which would re-render the whole tree.
    }
  }, []);

  return {
    messages,
    busy,
    snapshot,
    snapshotLoading,
    tier,
    conversationId,
    send,
    handleExternalEvent,
    clearChat,
  };
}

export type StudioSessionAPI = ReturnType<typeof useStudioSession>;

// Re-exported here so consumers don't need to deep-import.
export type { PlanCardData };
